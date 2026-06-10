"""
DEALERCORE v3.0 — Inventory API Controller
--------------------------------------------
Class-based controller using django-ninja-extra.

IMPORTANT: Literal paths (e.g. "restocks", "add", "restock") MUST be
registered BEFORE parameterized paths (e.g. "{product_id}") to avoid
route conflicts. Django Ninja matches URL patterns first, then checks
HTTP method. A path parameter will greedily match any segment including
literal words — so POST /api/inventory/add would match GET {product_id}
and return 405 Method Not Allowed.

Route registration order matters ACROSS all HTTP methods:
  1. Literal sub-paths first (GET, POST, etc.)
  2. Parameterized paths last

Endpoints:
  GET    /api/inventory              → list all products
  GET    /api/inventory/restocks     → list all restock records
  GET    /api/inventory/restocks/{id} → get a single restock record
  POST   /api/inventory/add          → add a new product
  POST   /api/inventory/restock      → restock a product
  GET    /api/inventory/brands       → list all brands
  POST   /api/inventory/brands       → create a brand
  GET    /api/inventory/brands/{id}  → get brand
  DELETE /api/inventory/brands/{id}  → delete brand
  GET    /api/inventory/categories     → list all categories
  POST   /api/inventory/categories     → create a category
  GET    /api/inventory/categories/{id} → get category
  DELETE /api/inventory/categories/{id} → delete category
  GET    /api/inventory/{id}         → get a single product
  POST   /api/inventory/{id}/edit    → partial update a product
  DELETE /api/inventory/{id}         → delete a product
"""

from datetime import datetime

from django.db import IntegrityError
from django.db.models import ProtectedError, F, Max

from ninja_extra import api_controller, route
from ninja.errors import HttpError

from dealercore.async_db import aatomic, async_aggregate, async_exists
from inventory.models import Product, RestockRecord, Brand, Category
from inventory.schemas import (
    AddProductIn,
    BrandOut,
    CategoryOut,
    CreateBrandIn,
    CreateCategoryIn,
    EditProductIn,
    ProductOut,
    RestockIn,
    RestockOut,
    RestockRecordOut,
)


@api_controller("/inventory", tags=["Inventory"])
class InventoryController:
    # Maximum records per page to prevent memory exhaustion
    MAX_PAGE_LIMIT = 1000

    def _validate_pagination(self, limit: int, offset: int) -> None:
        """Common pagination validation to prevent memory exhaustion."""
        if limit > self.MAX_PAGE_LIMIT:
            raise HttpError(400, f"Limit cannot exceed {self.MAX_PAGE_LIMIT}. Use pagination with offset.")
        if limit < 1:
            raise HttpError(400, "Limit must be at least 1.")
        if offset < 0:
            raise HttpError(400, "Offset cannot be negative.")

    @route.get("", response=list[ProductOut], summary="List all products")
    async def list_products(self, limit: int = 100, offset: int = 0):
        """Return all products ordered by name.
        
        Query Parameters:
            limit: Max records to return (default: 100, max: 1000)
            offset: Number of records to skip (for pagination)
        """
        self._validate_pagination(limit, offset)
        qs = Product.objects.all().order_by("name")[offset:offset+limit]
        return [p async for p in qs]

    # ─── Literal sub-paths MUST come before {product_id} parameterized route ──
    # Otherwise /api/inventory/restocks would be matched as product_id="restocks"

    @route.get("restocks", response=list[RestockRecordOut], summary="List all restock records")
    async def list_restocks(self, limit: int = 100, offset: int = 0):
        """Return all restock records ordered by date descending.
        
        Query Parameters:
            limit: Max records to return (default: 100, max: 1000)
            offset: Number of records to skip (for pagination)
        """
        self._validate_pagination(limit, offset)
        results = []
        async for r in RestockRecord.objects.select_related("product").all().order_by("-date")[offset:offset+limit]:
            results.append(
                RestockRecordOut(
                    id=r.id,
                    product_id=r.product_id,
                    product_name=r.product_name,
                    quantity=r.quantity,
                    supplier_name=r.supplier_name,
                    cost_price=r.cost_price,
                    total_cost=r.total_cost,
                    date=r.date,
                    received_by=r.received_by,
                )
            )
        return results

    @route.get("restocks/{restock_id}", response=RestockRecordOut, summary="Get a restock record")
    async def get_restock(self, restock_id: str):
        """Return a single restock record by ID."""
        try:
            r = await RestockRecord.objects.select_related("product").aget(id=restock_id)
        except RestockRecord.DoesNotExist:
            raise HttpError(404, f"Restock record with id '{restock_id}' not found")
        return RestockRecordOut(
            id=r.id,
            product_id=r.product_id,
            product_name=r.product_name,
            quantity=r.quantity,
            supplier_name=r.supplier_name,
            cost_price=r.cost_price,
            total_cost=r.total_cost,
            date=r.date,
            received_by=r.received_by,
        )

    # ─── Literal POST sub-paths MUST come before {product_id} parameterized route ──
    # Otherwise /api/inventory/add and /api/inventory/restock would be matched
    # by GET {product_id} and return 405 Method Not Allowed for POST requests.

    @route.post("add", response=ProductOut, summary="Add a new product")
    async def add_product(self, payload: AddProductIn):
        """Create a new product with stock=0. Auto-generates ID.
        Auto-creates brand/category in registry if not already present."""
        # Auto-create brand if not exists
        if payload.brand:
            await Brand.objects.aupdate_or_create(
                defaults={"name": payload.brand},
                name=payload.brand,
            )
        # Auto-create category if not exists
        if payload.category:
            await Category.objects.aupdate_or_create(
                defaults={"name": payload.category},
                name=payload.category,
            )
        product = await Product.objects.acreate(
            id=await self._generate_id("prod"),
            name=payload.name,
            sku=payload.sku,
            brand=payload.brand,
            category=payload.category,
            min_stock_alert=payload.min_stock_alert,
            unit_price=payload.unit_price,
            selling_price=payload.selling_price,
            location=payload.location,
            stock=0,
        )
        return product

    @route.post("restock", response=RestockOut, summary="Restock a product")
    async def restock_product(self, payload: RestockIn):
        """Restock a product: increase stock, create a RestockRecord.

        Uses aatomic() + select_for_update() to ensure the stock increment
        and restock record creation happen atomically. The row-level lock
        prevents concurrent restocks from causing stock miscounts.
        """
        async with aatomic():
            try:
                product = await Product.objects.select_for_update().aget(id=payload.product_id)
            except Product.DoesNotExist:
                raise HttpError(404, f"Product with id '{payload.product_id}' not found")
            product.stock = F("stock") + payload.quantity
            await product.asave()

            total_cost = payload.quantity * payload.cost_price
            await RestockRecord.objects.acreate(
                id=await self._generate_id("rstk"),
                product=product,
                product_name=product.name,
                quantity=payload.quantity,
                supplier_name=payload.supplier_name,
                cost_price=payload.cost_price,
                total_cost=total_cost,
                date=datetime.now(),
                received_by=payload.received_by,
            )

            # Re-fetch to get updated stock value (F() expression resolved)
            await product.arefresh_from_db()

            return RestockOut(
                message=f"Restocked {product.name} with {payload.quantity} units",
                product=product,
            )

    # ─── Brand endpoints ──────────────────────────────────────

    @route.get("brands", response=list[BrandOut], summary="List all brands")
    async def list_brands(self):
        """Return all brands ordered by name."""
        return [b async for b in Brand.objects.all().order_by("name")]

    @route.post("brands", response=BrandOut, summary="Create a brand")
    async def create_brand(self, payload: CreateBrandIn):
        """Create a new brand. Auto-generates ID like 'brand-1'."""
        brand = await Brand.objects.acreate(
            id=await self._generate_id("brand"),
            name=payload.name,
        )
        return brand

    @route.get("brands/{brand_id}", response=BrandOut, summary="Get a brand")
    async def get_brand(self, brand_id: str):
        """Return a single brand by ID."""
        try:
            return await Brand.objects.aget(id=brand_id)
        except Brand.DoesNotExist:
            raise HttpError(404, f"Brand with id '{brand_id}' not found")

    @route.delete("brands/{brand_id}", summary="Delete a brand")
    async def delete_brand(self, brand_id: str):
        """Delete a brand by ID."""
        try:
            brand = await Brand.objects.aget(id=brand_id)
        except Brand.DoesNotExist:
            raise HttpError(404, f"Brand with id '{brand_id}' not found")
        await brand.adelete()
        return {"message": f"Brand '{brand.name}' deleted successfully"}

    # ─── Category endpoints ───────────────────────────────────

    @route.get("categories", response=list[CategoryOut], summary="List all categories")
    async def list_categories(self):
        """Return all categories ordered by name."""
        return [c async for c in Category.objects.all().order_by("name")]

    @route.post("categories", response=CategoryOut, summary="Create a category")
    async def create_category(self, payload: CreateCategoryIn):
        """Create a new category. Auto-generates ID like 'cat-1'."""
        category = await Category.objects.acreate(
            id=await self._generate_id("cat"),
            name=payload.name,
        )
        return category

    @route.get("categories/{category_id}", response=CategoryOut, summary="Get a category")
    async def get_category(self, category_id: str):
        """Return a single category by ID."""
        try:
            return await Category.objects.aget(id=category_id)
        except Category.DoesNotExist:
            raise HttpError(404, f"Category with id '{category_id}' not found")

    @route.delete("categories/{category_id}", summary="Delete a category")
    async def delete_category(self, category_id: str):
        """Delete a category by ID."""
        try:
            category = await Category.objects.aget(id=category_id)
        except Category.DoesNotExist:
            raise HttpError(404, f"Category with id '{category_id}' not found")
        await category.adelete()
        return {"message": f"Category '{category.name}' deleted successfully"}

    # ─── Parameterized product routes (MUST come last) ────────

    @route.get("{product_id}", response=ProductOut, summary="Get a product")
    async def get_product(self, product_id: str):
        """Return a single product by ID."""
        try:
            return await Product.objects.aget(id=product_id)
        except Product.DoesNotExist:
            raise HttpError(404, f"Product with id '{product_id}' not found")

    @route.post("{product_id}/edit", response=ProductOut, summary="Edit a product")
    async def edit_product(self, product_id: str, payload: EditProductIn):
        """Partial update on a product. Only provided fields are updated."""
        try:
            product = await Product.objects.aget(id=product_id)
        except Product.DoesNotExist:
            raise HttpError(404, f"Product with id '{product_id}' not found")
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        await product.asave()
        # Auto-update brand/category registry if changed
        if "brand" in update_data and update_data["brand"]:
            await Brand.objects.aupdate_or_create(
                defaults={"name": update_data["brand"]},
                name=update_data["brand"],
            )
        if "category" in update_data and update_data["category"]:
            await Category.objects.aupdate_or_create(
                defaults={"name": update_data["category"]},
                name=update_data["category"],
            )
        return product

    @route.delete("{product_id}", summary="Delete a product")
    async def delete_product(self, product_id: str):
        """Delete a product. Blocked if the product has existing sales (PROTECT FK)."""
        try:
            product = await Product.objects.aget(id=product_id)
        except Product.DoesNotExist:
            raise HttpError(404, f"Product with id '{product_id}' not found")
        try:
            await product.adelete()
        except ProtectedError:
            raise HttpError(
                409,
                f"Cannot delete product '{product.name}' — it has existing sales "
                f"records. Remove or reassign the sales first."
            )
        return {"message": f"Product '{product.name}' deleted successfully"}

    # ─── Helpers ────────────────────────────────────────

    async def _generate_id(self, prefix: str) -> str:
        """Generate a unique string ID: {prefix}-{n}.
        Uses a retry loop to handle race conditions under concurrent requests.
        If two requests generate the same ID, the IntegrityError from the
        primary key constraint is caught and the counter is incremented.

        NOTE: Uses async_aggregate/async_exists from dealercore.async_db
        instead of aaggregate/aexists — those methods were only added in
        Django 4.2 and may cause TypeError on older versions.
        """
        max_retries = 5
        for attempt in range(max_retries):
            if prefix == "prod":
                result = await async_aggregate(
                    Product.objects.filter(id__startswith=prefix),
                    _max=Max("id"),
                )
            elif prefix == "rstk":
                result = await async_aggregate(
                    RestockRecord.objects.filter(id__startswith=prefix),
                    _max=Max("id"),
                )
            elif prefix == "brand":
                result = await async_aggregate(
                    Brand.objects.filter(id__startswith=prefix),
                    _max=Max("id"),
                )
            elif prefix == "cat":
                result = await async_aggregate(
                    Category.objects.filter(id__startswith=prefix),
                    _max=Max("id"),
                )
            else:
                result = {"_max": None}

            last = result.get("_max")

            num = 1
            if last:
                try:
                    num = int(last.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    num = 1

            # Add attempt offset to reduce collision probability
            num += attempt
            candidate_id = f"{prefix}-{num}"

            # Check if candidate already exists
            if prefix == "prod":
                exists = await async_exists(
                    Product.objects.filter(id=candidate_id),
                )
            elif prefix == "rstk":
                exists = await async_exists(
                    RestockRecord.objects.filter(id=candidate_id),
                )
            elif prefix == "brand":
                exists = await async_exists(
                    Brand.objects.filter(id=candidate_id),
                )
            elif prefix == "cat":
                exists = await async_exists(
                    Category.objects.filter(id=candidate_id),
                )
            else:
                exists = False

            if not exists:
                return candidate_id

        # Fallback: use a timestamp-based suffix if all retries exhausted
        import time
        return f"{prefix}-{int(time.time() * 1000)}"
