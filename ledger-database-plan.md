# Ledger Database Plan

> **Project**: Sattabase Ledger — Sister Domain  
> **Status**: Draft — Awaiting Approval  
> **Date**: May 2026  

---

## Table of Contents

1. [Architecture Principles](#1-architecture-principles)
2. [Abstract Base Models](#2-abstract-base-models)
3. [Module 1 — Core (Accounts & Transactions)](#3-module-1--core-accounts--transactions)
4. [Module 2 — Categories & Tags](#4-module-2--categories--tags)
5. [Module 3 — Cards](#5-module-3--cards)
6. [Module 4 — Debt & Loans](#6-module-4--debt--loans)
7. [Module 5 — Bills & Recurring Payments](#7-module-5--bills--recurring-payments)
8. [Module 6 — Budgets](#8-module-6--budgets)
9. [Module 7 — Investments & Holdings](#9-module-7--investments--holdings)
10. [Module 8 — Savings Goals](#10-module-8--savings-goals)
11. [Module 9 — Insurance](#11-module-9--insurance)
12. [Module 10 — Invoices (Freelancer)](#12-module-10--invoices-freelancer)
13. [Module 11 — Document Vault](#13-module-11--document-vault)
14. [Analysis of Your Original Plan](#14-analysis-of-your-original-plan)
15. [Removed / Merged Models](#15-removed--merged-models)
16. [New Models Not in Original Plan](#16-new-models-not-in-original-plan)
17. [Multi-Currency Architecture](#17-multi-currency-architecture)
18. [Entity Relationship Summary](#18-entity-relationship-summary)
19. [Recommended Implementation Phases](#19-recommended-implementation-phases)

---

## 1. Architecture Principles

### 1.1 User Identity — No Local User Model

Ledger is a **sister domain** of Sattabase. Users are authenticated by the base backend via `sattabase_sdk.middleware.SattabaseAuthMiddleware`, which populates `request.sattabase_user` with the user's profile. The User model lives in the base backend — Ledger must **never** have its own User table or a Django FK to a local User model.

Instead, every user-owned model uses a **`user_id` integer field** (PositiveIntegerField) that references `Sattabase User.id`. This is the established pattern in the existing `TestNote` model and matches how the SDK middleware works.

### 1.2 Currency Metadata — No Local Currency Table

Currency metadata (symbol, name, decimal_digits) is the **single source of truth** in the base backend's `CURRENCY_META` dict, exposed via `GET /billing/currencies` and piggybacked on `auth/me`. Ledger's `api/currency.py` already caches this in Redis (24h TTL). Therefore:

- **No `Currency` model in Ledger**. No local table duplicating what the base backend owns.
- Account and Transaction store **ISO 4217 codes as CharField(3)**, not FKs to a Currency table.
- Display formatting uses `format_currency()` from `api/currency.py`, which reads from the cached metadata.

### 1.3 Exchange Rates — Store at Transaction Time

When a transaction is created in a foreign currency:

1. The backend calls `convert_amount()` from `api/currency.py` to get the rate and converted amount.
2. Both `exchange_rate` and `amount_base` are **stored on the Transaction row** at creation time.
3. This preserves historical accuracy — even if rates change later, the original conversion is immutable.
4. Dashboards can additionally show **current value** by calling `get_current_value()` which uses the latest cached rates.

### 1.4 Soft Deletes

Financial data should rarely be hard-deleted. All models inherit `SoftDeleteModel` from `common/models.py` (which provides `is_deleted` + `deleted_at`). Queries should default to `is_deleted=False` via a custom manager.

### 1.5 Module Organization

Models are grouped into logical modules (Django apps) rather than one monolithic `models.py`. This keeps migrations independent and allows per-module API versioning:

| App | Models | Purpose |
|-----|--------|---------|
| `api` | (existing TestNote — remove later) | Shared app, will be restructured |
| `core` | Account, Transaction, Institution | The ledger — where money is tracked |
| `categories` | Category, Tag, TransactionTag | Classification & labeling |
| `cards` | Card | Debit/credit cards linked to accounts |
| `debt` | DebtFacility, DebtPayment | Loans & mortgages |
| `bills` | Bill, BillPayment | Recurring obligations |
| `budgets` | Budget, BudgetPeriod | Spending limits |
| `investments` | InvestmentAccount, Holding | Stocks, crypto, bonds |
| `goals` | SavingsGoal | Target-based savings |
| `insurance` | InsurancePolicy | Coverage tracking |
| `invoices` | Invoice, InvoiceLineItem | Freelancer invoicing |
| `vault` | DocumentVault | Secure document storage |

> **Simpler alternative**: Keep all models in the `api` app but split them into separate files (`api/models_core.py`, `api/models_debt.py`, etc.) and import them in `api/models.py`. This avoids the overhead of managing 12 Django apps while still keeping the code organized. The choice depends on team size and deployment complexity.

---

## 2. Abstract Base Models

### 2.1 UserOwnedModel (Replace Your Original)

Your original `UserOwnedModel` used `models.ForeignKey(settings.AUTH_USER_MODEL, ...)`. Since Ledger has no local User model, this must change to `user_id` as a plain integer field.

```python
# common/models.py — ADD this alongside existing TimeStampedModel, SoftDeleteModel, ActivatorModel

class UserOwnedModel(TimeStampedModel, SoftDeleteModel, ActivatorModel):
    """
    Abstract base for all user-owned entities in Ledger.
    
    - user_id: Integer reference to Sattabase User.id (NOT a Django FK)
    - created_at / updated_at: From TimeStampedModel
    - is_deleted / deleted_at: From SoftDeleteModel (soft deletes for financial data)
    - is_active / activated_at: From ActivatorModel (deactivate without deleting)
    """
    user_id = models.PositiveIntegerField(
        db_index=True,
        help_text="Sattabase User.id — the central identity reference",
    )

    class Meta:
        abstract = True
```

**Why this design:**

| Concern | Decision | Reason |
|---------|----------|--------|
| User FK | `user_id` (int), not Django FK | User table lives in base backend; no local User model exists |
| Timestamps | Inherited from `TimeStampedModel` | Every financial record needs audit trail |
| Soft delete | Inherited from `SoftDeleteModel` | Financial records should never be hard-deleted; balance recalculation needs history |
| Active/inactive | Inherited from `ActivatorModel` | Accounts, cards, goals can be deactivated without deletion |
| All three | Multiple inheritance | Clean — each concern is a mixin, no duplication |

**Custom Manager (recommended addition):**

```python
class ActiveManager(models.Manager):
    """Default manager that excludes soft-deleted records."""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class UserOwnedModel(TimeStampedModel, SoftDeleteModel, ActivatorModel):
    user_id = models.PositiveIntegerField(db_index=True, ...)
    
    objects = ActiveManager()       # Default: excludes deleted
    all_objects = models.Manager()  # Includes deleted (for admin/audit)
    
    class Meta:
        abstract = True
```

---

## 3. Module 1 — Core (Accounts & Transactions)

### 3.1 Institution

Banks, crypto exchanges, brokerage firms — the entities that hold accounts.

```python
class Institution(UserOwnedModel):
    """Financial institution where accounts are held.
    
    Examples: Chase Bank, HSBC, Binance, Fidelity, "Cash (Wallet)"
    """
    name = models.CharField(max_length=100)
    institution_type = models.CharField(
        max_length=20,
        choices=[
            ('BANK', 'Bank'),
            ('CREDIT_UNION', 'Credit Union'),
            ('BROKERAGE', 'Brokerage'),
            ('CRYPTO', 'Crypto Exchange'),
            ('WALLET', 'Digital Wallet'),
            ('OTHER', 'Other'),
        ],
        default='BANK',
    )
    website = models.URLField(blank=True)
    customer_service_phone = models.CharField(max_length=20, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name from icon library")
    color = models.CharField(max_length=7, blank=True, help_text="Hex color for UI, e.g. #1A73E8")
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "core_institution"
        ordering = ["name"]
        unique_together = [("user_id", "name")]

    def __str__(self):
        return self.name
```

**Changes from your original:**

| Your Version | Revised | Why |
|---|---|---|
| — | `institution_type` | Needed for UI grouping and filtering (show all banks together, all crypto together) |
| — | `icon` | Icons make the UI much more recognizable (bank logo placeholders) |
| — | `color` | Visual identification in dashboard cards |
| — | `notes` | Users want to store account numbers, branch info, etc. |
| — | `unique_together` | Prevent duplicate institutions per user |

### 3.2 Account

The core entity — where money lives.

```python
class Account(UserOwnedModel):
    """The Ledger: Where money is tracked.
    
    Every transaction belongs to an account. Accounts can be assets (checking, savings),
    liabilities (credit cards, loans), or investment (brokerage, crypto).
    
    Currency is stored as ISO 4217 code (CharField) — NOT a FK to a Currency model.
    Currency metadata (symbol, name, decimal_digits) comes from the base backend's
    /billing/currencies endpoint, cached in Redis by api/currency.py.
    """
    ACCOUNT_TYPES = [
        ('ASSET', 'Asset (Cash, Savings, Checking)'),
        ('LIABILITY', 'Liability (Credit Card, Personal Loan)'),
        ('INVESTMENT', 'Investment (Brokerage, Crypto)'),
    ]

    name = models.CharField(max_length=100)
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name='accounts'
    )
    account_type = models.CharField(max_length=15, choices=ACCOUNT_TYPES)
    currency = models.CharField(
        max_length=3, default='USD',
        help_text="ISO 4217 code. Metadata from base backend /billing/currencies.",
    )
    
    # ── Balance tracking ──
    # current_balance is denormalized for dashboard performance.
    # The authoritative source is always the sum of transactions.
    current_balance = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Denormalized. Recalculated from transactions. In account currency.",
    )
    
    # ── Credit / Loan fields ──
    credit_limit = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text="Only for LIABILITY accounts (credit cards, lines of credit).",
    )
    interest_rate = models.DecimalField(
        max_digits=6, decimal_places=3, default=0,
        help_text="APR as percentage (e.g. 24.99 = 24.99%). Only for LIABILITY accounts.",
    )
    
    # ── Credit Card billing cycle ──
    statement_closing_day = models.IntegerField(
        null=True, blank=True,
        help_text="Day of month when statement closes (e.g. 15). Only for credit cards.",
    )
    due_day = models.IntegerField(
        null=True, blank=True,
        help_text="Day of month when payment is due (e.g. 1). Only for credit cards.",
    )
    
    # ── Display ──
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, blank=True, help_text="Hex color for UI")
    notes = models.TextField(blank=True)
    
    # ── Sorting ──
    sort_order = models.IntegerField(default=0, help_text="Manual sort order in UI")

    class Meta:
        db_table = "core_account"
        ordering = ["sort_order", "name"]
        unique_together = [("user_id", "institution", "name")]

    @property
    def available_credit(self):
        """Available credit = credit_limit - current_balance (for liability accounts)."""
        if self.account_type == 'LIABILITY' and self.credit_limit:
            return self.credit_limit - self.current_balance
        return None  # Not applicable — distinguish from 0

    @property
    def currency_symbol(self):
        """Get symbol from cached base backend metadata."""
        from api.currency import get_currency_symbol
        return get_currency_symbol(self.currency)

    def recalculate_balance(self):
        """Recalculate current_balance from transactions. Call after bulk operations."""
        from django.db.models import Sum, Case, When, Value, DecimalField
        # This will be implemented with proper sign logic based on transaction type
        ...
        self.save(update_fields=['current_balance', 'updated_at'])
```

**Changes from your original:**

| Your Version | Revised | Why |
|---|---|---|
| `currency = FK('Currency')` | `currency = CharField(3)` | No local Currency model — base backend is the source of truth |
| `interest_rate = Decimal(5,2)` | `interest_rate = Decimal(6,3)` | APR can be 24.99% or 0.125% (crypto lending) — need 3 decimal places |
| — | `icon`, `color`, `notes` | UI display and user customization |
| — | `sort_order` | Users want manual control over account ordering |
| — | `unique_together` | Prevent duplicate account names within same institution |
| — | `recalculate_balance()` | Denormalized balance needs a recalculation method |
| — | `available_credit` returns `None` | Distinguish "not applicable" from "zero available credit" |

### 3.3 Transaction

The heart of the ledger — every financial movement.

```python
class Transaction(UserOwnedModel):
    """A single financial transaction.
    
    Multi-currency architecture:
    - amount_original + currency_original: What was actually spent/received (foreign currency)
    - amount_base: Converted to user's base currency at transaction time (for reports)
    - exchange_rate: Rate captured at transaction creation (immutable historical record)
    
    For same-currency transactions: amount_original == amount_base, exchange_rate == 1.0
    
    Internal transfers (e.g. paying credit card from checking):
    - Two Transaction rows linked via transfer_pair (OneToOneField)
    - One is the "outflow" from Account A, the other is the "inflow" to Account B
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CLEARED', 'Cleared'),
        ('VOID', 'Void'),
    ]
    
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('TRANSFER', 'Transfer'),
        ('REFUND', 'Refund'),
    ]

    # ── Core ──
    date = models.DateField(db_index=True)
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='transactions'
    )
    card = models.ForeignKey(
        'cards.Card', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transactions',
    )
    transaction_type = models.CharField(
        max_length=10, choices=TRANSACTION_TYPES, default='EXPENSE',
    )
    
    # ── Amounts ──
    amount_original = models.DecimalField(
        max_digits=18, decimal_places=2,
        help_text="Amount in the original (transaction) currency. Always positive.",
    )
    currency_original = models.CharField(
        max_length=3, default='USD',
        help_text="ISO 4217 code of the transaction currency.",
    )
    amount_base = models.DecimalField(
        max_digits=18, decimal_places=2,
        help_text="Amount converted to user's base currency at transaction time.",
    )
    exchange_rate = models.DecimalField(
        max_digits=18, decimal_places=8,
        help_text="Rate used for conversion: amount_base = amount_original * exchange_rate",
    )
    
    # ── Classification ──
    category = models.ForeignKey(
        'categories.Category', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='transactions',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='CLEARED')
    
    # ── Description ──
    payee = models.CharField(
        max_length=200, blank=True,
        help_text="Who was paid or who paid you. E.g. 'Amazon', 'Salary from Acme Corp'",
    )
    description = models.TextField(blank=True)
    reference_number = models.CharField(
        max_length=100, blank=True,
        help_text="Check number, transaction ID, or reference from bank statement",
    )
    
    # ── Internal Transfers ──
    transfer_pair = models.OneToOneField(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='linked_transfer',
        help_text="For TRANSFER type: links the outflow and inflow transactions.",
    )
    
    # ── Metadata ──
    is_recurring = models.BooleanField(default=False, help_text="Auto-set if created from a Bill")
    bill = models.ForeignKey(
        'bills.Bill', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='generated_transactions',
        help_text="If this transaction was auto-generated from a recurring bill.",
    )

    class Meta:
        db_table = "core_transaction"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user_id", "date"], name="idx_txn_user_date"),
            models.Index(fields=["user_id", "account_id", "date"], name="idx_txn_acct_date"),
            models.Index(fields=["user_id", "category_id"], name="idx_txn_user_cat"),
            models.Index(fields=["user_id", "transaction_type"], name="idx_txn_user_type"),
        ]

    def save(self, *args, **kwargs):
        """Auto-convert currency on creation if not already set."""
        if not self.pk and self.amount_base == 0:
            self._convert_to_base_currency()
        super().save(*args, kwargs)
        # Update account balance
        self.account.recalculate_balance()

    def _convert_to_base_currency(self):
        """Convert amount_original to user's base currency using current rates."""
        from api.currency import convert_amount, get_currency_symbol
        # Get user's base currency from request context or account default
        base_currency = self.currency_original  # Will be overridden from user profile
        if self.currency_original != base_currency:
            converted, rate = convert_amount(
                self.amount_original, self.currency_original, base_currency
            )
            if converted is not None:
                self.amount_base = converted
                self.exchange_rate = rate
                return
        # Same currency or conversion failed — use 1:1
        self.amount_base = self.amount_original
        self.exchange_rate = Decimal("1.0")

    def __str__(self):
        return f"{self.date} | {self.payee or 'N/A'} | {self.amount_original} {self.currency_original}"
```

**Changes from your original:**

| Your Version | Revised | Why |
|---|---|---|
| `currency_original = FK('Currency')` | `currency_original = CharField(3)` | No local Currency model |
| `transfer_transaction` | `transfer_pair` | Better naming — it's a pair, not one-directional |
| — | `transaction_type` | Explicit INCOME/EXPENSE/TRANSFER/REFUND — essential for reporting and sign logic |
| — | `payee` | Critical for transaction search and grouping ("show all Amazon purchases") |
| — | `reference_number` | Check numbers, bank reference IDs — needed for reconciliation |
| — | `is_recurring`, `bill` FK | Link auto-generated transactions back to their Bill source |
| — | `description` (TextField) | Your original had none — users need notes on transactions |
| — | Database indexes | Performance: transactions table will be the largest, needs proper indexing |
| — | `_convert_to_base_currency()` in save() | Auto-conversion on creation — the "store rate at transaction time" pattern |

### 3.4 TransactionSplit (NEW)

For split transactions — when one transaction covers multiple categories.

```python
class TransactionSplit(UserOwnedModel):
    """A portion of a transaction assigned to a specific category.
    
    Example: A $100 Walmart purchase split into:
      - $60 Groceries (category: Food)
      - $30 Electronics (category: Shopping)  
      - $10 Household (category: Home)
    
    The sum of all splits for a transaction must equal the transaction's amount_original.
    """
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name='splits'
    )
    category = models.ForeignKey(
        'categories.Category', on_delete=models.SET_NULL, null=True,
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "core_transaction_split"

    def clean(self):
        """Validate that splits don't exceed transaction amount."""
        from django.core.exceptions import ValidationError
        total = TransactionSplit.objects.filter(
            transaction=self.transaction
        ).exclude(pk=self.pk).aggregate(total=Sum('amount'))['total'] or 0
        if total + self.amount > self.transaction.amount_original:
            raise ValidationError("Split amounts exceed transaction total.")
```

---

## 4. Module 2 — Categories & Tags

### 4.1 Category

```python
class Category(UserOwnedModel):
    """Transaction category with optional hierarchy.
    
    Supports nested subcategories via parent FK.
    is_income determines whether the category represents income (True) or expense (False).
    
    Examples:
      - Food (parent=None, is_income=False)
        - Groceries (parent=Food, is_income=False)
        - Dining Out (parent=Food, is_income=False)
      - Salary (parent=None, is_income=True)
      - Freelance (parent=None, is_income=True)
    """
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name from icon library")
    color = models.CharField(max_length=7, blank=True, help_text="Hex color for charts and UI")
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='subcategories',
    )
    is_income = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "categories_category"
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"
        unique_together = [("user_id", "name", "parent")]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
```

**Changes from your original:**

| Your Version | Revised | Why |
|---|---|---|
| — | `color` | Categories need distinct colors for charts and budget visuals |
| — | `sort_order` | Users want custom ordering, not just alphabetical |
| — | `unique_together` | Prevent duplicate category names at same level |

### 4.2 Tag (NEW)

Tags are flat, cross-cutting labels — unlike categories which are hierarchical.

```python
class Tag(UserOwnedModel):
    """Flat, cross-cutting label for transactions.
    
    Unlike categories (hierarchical, mutually exclusive), tags are flat and additive.
    A transaction has ONE category but can have MANY tags.
    
    Examples: #vacation2026, #tax-deductible, #business, #reimbursable
    """
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, blank=True)

    class Meta:
        db_table = "categories_tag"
        ordering = ["name"]
        unique_together = [("user_id", "name")]

    def __str__(self):
        return f"#{self.name}"
```

### 4.3 TransactionTag (NEW — M2M Through)

```python
class TransactionTag(UserOwnedModel):
    """Many-to-many link between Transaction and Tag."""
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name='tag_links'
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='transaction_links')

    class Meta:
        db_table = "categories_transaction_tag"
        unique_together = [("transaction", "tag")]
```

> **Why not Django's ManyToManyField?** Because we need `user_id` on the through table for consistent ownership queries and soft-delete support.

---

## 5. Module 3 — Cards

### 5.1 Card

```python
class Card(UserOwnedModel):
    """Debit or credit card linked to an account.
    
    Cards exist because one account can have multiple cards (e.g., joint credit card
    with authorized users, debit card + ATM card on same checking account).
    Transactions can optionally specify which card was used.
    """
    CARD_TYPES = [
        ('DEBIT', 'Debit'),
        ('CREDIT', 'Credit'),
    ]

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name='cards'
    )
    card_type = models.CharField(max_length=10, choices=CARD_TYPES)
    card_name = models.CharField(
        max_length=50,
        help_text="E.g., 'Amazon Prime Visa', 'Chase Sapphire Reserve'",
    )
    last_four = models.CharField(max_length=4)
    expiry_date = models.DateField(null=True, blank=True)
    
    # ── Fee tracking ──
    annual_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Annual fee for this card.",
    )
    annual_fee_date = models.DateField(
        null=True, blank=True,
        help_text="When the annual fee is charged.",
    )
    
    # ── Display ──
    color = models.CharField(max_length=7, blank=True, help_text="Card color for UI")
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "cards_card"
        ordering = ["sort_order", "card_name"]
        unique_together = [("user_id", "account", "last_four")]
```

**Changes from your original:**

| Your Version | Revised | Why |
|---|---|---|
| — | `color` | Visual identification — users want to see card colors |
| — | `sort_order` | Manual ordering |
| — | `unique_together` | Prevent duplicate cards |

---

## 6. Module 4 — Debt & Loans

### 6.1 DebtFacility (Merged from your Debt + DebtFacility)

Your original plan had **two overlapping models**: `Debt` and `DebtFacility`. Both tracked loans with principal, interest rate, and payment schedules. They are consolidated into one model.

```python
class DebtFacility(UserOwnedModel):
    """A loan, mortgage, or lending arrangement.
    
    Covers both sides:
    - MONEY_BORROWED: You owe someone (liability) — bank loan, credit card debt, mortgage
    - MONEY_LENT: Someone owes you (asset) — personal loan you gave, mortgage you hold
    
    Payments against this debt are tracked in DebtPayment records.
    The linked Account tracks the running balance.
    """
    DEBT_NATURE = [
        ('MONEY_BORROWED', 'Money Borrowed (I owe)'),
        ('MONEY_LENT', 'Money Lent (They owe me)'),
    ]
    
    DEBT_TYPES = [
        ('MORTGAGE', 'Mortgage'),
        ('PERSONAL', 'Personal Loan'),
        ('STUDENT', 'Student Loan'),
        ('AUTO', 'Auto Loan'),
        ('BUSINESS', 'Business Loan'),
        ('INFORMAL', 'Informal Loan (Friends/Family)'),
    ]

    name = models.CharField(max_length=100, help_text="E.g., 'Chase Mortgage', 'Loan to John'")
    debt_nature = models.CharField(
        max_length=15, choices=DEBT_NATURE,
        help_text="Who owes whom? MONEY_BORROWED = you owe; MONEY_LENT = they owe you",
    )
    debt_type = models.CharField(max_length=15, choices=DEBT_TYPES)
    
    # ── Counterparty ──
    entity_name = models.CharField(
        max_length=100,
        help_text="Lender name (if borrowed) or borrower name (if lent)",
    )
    institution = models.ForeignKey(
        Institution, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Link to institution if it's a bank loan (optional).",
    )
    
    # ── Terms ──
    principal_amount = models.DecimalField(max_digits=18, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    interest_rate = models.DecimalField(
        max_digits=6, decimal_places=3,
        help_text="APR as percentage (e.g. 6.5 = 6.5%)",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    term_months = models.IntegerField(null=True, blank=True, help_text="E.g., 360 for 30-year mortgage")
    
    # ── Payment schedule ──
    monthly_payment = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text="Minimum or agreed monthly payment amount.",
    )
    payment_day = models.IntegerField(
        null=True, blank=True,
        help_text="Day of month when payment is due.",
    )
    
    # ── Linked account ──
    account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='linked_debts',
        help_text="Account used for payments on this debt.",
    )
    
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "debt_debt_facility"
        ordering = ["-remaining_balance"]

    @property
    def is_mine(self):
        """True if this is money I borrowed (I owe someone)."""
        return self.debt_nature == 'MONEY_BORROWED'

    @property
    def progress_percent(self):
        """How much of the principal has been paid off."""
        if self.principal_amount == 0:
            return 100
        paid = self.principal_amount - self.remaining_balance
        return round((paid / self.principal_amount) * 100, 1)
```

### 6.2 DebtPayment (NEW)

Track individual payments against a debt facility.

```python
class DebtPayment(UserOwnedModel):
    """A single payment made against a DebtFacility.
    
    Each payment breaks down into:
    - Principal portion (reduces remaining_balance)
    - Interest portion (cost of borrowing)
    - Extra payment (additional principal reduction)
    
    This enables amortization schedules and interest tracking.
    """
    debt = models.ForeignKey(
        DebtFacility, on_delete=models.CASCADE, related_name='payments'
    )
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Total payment amount")
    principal_portion = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    interest_portion = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    extra_payment = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # ── Auto-generated transaction link ──
    transaction = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="If this payment was recorded as a transaction.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "debt_debt_payment"
        ordering = ["-payment_date"]
```

**Why this is better than your original two models:**

| Your Version | Problem | Resolution |
|---|---|---|
| `Debt` + `DebtFacility` | Overlapping fields: both have entity_name/lender_name, principal, interest_rate, dates, account FK | Merged into `DebtFacility` with `debt_nature` field to distinguish borrowed vs lent |
| `Debt.type` had MORTGAGE_TAKEN/MORTGAGE_HELD | Confusing — two axes (type + direction) mixed into one choice field | Separated: `debt_type` (what kind) + `debt_nature` (who owes whom) |
| No payment tracking | Can't see amortization or interest paid over time | Added `DebtPayment` with principal/interest/extra breakdown |
| `DebtFacility.lender_name` was CharField | Can't link to Institution for bank loans | Added optional `institution` FK |

---

## 7. Module 5 — Bills & Recurring Payments

### 7.1 Bill

Your original `Bill` was too simple — it didn't support recurring bills properly.

```python
class Bill(UserOwnedModel):
    """Recurring or one-time bill/subscription.
    
    Examples: Netflix ($15.99/mo), Rent ($1,500/mo), Annual insurance premium,
    Electricity (variable amount), Spotify, Domain renewal.
    
    Supports:
    - Fixed amount bills (Netflix) and variable amount bills (Electricity)
    - Multiple recurrence periods (weekly, monthly, yearly)
    - Automatic transaction generation on due date
    - Notification reminders before due date
    """
    RECURRENCE_CHOICES = [
        ('WEEKLY', 'Weekly'),
        ('BIWEEKLY', 'Every 2 Weeks'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
        ('ONE_TIME', 'One Time'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('PAUSED', 'Paused'),
        ('CANCELLED', 'Cancelled'),
    ]

    payee = models.CharField(max_length=100, help_text="Who gets paid (e.g., 'Netflix', 'Landlord')")
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        help_text="Expected amount. 0 for variable bills like electricity.",
    )
    currency = models.CharField(max_length=3, default='USD')
    is_amount_fixed = models.BooleanField(
        default=True,
        help_text="If True, amount is always the same. If False, amount varies each period.",
    )
    
    # ── Recurrence ──
    recurrence = models.CharField(max_length=10, choices=RECURRENCE_CHOICES, default='MONTHLY')
    start_date = models.DateField(help_text="When this bill first started")
    end_date = models.DateField(null=True, blank=True, help_text="When this bill ends (blank = ongoing)")
    next_due_date = models.DateField(help_text="Next payment due date (auto-updated after each payment)")
    
    # ── Account ──
    account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Account used to pay this bill.",
    )
    category = models.ForeignKey(
        'categories.Category', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Default category for auto-generated transactions.",
    )
    
    # ── Status ──
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    
    # ── Reminders ──
    remind_me = models.BooleanField(default=True)
    days_before_reminder = models.IntegerField(default=5, help_text="Days before due date to send reminder")
    
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "bills_bill"
        ordering = ["next_due_date"]

    def generate_transaction(self):
        """Create a Transaction from this bill (called by Celery on due date)."""
        if self.status != 'ACTIVE':
            return None
        txn = Transaction.objects.create(
            user_id=self.user_id,
            date=self.next_due_date,
            account=self.account,
            transaction_type='EXPENSE',
            amount_original=self.amount,
            currency_original=self.currency,
            amount_base=self.amount,  # Will be converted in save()
            exchange_rate=Decimal("1.0"),
            category=self.category,
            payee=self.payee,
            description=f"Auto-generated from bill: {self.payee}",
            is_recurring=True,
            bill=self,
        )
        # Advance next_due_date
        self._advance_next_due_date()
        return txn

    def _advance_next_due_date(self):
        """Move next_due_date forward by one period."""
        from dateutil.relativedelta import relativedelta
        if self.recurrence == 'WEEKLY':
            self.next_due_date += relativedelta(weeks=1)
        elif self.recurrence == 'BIWEEKLY':
            self.next_due_date += relativedelta(weeks=2)
        elif self.recurrence == 'MONTHLY':
            self.next_due_date += relativedelta(months=1)
        elif self.recurrence == 'QUARTERLY':
            self.next_due_date += relativedelta(months=3)
        elif self.recurrence == 'YEARLY':
            self.next_due_date += relativedelta(years=1)
        self.save(update_fields=['next_due_date', 'updated_at'])
```

### 7.2 BillPayment (NEW)

Track individual payments against bills.

```python
class BillPayment(UserOwnedModel):
    """Record of a payment made for a Bill.
    
    For fixed-amount bills, the amount usually matches the bill amount.
    For variable-amount bills (electricity), the actual amount is recorded here.
    """
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="The transaction created by this payment.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "bills_bill_payment"
        ordering = ["-payment_date"]
```

**Changes from your original Bill:**

| Your Version | Revised | Why |
|---|---|---|
| Single `due_date` | `start_date` + `next_due_date` + `end_date` | Recurring bills need a start date and auto-advancing next due date |
| Single `amount` | `amount` + `is_amount_fixed` | Some bills vary (electricity, gas) — need to track expected vs actual |
| No recurrence | `recurrence` with WEEKLY/BIWEEKLY/MONTHLY/QUARTERLY/YEARLY/ONE_TIME | Bills recur at different intervals |
| `is_paid` boolean | `status` (ACTIVE/PAUSED/CANCELLED) | A boolean is too simplistic — bills can be paused and resumed |
| No category | `category` FK | Auto-generated transactions need a default category |
| No account | `account` FK | Need to know which account pays the bill |
| — | `generate_transaction()` | Auto-generate transactions from bills via Celery task |
| — | `BillPayment` model | Track payment history for variable-amount bills |

---

## 8. Module 6 — Budgets

### 8.1 Budget

```python
class Budget(UserOwnedModel):
    """Spending limit for a category over a time period.
    
    Supports monthly and weekly budgets. The `spent_amount` is denormalized
    and recalculated from transactions for performance.
    """
    PERIOD_CHOICES = [
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]

    category = models.ForeignKey(
        'categories.Category', on_delete=models.CASCADE,
        related_name='budgets',
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Budget limit")
    currency = models.CharField(max_length=3, default='USD')
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='MONTHLY')
    start_date = models.DateField(help_text="When this budget period starts")
    
    # ── Rollover ──
    allow_rollover = models.BooleanField(
        default=False,
        help_text="If True, unspent amount rolls over to next period.",
    )

    class Meta:
        db_table = "budgets_budget"
        ordering = ["-start_date"]
        unique_together = [("user_id", "category", "period", "start_date")]

    @property
    def spent_amount(self):
        """Calculate total spent in this budget period from transactions."""
        from django.db.models import Sum, Q
        from django.utils import timezone
        
        end_date = self._get_end_date()
        return Transaction.objects.filter(
            user_id=self.user_id,
            category=self.category,
            transaction_type='EXPENSE',
            date__gte=self.start_date,
            date__lte=end_date,
            status='CLEARED',
            is_deleted=False,
        ).aggregate(total=Sum('amount_base'))['total'] or Decimal("0")

    @property
    def remaining(self):
        return self.amount - self.spent_amount

    @property
    def percent_used(self):
        if self.amount == 0:
            return 0
        return min(round((self.spent_amount / self.amount) * 100, 1), 100)

    def _get_end_date(self):
        from dateutil.relativedelta import relativedelta
        if self.period == 'WEEKLY':
            return self.start_date + relativedelta(weeks=1)
        elif self.period == 'MONTHLY':
            return self.start_date + relativedelta(months=1)
        elif self.period == 'YEARLY':
            return self.start_date + relativedelta(years=1)
        return self.start_date
```

**Changes from your original:**

| Your Version | Revised | Why |
|---|---|---|
| `period` was CharField with no choices | Proper `PERIOD_CHOICES` + added YEARLY | Users want yearly budgets too |
| — | `currency` | Budgets need currency for multi-currency users |
| — | `allow_rollover` | Common feature request — unspent budget rolls over |
| — | `spent_amount` computed property | Real-time budget tracking |
| — | `unique_together` | Prevent duplicate budgets for same category/period |

---

## 9. Module 7 — Investments & Holdings

### 9.1 InvestmentAccount (NEW — wraps Account)

Your original had both `Investment` and `InvestmentHolding` as separate models with overlapping fields. The proper design is: an `InvestmentAccount` (which IS an Account) contains multiple `Holding` records.

```python
class InvestmentAccount(UserOwnedModel):
    """Extension of Account for investment/brokerage accounts.
    
    An Account with account_type=INVESTMENT can optionally have this
    extension model for investment-specific tracking (overall portfolio
    value, unrealized gains/losses).
    """
    account = models.OneToOneField(
        Account, on_delete=models.CASCADE, related_name='investment_profile'
    )
    portfolio_value = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Total current value of all holdings.",
    )
    cost_basis_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text="Total amount invested across all holdings.",
    )
    last_synced_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When holdings were last updated from market data.",
    )

    class Meta:
        db_table = "investments_investment_account"

    @property
    def unrealized_gain_loss(self):
        return self.portfolio_value - self.cost_basis_total

    @property
    def unrealized_gain_loss_percent(self):
        if self.cost_basis_total == 0:
            return 0
        return round((self.unrealized_gain_loss / self.cost_basis_total) * 100, 2)
```

### 9.2 Holding (Replaces your Investment + InvestmentHolding)

```python
class Holding(UserOwnedModel):
    """A single investment position within an InvestmentAccount.
    
    Examples: 10 shares of AAPL, 0.5 BTC, $5,000 in Vanguard Total Market Index.
    """
    ASSET_TYPES = [
        ('STOCK', 'Stock'),
        ('ETF', 'ETF'),
        ('CRYPTO', 'Cryptocurrency'),
        ('BOND', 'Bond'),
        ('MUTUAL_FUND', 'Mutual Fund'),
        ('OTHER', 'Other'),
    ]

    investment_account = models.ForeignKey(
        InvestmentAccount, on_delete=models.CASCADE, related_name='holdings'
    )
    symbol = models.CharField(max_length=20, help_text="Ticker symbol: AAPL, BTC, VTI")
    asset_name = models.CharField(max_length=100, help_text="Full name: Apple Inc., Bitcoin, Vanguard Total Stock Market")
    asset_type = models.CharField(max_length=15, choices=ASSET_TYPES)
    
    # ── Position ──
    quantity = models.DecimalField(max_digits=18, decimal_places=8, help_text="Shares/units held")
    cost_basis = models.DecimalField(
        max_digits=18, decimal_places=2,
        help_text="Total amount paid for this position (not per-share).",
    )
    current_price = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text="Latest market price per unit (updated via API).",
    )
    current_value = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text="quantity * current_price (updated via API).",
    )
    currency = models.CharField(max_length=3, default='USD')
    
    # ── Metadata ──
    purchase_date = models.DateField(null=True, blank=True)
    last_price_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "investments_holding"
        ordering = ["-current_value"]
        unique_together = [("user_id", "investment_account", "symbol")]

    @property
    def unrealized_gain_loss(self):
        if self.current_value and self.cost_basis:
            return self.current_value - self.cost_basis
        return None

    @property
    def average_purchase_price(self):
        if self.quantity and self.quantity > 0:
            return self.cost_basis / self.quantity
        return None
```

**Why this replaces your two models:**

| Your Version | Problem | Resolution |
|---|---|---|
| `Investment` (standalone) | Duplicate of Holding — both track symbol, quantity, price, type | Removed — all investment tracking goes through `Holding` |
| `InvestmentHolding.account` FK to Account | No way to track portfolio-level metrics | Created `InvestmentAccount` as an extension of Account |
| No portfolio rollup | Can't see total portfolio value/gain | `InvestmentAccount.portfolio_value` + `cost_basis_total` |

---

## 10. Module 8 — Savings Goals

### 8.1 SavingsGoal

```python
class SavingsGoal(UserOwnedModel):
    """Target-based savings tracker.
    
    Users can create goals like 'Emergency Fund ($10,000)' or 'Vacation ($3,000)'
    and track progress over time. Contributions are linked to transactions.
    """
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    deadline = models.DateField(null=True, blank=True)
    
    # ── Linked account ──
    account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Account where this savings is held.",
    )
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, blank=True)

    class Meta:
        db_table = "goals_savings_goal"
        ordering = ["deadline"]

    @property
    def progress_percent(self):
        if self.target_amount == 0:
            return 100
        return min(round((self.current_amount / self.target_amount) * 100, 1), 100)

    @property
    def remaining(self):
        return max(self.target_amount - self.current_amount, 0)

    @property
    def is_completed(self):
        return self.current_amount >= self.target_amount

    @property
    def days_remaining(self):
        if not self.deadline:
            return None
        from django.utils import timezone
        delta = self.deadline - timezone.now().date()
        return max(delta.days, 0)
```

**Changes from your original:**

| Your Version | Revised | Why |
|---|---|---|
| — | `currency` | Multi-currency users need to know which currency the goal is in |
| — | `account` FK | Link savings to the account holding the money |
| — | `icon`, `color` | Visual customization for goal cards |
| — | Computed properties | Progress, remaining, is_completed, days_remaining — essential for UI |

---

## 11. Module 9 — Insurance

### 9.1 InsurancePolicy

```python
class InsurancePolicy(UserOwnedModel):
    """Insurance policy tracker.
    
    Track premiums, renewal dates, and coverage details for all types
    of insurance (health, auto, home, life, travel, etc.).
    """
    INSURANCE_TYPES = [
        ('HEALTH', 'Health'),
        ('AUTO', 'Auto'),
        ('HOME', 'Home/Renters'),
        ('LIFE', 'Life'),
        ('TRAVEL', 'Travel'),
        ('BUSINESS', 'Business'),
        ('OTHER', 'Other'),
    ]

    policy_name = models.CharField(max_length=100, help_text="E.g., 'Blue Cross Health', 'Geico Auto'")
    insurance_type = models.CharField(max_length=10, choices=INSURANCE_TYPES, default='OTHER')
    provider = models.CharField(max_length=100)
    institution = models.ForeignKey(
        Institution, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Link to institution if provider is in your institutions list.",
    )
    policy_number = models.CharField(max_length=100, blank=True)
    
    # ── Premium ──
    premium_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    premium_frequency = models.CharField(
        max_length=10, choices=[
            ('MONTHLY', 'Monthly'),
            ('QUARTERLY', 'Quarterly'),
            ('YEARLY', 'Yearly'),
        ],
        default='MONTHLY',
    )
    renewal_date = models.DateField()
    
    # ── Coverage ──
    coverage_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text="Total coverage amount.",
    )
    coverage_details = models.TextField(blank=True)
    deductible = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
    )
    
    # ── Reminders ──
    remind_renewal = models.BooleanField(default=True)
    days_before_renewal_reminder = models.IntegerField(default=30)

    class Meta:
        db_table = "insurance_insurance_policy"
        ordering = ["renewal_date"]
```

**Changes from your original:**

| Your Version | Revised | Why |
|---|---|---|
| — | `insurance_type` | Categorize policies for dashboard grouping |
| — | `institution` FK | Link to institution for unified financial view |
| — | `premium_frequency` | Premiums aren't always monthly — some are yearly |
| — | `coverage_amount`, `deductible` | Key insurance details users want to track |
| — | `currency` | Multi-currency support |
| — | `remind_renewal`, `days_before_renewal_reminder` | Insurance renewals are important reminders |

---

## 12. Module 10 — Invoices (Freelancer)

### 12.1 Invoice

```python
class Invoice(UserOwnedModel):
    """Invoice for freelancers/solopreneurs.
    
    Track invoices sent to clients, from creation to payment.
    Linked to a Transaction when payment is received.
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('VIEWED', 'Viewed'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    ]

    invoice_number = models.CharField(max_length=50)
    client_name = models.CharField(max_length=100)
    client_email = models.EmailField(blank=True)
    
    # ── Dates ──
    issue_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    
    # ── Amounts ──
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    
    # ── Status ──
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    
    # ── Link to transaction when paid ──
    transaction = models.ForeignKey(
        Transaction, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="The income transaction created when this invoice is paid.",
    )
    
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True, help_text="Payment terms (e.g., 'Net 30')")

    class Meta:
        db_table = "invoices_invoice"
        ordering = ["-issue_date"]
        unique_together = [("user_id", "invoice_number")]

    @property
    def amount_due(self):
        return self.total_amount - self.amount_paid

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.status not in ('PAID', 'CANCELLED') and self.due_date < timezone.now().date()
```

### 12.2 InvoiceLineItem (NEW)

```python
class InvoiceLineItem(UserOwnedModel):
    """A line item on an invoice."""
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='line_items'
    )
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(max_digits=15, decimal_places=2, help_text="quantity * unit_price")

    class Meta:
        db_table = "invoices_invoice_line_item"
        ordering = ["id"]
```

**Changes from your original:**

| Your Version | Revised | Why |
|---|---|---|
| `amount_due` (single field) | `subtotal` + `tax_amount` + `total_amount` + `amount_paid` | Proper invoice structure with tax support |
| 3 statuses (UNPAID/PARTIAL/PAID) | 7 statuses (DRAFT/SENT/VIEWED/PARTIAL/PAID/OVERDUE/CANCELLED) | Full invoice lifecycle tracking |
| — | `client_email` | Needed for sending invoices |
| — | `paid_date` | When was it actually paid? |
| — | `transaction` FK | Link payment to income transaction |
| — | `terms` | Payment terms are standard on invoices |
| — | `InvoiceLineItem` | Invoices need itemized lines, not just a flat amount |

---

## 13. Module 11 — Document Vault

### 13.1 DocumentVault

```python
class DocumentVault(UserOwnedModel):
    """Secure document storage linked to financial items.
    
    Uses Django's ContentType framework for generic relations — a document
    can be attached to any model (Account, InsurancePolicy, Transaction, etc.).
    """
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='vault/%Y/%m/')
    file_type = models.CharField(max_length=50, blank=True, help_text="Auto-detected: PDF, PNG, JPG, etc.")
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    
    # ── Expiry tracking ──
    expiry_date = models.DateField(
        null=True, blank=True,
        help_text="For documents that expire: IDs, insurance policies, certificates.",
    )
    remind_before_expiry = models.BooleanField(default=False)
    days_before_expiry_reminder = models.IntegerField(default=30)
    
    # ── Generic relation ──
    content_type = models.ForeignKey(
        'contenttypes.ContentType', on_delete=models.CASCADE
    )
    object_id = models.PositiveIntegerField()
    # To access the linked object: doc.content_object (needs GenericForeignKey)

    class Meta:
        db_table = "vault_document"

    def save(self, *args, **kwargs):
        """Auto-detect file type and size."""
        if self.file:
            self.file_size = self.file.size
            name = self.file.name.lower()
            if name.endswith('.pdf'):
                self.file_type = 'PDF'
            elif name.endswith(('.png', '.jpg', '.jpeg')):
                self.file_type = 'IMAGE'
            elif name.endswith('.xlsx'):
                self.file_type = 'EXCEL'
            elif name.endswith('.csv'):
                self.file_type = 'CSV'
            else:
                self.file_type = 'OTHER'
        super().save(*args, **kwargs)
```

**Changes from your original:**

| Your Version | Revised | Why |
|---|---|---|
| — | `file_type`, `file_size` | Auto-detected metadata for display and filtering |
| — | `remind_before_expiry`, `days_before_expiry_reminder` | Expiry reminders are the main value of document tracking |

---

## 14. Analysis of Your Original Plan

### Issues Found and Fixed

| # | Issue | Original | Fix | Impact |
|---|-------|----------|-----|--------|
| 1 | **User FK** | `ForeignKey(settings.AUTH_USER_MODEL)` | `user_id = PositiveIntegerField` | User table doesn't exist in Ledger — would crash at migration |
| 2 | **Currency FK** | `ForeignKey('Currency')` on Account & Transaction | `CharField(3)` — ISO code stored, metadata from base backend | No Currency model defined — would crash. Also violates single source of truth |
| 3 | **No Currency model** | Referenced but never defined | Removed entirely — base backend owns currency metadata | Architectural correctness |
| 4 | **Debt + DebtFacility overlap** | Two models with ~80% field overlap | Merged into `DebtFacility` with `debt_nature` field | Simpler schema, less confusion |
| 5 | **Investment + InvestmentHolding overlap** | Two models tracking same thing | `InvestmentAccount` (extension) + `Holding` (per-position) | Cleaner ownership hierarchy |
| 6 | **Bill too simple** | No recurrence, single due_date, `is_paid` boolean | Full recurrence system, status lifecycle, `BillPayment` | Required for real recurring bills |
| 7 | **No Tag model** | Only Category for classification | Added `Tag` + `TransactionTag` (flat labels) | Cross-cutting labels (#vacation, #business) |
| 8 | **No TransactionSplit** | One category per transaction | Added `TransactionSplit` | Split transactions are essential (Walmart = groceries + electronics) |
| 9 | **No transaction_type** | Category's `is_income` determines sign | Explicit `INCOME/EXPENSE/TRANSFER/REFUND` | Critical for balance calculation and reporting |
| 10 | **No payee field** | Transactions had no payee | Added `payee` | Essential for search and grouping |
| 11 | **No soft delete** | Records could be hard-deleted | `SoftDeleteModel` mixin | Financial data must be recoverable |
| 12 | **No indexes** | Transaction table would be slow | Added composite indexes on user_id, date, account | Performance at scale |
| 13 | **Missing currency on several models** | Budget, SavingsGoal, Bill, Invoice had no currency | Added `currency` CharField(3) everywhere | Multi-currency support |
| 14 | **No BillPayment** | Bills had no payment history | Added `BillPayment` model | Variable-amount bills need per-payment tracking |
| 15 | **No InvoiceLineItem** | Invoice was a flat amount | Added itemized line items | Professional invoices need itemization |

---

## 15. Removed / Merged Models

| Original Model | Disposition | Reason |
|---|---|---|
| `Debt` | **Merged into DebtFacility** | 80% field overlap with DebtFacility. The `debt_nature` field (MONEY_BORROWED/MONEY_LENT) replaces the confusing type choices that mixed loan kind with direction |
| `Investment` | **Replaced by Holding** | InvestmentHolding already had all the same fields plus more. Investment was a simplified duplicate |
| `Currency` (implied) | **Not created** | Base backend is the single source of truth for currency metadata. No local Currency table |

---

## 16. New Models Not in Original Plan

| Model | Module | Why It's Needed |
|---|---|---|
| `TransactionSplit` | Core | Split transactions across categories (essential feature) |
| `Tag` + `TransactionTag` | Categories | Flat, cross-cutting labels that categories can't provide |
| `DebtPayment` | Debt | Track individual payments with principal/interest breakdown |
| `BillPayment` | Bills | Track payment history for variable-amount recurring bills |
| `InvestmentAccount` | Investments | Portfolio-level rollups (total value, total gain/loss) |
| `InvoiceLineItem` | Invoices | Itemized invoices — a flat amount isn't professional |

---

## 17. Multi-Currency Architecture

### How It Works End-to-End

```
┌─────────────────────────────────────────────────────────────────┐
│                    BASE BACKEND (Source of Truth)                │
│  CURRENCY_META dict → /billing/currencies → auth/me piggyback   │
│  ExchangeRate model → /billing/exchange-rates → Celery daily    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    API calls + Redis cache
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                    LEDGER BACKEND (Consumer)                     │
│  api/currency.py:                                               │
│    ├─ get_currencies_meta() → Redis cache (24h TTL)             │
│    ├─ get_currency_symbol(code) → cached meta → "$"            │
│    ├─ convert_amount(amt, from, to) → (converted, rate)        │
│    ├─ get_current_value(amt, from, base) → latest rate         │
│    └─ format_currency(amt, code) → "$1,234.56"                 │
│                                                                 │
│  Transaction creation flow:                                     │
│    1. User enters: 100 EUR on their USD-base account            │
│    2. Backend calls convert_amount(100, "EUR", "USD")           │
│    3. Stores: amount_original=100, currency_original="EUR",     │
│              amount_base=108.50, exchange_rate=1.08500000       │
│    4. Historical accuracy: rate is frozen at creation time       │
│    5. Dashboard "current value": get_current_value() → latest   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    API response + session storage
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                    LEDGER FRONTEND (Consumer)                    │
│  src/lib/currency.ts:                                           │
│    ├─ cacheCurrenciesMeta() → localStorage (persistent)         │
│    ├─ cacheExchangeRates() → sessionStorage (per-session)       │
│    ├─ formatCurrency(amt, code) → "€100.00" or "$108.50"       │
│    ├─ convertAmount(amt, from, to) → client-side conversion    │
│    └─ getCurrencySymbol(code) → cached meta → "€"              │
└─────────────────────────────────────────────────────────────────┘
```

### Currency Fields by Model

| Model | Currency Field | Purpose |
|---|---|---|
| Account | `currency` CharField(3) | Account's native currency |
| Transaction | `currency_original` CharField(3) | Transaction currency (may differ from account) |
| Transaction | `amount_base` Decimal | Converted to user's base currency (for reports) |
| Transaction | `exchange_rate` Decimal | Rate frozen at creation time |
| DebtFacility | `currency` CharField(3) | Debt denomination |
| Bill | `currency` CharField(3) | Bill denomination |
| Budget | `currency` CharField(3) | Budget denomination |
| Holding | `currency` CharField(3) | Investment currency |
| SavingsGoal | `currency` CharField(3) | Goal denomination |
| InsurancePolicy | `currency` CharField(3) | Premium currency |
| Invoice | `currency` CharField(3) | Invoice denomination |

---

## 18. Entity Relationship Summary

```
Institution ──┐
              │ 1:N
              ▼
           Account ──────────────────────────────────────┐
           │ │ │                                        │
     1:N   │ │ │ 1:N                              1:1   │
           │ │ │                                        │
    ┌──────┘ │ └──────┐                    InvestmentAccount
    │        │        │                           │ 1:N
    ▼        ▼        ▼                           ▼
  Card   Transaction  DebtFacility            Holding
           │ │ │        │
     1:N   │ │ │   1:N  │
           │ │ │        ▼
    ┌──────┘ │ └────┐  DebtPayment
    │        │      │
    ▼        ▼      ▼
 Category  Tag    Bill
    │        │      │
    │  M:N   │  1:N │
    └───┬────┘      ▼
        │       BillPayment
  TransactionTag
        
Category ──→ Budget
Account  ──→ SavingsGoal
Institution ──→ InsurancePolicy
Invoice ──→ InvoiceLineItem
Transaction ──→ TransactionSplit
ContentType ──→ DocumentVault (generic FK)
```

---

## 19. Recommended Implementation Phases

### Phase 1 — Core (Start Here)
The absolute minimum for a working ledger: accounts and transactions.

| Model | Priority |
|---|---|
| `UserOwnedModel` (abstract) | Critical |
| `Institution` | Critical |
| `Account` | Critical |
| `Category` | Critical |
| `Transaction` | Critical |
| `TransactionSplit` | High |

**Deliverables**: CRUD APIs, balance tracking, multi-currency conversion, basic dashboard.

### Phase 2 — Bills & Budgets
Monthly financial planning features.

| Model | Priority |
|---|---|
| `Bill` | High |
| `BillPayment` | Medium |
| `Budget` | High |
| `Tag` + `TransactionTag` | Medium |

**Deliverables**: Recurring bill management, auto-transaction generation (Celery), budget tracking UI.

### Phase 3 — Cards & Debt
Credit management and loan tracking.

| Model | Priority |
|---|---|
| `Card` | High |
| `DebtFacility` | High |
| `DebtPayment` | Medium |

**Deliverables**: Card management, debt amortization, credit utilization tracking.

### Phase 4 — Investments
Portfolio tracking (requires market data API integration).

| Model | Priority |
|---|---|
| `InvestmentAccount` | Medium |
| `Holding` | Medium |

**Deliverables**: Portfolio dashboard, unrealized gains/losses, market data sync.

### Phase 5 — Goals, Insurance, Invoices, Vault
Extended features for power users and freelancers.

| Model | Priority |
|---|---|
| `SavingsGoal` | Medium |
| `InsurancePolicy` | Low |
| `Invoice` + `InvoiceLineItem` | Medium (if freelancer feature) |
| `DocumentVault` | Low |

**Deliverables**: Goal tracking, insurance reminders, invoice creation/payment, document upload.

---

## Final Model Count

| Module | Models |
|---|---|
| Abstract | 1 (UserOwnedModel) |
| Core | 4 (Institution, Account, Transaction, TransactionSplit) |
| Categories | 3 (Category, Tag, TransactionTag) |
| Cards | 1 (Card) |
| Debt | 2 (DebtFacility, DebtPayment) |
| Bills | 2 (Bill, BillPayment) |
| Budgets | 1 (Budget) |
| Investments | 2 (InvestmentAccount, Holding) |
| Goals | 1 (SavingsGoal) |
| Insurance | 1 (InsurancePolicy) |
| Invoices | 2 (Invoice, InvoiceLineItem) |
| Vault | 1 (DocumentVault) |
| **Total** | **21 models** (1 abstract + 20 concrete) |

Your original plan had 14 models. This plan has 21 models (6 new, 3 removed/merged). The additions are all essential for a production-quality financial application.
