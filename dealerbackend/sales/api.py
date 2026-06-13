"""
DEALERCORE v3.0 — Sales API Controller
-----------------------------------------
Class-based controller using django-ninja-extra.

IMPORTANT: Literal paths (e.g. "bulk") MUST be registered BEFORE
parameterized paths (e.g. "{sale_id}") to avoid route conflicts.
Django Ninja matches URL patterns first, then checks HTTP method.

Route registration order matters ACROSS all HTTP methods:
  1. Literal sub-paths first (POST, GET, etc.)
  2. Parameterized paths last

MULTI-TENANCY:
  All endpoints are scoped to the dealer context extracted from JWT.
  - Dealers see only their own data
  - DSRs/Collectors see data from their assigned dealer (via X-Dealer-Context header)

Endpoints:
  GET    /api/sales                   → list all sales (dealer-scoped)
  POST   /api/sales                   → create a single sale
  POST   /api/sales/bulk              → create multiple sales at once
  GET    /api/sales/{id}              → get a single sale
  POST   /api/sales/{id}/collect      → collect payment on a credit sale
  POST   /api/sales/{id}/close-with-due → close a sale with outstanding due
  POST   /api/sales/{id}/return       → process a product return
  POST   /api/sales/{id}/void         → void a sale
  POST   /api/sales/{id}/edit         → edit non-financial fields + DSR reassignment

BUSINESS RULES:
  - Returns: Adjust sale's return_total_amount + recalculate collection_status
             based on net_amount (= total_amount - return_total_amount).
             If net_amount <= amount_paid → status becomes "Fully Paid".
  - Void:    Complete reversal — restores stock, sets is_voided=True,
             status="Voided". Voided sales excluded from all reports/revenue.
  - Write-off: Sets is_closed_with_due=True, status="Written Off".
             Written-off sales excluded from revenue but reported separately.
  - DSR edit: Changing dsr_id reassigns CURRENT collector only.
             original_dsr (who made the sale) is NEVER changed after creation.
"""

from datetime import datetime, date
from decimal import Decimal

from django.db.models import F, Max, Sum

from ninja_extra import api_controller, route
from ninja.errors import HttpError

from dealercore.async_db import aatomic, async_aggregate, async_exists
from common.dealer_context import get_dealer_context
from dealer.models import DealerConfig
from inventory.models import Product
from dsr.models import DSR
from sales.models import SaleRecord, CreditPayment, SaleReturn
from sales.schemas import (
    BulkSaleIn,
    CollectPaymentIn,
    CreateReturnIn,
    EditSaleIn,
    CreateSaleIn,
    SaleRecordOut,
    SaleReturnOut,
    CreditPaymentOut,
)


@api_controller("/sales", tags=["Sales"])
class SalesController:

    # Maximum records per page to prevent memory exhaustion
    MAX_PAGE_LIMIT = 1000

    @route.get("", response=list[SaleRecordOut], summary="List all sales")
    async def list_sales(self, request, limit: int = 100, offset: int = 0):
        """Return all sales for the current dealer context ordered by date descending.
        
        Query Parameters:
            limit: Max records to return (default: 100, max: 1000)
            offset: Number of records to skip (for pagination)
        """
        # Enforce maximum limit to prevent memory issues
        if limit > self.MAX_PAGE_LIMIT:
            raise HttpError(400, f"Limit cannot exceed {self.MAX_PAGE_LIMIT}. Use pagination with offset.")
        if limit < 1:
            raise HttpError(400, "Limit must be at least 1.")
        if offset < 0:
            raise HttpError(400, "Offset cannot be negative.")
        dealer_username = await get_dealer_context(request)
        return await self._list_sales_qs(dealer_username, limit, offset)

    # ─── Literal POST sub-paths MUST come before {sale_id} parameterized route ──

    @route.post("", response=SaleRecordOut, summary="Create a sale")
    async def create_sale(self, request, payload: CreateSaleIn):
        """Create a single sale. Decreases product stock, handles cash/credit logic.
        Sets original_dsr = dsr at creation time (immutable thereafter).
        
        The sale is automatically associated with the current dealer context.
        """
        dealer_username = await get_dealer_context(request)
        async with aatomic():
            return await self._process_single_sale(request, payload, dealer_username)

    @route.post("bulk", response=list[SaleRecordOut], summary="Create bulk sales")
    async def create_bulk_sales(self, request, payload: BulkSaleIn):
        """Create multiple sales in one transaction. Shares vehicle_number and dsr_id.
        
        All sales are automatically associated with the current dealer context.
        """
        dealer_username = await get_dealer_context(request)
        
        # Validate due_date required for credit sales at bulk level
        for idx, row in enumerate(payload.rows):
            if row.payment_type == SaleRecord.PAYMENT_CREDIT and not row.due_date:
                raise HttpError(
                    400, 
                    f"Row {idx + 1}: Credit sales require a due_date. "
                    f"Set due_date for {row.customer_name or 'this sale'}."
                )
        
        async with aatomic():
            results = []
            for row in payload.rows:
                sale_data = CreateSaleIn(
                    product_id=row.product_id,
                    quantity=row.quantity,
                    customer_name=row.customer_name,
                    customer_phone=row.customer_phone,
                    is_vehicle=payload.vehicle_number.strip() != "",
                    vehicle_number=payload.vehicle_number.strip() if payload.vehicle_number.strip() else None,
                    dsr_id=payload.dsr_id,
                    payment_type=row.payment_type,
                    amount_paid=row.amount_paid,
                    due_date=row.due_date,
                )
                sale = await self._process_single_sale(request, sale_data, dealer_username, is_bulk=True)
                results.append(sale)
            return results

    @route.get("{sale_id}", response=SaleRecordOut, summary="Get a sale")
    async def get_sale(self, request, sale_id: str):
        """Return a single sale by ID with its embedded payments and returns (dealer-scoped)."""
        dealer_username = await get_dealer_context(request)
        try:
            sale = await SaleRecord.objects.prefetch_related("payments", "returns").aget(
                id=sale_id,
                dealer_id=dealer_username
            )
        except SaleRecord.DoesNotExist:
            raise HttpError(404, f"Sale with id '{sale_id}' not found")
        return await self._serialize_sale(sale)

    @route.post("{sale_id}/collect", response=SaleRecordOut, summary="Collect payment")
    async def collect_payment(self, request, sale_id: str, payload: CollectPaymentIn):
        """Collect a payment against a credit sale. Updates amount_paid and status.

        Uses select_for_update() on the sale row to prevent concurrent
        collection requests from causing incorrect amount_paid totals.
        Collection status is recalculated against net_amount (after returns).
        """
        dealer_username = await get_dealer_context(request)
        async with aatomic():
            try:
                sale = await SaleRecord.objects.select_for_update().prefetch_related("payments", "returns").aget(
                    id=sale_id,
                    dealer_id=dealer_username
                )
            except SaleRecord.DoesNotExist:
                raise HttpError(404, f"Sale with id '{sale_id}' not found")

            if sale.is_voided:
                raise HttpError(400, "Cannot collect payment on a voided sale")
            if sale.is_closed_with_due:
                raise HttpError(400, "Cannot collect payment on a written-off sale")

            await CreditPayment.objects.acreate(
                id=await self._generate_id("pay", dealer_username),
                sale=sale,
                amount=payload.amount,
                date=datetime.now(),
                received_by=payload.received_by,
            )

            sale.amount_paid = F("amount_paid") + payload.amount
            await sale.asave(update_fields=["amount_paid", "updated_at"])
            await sale.arefresh_from_db()

            # Recalculate status against net_amount (after returns)
            sale.collection_status = self._calc_collection_status(
                float(sale.net_amount), float(sale.amount_paid)
            )
            await sale.asave(update_fields=["collection_status", "updated_at"])

            return await self._serialize_sale(sale)

    @route.post(
        "{sale_id}/close-with-due", response=SaleRecordOut, summary="Close sale with due"
    )
    async def close_sale_with_due(self, request, sale_id: str):
        """Write off a sale as bad debt. Sets is_closed_with_due flag (dealer-scoped).

        COMPLETE CIRCLE:
        - Sets is_closed_with_due = True
        - Sets collection_status = "Written Off"
        - Written-off sales are EXCLUDED from:
          * Revenue calculations (reports)
          * Credit pending / credit collected metrics
          * DSR performance (total_sales, collected)
          * Vehicle tracking pending amounts
          * Customer due reports
        - Written-off outstanding is reported SEPARATELY for transparency

        Uses select_for_update() to prevent race conditions with concurrent
        collection requests on the same sale.
        """
        dealer_username = await get_dealer_context(request)
        async with aatomic():
            try:
                sale = await SaleRecord.objects.select_for_update().prefetch_related("payments", "returns").aget(
                    id=sale_id,
                    dealer_id=dealer_username
                )
            except SaleRecord.DoesNotExist:
                raise HttpError(404, f"Sale with id '{sale_id}' not found")

            if sale.is_voided:
                raise HttpError(400, "Cannot close a voided sale with due")
            if sale.is_closed_with_due:
                raise HttpError(400, "Sale is already written off")

            sale.is_closed_with_due = True
            sale.collection_status = SaleRecord.STATUS_WRITTEN_OFF
            await sale.asave()
            return await self._serialize_sale(sale)

    @route.post("{sale_id}/return", response=SaleRecordOut, summary="Process a sale return")
    async def process_return(self, request, sale_id: str, payload: CreateReturnIn):
        """Process a product return from a sale (dealer-scoped).

        COMPLETE CIRCLE:
        1. Increments product stock (inventory corrected)
        2. Creates SaleReturn record (audit trail preserved)
        3. Updates sale.return_total_amount (cumulative returns)
        4. Recalculates collection_status against net_amount
           - If net_amount <= amount_paid → "Fully Paid"
           - If amount_paid == 0 and net_amount > 0 → "Pending"
           - Otherwise → "Partial"
        5. If sale was written-off and returns bring net_amount <= amount_paid,
           the write-off flag remains (it's a historical record), but status
           reflects the actual state.

        Uses aatomic() + select_for_update() for safe concurrent access.
        """
        dealer_username = await get_dealer_context(request)
        async with aatomic():
            try:
                sale = await SaleRecord.objects.select_for_update().prefetch_related("payments", "returns").aget(
                    id=sale_id,
                    dealer_id=dealer_username
                )
            except SaleRecord.DoesNotExist:
                raise HttpError(404, f"Sale with id '{sale_id}' not found")

            # Validate: sale must not be voided
            if sale.is_voided:
                raise HttpError(400, "Cannot process return on a voided sale")

            # Validate: return quantity <= remaining quantity (after previous returns)
            already_returned = sum(r.quantity for r in sale.returns.all())
            remaining = sale.quantity - already_returned
            if payload.quantity > remaining:
                raise HttpError(
                    400,
                    f"Return quantity ({payload.quantity}) exceeds remaining quantity ({remaining}). "
                    f"Original: {sale.quantity}, already returned: {already_returned}"
                )

            if payload.quantity <= 0:
                raise HttpError(400, "Return quantity must be positive")

            # Increment product stock via F() expression (dealer-scoped)
            try:
                product = await Product.objects.select_for_update().aget(
                    id=sale.product_id,
                    dealer_id=dealer_username
                )
            except Product.DoesNotExist:
                raise HttpError(404, f"Product with id '{sale.product_id}' not found")

            product.stock = F("stock") + payload.quantity
            await product.asave()

            # Calculate return amount proportionally
            return_amount = sale.selling_price * Decimal(str(payload.quantity))

            # Create SaleReturn record
            await SaleReturn.objects.acreate(
                id=await self._generate_id("ret", dealer_username),
                sale=sale,
                product_name=sale.product_name,
                quantity=payload.quantity,
                return_amount=return_amount,
                reason=payload.reason,
                processed_by=payload.processed_by,
                date=datetime.now(),
            )

            # Update sale's cumulative return total
            sale.return_total_amount = F("return_total_amount") + return_amount
            await sale.asave(update_fields=["return_total_amount", "updated_at"])
            await sale.arefresh_from_db()

            # Recalculate collection status against net_amount
            # net_amount = total_amount - return_total_amount
            if not sale.is_closed_with_due:
                sale.collection_status = self._calc_collection_status(
                    float(sale.net_amount), float(sale.amount_paid)
                )
                await sale.asave(update_fields=["collection_status", "updated_at"])

            # Re-fetch sale with updated returns and payments
            sale = await SaleRecord.objects.prefetch_related("payments", "returns").aget(id=sale_id)
            return await self._serialize_sale(sale)

    @route.post("{sale_id}/void", response=SaleRecordOut, summary="Void a sale")
    async def void_sale(self, request, sale_id: str, force: bool = False):
        """Void a sale — complete reversal of the entire transaction (dealer-scoped).

        BUSINESS RULE — VOID PROTECTION:
        If a sale has had payment transactions (amount_paid > 0 or has
        CreditPayment records), voiding is BLOCKED by default because it
        reverses financial history. The user must either:
          a) Use "Return" instead (partial reversal, preserves audit trail)
          b) Pass force=True to explicitly override (for mistake entries)
        This prevents accidental voiding of sales where money has already
        changed hands, which would create reconciliation discrepancies.

        COMPLETE CIRCLE:
        1. Restores product stock (inventory corrected)
           - Only restores the un-returned quantity
             (already-returned items were already restocked)
        2. Sets is_voided = True (permanent flag)
        3. Sets collection_status = "Voided"
        4. Voided sales are EXCLUDED from ALL financial computations:
           * Revenue (reports)
           * Credit pending / credit collected
           * DSR performance metrics
           * Vehicle tracking pending amounts
           * Customer due reports
           * Product performance totals
        5. Voided sales still appear in lists (for audit trail) but are
           visually marked and filtered out of all active calculations.

        This is a one-way operation — voided sales cannot be un-voided.
        Uses aatomic() + select_for_update() for safe concurrent access.
        """
        dealer_username = await get_dealer_context(request)
        async with aatomic():
            try:
                sale = await SaleRecord.objects.select_for_update().prefetch_related("payments", "returns").aget(
                    id=sale_id,
                    dealer_id=dealer_username
                )
            except SaleRecord.DoesNotExist:
                raise HttpError(404, f"Sale with id '{sale_id}' not found")

            # Validate: sale must not already be voided
            if sale.is_voided:
                raise HttpError(400, "Sale is already voided")

            # VOID PROTECTION: Block void if transactions have occurred
            has_payments = sale.amount_paid and sale.amount_paid > 0
            payment_count = await sale.payments.acount()
            if (has_payments or payment_count > 0) and not force:
                raise HttpError(
                    400,
                    f"Cannot void: this sale has {payment_count} payment(s) totaling "
                    f"{sale.amount_paid}. Use 'Return' for partial reversal, or "
                    f"pass force=true to override (for mistake entries)."
                )

            # Reverse stock: only restore the un-returned quantity
            # (already-returned items were already restocked via the return flow)
            already_returned = sum(r.quantity for r in sale.returns.all())
            qty_to_restore = sale.quantity - already_returned

            if qty_to_restore > 0:
                try:
                    product = await Product.objects.select_for_update().aget(
                        id=sale.product_id,
                        dealer_id=dealer_username
                    )
                except Product.DoesNotExist:
                    raise HttpError(404, f"Product with id '{sale.product_id}' not found")

                product.stock = F("stock") + qty_to_restore
                await product.asave()

            # Mark sale as voided
            sale.is_voided = True
            sale.collection_status = SaleRecord.STATUS_VOIDED
            await sale.asave()

            return await self._serialize_sale(sale)

    @route.post("{sale_id}/edit", response=SaleRecordOut, summary="Edit sale fields + DSR reassignment")
    async def edit_sale(self, request, sale_id: str, payload: EditSaleIn):
        """Edit non-financial fields and reassign collection DSR on a sale (dealer-scoped).

        Only customer_name, customer_phone, due_date, vehicle_number, and dsr_id
        can be changed. Financial fields require voiding and re-creating.

        DSR REASSIGNMENT RULES:
        - Changing dsr_id reassigns the CURRENT collector (dsr/dsr_name)
        - The ORIGINAL seller (original_dsr/original_dsr_name) is NEVER changed
        - This preserves the audit trail: "who sold" vs "who is collecting"
        - When a sale's collection is reassigned to a different DSR/OC,
          the new collector sees it in their active list, but sales
          attribution reports still credit the original DSR.
        """
        dealer_username = await get_dealer_context(request)
        async with aatomic():
            try:
                sale = await SaleRecord.objects.select_for_update().prefetch_related("payments", "returns").aget(
                    id=sale_id,
                    dealer_id=dealer_username
                )
            except SaleRecord.DoesNotExist:
                raise HttpError(404, f"Sale with id '{sale_id}' not found")

            if sale.is_voided:
                raise HttpError(400, "Cannot edit a voided sale")

            update_data = payload.model_dump(exclude_unset=True)
            if not update_data:
                raise HttpError(400, "No fields provided for update")

            # Handle DSR reassignment separately — resolve dsr_name
            if "dsr_id" in update_data:
                new_dsr_id = update_data.pop("dsr_id")
                if new_dsr_id:
                    try:
                        new_dsr = await DSR.objects.aget(id=new_dsr_id)
                        sale.dsr = new_dsr
                        sale.dsr_name = new_dsr.name
                    except DSR.DoesNotExist:
                        raise HttpError(400, f"DSR with id '{new_dsr_id}' not found")
                else:
                    sale.dsr = None
                    sale.dsr_name = ""
                # IMPORTANT: original_dsr is NEVER changed here

            # Apply remaining non-financial fields
            safe_fields = {"customer_name", "customer_phone", "due_date", "vehicle_number"}
            for field, value in update_data.items():
                if field in safe_fields:
                    setattr(sale, field, value)

            await sale.asave()
            return await self._serialize_sale(sale)

    # ─── Helpers ────────────────────────────────────────

    async def _list_sales_qs(self, dealer_username: str, limit: int = 100, offset: int = 0) -> list[SaleRecordOut]:
        """List all sales with serialized payments and returns (dealer-scoped)."""
        results = []
        async for sale in SaleRecord.objects.select_related("dsr").prefetch_related(
            "payments", "returns"
        ).filter(dealer_id=dealer_username)[offset:offset+limit]:
            results.append(await self._serialize_sale(sale))
        return results

    async def _process_single_sale(
        self, request, payload: CreateSaleIn, dealer_username: str, is_bulk: bool = False
    ) -> SaleRecordOut:
        """Core sale creation logic — shared between single and bulk endpoints.

        IMPORTANT: This method MUST be called inside `async with aatomic():`
        to ensure transaction atomicity. The select_for_update() call
        acquires a row-level lock on the Product row, preventing concurrent
        requests from reading stale stock values.

        At creation, original_dsr = dsr (who made the sale = who collects).
        The original_dsr is immutable after creation. The dsr can be
        reassigned later via the edit endpoint for collection handoff.
        """
        dealer = await DealerConfig.objects.aget(username=dealer_username)
        
        # Validate due_date required for credit sales
        if payload.payment_type == SaleRecord.PAYMENT_CREDIT and not payload.due_date:
            customer_info = f" for {payload.customer_name}" if payload.customer_name else ""
            raise HttpError(
                400, 
                f"Credit sales require a due_date{customer_info}. "
                "Set due_date in YYYY-MM-DD format."
            )
        
        try:
            product = await Product.objects.select_for_update().aget(
                id=payload.product_id,
                dealer_id=dealer_username
            )
        except Product.DoesNotExist:
            raise HttpError(404, f"Product with id '{payload.product_id}' not found")

        # Validate stock availability — product row is locked by select_for_update()
        if product.stock < payload.quantity:
            raise HttpError(400, f"Insufficient stock: only {product.stock} available, {payload.quantity} requested")

        # Decrease stock via F() expression — DB-level arithmetic, race-safe
        product.stock = F("stock") - payload.quantity
        await product.asave()

        # Resolve DSR if provided
        dsr_name = ""
        dsr_obj = None
        if payload.dsr_id:
            try:
                dsr_obj = await DSR.objects.aget(id=payload.dsr_id)
                dsr_name = dsr_obj.name
            except DSR.DoesNotExist:
                pass

        # Compute totals
        total_amount = payload.quantity * product.selling_price
        amount_paid = payload.amount_paid or Decimal("0")

        # Validate amount_paid does not exceed total_amount for credit sales
        if payload.payment_type == SaleRecord.PAYMENT_CREDIT:
            if amount_paid > total_amount:
                raise HttpError(
                    400,
                    f"Amount paid ({amount_paid}) cannot exceed total amount ({total_amount}). "
                    f"For credit sales, amount_paid should be <= total_amount."
                )

        # Determine initial collection status
        payment_type = payload.payment_type
        if payment_type == "Cash":
            collection_status = SaleRecord.STATUS_FULLY_PAID
            amount_paid = total_amount
        else:
            collection_status = self._calc_collection_status(
                float(total_amount), float(amount_paid)
            )

        # due_date is already a date object (Pydantic parses ISO strings automatically)
        due_date = payload.due_date

        is_vehicle = payload.is_vehicle or False
        vehicle_number = payload.vehicle_number or ""

        # For bulk sales, explicitly resolve and set original_dsr to current dsr
        # at creation time to ensure sales attribution is preserved correctly
        sale_original_dsr = dsr_obj
        sale_original_dsr_name = dsr_name
        if is_bulk and dsr_obj:
            try:
                sale_original_dsr = await DSR.objects.aget(id=dsr_obj.id)
                sale_original_dsr_name = sale_original_dsr.name
            except (DSR.DoesNotExist, AttributeError):
                sale_original_dsr = dsr_obj
                sale_original_dsr_name = dsr_name

        sale = await SaleRecord.objects.acreate(
            id=await self._generate_id("sale", dealer_username),
            product=product,
            product_name=product.name,
            quantity=payload.quantity,
            customer_name=payload.customer_name,
            customer_phone=payload.customer_phone or "",
            is_vehicle=is_vehicle,
            vehicle_number=vehicle_number,
            dsr=dsr_obj,
            dsr_name=dsr_name,
            original_dsr=sale_original_dsr,  # Immutable: who MADE the sale
            original_dsr_name=sale_original_dsr_name,  # Immutable: preserved for attribution
            selling_price=product.selling_price,
            total_amount=total_amount,
            return_total_amount=Decimal("0"),
            payment_type=payment_type,
            amount_paid=amount_paid,
            collection_status=collection_status,
            due_date=due_date,
            date=datetime.now(),
            dealer=dealer,
        )

        return await self._serialize_sale(sale)

    @staticmethod
    def _calc_collection_status(net_amount: float, paid: float) -> str:
        """Determine collection status based on net amount vs paid amounts.

        net_amount = total_amount - return_total_amount
        This is the effective obligation the customer owes.
        """
        if paid <= 0:
            return SaleRecord.STATUS_PENDING
        elif paid >= net_amount:
            return SaleRecord.STATUS_FULLY_PAID
        else:
            return SaleRecord.STATUS_PARTIAL

    @staticmethod
    async def _serialize_sale(sale: SaleRecord) -> SaleRecordOut:
        """Serialize a SaleRecord with its embedded payments and returns lists."""
        payments = [p async for p in sale.payments.all()]
        returns = [r async for r in sale.returns.all()]
        return SaleRecordOut(
            id=sale.id,
            product_id=sale.product_id,
            product_name=sale.product_name,
            quantity=sale.quantity,
            customer_name=sale.customer_name,
            customer_phone=sale.customer_phone,
            is_vehicle=sale.is_vehicle,
            vehicle_number=sale.vehicle_number,
            dsr_id=sale.dsr_id,
            dsr_name=sale.dsr_name,
            original_dsr_id=sale.original_dsr_id,
            original_dsr_name=sale.original_dsr_name,
            selling_price=sale.selling_price,
            total_amount=sale.total_amount,
            return_total_amount=sale.return_total_amount,
            net_amount=sale.net_amount,
            balance_due=sale.balance_due,
            payment_type=sale.payment_type,
            amount_paid=sale.amount_paid,
            collection_status=sale.collection_status,
            due_date=sale.due_date,
            date=sale.date,
            payments=[
                CreditPaymentOut(
                    id=p.id,
                    amount=p.amount,
                    date=p.date,
                    received_by=p.received_by,
                )
                for p in payments
            ],
            is_closed_with_due=sale.is_closed_with_due,
            is_voided=sale.is_voided,
            returns=[
                SaleReturnOut(
                    id=r.id,
                    sale_id=r.sale_id,
                    product_name=r.product_name,
                    quantity=r.quantity,
                    return_amount=r.return_amount,
                    reason=r.reason,
                    processed_by=r.processed_by,
                    date=r.date,
                )
                for r in returns
            ],
        )

    async def _generate_id(self, prefix: str, dealer_username: str) -> str:
        """Generate a unique string ID: {prefix}-{n}.
        
        Uses dealer-scoped queries to ensure ID uniqueness per dealer.
        Uses a retry loop with existence check to handle race conditions
        under concurrent requests.
        """
        max_retries = 5
        for attempt in range(max_retries):
            if prefix == "sale":
                result = await async_aggregate(
                    SaleRecord.objects.filter(id__startswith=prefix, dealer_id=dealer_username),
                    _max=Max("id"),
                )
            elif prefix == "pay":
                result = await async_aggregate(
                    CreditPayment.objects.filter(id__startswith=prefix),
                    _max=Max("id"),
                )
            elif prefix == "ret":
                result = await async_aggregate(
                    SaleReturn.objects.filter(id__startswith=prefix),
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

            # Check if candidate already exists (dealer-scoped for sale)
            if prefix == "sale":
                exists = await async_exists(
                    SaleRecord.objects.filter(id=candidate_id, dealer_id=dealer_username),
                )
            elif prefix == "pay":
                exists = await async_exists(
                    CreditPayment.objects.filter(id=candidate_id),
                )
            elif prefix == "ret":
                exists = await async_exists(
                    SaleReturn.objects.filter(id=candidate_id),
                )
            else:
                exists = False

            if not exists:
                return candidate_id

        # Fallback: use a timestamp-based suffix if all retries exhausted
        import time
        return f"{prefix}-{int(time.time() * 1000)}"
