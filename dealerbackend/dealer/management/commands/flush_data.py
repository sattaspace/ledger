"""
DEALERCORE v3.0 — Flush Data Management Command
=================================================
Wipes all DEALERCORE data from the database (child tables first).

Usage:
    python manage.py flush_data                # Remove all seed data
    python manage.py flush_data --confirm      # Skip confirmation prompt
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from supplier.models import Supplier
from inventory.models import Product, RestockRecord, Brand, Category
from dsr.models import DSR
from dealer.models import DealerConfig
from sales.models import SaleRecord, CreditPayment, SaleReturn


class Command(BaseCommand):
    help = "Flush all DEALERCORE data from the database (children first)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            confirm = input(
                "This will DELETE all dealers, sales, products, DSRs, suppliers, "
                "and restock records. Continue? [y/N] "
            )
            if confirm.lower() != "y":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        with transaction.atomic():
            counts = {
                "Credit Payments": CreditPayment.objects.count(),
                "Sale Returns": SaleReturn.objects.count(),
                "Sales": SaleRecord.objects.count(),
                "Restocks": RestockRecord.objects.count(),
                "Products": Product.objects.count(),
                "Categories": Category.objects.count(),
                "Brands": Brand.objects.count(),
                "DSRs": DSR.objects.count(),
                "Dealers": DealerConfig.objects.count(),
                "Suppliers": Supplier.objects.count(),
            }

            CreditPayment.objects.all().delete()
            SaleReturn.objects.all().delete()
            SaleRecord.objects.all().delete()
            RestockRecord.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Brand.objects.all().delete()
            DSR.objects.all().delete()
            DealerConfig.objects.all().delete()
            Supplier.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("All DEALERCORE data flushed:"))
        for name, count in counts.items():
            self.stdout.write(f"  - {name}: {count} deleted")
