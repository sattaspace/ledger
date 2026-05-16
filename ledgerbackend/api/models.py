"""Ledger API models.

All models live in separate module files for organization, but are
imported here so Django discovers them as part of the `api` app.

Module files:
    models_core.py        — Institution, Account, Transaction, TransactionSplit
    models_categories.py  — Category, Tag, TransactionTag
    models_cards.py       — Card
    models_debt.py        — DebtFacility, DebtPayment
    models_bills.py       — Bill, BillPayment
    models_budgets.py     — Budget
    models_investments.py — InvestmentAccount, Holding
    models_goals.py       — SavingsGoal
    models_insurance.py   — InsurancePolicy
    models_invoices.py    — Invoice, InvoiceLineItem
    models_vault.py       — DocumentVault

Abstract base:
    common/models.py      — UserOwnedModel (with ActiveManager, TimeStampedModel,
                            SoftDeleteModel, ActivatorModel)
"""

# NOTE: TestNote model has been removed. If you need to restore it,
# check git history. The model, controller, and schemas have been
# cleaned up as part of the audit findings fix (M6).


# ── Core models ──────────────────────────────────────────────────────────────
from api.models_core import Institution, Account, Transaction, TransactionSplit  # noqa: E402, F401

# ── Category & Tag models ────────────────────────────────────────────────────
from api.models_categories import Category, Tag, TransactionTag  # noqa: E402, F401

# ── Card model ───────────────────────────────────────────────────────────────
from api.models_cards import Card  # noqa: E402, F401

# ── Debt models ──────────────────────────────────────────────────────────────
from api.models_debt import DebtFacility, DebtPayment  # noqa: E402, F401

# ── Bill models ──────────────────────────────────────────────────────────────
from api.models_bills import Bill, BillPayment  # noqa: E402, F401

# ── Budget model ─────────────────────────────────────────────────────────────
from api.models_budgets import Budget  # noqa: E402, F401

# ── Investment models ────────────────────────────────────────────────────────
from api.models_investments import InvestmentAccount, Holding  # noqa: E402, F401

# ── Savings Goal model ──────────────────────────────────────────────────────
from api.models_goals import SavingsGoal  # noqa: E402, F401

# ── Insurance model ──────────────────────────────────────────────────────────
from api.models_insurance import InsurancePolicy  # noqa: E402, F401

# ── Invoice models ───────────────────────────────────────────────────────────
from api.models_invoices import Invoice, InvoiceLineItem  # noqa: E402, F401

# ── Document Vault model ────────────────────────────────────────────────────
from api.models_vault import DocumentVault  # noqa: E402, F401
