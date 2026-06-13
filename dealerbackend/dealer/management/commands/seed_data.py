"""
DEALERCORE v3.0 — Seed Data Management Command
=================================================
Populates the database with realistic dummy data matching the frontend mock layer.

ARCHITECTURE:
  - ONE DealerConfig: Represents the SattaBase subscriber (the actual dealer)
  - Multiple DSRs: Employees invited by the dealer
  - DsrDealerAssignment: Links DSRs to work for the dealer
  - All business data linked to the dealer's username

Multi-Tenancy:
  All business data (products, sales, suppliers, etc.) is associated with
  a specific dealer via the `dealer` FK field for tenant isolation.

Usage:
    python manage.py seed_data                # Seed all tables (safe — skips if data exists)
    python manage.py seed_data --flush        # Wipe existing data, then seed fresh
    python manage.py seed_data --flush --verbose

Flags:
    --flush     Delete all existing records before seeding
    --verbose   Print every created record
"""

from decimal import Decimal
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import make_aware, get_current_timezone

TZ = get_current_timezone()

from supplier.models import Supplier
from inventory.models import Product, RestockRecord, Brand, Category
from dsr.models import DSR, DsrDealerAssignment
from dealer.models import DealerConfig
from sales.models import SaleRecord, CreditPayment


# ═══════════════════════════════════════════════════════
#  PRIMARY DEALER (SattaBase Subscriber)
# ═══════════════════════════════════════════════════════
# This is the ONE dealer who subscribed on SattaBase
# Their username is the user_id from SattaBase JWT
# SattaBase does NOT have usernames - it uses user_id (e.g., "1")
# The DealerConfig.username field stores this user_id as the primary key

PRIMARY_DEALER = {
    "username": "1",  # Matches SattaBase user_id (subscriber ID from Base system)
    "full_name": "Haradhan Sharma",
    "role": "Senior Dealer Admin & Manager",
    "business_name": "Sri Balaji Enterprises",
    "address": "Plot No. 45, Sector 12, Industrial Area, Ahmedabad, Gujarat 380015",
    "phone_number": "9876543210",
    "email": "info@sribalajienterprises.com",
    "gst_number": "24AABCS1429B1Z5",
    "google_map_url": "https://maps.google.com/?q=23.0225,72.5714",
    "communication_number": "9876543210",
    "default_currency": "INR",
    "default_locale": "en-IN",
}

# ═══════════════════════════════════════════════════════
#  DSRs (Sales Representatives)
#  These work FOR the dealer, linked via DsrDealerAssignment
# ═══════════════════════════════════════════════════════

DSRS = [
    {
        "id": "dsr-1",
        "name": "Rajesh Kumar",
        "phone": "9876543210",
        "role": "DSR",
        "parent_dsr_id": None,
        "parent_dsr_name": "",
    },
    {
        "id": "dsr-2",
        "name": "Priya Patel",
        "phone": "9812345670",
        "role": "DSR",
        "parent_dsr_id": None,
        "parent_dsr_name": "",
    },
    {
        "id": "dsr-3",
        "name": "Sanjay Sharma",
        "phone": "9988776655",
        "role": "DSR",
        "parent_dsr_id": None,
        "parent_dsr_name": "",
    },
    {
        "id": "dsr-4",
        "name": "Michael Chang",
        "phone": "9123456789",
        "role": "Order Collector",
        "parent_dsr_id": "dsr-1",
        "parent_dsr_name": "Rajesh Kumar",
    },
]

# ═══════════════════════════════════════════════════════
#  BUSINESS DATA (linked to primary dealer)
# ═══════════════════════════════════════════════════════

BRANDS = [
    {"id": "brand-1", "name": "Michelin"},
    {"id": "brand-2", "name": "Castrol"},
    {"id": "brand-3", "name": "Bosch"},
    {"id": "brand-4", "name": "Exide"},
]

CATEGORIES = [
    {"id": "cat-1", "name": "Tyres"},
    {"id": "cat-2", "name": "Fluids"},
    {"id": "cat-3", "name": "Parts"},
    {"id": "cat-4", "name": "Batteries"},
]

SUPPLIERS = [
    {"id": "sup-1", "name": "Michelin Distributors", "phone": "9899001122", "category": "Tyres"},
    {"id": "sup-2", "name": "Castrol India", "phone": "9876003344", "category": "Fluids"},
    {"id": "sup-3", "name": "Bosch Parts Direct", "phone": "9877004455", "category": "Parts"},
    {"id": "sup-4", "name": "Exide Industries", "phone": "9878005566", "category": "Batteries"},
]

PRODUCTS = [
    {
        "id": "prod-1",
        "name": "Michelin Primacy 4 SUV Tyre",
        "sku": "MCH-PRM4-225/65R17",
        "brand": "Michelin",
        "category": "Tyres",
        "stock": 0,  # Stock is computed dynamically: 0 + restocked - sold
        "min_stock_alert": 5,
        "unit_price": Decimal("120"),
        "selling_price": Decimal("185"),
        "location": "Warehouse A - Rack 3",
    },
    {
        "id": "prod-2",
        "name": "Castrol EDGE 5W-40 Engine Oil Full Synthetic",
        "sku": "CST-EDGE-5W40-4L",
        "brand": "Castrol",
        "category": "Fluids",
        "stock": 0,  # Stock is computed dynamically: 0 + restocked - sold
        "min_stock_alert": 3,
        "unit_price": Decimal("25"),
        "selling_price": Decimal("45"),
        "location": "Warehouse A - Shelf 1",
    },
    {
        "id": "prod-3",
        "name": "Bosch Super 4 Spark Plug",
        "sku": "BSC-S4-0242229505",
        "brand": "Bosch",
        "category": "Parts",
        "stock": 0,  # Stock is computed dynamically: 0 + restocked - sold
        "min_stock_alert": 10,
        "unit_price": Decimal("8"),
        "selling_price": Decimal("15"),
        "location": "Warehouse B - Bin 7",
    },
    {
        "id": "prod-4",
        "name": "Exide Matrix 12V Car Battery",
        "sku": "EXD-MTX-55B24R",
        "brand": "Exide",
        "category": "Batteries",
        "stock": 0,  # Stock is computed dynamically: 0 + restocked - sold
        "min_stock_alert": 2,
        "unit_price": Decimal("55"),
        "selling_price": Decimal("95"),
        "location": "Warehouse B - Rack 1",
    },
    {
        "id": "prod-5",
        "name": "Bosch Blue Line Brake Pads Front",
        "sku": "BSC-BLP-0986TB3491",
        "brand": "Bosch",
        "category": "Parts",
        "stock": 0,  # Stock is computed dynamically: 0 + restocked - sold
        "min_stock_alert": 5,
        "unit_price": Decimal("12"),
        "selling_price": Decimal("22"),
        "location": "Warehouse A - Shelf 4",
    },
]

RESTOCKS = [
    {
        "id": "restock-1",
        "product_id": "prod-1",
        "product_name": "Michelin Primacy 4 SUV Tyre",
        "quantity": 20,
        "supplier_name": "Michelin Distributors",
        "cost_price": Decimal("120"),
        "total_cost": Decimal("2400"),
        "date": make_aware(datetime(2026, 5, 10, 10, 0, 0), TZ),
        "received_by": "Haradhan Sharma (Manager)",
    },
    {
        "id": "restock-2",
        "product_id": "prod-2",
        "product_name": "Castrol EDGE 5W-40 Engine Oil Full Synthetic",
        "quantity": 10,
        "supplier_name": "Castrol India",
        "cost_price": Decimal("25"),
        "total_cost": Decimal("250"),
        "date": make_aware(datetime(2026, 5, 12, 14, 30, 0), TZ),
        "received_by": "Rajesh Kumar (DSR)",
    },
    {
        "id": "restock-3",
        "product_id": "prod-3",
        "product_name": "Bosch Super 4 Spark Plug",
        "quantity": 35,
        "supplier_name": "Bosch Parts Direct",
        "cost_price": Decimal("8"),
        "total_cost": Decimal("280"),
        "date": make_aware(datetime(2026, 5, 8, 9, 0, 0), TZ),
        "received_by": "Haradhan Sharma (Manager)",
    },
    {
        "id": "restock-4",
        "product_id": "prod-4",
        "product_name": "Exide Matrix 12V Car Battery",
        "quantity": 3,
        "supplier_name": "Exide Industries",
        "cost_price": Decimal("55"),
        "total_cost": Decimal("165"),
        "date": make_aware(datetime(2026, 5, 9, 11, 0, 0), TZ),
        "received_by": "Haradhan Sharma (Manager)",
    },
    {
        "id": "restock-5",
        "product_id": "prod-5",
        "product_name": "Bosch Blue Line Brake Pads Front",
        "quantity": 16,
        "supplier_name": "Bosch Parts Direct",
        "cost_price": Decimal("12"),
        "total_cost": Decimal("192"),
        "date": make_aware(datetime(2026, 5, 11, 13, 0, 0), TZ),
        "received_by": "Rajesh Kumar (DSR)",
    },
]

SALES = [
    {
        "id": "sale-1",
        "product_id": "prod-1",
        "product_name": "Michelin Primacy 4 SUV Tyre",
        "quantity": 2,
        "customer_name": "Ramesh Patel",
        "customer_phone": "9876543210",
        "is_vehicle": True,
        "vehicle_number": "GJ-01-AB-1234",
        "dsr_id": None,
        "dsr_name": "",
        "selling_price": Decimal("185"),
        "total_amount": Decimal("370"),
        "payment_type": "Cash",
        "amount_paid": Decimal("370"),
        "collection_status": "Fully Paid",
        "due_date": None,
        "date": make_aware(datetime(2026, 5, 15, 10, 30, 0), TZ),
        "is_closed_with_due": False,
        "payments": [],
    },
    {
        "id": "sale-2",
        "product_id": "prod-2",
        "product_name": "Castrol EDGE 5W-40 Engine Oil Full Synthetic",
        "quantity": 5,
        "customer_name": "Standard Auto Service",
        "customer_phone": "9812345670",
        "is_vehicle": False,
        "vehicle_number": "",
        "dsr_id": "dsr-1",
        "dsr_name": "Rajesh Kumar",
        "selling_price": Decimal("45"),
        "total_amount": Decimal("225"),
        "payment_type": "Credit",
        "amount_paid": Decimal("100"),
        "collection_status": "Partial",
        "due_date": datetime(2026, 6, 15).date(),
        "date": make_aware(datetime(2026, 5, 16, 14, 0, 0), TZ),
        "is_closed_with_due": False,
        "payments": [
            {
                "id": "pay-1",
                "amount": Decimal("100"),
                "date": make_aware(datetime(2026, 5, 16, 14, 0, 0), TZ),
                "received_by": "Counter Staff",
            }
        ],
    },
    {
        "id": "sale-3",
        "product_id": "prod-5",
        "product_name": "Bosch Blue Line Brake Pads Front",
        "quantity": 4,
        "customer_name": "Ghanshyambhai Motor Garage",
        "customer_phone": "9912345678",
        "is_vehicle": False,
        "vehicle_number": "",
        "dsr_id": "dsr-2",
        "dsr_name": "Priya Patel",
        "selling_price": Decimal("22"),
        "total_amount": Decimal("88"),
        "payment_type": "Credit",
        "amount_paid": Decimal("0"),
        "collection_status": "Pending",
        "due_date": datetime(2026, 6, 30).date(),
        "date": make_aware(datetime(2026, 5, 17, 9, 0, 0), TZ),
        "is_closed_with_due": False,
        "payments": [],
    },
]


# ═══════════════════════════════════════════════════════
#  COMMAND
# ═══════════════════════════════════════════════════════

class Command(BaseCommand):
    help = "Seed DEALERCORE database with dummy data (multi-tenant)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing records before seeding",
        )

    def handle(self, *args, **options):
        flush = options["flush"]
        verbose = options["verbosity"] >= 2

        if flush:
            self.stdout.write(self.style.WARNING("Flushing existing data..."))
            self._flush_all()

        self.stdout.write(self.style.HTTP_NOT_FOUND("Seeding DEALERCORE v3.0 (Multi-Tenant)...\n"))

        with transaction.atomic():
            # Seed the ONE dealer (SattaBase subscriber)
            dealer = self._seed_dealer(verbose)
            
            # Seed DSRs and their assignments to the dealer
            self._seed_dsrs(dealer, verbose)
            
            # Seed all business data associated with the dealer
            self._seed_brands(dealer, verbose)
            self._seed_categories(dealer, verbose)
            self._seed_suppliers(dealer, verbose)
            self._seed_products(dealer, verbose)
            self._seed_restocks(dealer, verbose)
            self._seed_sales(dealer, verbose)

        self.stdout.write(self.style.SUCCESS("\nDone. Database seeded successfully."))
        self.stdout.write(self.style.SUCCESS(
            "  1 dealer (subscriber), 4 DSRs, 4 brands, 4 categories, 4 suppliers, 5 products, 5 restocks, 3 sales"
        ))
        self.stdout.write(self.style.NOTICE(
            f"  All business data associated with dealer: {dealer.username}"
        ))

    # ─── Flush ──────────────────────────────────────────

    def _flush_all(self):
        """Delete all records respecting FK constraints (children first)."""
        CreditPayment.objects.all().delete()
        SaleRecord.objects.all().delete()
        RestockRecord.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Brand.objects.all().delete()
        DsrDealerAssignment.objects.all().delete()
        DSR.objects.all().delete()
        DealerConfig.objects.all().delete()
        Supplier.objects.all().delete()

    # ─── Seeders (order matters for FK constraints) ────

    def _seed_dealer(self, verbose):
        """Seed the ONE dealer configuration (SattaBase subscriber)."""
        obj, created = DealerConfig.objects.get_or_create(
            username=PRIMARY_DEALER["username"],
            defaults=PRIMARY_DEALER,
        )
        if created:
            if verbose:
                self.stdout.write(f"  + Dealer: {obj.full_name} (@{obj.username})")
        self.stdout.write(
            self.style.SUCCESS(f"  Dealer:   {obj.username} ({obj.full_name})")
        )
        return obj

    def _seed_dsrs(self, dealer, verbose):
        """Seed DSRs and create dealer assignments."""
        count = 0
        assignment_count = 0
        for d in DSRS:
            parent = None
            if d["parent_dsr_id"]:
                parent = DSR.objects.get(id=d["parent_dsr_id"])

            obj, created = DSR.objects.get_or_create(
                id=d["id"],
                defaults={
                    "name": d["name"],
                    "phone": d["phone"],
                    "role": d["role"],
                    "parent_dsr": parent,
                    "parent_dsr_name": d["parent_dsr_name"],
                },
            )
            if created:
                count += 1
                if verbose:
                    self.stdout.write(f"  + DSR: {obj.name} ({obj.role})")
            
            # Create dealer assignment - DSR works FOR the dealer
            assignment_id = f"{d['id']}-{dealer.username}"
            assignment, assignment_created = DsrDealerAssignment.objects.get_or_create(
                id=assignment_id,
                defaults={
                    "dsr": obj,
                    "dealer": dealer,
                    "role": obj.role,
                    "is_active": True,
                    "commission_rate": Decimal("5.00"),
                },
            )
            if assignment_created:
                assignment_count += 1
                if verbose:
                    self.stdout.write(f"    + Assignment: {obj.name} → {dealer.username}")
        
        self.stdout.write(
            self.style.SUCCESS(f"  DSRs:     {count} created, {assignment_count} assignments")
        )

    def _seed_brands(self, dealer, verbose):
        """Seed brands with dealer association for multi-tenancy."""
        count = 0
        for b in BRANDS:
            obj, created = Brand.objects.get_or_create(
                id=b["id"],
                defaults={
                    **b,
                    "dealer": dealer,
                },
            )
            if created:
                count += 1
                if verbose:
                    self.stdout.write(f"  + Brand: {obj.name} (dealer={dealer.username})")
        self.stdout.write(
            self.style.SUCCESS(f"  Brands:    {count} created")
        )

    def _seed_categories(self, dealer, verbose):
        """Seed categories with dealer association for multi-tenancy."""
        count = 0
        for c in CATEGORIES:
            obj, created = Category.objects.get_or_create(
                id=c["id"],
                defaults={
                    **c,
                    "dealer": dealer,
                },
            )
            if created:
                count += 1
                if verbose:
                    self.stdout.write(f"  + Category: {obj.name} (dealer={dealer.username})")
        self.stdout.write(
            self.style.SUCCESS(f"  Categories: {count} created")
        )

    def _seed_suppliers(self, dealer, verbose):
        """Seed suppliers with dealer association for multi-tenancy."""
        count = 0
        for s in SUPPLIERS:
            obj, created = Supplier.objects.get_or_create(
                id=s["id"],
                defaults={
                    **s,
                    "dealer": dealer,
                },
            )
            if created:
                count += 1
                if verbose:
                    self.stdout.write(f"  + Supplier: {obj.name} (dealer={dealer.username})")
        self.stdout.write(
            self.style.SUCCESS(f"  Suppliers: {count} created")
        )

    def _seed_products(self, dealer, verbose):
        """Seed products with dealer association for multi-tenancy."""
        count = 0
        for p in PRODUCTS:
            obj, created = Product.objects.get_or_create(
                id=p["id"],
                defaults={
                    **p,
                    "dealer": dealer,
                },
            )
            if created:
                count += 1
                if verbose:
                    self.stdout.write(f"  + Product: {obj.name} (stock={obj.stock}, dealer={dealer.username})")
        self.stdout.write(
            self.style.SUCCESS(f"  Products:  {count} created")
        )

    def _seed_restocks(self, dealer, verbose):
        """Seed restock records with dealer association for multi-tenancy."""
        count = 0
        for r in RESTOCKS:
            product = Product.objects.get(id=r["product_id"])
            obj, created = RestockRecord.objects.get_or_create(
                id=r["id"],
                defaults={
                    **r,
                    "product": product,
                    "dealer": dealer,
                },
            )
            if created:
                # Increase product stock to keep stock consistent: stock += restock_quantity
                product.stock = product.stock + r["quantity"]
                product.save(update_fields=["stock", "updated_at"])
                count += 1
                if verbose:
                    self.stdout.write(
                        f"  + Restock: {obj.product_name} x{obj.quantity} "
                        f"(stock now: {product.stock}, dealer={dealer.username})"
                    )
        self.stdout.write(
            self.style.SUCCESS(f"  Restocks:  {count} created")
        )

    def _seed_sales(self, dealer, verbose):
        """Seed sales records with dealer association for multi-tenancy."""
        count = 0
        for s in SALES:
            product = Product.objects.get(id=s["product_id"])
            dsr = None
            if s["dsr_id"]:
                dsr = DSR.objects.get(id=s["dsr_id"])

            obj, created = SaleRecord.objects.get_or_create(
                id=s["id"],
                defaults={
                    "product": product,
                    "product_name": s["product_name"],
                    "quantity": s["quantity"],
                    "customer_name": s["customer_name"],
                    "customer_phone": s["customer_phone"],
                    "is_vehicle": s["is_vehicle"],
                    "vehicle_number": s["vehicle_number"],
                    "dsr": dsr,
                    "dsr_name": s["dsr_name"],
                    "selling_price": s["selling_price"],
                    "total_amount": s["total_amount"],
                    "payment_type": s["payment_type"],
                    "amount_paid": s["amount_paid"],
                    "collection_status": s["collection_status"],
                    "due_date": s["due_date"],
                    "date": s["date"],
                    "is_closed_with_due": s["is_closed_with_due"],
                    "dealer": dealer,
                },
            )
            if created:
                # Decrease product stock to keep stock consistent: stock -= sale_quantity
                # Safety check: skip stock decrement if it would go negative
                # (shouldn't happen with correct seed data, but prevents IntegrityError)
                if product.stock >= s["quantity"]:
                    product.stock = product.stock - s["quantity"]
                else:
                    product.stock = 0
                product.save(update_fields=["stock", "updated_at"])

                # Seed embedded payments
                for p in s["payments"]:
                    CreditPayment.objects.create(
                        id=p["id"],
                        sale=obj,
                        amount=p["amount"],
                        date=p["date"],
                        received_by=p["received_by"],
                    )
                count += 1
                if verbose:
                    self.stdout.write(
                        f"  + Sale: {obj.customer_name} — {obj.product_name} "
                        f"x{obj.quantity} ({obj.payment_type}) "
                        f"(stock now: {product.stock}, dealer={dealer.username})"
                    )
        self.stdout.write(
            self.style.SUCCESS(f"  Sales:     {count} created")
        )
