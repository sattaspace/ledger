"""
DEALERCORE v3.0 — Seed Data Management Command
=================================================
Populates the database with realistic dummy data matching the frontend mock layer.

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
from inventory.models import Product, RestockRecord
from dsr.models import DSR
from dealer.models import DealerConfig
from sales.models import SaleRecord, CreditPayment


# ═══════════════════════════════════════════════════════
#  SEED DATA — exact replica of frontend mock layer
# ═══════════════════════════════════════════════════════

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
        "stock": 18,
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
        "stock": 8,
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
        "stock": 35,
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
        "stock": 3,
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
        "stock": 12,
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
        "received_by": "Sanjay Sharma (Manager)",
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
]

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
        "name": "Amit Patel",
        "phone": "9812345670",
        "role": "DSR",
        "parent_dsr_id": None,
        "parent_dsr_name": "",
    },
    {
        "id": "dsr-3",
        "name": "Sarah Jenkins",
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

DEALERS = [
    {
        "username": "sanjay",
        "full_name": "Sanjay Sharma",
        "role": "Senior Dealer Admin & manager",
        "default_currency": "INR",
        "default_locale": "en-IN",
    },
    {
        "username": "rajesh",
        "full_name": "Rajesh Kumar",
        "role": "North Regional Principal",
        "default_currency": "INR",
        "default_locale": "en-IN",
    },
    {
        "username": "priya",
        "full_name": "Priya Patel",
        "role": "Franchise Partner (Mumbai)",
        "default_currency": "USD",
        "default_locale": "en-US",
    },
    {
        "username": "vijay",
        "full_name": "Vijay Singh",
        "role": "Bengaluru Fleet Director",
        "default_currency": "INR",
        "default_locale": "en-IN",
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
        "dsr_name": "Amit Patel",
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
    help = "Seed DEALERCORE database with dummy data"

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

        self.stdout.write(self.style.HTTP_NOT_FOUND("Seeding DEALERCORE v3.0...\n"))

        with transaction.atomic():
            self._seed_suppliers(verbose)
            self._seed_products(verbose)
            self._seed_restocks(verbose)
            self._seed_dsrs(verbose)
            self._seed_dealers(verbose)
            self._seed_sales(verbose)

        self.stdout.write(self.style.SUCCESS("\nDone. Database seeded successfully."))
        self.stdout.write(self.style.SUCCESS(
            "  4 suppliers, 5 products, 2 restocks, 4 DSRs, 4 dealers, 3 sales"
        ))

    # ─── Flush ──────────────────────────────────────────

    def _flush_all(self):
        """Delete all records respecting FK constraints (children first)."""
        CreditPayment.objects.all().delete()
        SaleRecord.objects.all().delete()
        RestockRecord.objects.all().delete()
        Product.objects.all().delete()
        DSR.objects.all().delete()
        DealerConfig.objects.all().delete()
        Supplier.objects.all().delete()

    # ─── Seeders (order matters for FK constraints) ────

    def _seed_suppliers(self, verbose):
        count = 0
        for s in SUPPLIERS:
            obj, created = Supplier.objects.get_or_create(
                id=s["id"],
                defaults=s,
            )
            if created:
                count += 1
                if verbose:
                    self.stdout.write(f"  + Supplier: {obj.name}")
        self.stdout.write(
            self.style.SUCCESS(f"  Suppliers: {count} created")
        )

    def _seed_products(self, verbose):
        count = 0
        for p in PRODUCTS:
            obj, created = Product.objects.get_or_create(
                id=p["id"],
                defaults=p,
            )
            if created:
                count += 1
                if verbose:
                    self.stdout.write(f"  + Product: {obj.name} (stock={obj.stock})")
        self.stdout.write(
            self.style.SUCCESS(f"  Products:  {count} created")
        )

    def _seed_restocks(self, verbose):
        count = 0
        for r in RESTOCKS:
            product = Product.objects.get(id=r["product_id"])
            obj, created = RestockRecord.objects.get_or_create(
                id=r["id"],
                defaults={
                    **r,
                    "product": product,
                },
            )
            if created:
                count += 1
                if verbose:
                    self.stdout.write(
                        f"  + Restock: {obj.product_name} x{obj.quantity}"
                    )
        self.stdout.write(
            self.style.SUCCESS(f"  Restocks:  {count} created")
        )

    def _seed_dsrs(self, verbose):
        count = 0
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
        self.stdout.write(
            self.style.SUCCESS(f"  DSRs:      {count} created")
        )

    def _seed_dealers(self, verbose):
        count = 0
        for d in DEALERS:
            obj, created = DealerConfig.objects.get_or_create(
                username=d["username"],
                defaults=d,
            )
            if created:
                count += 1
                if verbose:
                    self.stdout.write(f"  + Dealer: {obj.full_name} (@{obj.username})")
        self.stdout.write(
            self.style.SUCCESS(f"  Dealers:   {count} created")
        )

    def _seed_sales(self, verbose):
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
                },
            )
            if created:
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
                        f"x{obj.quantity} ({obj.payment_type})"
                    )
        self.stdout.write(
            self.style.SUCCESS(f"  Sales:     {count} created")
        )
