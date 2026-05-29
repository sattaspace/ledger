"""API configuration for the Satta Ledger project.

This module creates the NinjaExtraAPI instance and imports all controllers
so ``auto_discover_controllers()`` can register them with the API.

Controller import order matches domain priority:
  1. Foundation: Institution, Account, Category, Tag
  2. Core: Transaction (with splits & transfer), Card
  3. Features: Bill, Debt, Budget
  4. Extended: Investment, SavingsGoal, Insurance, Invoice, Vault

All controllers inherit from LedgerControllerBase (controllers/base.py)
which provides Sattabase auth, user_id scoping, pagination, and soft-delete.
"""

import logging

from ninja_extra import NinjaExtraAPI

logger = logging.getLogger(__name__)

api = NinjaExtraAPI(
    title="Satta Ledger API",
    version="1.0.0",
    description="Satta Ledger backend — powered by Sattabase SDK for auth & billing.",
    urls_namespace="sattaledger",
    openapi_extra={
        "info": {
            "contact": {
                "name": "Satta Ledger Support",
                "email": "ledger@sattaspace.com",
            },
            "license": {"name": "Private"},
        },
        "servers": [
            {"url": "http://localhost:8087", "description": "Local Development"}
        ],
    },
)

# ── Exception handlers for auth & feature gating ─────────────────────────

from django.http import JsonResponse
from api.controllers.base import (
    AuthRequiredError,
    AuthServiceUnavailableError,
    FeatureRequiredError,
    SubscriptionInactiveError,
    PlanLimitReachedError,
)
from api.errors import TooManyRequestsError

@api.exception_handler(AuthRequiredError)
def auth_required_handler(request, exc):
    return JsonResponse(
        {"detail": exc.detail},
        status=exc.status_code,
    )

@api.exception_handler(FeatureRequiredError)
def feature_required_handler(request, exc):
    return JsonResponse(
        {"detail": exc.detail, "feature": exc.feature},
        status=exc.status_code,
    )

@api.exception_handler(SubscriptionInactiveError)
def subscription_inactive_handler(request, exc):
    return JsonResponse(
        {"detail": exc.detail},
        status=exc.status_code,
    )

@api.exception_handler(PlanLimitReachedError)
def plan_limit_reached_handler(request, exc):
    return JsonResponse(
        {"detail": exc.detail, "limit_key": exc.limit_key, "max_allowed": exc.max_allowed},
        status=exc.status_code,
    )

@api.exception_handler(AuthServiceUnavailableError)
def auth_service_unavailable_handler(request, exc):
    return JsonResponse(
        {"detail": exc.detail},
        status=exc.status_code,
    )

@api.exception_handler(TooManyRequestsError)
def too_many_requests_handler(request, exc):
    return JsonResponse(
        {"detail": exc.message},
        status=429,
    )


# ── Health check endpoint ─────────────────────────────────────────────────

from ninja import Router as NinjaRouter

health_router = NinjaRouter(tags=["Health"])


@health_router.get("/health", response=dict)
def health_check(request):
    """Health check endpoint — verifies Sattabase connectivity and database.

    Returns:
        - status: "healthy" or "degraded"
        - sattabase: connectivity check result
        - database: database connectivity check result
    """
    from api.middleware import check_sattabase_health

    checks = {
        "status": "healthy",
        "sattabase": None,
        "database": None,
    }

    # Check Sattabase connectivity
    sattabase_result = check_sattabase_health()
    checks["sattabase"] = sattabase_result
    if not sattabase_result["sattabase_reachable"]:
        checks["status"] = "degraded"

    # Check database connectivity
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = {"connected": True}
    except Exception as exc:
        checks["database"] = {"connected": False, "error": str(exc)}
        checks["status"] = "degraded"

    status_code = 200 if checks["status"] == "healthy" else 503
    return JsonResponse(checks, status=status_code)


api.add_router("", health_router)

# ── Import all controllers so auto_discover picks them up ──────────────────

# Foundation
from api.controllers.institution_controller import InstitutionController  # noqa: E402, F401
from api.controllers.account_controller import AccountController  # noqa: E402, F401
from api.controllers.category_controller import CategoryController  # noqa: E402, F401
from api.controllers.tag_controller import TagController, TransactionTagController  # noqa: E402, F401

# Core
from api.controllers.transaction_controller import TransactionController  # noqa: E402, F401
from api.controllers.card_controller import CardController  # noqa: E402, F401

# Features
from api.controllers.bill_controller import BillController  # noqa: E402, F401
from api.controllers.debt_controller import DebtController  # noqa: E402, F401
from api.controllers.budget_controller import BudgetController  # noqa: E402, F401

# Extended
from api.controllers.investment_controller import InvestmentController  # noqa: E402, F401
from api.controllers.savings_goal_controller import SavingsGoalController  # noqa: E402, F401
from api.controllers.insurance_controller import InsuranceController  # noqa: E402, F401
from api.controllers.invoice_controller import InvoiceController  # noqa: E402, F401
from api.controllers.vault_controller import VaultController  # noqa: E402, F401

api.auto_discover_controllers()
