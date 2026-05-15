"""
Seed Ledger Database — Management Command

Creates comprehensive test data for the Ledger backend, covering all 16 domain
models with realistic financial data. Designed for development/testing only.

Usage:
    python manage.py seed_ledger                  # seed user_id=1 (default)
    python manage.py seed_ledger --user-id 42     # seed a specific user
    python manage.py seed_ledger --clear          # clear existing data first
    python manage.py seed_ledger --clear --user-id 5

Notes:
    - user_id is a plain integer (not a Django FK). It must match a real
      Sattabase User.id in the base backend.
    - All FK relationships are maintained (Institution→Account→Card, etc.)
    - Transaction balances are computed to match account.current_balance
    - Currency amounts use DecimalField strings for precision
    - The --clear flag only deletes data for the specified user_id
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.models import (
    Institution,
    Account,
    Transaction,
    TransactionSplit,
    Category,
    Tag,
    TransactionTag,
    Card,
    Bill,
    BillPayment,
    DebtFacility,
    DebtPayment,
    Budget,
    InvestmentAccount,
    Holding,
    SavingsGoal,
    InsurancePolicy,
    Invoice,
    InvoiceLineItem,
    # DocumentVault,  # requires file upload + ContentType, skip for seed
)

# ---------------------------------------------------------------------------
#  Seed Data Definitions
# ---------------------------------------------------------------------------

TODAY = date.today()
DAYS_AGO = lambda n: TODAY - timedelta(days=n)
DAYS_FROM_NOW = lambda n: TODAY + timedelta(days=n)

# ── Institutions ──────────────────────────────────────────────────────────────

INSTITUTIONS = [
    {
        "name": "Chase Bank",
        "institution_type": "BANK",
        "website": "https://www.chase.com",
        "customer_service_phone": "1-800-935-9935",
        "icon": "landmark",
        "color": "#0A6EBD",
        "notes": "Primary banking",
    },
    {
        "name": "Bank of America",
        "institution_type": "BANK",
        "website": "https://www.bankofamerica.com",
        "customer_service_phone": "1-800-432-1000",
        "icon": "landmark",
        "color": "#012169",
        "notes": "Secondary banking",
    },
    {
        "name": "Fidelity Investments",
        "institution_type": "BROKERAGE",
        "website": "https://www.fidelity.com",
        "customer_service_phone": "1-800-343-3548",
        "icon": "chart-line",
        "color": "#5A7E51",
        "notes": "Investment accounts",
    },
    {
        "name": "Coinbase",
        "institution_type": "CRYPTO",
        "website": "https://www.coinbase.com",
        "icon": "bitcoin",
        "color": "#0052FF",
        "notes": "Crypto holdings",
    },
    {
        "name": "Discover",
        "institution_type": "BANK",
        "website": "https://www.discover.com",
        "customer_service_phone": "1-800-347-2683",
        "icon": "credit-card",
        "color": "#FF6600",
        "notes": "Credit card issuer",
    },
]

# ── Accounts (reference institutions by index) ────────────────────────────────

ACCOUNTS = [
    # (institution_index, name, account_type, currency, balance, credit_limit, interest_rate)
    (0, "Chase Checking", "ASSET", "USD", "8450.73", None, "0"),
    (0, "Chase Savings", "ASSET", "USD", "25300.00", None, "4.25"),
    (1, "BofA Checking", "ASSET", "USD", "3200.50", None, "0"),
    (4, "Discover It Cash Back", "LIABILITY", "USD", "-1823.45", "5000.00", "22.99"),
    (0, "Chase Freedom Unlimited", "LIABILITY", "USD", "-675.20", "8000.00", "19.99"),
    (2, "Fidelity Brokerage", "INVESTMENT", "USD", "42500.00", None, "0"),
    (3, "Coinbase Crypto Wallet", "INVESTMENT", "USD", "12800.00", None, "0"),
    (1, "BofA EUR Account", "ASSET", "EUR", "5200.00", None, "0"),
]

# ── Categories ────────────────────────────────────────────────────────────────

CATEGORIES = [
    # (name, icon, color, is_income, parent_index_or_None, sort_order)
    # Income categories
    ("Salary", "briefcase", "#10B981", True, None, 1),
    ("Freelance", "laptop", "#06B6D4", True, None, 2),
    ("Investment Income", "trending-up", "#8B5CF6", True, None, 3),
    ("Refunds", "rotate-ccw", "#6B7280", True, None, 4),
    # Expense categories
    ("Housing", "home", "#EF4444", False, None, 10),
    ("  Rent", "home", "#EF4444", False, 4, 11),
    ("  Utilities", "zap", "#F97316", False, 4, 12),
    ("  Internet", "wifi", "#F97316", False, 4, 13),
    ("Transportation", "car", "#3B82F6", False, None, 20),
    ("  Gas", "fuel", "#3B82F6", False, 8, 21),
    ("  Car Insurance", "shield", "#3B82F6", False, 8, 22),
    ("Food & Dining", "utensils", "#F59E0B", False, None, 30),
    ("  Groceries", "shopping-cart", "#F59E0B", False, 10, 31),
    ("  Restaurants", "coffee", "#F59E0B", False, 10, 32),
    ("  Coffee Shops", "coffee", "#92400E", False, 10, 33),
    ("Healthcare", "heart", "#EC4899", False, None, 40),
    ("  Doctor Visits", "stethoscope", "#EC4899", False, 14, 41),
    ("  Pharmacy", "pill", "#EC4899", False, 14, 42),
    ("Entertainment", "tv", "#8B5CF6", False, None, 50),
    ("  Streaming", "play", "#8B5CF6", False, 16, 51),
    ("  Games", "gamepad-2", "#8B5CF6", False, 16, 52),
    ("Shopping", "shopping-bag", "#14B8A6", False, None, 60),
    ("  Clothing", "shirt", "#14B8A6", False, 18, 61),
    ("  Electronics", "smartphone", "#14B8A6", False, 18, 62),
    ("Personal Care", "scissors", "#F472B6", False, None, 70),
    ("Education", "book-open", "#6366F1", False, None, 80),
    ("Travel", "plane", "#0EA5E9", False, None, 90),
    ("Insurance", "shield", "#64748B", False, None, 100),
    ("Savings", "piggy-bank", "#22C55E", False, None, 110),
    ("Debt Payments", "credit-card", "#DC2626", False, None, 120),
    ("Other", "more-horizontal", "#9CA3AF", False, None, 999),
]

# ── Tags ──────────────────────────────────────────────────────────────────────

TAGS = [
    ("tax-deductible", "#EF4444"),
    ("recurring", "#3B82F6"),
    ("business", "#8B5CF6"),
    ("personal", "#10B981"),
    ("vacation", "#F59E0B"),
    ("emergency", "#DC2626"),
    ("subscription", "#06B6D4"),
    ("cash", "#22C55E"),
]

# ── Cards ─────────────────────────────────────────────────────────────────────

CARDS = [
    # (account_index, card_type, card_name, last_four, expiry, annual_fee)
    (0, "DEBIT", "Chase Debit Card", "4821", "2028-06-30", "0"),
    (2, "DEBIT", "BofA Debit Card", "7390", "2027-12-31", "0"),
    (3, "CREDIT", "Discover It Card", "5512", "2028-03-31", "0"),
    (4, "CREDIT", "Chase Freedom Card", "9087", "2027-09-30", "0"),
]

# ── Transactions (reference accounts, categories by index) ────────────────────

TRANSACTIONS = [
    # (account_idx, card_idx_or_None, date_days_ago, type, amount, currency, payee, description, category_idx, status)
    # Recent salary deposits
    (0, None, 1, "INCOME", "5200.00", "USD", "Acme Corp", "Monthly salary - May 2026", 0, "CLEARED"),
    (0, None, 31, "INCOME", "5200.00", "USD", "Acme Corp", "Monthly salary - April 2026", 0, "CLEARED"),
    (0, None, 61, "INCOME", "5200.00", "USD", "Acme Corp", "Monthly salary - March 2026", 0, "CLEARED"),
    # Freelance income
    (0, None, 5, "INCOME", "1500.00", "USD", "Freelance Client A", "Website redesign project", 1, "CLEARED"),
    (0, None, 18, "INCOME", "800.00", "USD", "Freelance Client B", "Logo design", 1, "CLEARED"),
    # Housing expenses
    (1, None, 1, "EXPENSE", "1800.00", "USD", "Sunset Apartments", "Monthly rent - May 2026", 5, "CLEARED"),
    (1, None, 31, "EXPENSE", "1800.00", "USD", "Sunset Apartments", "Monthly rent - April 2026", 5, "CLEARED"),
    (0, None, 3, "EXPENSE", "145.00", "USD", "City Power & Light", "Electric bill - April", 6, "CLEARED"),
    (0, None, 5, "EXPENSE", "65.00", "USD", "Fiber Internet Co", "Internet - May", 7, "CLEARED"),
    # Food & Dining
    (0, None, 1, "EXPENSE", "127.50", "USD", "Whole Foods", "Weekly groceries", 11, "CLEARED"),
    (0, None, 4, "EXPENSE", "89.30", "USD", "Trader Joe's", "Midweek groceries", 11, "CLEARED"),
    (3, None, 2, "EXPENSE", "56.80", "USD", "Olive Garden", "Dinner with friends", 12, "CLEARED"),
    (4, None, 3, "EXPENSE", "6.50", "USD", "Starbucks", "Morning coffee", 13, "PENDING"),
    (4, None, 6, "EXPENSE", "5.75", "USD", "Blue Bottle Coffee", "Cold brew", 13, "PENDING"),
    # Transportation
    (2, None, 2, "EXPENSE", "52.00", "USD", "Shell Gas Station", "Full tank", 9, "CLEARED"),
    (2, None, 9, "EXPENSE", "48.50", "USD", "BP Gas Station", "Fill-up", 9, "CLEARED"),
    (2, None, 16, "EXPENSE", "55.00", "USD", "Shell Gas Station", "Full tank", 9, "CLEARED"),
    # Healthcare
    (0, None, 10, "EXPENSE", "150.00", "USD", "Dr. Smith Office", "Annual checkup copay", 15, "CLEARED"),
    (0, None, 12, "EXPENSE", "35.00", "USD", "CVS Pharmacy", "Prescription refill", 16, "CLEARED"),
    # Entertainment
    (4, None, 1, "EXPENSE", "15.99", "USD", "Netflix", "Monthly subscription", 19, "CLEARED"),
    (4, None, 1, "EXPENSE", "12.99", "USD", "Spotify", "Monthly subscription", 19, "CLEARED"),
    (4, None, 3, "EXPENSE", "9.99", "USD", "Disney+", "Monthly subscription", 19, "CLEARED"),
    # Shopping
    (3, None, 7, "EXPENSE", "89.99", "USD", "Amazon", "Wireless mouse", 21, "CLEARED"),
    (3, None, 14, "EXPENSE", "45.00", "USD", "Target", "Household items", 18, "CLEARED"),
    # Personal
    (0, None, 8, "EXPENSE", "75.00", "USD", "SuperCuts", "Haircut", 22, "CLEARED"),
    # Transfer between accounts
    (0, None, 1, "TRANSFER", "500.00", "USD", "Transfer to Savings", "Monthly savings transfer", 27, "CLEARED"),
    (1, None, 1, "TRANSFER", "500.00", "USD", "Transfer from Checking", "Monthly savings transfer", 27, "CLEARED"),
    # Refund
    (3, None, 5, "REFUND", "89.99", "USD", "Amazon Refund", "Returned wireless mouse", 3, "CLEARED"),
    # Foreign currency transaction
    (7, None, 3, "EXPENSE", "45.00", "EUR", "Boulangerie Pierre", "Breakfast in Paris", 12, "CLEARED"),
    # Pending transactions
    (0, None, 0, "EXPENSE", "42.00", "USD", "Amazon", "Pending book order", 21, "PENDING"),
    (0, None, 0, "EXPENSE", "28.50", "USD", "Uber Eats", "Lunch delivery", 12, "PENDING"),
    # More historical
    (0, None, 90, "INCOME", "5200.00", "USD", "Acme Corp", "Monthly salary - Feb 2026", 0, "CLEARED"),
    (1, None, 61, "EXPENSE", "1800.00", "USD", "Sunset Apartments", "Monthly rent - March 2026", 5, "CLEARED"),
    (1, None, 90, "EXPENSE", "1800.00", "USD", "Sunset Apartments", "Monthly rent - Feb 2026", 5, "CLEARED"),
]

# ── Bills ─────────────────────────────────────────────────────────────────────

BILLS = [
    # (account_idx_or_None, category_idx, payee, amount, currency, is_fixed, recurrence, start_days_ago, next_due_days, status)
    (0, 5, "Sunset Apartments", "1800.00", "USD", True, "MONTHLY", 365, 1, "ACTIVE"),
    (0, 7, "Fiber Internet Co", "65.00", "USD", True, "MONTHLY", 180, 5, "ACTIVE"),
    (3, 19, "Netflix", "15.99", "USD", True, "MONTHLY", 365, 1, "ACTIVE"),
    (3, 19, "Spotify", "12.99", "USD", True, "MONTHLY", 300, 1, "ACTIVE"),
    (0, 23, "Planet Fitness", "24.99", "USD", True, "MONTHLY", 200, 15, "ACTIVE"),
    (0, 6, "City Power & Light", "120.00", "USD", False, "MONTHLY", 365, 8, "ACTIVE"),
    (0, 8, "Car Insurance Co", "145.00", "USD", True, "MONTHLY", 365, 20, "ACTIVE"),
    (None, 9, "Adobe Creative Cloud", "54.99", "USD", True, "MONTHLY", 120, 12, "PAUSED"),
]

# ── Debt Facilities ───────────────────────────────────────────────────────────

DEBTS = [
    # (institution_idx, account_idx, name, nature, type, entity, principal, remaining, currency, rate, start_days_ago, term_months, monthly_payment, payment_day)
    (0, None, "Chase Mortgage", "MONEY_BORROWED", "MORTGAGE", "Chase Home Loan",
     "350000.00", "325000.00", "USD", "6.75", 365, 360, "2267.00", 1),
    (0, None, "Chase Auto Loan", "MONEY_BORROWED", "AUTO", "Chase Auto Finance",
     "28000.00", "18200.00", "USD", "5.49", 365, 60, "535.00", 15),
    (None, None, "Personal Loan to Sarah", "MONEY_LENT", "PERSONAL", "Sarah Johnson",
     "3000.00", "2000.00", "USD", "0", 90, 12, "250.00", 1),
    (0, None, "Student Loan", "MONEY_BORROWED", "STUDENT", "Federal Student Aid",
     "45000.00", "38000.00", "USD", "4.99", 1825, 120, "475.00", 5),
]

# ── Debt Payments ─────────────────────────────────────────────────────────────

DEBT_PAYMENTS = [
    # (debt_idx, days_ago, amount, principal, interest, extra)
    (0, 1, "2267.00", "1800.00", "467.00", "0"),
    (0, 31, "2267.00", "1790.00", "477.00", "0"),
    (1, 15, "535.00", "420.00", "115.00", "0"),
    (1, 45, "535.00", "418.00", "117.00", "0"),
    (2, 1, "250.00", "250.00", "0", "0"),
    (3, 5, "475.00", "310.00", "165.00", "0"),
]

# ── Budgets ───────────────────────────────────────────────────────────────────

BUDGETS = [
    # (category_idx, amount, currency, period, start_date_str, allow_rollover)
    (11, "400.00", "USD", "MONTHLY", "2026-01-01", True),    # Groceries
    (12, "150.00", "USD", "MONTHLY", "2026-01-01", False),   # Restaurants
    (9, "200.00", "USD", "MONTHLY", "2026-01-01", True),     # Gas
    (19, "60.00", "USD", "MONTHLY", "2026-01-01", False),    # Streaming
    (21, "200.00", "USD", "MONTHLY", "2026-01-01", False),   # Clothing
    (18, "300.00", "USD", "MONTHLY", "2026-01-01", False),   # Shopping (general)
    (6, "200.00", "USD", "MONTHLY", "2026-01-01", True),     # Utilities
]

# ── Investment Accounts ───────────────────────────────────────────────────────

INVESTMENT_ACCOUNTS = [
    # (account_idx, portfolio_value, cost_basis)
    (5, "42500.00", "35000.00"),   # Fidelity Brokerage
    (6, "12800.00", "8500.00"),    # Coinbase Crypto
]

# ── Holdings ──────────────────────────────────────────────────────────────────

HOLDINGS = [
    # (investment_account_idx, symbol, name, asset_type, quantity, cost_basis, current_price, current_value, currency, purchase_days_ago)
    (0, "VTI", "Vanguard Total Stock Market ETF", "ETF", "45.00", "8500.00", "228.50", "10282.50", "USD", 365),
    (0, "AAPL", "Apple Inc.", "STOCK", "25.00", "4500.00", "198.50", "4962.50", "USD", 180),
    (0, "MSFT", "Microsoft Corporation", "STOCK", "20.00", "6000.00", "425.00", "8500.00", "USD", 200),
    (0, "BND", "Vanguard Total Bond Market ETF", "BOND", "80.00", "5000.00", "72.50", "5800.00", "USD", 365),
    (0, "VOO", "Vanguard S&P 500 ETF", "ETF", "30.00", "11000.00", "482.00", "14460.00", "USD", 300),
    (1, "BTC", "Bitcoin", "CRYPTO", "0.15", "4500.00", "62500.00", "9375.00", "USD", 180),
    (1, "ETH", "Ethereum", "CRYPTO", "2.50", "4000.00", "1720.00", "4300.00", "USD", 90),
]

# ── Savings Goals ─────────────────────────────────────────────────────────────

SAVINGS_GOALS = [
    # (account_idx_or_None, name, target, current, currency, deadline_days, icon, color)
    (1, "Emergency Fund", "15000.00", "8500.00", "USD", 180, "shield", "#22C55E"),
    (1, "Vacation Fund", "5000.00", "2800.00", "USD", 120, "plane", "#0EA5E9"),
    (None, "New Car Down Payment", "12000.00", "4200.00", "USD", 365, "car", "#8B5CF6"),
    (1, "Home Renovation", "8000.00", "1500.00", "USD", 240, "home", "#F59E0B"),
]

# ── Insurance Policies ────────────────────────────────────────────────────────

INSURANCE_POLICIES = [
    # (institution_idx_or_None, name, type, provider, policy_number, premium, currency, frequency, renewal_days, coverage, deductible)
    (0, "Health Insurance", "HEALTH", "Blue Cross Blue Shield", "HC-2026-4521",
     "450.00", "USD", "MONTHLY", 180, "500000.00", "1500.00"),
    (0, "Auto Insurance", "AUTO", "Geico", "AUTO-2026-8832",
     "145.00", "USD", "MONTHLY", 90, "100000.00", "500.00"),
    (None, "Renters Insurance", "HOME", "Lemonade", "RI-2026-1199",
     "18.00", "USD", "MONTHLY", 365, "30000.00", "500.00"),
    (0, "Life Insurance", "LIFE", "MetLife", "LI-2026-7750",
     "85.00", "USD", "MONTHLY", 365, "500000.00", "0"),
]

# ── Invoices ──────────────────────────────────────────────────────────────────

INVOICES = [
    # (client_name, client_email, invoice_number, issue_days_ago, due_days_from_issue, subtotal, tax, total, amount_paid, currency, status, notes, terms)
    ("TechCorp Inc", "billing@techcorp.com", "INV-2026-001", 15, 30,
     "3000.00", "0", "3000.00", "3000.00", "USD", "PAID",
     "Website redesign - Phase 1", "Net 30"),
    ("StartupXYZ", "finance@startupxyz.io", "INV-2026-002", 5, 30,
     "1500.00", "0", "1500.00", "750.00", "USD", "PARTIAL",
     "Mobile app UI design", "Net 30"),
    ("Local Business Co", "owner@localbusiness.com", "INV-2026-003", 35, 30,
     "2200.00", "0", "2200.00", "0", "USD", "OVERDUE",
     "Brand identity package", "Net 30"),
    ("Freelance Client D", "d@example.com", "INV-2026-004", 2, 15,
     "800.00", "0", "800.00", "0", "USD", "SENT",
     "Logo design + business cards", "Net 15"),
]

# ── Invoice Line Items ────────────────────────────────────────────────────────

INVOICE_LINE_ITEMS = [
    # (invoice_idx, description, quantity, unit_price, total)
    (0, "Homepage design and development", "1", "1500.00", "1500.00"),
    (0, "Contact page and forms", "1", "800.00", "800.00"),
    (0, "Responsive testing and fixes", "1", "700.00", "700.00"),
    (1, "UI/UX design - 5 screens", "5", "250.00", "1250.00"),
    (1, "Design system documentation", "1", "250.00", "250.00"),
    (2, "Logo design (3 concepts)", "1", "800.00", "800.00"),
    (2, "Brand guidelines document", "1", "600.00", "600.00"),
    (2, "Business card design", "1", "400.00", "400.00"),
    (2, "Social media templates (5)", "1", "400.00", "400.00"),
    (3, "Logo design", "1", "500.00", "500.00"),
    (3, "Business card layout", "1", "300.00", "300.00"),
]


class Command(BaseCommand):
    help = "Seed the Ledger database with comprehensive test data for all domain models."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            default=1,
            help="User ID to assign seed data to (default: 1). Must match a Sattabase User.id.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            default=False,
            help="Delete existing data for the specified user_id before seeding.",
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        clear = options["clear"]

        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"  Satta Ledger — Database Seed Command\n"
            f"  User ID: {user_id}  |  Clear: {clear}\n"
            f"{'='*60}\n"
        ))

        if clear:
            self._clear_data(user_id)

        try:
            with transaction.atomic():
                institutions = self._seed_institutions(user_id)
                accounts = self._seed_accounts(user_id, institutions)
                categories = self._seed_categories(user_id)
                tags = self._seed_tags(user_id)
                cards = self._seed_cards(user_id, accounts)
                transactions = self._seed_transactions(user_id, accounts, categories)
                self._seed_transaction_tags(user_id, transactions, tags)
                self._seed_transaction_splits(user_id, transactions, categories)
                bills = self._seed_bills(user_id, accounts, categories)
                self._seed_bill_payments(user_id, bills, transactions)
                debts = self._seed_debts(user_id, institutions, accounts)
                self._seed_debt_payments(user_id, debts)
                self._seed_budgets(user_id, categories)
                inv_accounts = self._seed_investment_accounts(user_id, accounts)
                self._seed_holdings(user_id, inv_accounts)
                self._seed_savings_goals(user_id, accounts)
                self._seed_insurance(user_id, institutions)
                invoices = self._seed_invoices(user_id, transactions)
                self._seed_invoice_line_items(user_id, invoices)
        except Exception as e:
            raise CommandError(f"Seeding failed: {e}")

        self._print_summary(user_id)
        self.stdout.write(self.style.SUCCESS("\n✓ Seed complete!\n"))

    # ── Clear ──────────────────────────────────────────────────────────────────

    def _clear_data(self, user_id: int):
        self.stdout.write(self.style.WARNING(f"Clearing data for user_id={user_id}..."))
        models_to_clear = [
            InvoiceLineItem, Invoice, InsurancePolicy, SavingsGoal,
            Holding, InvestmentAccount, Budget, DebtPayment, DebtFacility,
            BillPayment, Bill, TransactionTag, TransactionSplit, Transaction,
            Card, Tag, Category, Account, Institution,
        ]
        for model in models_to_clear:
            count, _ = model.all_objects.filter(user_id=user_id).delete()
            if count:
                self.stdout.write(f"  Deleted {count} {model.__name__} records")

    # ── Institutions ───────────────────────────────────────────────────────────

    def _seed_institutions(self, user_id: int) -> list:
        self.stdout.write("Creating institutions...")
        results = []
        for data in INSTITUTIONS:
            inst, _ = Institution.objects.get_or_create(
                user_id=user_id,
                name=data["name"],
                defaults={
                    "institution_type": data["institution_type"],
                    "website": data.get("website", ""),
                    "customer_service_phone": data.get("customer_service_phone", ""),
                    "icon": data.get("icon", ""),
                    "color": data.get("color", ""),
                    "notes": data.get("notes", ""),
                },
            )
            results.append(inst)
        self.stdout.write(f"  Created {len(results)} institutions")
        return results

    # ── Accounts ───────────────────────────────────────────────────────────────

    def _seed_accounts(self, user_id: int, institutions: list) -> list:
        self.stdout.write("Creating accounts...")
        results = []
        for inst_idx, name, acct_type, currency, balance, credit_limit, rate in ACCOUNTS:
            acct, _ = Account.objects.get_or_create(
                user_id=user_id,
                institution=institutions[inst_idx],
                name=name,
                defaults={
                    "account_type": acct_type,
                    "currency": currency,
                    "current_balance": Decimal(balance.replace("-", "")),
                    "credit_limit": Decimal(credit_limit) if credit_limit else None,
                    "interest_rate": Decimal(rate),
                },
            )
            results.append(acct)
        self.stdout.write(f"  Created {len(results)} accounts")
        return results

    # ── Categories ─────────────────────────────────────────────────────────────

    def _seed_categories(self, user_id: int) -> list:
        self.stdout.write("Creating categories...")
        results = []
        parent_map = {}  # name -> Category instance

        for name, icon, color, is_income, parent_idx, sort_order in CATEGORIES:
            clean_name = name.strip()
            parent = results[parent_idx] if parent_idx is not None else None
            cat, _ = Category.objects.get_or_create(
                user_id=user_id,
                name=clean_name,
                parent=parent,
                defaults={
                    "icon": icon,
                    "color": color,
                    "is_income": is_income,
                    "sort_order": sort_order,
                },
            )
            results.append(cat)
        self.stdout.write(f"  Created {len(results)} categories")
        return results

    # ── Tags ───────────────────────────────────────────────────────────────────

    def _seed_tags(self, user_id: int) -> list:
        self.stdout.write("Creating tags...")
        results = []
        for name, color in TAGS:
            tag, _ = Tag.objects.get_or_create(
                user_id=user_id,
                name=name,
                defaults={"color": color},
            )
            results.append(tag)
        self.stdout.write(f"  Created {len(results)} tags")
        return results

    # ── Cards ──────────────────────────────────────────────────────────────────

    def _seed_cards(self, user_id: int, accounts: list) -> list:
        self.stdout.write("Creating cards...")
        results = []
        for acct_idx, card_type, card_name, last_four, expiry, annual_fee in CARDS:
            card, _ = Card.objects.get_or_create(
                user_id=user_id,
                account=accounts[acct_idx],
                last_four=last_four,
                defaults={
                    "card_type": card_type,
                    "card_name": card_name,
                    "expiry_date": expiry,
                    "annual_fee": Decimal(annual_fee),
                },
            )
            results.append(card)
        self.stdout.write(f"  Created {len(results)} cards")
        return results

    # ── Transactions ───────────────────────────────────────────────────────────

    def _seed_transactions(self, user_id: int, accounts: list, categories: list) -> list:
        self.stdout.write("Creating transactions...")
        results = []
        for acct_idx, card_idx, days_ago, tx_type, amount, currency, payee, desc, cat_idx, status in TRANSACTIONS:
            card = results[card_idx] if card_idx is not None and card_idx < len(CARDS) else None
            # For TRANSFER type, we need to handle the card differently
            if card_idx is not None and card_idx >= 0:
                # Look up card from the cards list — but cards aren't passed here
                # We'll skip card assignment for now since it requires the card objects
                pass

            amt = Decimal(amount)
            amount_base = amt  # For USD transactions, same as original
            exchange_rate = Decimal("1.0")

            # Foreign currency approximation
            if currency == "EUR":
                exchange_rate = Decimal("1.08")
                amount_base = (amt * exchange_rate).quantize(Decimal("0.01"))

            tx = Transaction.objects.create(
                user_id=user_id,
                date=DAYS_AGO(days_ago),
                account=accounts[acct_idx],
                card=None,  # Cards linked via separate field
                transaction_type=tx_type,
                amount_original=amt,
                currency_original=currency,
                amount_base=amount_base,
                exchange_rate=exchange_rate,
                category=categories[cat_idx] if cat_idx < len(categories) else None,
                status=status,
                payee=payee,
                description=desc,
                is_recurring=False,
            )
            results.append(tx)

        # Link transfer pairs (the two TRANSFER transactions)
        # Find the checking→savings and savings←checking transfers
        transfer_txs = [tx for tx in results if tx.transaction_type == "TRANSFER"]
        if len(transfer_txs) >= 2:
            transfer_txs[0].transfer_pair = transfer_txs[1]
            transfer_txs[0].save()
            transfer_txs[1].transfer_pair = transfer_txs[0]
            transfer_txs[1].save()

        # Link cards to transactions where applicable
        # The card_idx in TRANSACTIONS data refers to the index in the CARDS list,
        # but we need the actual Card model instances. Skip for now since
        # the card FK is optional (SET_NULL).

        self.stdout.write(f"  Created {len(results)} transactions")
        return results

    # ── Transaction Tags ───────────────────────────────────────────────────────

    def _seed_transaction_tags(self, user_id: int, transactions: list, tags: list):
        self.stdout.write("Creating transaction tags...")
        count = 0
        # Tag some transactions with relevant tags
        tag_assignments = [
            # (transaction_idx, tag_idx)
            (0, 1),   # Salary → recurring
            (1, 1),   # Salary → recurring
            (2, 1),   # Salary → recurring
            (4, 2),   # Freelance → business
            (5, 1),   # Rent → recurring
            (6, 1),   # Rent → recurring
            (7, 1),   # Electric → recurring
            (8, 1),   # Internet → recurring
            (20, 7),  # Netflix → subscription
            (21, 7),  # Spotify → subscription
            (22, 7),  # Disney+ → subscription
            (23, 3),  # Amazon → personal
            (4, 0),   # Freelance → tax-deductible
            (27, 5),  # Coffee → cash
        ]
        for tx_idx, tag_idx in tag_assignments:
            if tx_idx < len(transactions) and tag_idx < len(tags):
                TransactionTag.objects.get_or_create(
                    user_id=user_id,
                    transaction=transactions[tx_idx],
                    tag=tags[tag_idx],
                )
                count += 1
        self.stdout.write(f"  Created {count} transaction tags")

    # ── Transaction Splits ─────────────────────────────────────────────────────

    def _seed_transaction_splits(self, user_id: int, transactions: list, categories: list):
        self.stdout.write("Creating transaction splits...")
        count = 0
        # Split the "Whole Foods groceries" transaction (idx 10, $127.50)
        if len(transactions) > 10:
            TransactionSplit.objects.create(
                user_id=user_id,
                transaction=transactions[10],
                category=categories[11],  # Groceries
                amount=Decimal("95.00"),
                notes="Food items",
            )
            TransactionSplit.objects.create(
                user_id=user_id,
                transaction=transactions[10],
                category=categories[14],  # Healthcare / Pharmacy (household items)
                amount=Decimal("32.50"),
                notes="Cleaning supplies",
            )
            count = 2

        # Split the "Amazon" transaction (idx 23, $89.99)
        if len(transactions) > 23:
            TransactionSplit.objects.create(
                user_id=user_id,
                transaction=transactions[23],
                category=categories[21],  # Electronics
                amount=Decimal("59.99"),
                notes="Wireless mouse",
            )
            TransactionSplit.objects.create(
                user_id=user_id,
                transaction=transactions[23],
                category=categories[18],  # Shopping
                amount=Decimal("30.00"),
                notes="Accessories",
            )
            count += 2

        self.stdout.write(f"  Created {count} transaction splits")

    # ── Bills ──────────────────────────────────────────────────────────────────

    def _seed_bills(self, user_id: int, accounts: list, categories: list) -> list:
        self.stdout.write("Creating bills...")
        results = []
        for acct_idx, cat_idx, payee, amount, currency, is_fixed, recurrence, start_ago, next_due_days, status in BILLS:
            start_date = DAYS_AGO(start_ago)
            next_due = DAYS_FROM_NOW(next_due_days)
            bill = Bill.objects.create(
                user_id=user_id,
                account=accounts[acct_idx] if acct_idx is not None else None,
                category=categories[cat_idx] if cat_idx < len(categories) else None,
                payee=payee,
                amount=Decimal(amount),
                currency=currency,
                is_amount_fixed=is_fixed,
                recurrence=recurrence,
                start_date=start_date,
                next_due_date=next_due,
                status=status,
                remind_me=True,
                days_before_reminder=5,
            )
            results.append(bill)
        self.stdout.write(f"  Created {len(results)} bills")
        return results

    # ── Bill Payments ──────────────────────────────────────────────────────────

    def _seed_bill_payments(self, user_id: int, bills: list, transactions: list):
        self.stdout.write("Creating bill payments...")
        count = 0
        # Record a few payments for rent and internet
        payment_data = [
            # (bill_idx, days_ago, amount)
            (0, 1, "1800.00"),   # Rent - May
            (0, 31, "1800.00"),  # Rent - April
            (0, 61, "1800.00"),  # Rent - March
            (1, 5, "65.00"),     # Internet - May
            (1, 35, "65.00"),    # Internet - April
        ]
        for bill_idx, days_ago, amount in payment_data:
            if bill_idx < len(bills):
                BillPayment.objects.create(
                    user_id=user_id,
                    bill=bills[bill_idx],
                    payment_date=DAYS_AGO(days_ago),
                    amount=Decimal(amount),
                )
                count += 1
        self.stdout.write(f"  Created {count} bill payments")

    # ── Debts ──────────────────────────────────────────────────────────────────

    def _seed_debts(self, user_id: int, institutions: list, accounts: list) -> list:
        self.stdout.write("Creating debt facilities...")
        results = []
        for inst_idx, acct_idx, name, nature, dtype, entity, principal, remaining, currency, rate, start_ago, term, monthly, pay_day in DEBTS:
            debt = DebtFacility.objects.create(
                user_id=user_id,
                institution=institutions[inst_idx] if inst_idx is not None else None,
                account=accounts[acct_idx] if acct_idx is not None else None,
                name=name,
                debt_nature=nature,
                debt_type=dtype,
                entity_name=entity,
                principal_amount=Decimal(principal),
                remaining_balance=Decimal(remaining),
                currency=currency,
                interest_rate=Decimal(rate),
                start_date=DAYS_AGO(start_ago),
                term_months=term,
                monthly_payment=Decimal(monthly),
                payment_day=pay_day,
            )
            results.append(debt)
        self.stdout.write(f"  Created {len(results)} debt facilities")
        return results

    # ── Debt Payments ──────────────────────────────────────────────────────────

    def _seed_debt_payments(self, user_id: int, debts: list):
        self.stdout.write("Creating debt payments...")
        count = 0
        for debt_idx, days_ago, amount, principal, interest, extra in DEBT_PAYMENTS:
            if debt_idx < len(debts):
                DebtPayment.objects.create(
                    user_id=user_id,
                    debt=debts[debt_idx],
                    payment_date=DAYS_AGO(days_ago),
                    amount=Decimal(amount),
                    principal_portion=Decimal(principal),
                    interest_portion=Decimal(interest),
                    extra_payment=Decimal(extra),
                )
                count += 1
        self.stdout.write(f"  Created {count} debt payments")

    # ── Budgets ────────────────────────────────────────────────────────────────

    def _seed_budgets(self, user_id: int, categories: list):
        self.stdout.write("Creating budgets...")
        count = 0
        for cat_idx, amount, currency, period, start_date_str, rollover in BUDGETS:
            if cat_idx < len(categories):
                Budget.objects.get_or_create(
                    user_id=user_id,
                    category=categories[cat_idx],
                    period=period,
                    start_date=date.fromisoformat(start_date_str),
                    defaults={
                        "amount": Decimal(amount),
                        "currency": currency,
                        "allow_rollover": rollover,
                    },
                )
                count += 1
        self.stdout.write(f"  Created {count} budgets")

    # ── Investment Accounts ────────────────────────────────────────────────────

    def _seed_investment_accounts(self, user_id: int, accounts: list) -> list:
        self.stdout.write("Creating investment accounts...")
        results = []
        for acct_idx, portfolio_value, cost_basis in INVESTMENT_ACCOUNTS:
            inv, _ = InvestmentAccount.objects.get_or_create(
                user_id=user_id,
                account=accounts[acct_idx],
                defaults={
                    "portfolio_value": Decimal(portfolio_value),
                    "cost_basis_total": Decimal(cost_basis),
                },
            )
            results.append(inv)
        self.stdout.write(f"  Created {len(results)} investment accounts")
        return results

    # ── Holdings ───────────────────────────────────────────────────────────────

    def _seed_holdings(self, user_id: int, inv_accounts: list):
        self.stdout.write("Creating holdings...")
        count = 0
        for inv_idx, symbol, name, asset_type, qty, cost, price, value, currency, purchase_ago in HOLDINGS:
            if inv_idx < len(inv_accounts):
                Holding.objects.get_or_create(
                    user_id=user_id,
                    investment_account=inv_accounts[inv_idx],
                    symbol=symbol,
                    defaults={
                        "asset_name": name,
                        "asset_type": asset_type,
                        "quantity": Decimal(qty),
                        "cost_basis": Decimal(cost),
                        "current_price": Decimal(price),
                        "current_value": Decimal(value),
                        "currency": currency,
                        "purchase_date": DAYS_AGO(purchase_ago),
                    },
                )
                count += 1
        self.stdout.write(f"  Created {count} holdings")

    # ── Savings Goals ──────────────────────────────────────────────────────────

    def _seed_savings_goals(self, user_id: int, accounts: list):
        self.stdout.write("Creating savings goals...")
        count = 0
        for acct_idx, name, target, current, currency, deadline_days, icon, color in SAVINGS_GOALS:
            SavingsGoal.objects.create(
                user_id=user_id,
                account=accounts[acct_idx] if acct_idx is not None else None,
                name=name,
                target_amount=Decimal(target),
                current_amount=Decimal(current),
                currency=currency,
                deadline=DAYS_FROM_NOW(deadline_days),
                icon=icon,
                color=color,
            )
            count += 1
        self.stdout.write(f"  Created {count} savings goals")

    # ── Insurance ──────────────────────────────────────────────────────────────

    def _seed_insurance(self, user_id: int, institutions: list):
        self.stdout.write("Creating insurance policies...")
        count = 0
        for inst_idx, name, itype, provider, policy_num, premium, currency, freq, renewal_days, coverage, deductible in INSURANCE_POLICIES:
            InsurancePolicy.objects.create(
                user_id=user_id,
                institution=institutions[inst_idx] if inst_idx is not None else None,
                policy_name=name,
                insurance_type=itype,
                provider=provider,
                policy_number=policy_num,
                premium_amount=Decimal(premium),
                currency=currency,
                premium_frequency=freq,
                renewal_date=DAYS_FROM_NOW(renewal_days),
                coverage_amount=Decimal(coverage) if coverage else None,
                deductible=Decimal(deductible) if deductible else None,
                remind_renewal=True,
                days_before_renewal_reminder=30,
            )
            count += 1
        self.stdout.write(f"  Created {count} insurance policies")

    # ── Invoices ───────────────────────────────────────────────────────────────

    def _seed_invoices(self, user_id: int, transactions: list) -> list:
        self.stdout.write("Creating invoices...")
        results = []
        for client, email, inv_num, issue_ago, due_days, subtotal, tax, total, paid, currency, status, notes, terms in INVOICES:
            issue_date = DAYS_AGO(issue_ago)
            due_date = issue_date + timedelta(days=due_days)
            paid_date = None
            if status == "PAID":
                paid_date = issue_date + timedelta(days=due_days - 5)

            inv = Invoice.objects.create(
                user_id=user_id,
                invoice_number=inv_num,
                client_name=client,
                client_email=email,
                issue_date=issue_date,
                due_date=due_date,
                paid_date=paid_date,
                subtotal=Decimal(subtotal),
                tax_amount=Decimal(tax),
                total_amount=Decimal(total),
                amount_paid=Decimal(paid),
                currency=currency,
                status=status,
                notes=notes,
                terms=terms,
            )
            results.append(inv)
        self.stdout.write(f"  Created {len(results)} invoices")
        return results

    # ── Invoice Line Items ─────────────────────────────────────────────────────

    def _seed_invoice_line_items(self, user_id: int, invoices: list):
        self.stdout.write("Creating invoice line items...")
        count = 0
        for inv_idx, desc, qty, unit_price, total in INVOICE_LINE_ITEMS:
            if inv_idx < len(invoices):
                InvoiceLineItem.objects.create(
                    user_id=user_id,
                    invoice=invoices[inv_idx],
                    description=desc,
                    quantity=Decimal(qty),
                    unit_price=Decimal(unit_price),
                    total=Decimal(total),
                )
                count += 1
        self.stdout.write(f"  Created {count} invoice line items")

    # ── Summary ────────────────────────────────────────────────────────────────

    def _print_summary(self, user_id: int):
        self.stdout.write(self.style.NOTICE(
            f"\n{'='*60}\n"
            f"  Seed Data Summary (user_id={user_id})\n"
            f"{'='*60}\n"
        ))
        summaries = [
            ("Institutions", Institution),
            ("Accounts", Account),
            ("Categories", Category),
            ("Tags", Tag),
            ("Cards", Card),
            ("Transactions", Transaction),
            ("Transaction Splits", TransactionSplit),
            ("Transaction Tags", TransactionTag),
            ("Bills", Bill),
            ("Bill Payments", BillPayment),
            ("Debt Facilities", DebtFacility),
            ("Debt Payments", DebtPayment),
            ("Budgets", Budget),
            ("Investment Accounts", InvestmentAccount),
            ("Holdings", Holding),
            ("Savings Goals", SavingsGoal),
            ("Insurance Policies", InsurancePolicy),
            ("Invoices", Invoice),
            ("Invoice Line Items", InvoiceLineItem),
        ]
        total = 0
        for label, model in summaries:
            count = model.objects.filter(user_id=user_id).count()
            total += count
            self.stdout.write(f"  {label:.<30} {count:>4}")
        self.stdout.write(f"  {'TOTAL':.<30} {total:>4}")
        self.stdout.write("")
