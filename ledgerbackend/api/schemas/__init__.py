"""Ledger API schemas — all schema classes for request/response validation.

Schemas are organized in separate modules matching the model structure,
but imported here for convenient access from controllers:

    from api.schemas import InstitutionCreate, InstitutionOut

Module layout:
    common.py        — PaginationIn, PaginatedResponse, MessageOut, etc.
    core.py          — Institution, Account, Transaction, TransactionSplit
    categories.py    — Category, Tag, TransactionTag
    cards.py         — Card
    bills.py         — Bill, BillPayment
    debt.py          — DebtFacility, DebtPayment
    budgets.py       — Budget
    investments.py   — InvestmentAccount, Holding
    goals.py         — SavingsGoal
    insurance.py     — InsurancePolicy
    invoices.py      — Invoice, InvoiceLineItem
    vault.py         — DocumentVault
"""

# ── Common ───────────────────────────────────────────────────────────────────
from api.schemas.common import (  # noqa: F401
    PaginationIn,
    PaginationOut,
    PaginatedResponse,
    MessageOut,
    ErrorResponse,
    ValidationErrorOut,
    BulkDeleteOut,
    BulkRestoreOut,
    DateRangeFilter,
    AmountRangeFilter,
    CurrencyFilter,
    # Legacy test schemas
    TestNoteCreate,
    TestNoteUpdate,
    TestNoteOut,
)

# ── Core ─────────────────────────────────────────────────────────────────────
from api.schemas.core import (  # noqa: F401
    InstitutionCreate,
    InstitutionUpdate,
    InstitutionOut,
    InstitutionListOut,
    InstitutionFilter,
    AccountCreate,
    AccountUpdate,
    AccountOut,
    AccountListOut,
    AccountFilter,
    BalanceRecalculateOut,
    TransactionCreate,
    TransactionUpdate,
    TransactionOut,
    TransactionListOut,
    TransactionFilter,
    TransferCreate,
    TransferOut,
    TransactionSplitCreate,
    TransactionSplitUpdate,
    TransactionSplitOut,
)

# ── Categories ───────────────────────────────────────────────────────────────
from api.schemas.categories import (  # noqa: F401
    CategoryCreate,
    CategoryUpdate,
    CategoryOut,
    CategoryListOut,
    CategoryTreeOut,
    CategoryFilter,
    TagCreate,
    TagUpdate,
    TagOut,
    TagListOut,
    TagFilter,
    TransactionTagCreate,
    TransactionTagOut,
    TransactionTagBulkCreate,
    TransactionTagBulkOut,
)

# ── Cards ────────────────────────────────────────────────────────────────────
from api.schemas.cards import (  # noqa: F401
    CardCreate,
    CardUpdate,
    CardOut,
    CardListOut,
    CardFilter,
)

# ── Bills ────────────────────────────────────────────────────────────────────
from api.schemas.bills import (  # noqa: F401
    BillCreate,
    BillUpdate,
    BillOut,
    BillListOut,
    BillFilter,
    BillGenerateTransactionOut,
    BillPaymentCreate,
    BillPaymentUpdate,
    BillPaymentOut,
    BillPaymentFilter,
)

# ── Debt ─────────────────────────────────────────────────────────────────────
from api.schemas.debt import (  # noqa: F401
    DebtFacilityCreate,
    DebtFacilityUpdate,
    DebtFacilityOut,
    DebtFacilityListOut,
    DebtFacilityFilter,
    DebtPaymentCreate,
    DebtPaymentUpdate,
    DebtPaymentOut,
    DebtPaymentFilter,
)

# ── Budgets ──────────────────────────────────────────────────────────────────
from api.schemas.budgets import (  # noqa: F401
    BudgetCreate,
    BudgetUpdate,
    BudgetOut,
    BudgetListOut,
    BudgetFilter,
)

# ── Investments ──────────────────────────────────────────────────────────────
from api.schemas.investments import (  # noqa: F401
    InvestmentAccountCreate,
    InvestmentAccountUpdate,
    InvestmentAccountOut,
    InvestmentAccountListOut,
    HoldingCreate,
    HoldingUpdate,
    HoldingOut,
    HoldingListOut,
    HoldingFilter,
)

# ── Goals ────────────────────────────────────────────────────────────────────
from api.schemas.goals import (  # noqa: F401
    SavingsGoalCreate,
    SavingsGoalUpdate,
    SavingsGoalOut,
    SavingsGoalListOut,
    SavingsGoalFilter,
    SavingsContribution,
    SavingsContributionOut,
)

# ── Insurance ────────────────────────────────────────────────────────────────
from api.schemas.insurance import (  # noqa: F401
    InsurancePolicyCreate,
    InsurancePolicyUpdate,
    InsurancePolicyOut,
    InsurancePolicyListOut,
    InsurancePolicyFilter,
)

# ── Invoices ─────────────────────────────────────────────────────────────────
from api.schemas.invoices import (  # noqa: F401
    InvoiceCreate,
    InvoiceUpdate,
    InvoiceOut,
    InvoiceListOut,
    InvoiceFilter,
    InvoiceMarkPaid,
    InvoiceLineItemCreate,
    InvoiceLineItemUpdate,
    InvoiceLineItemOut,
)

# ── Vault ────────────────────────────────────────────────────────────────────
from api.schemas.vault import (  # noqa: F401
    DocumentVaultCreate,
    DocumentVaultUpdate,
    DocumentVaultOut,
    DocumentVaultListOut,
    DocumentVaultFilter,
)
