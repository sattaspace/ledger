"""Audit logging model and decorator for the Ledger domain.

Provides a structured audit trail for all destructive and financial
actions. This is especially important for financial data where
regulatory compliance requires tracking who did what and when.

Usage in controllers::

    from api.audit import log_audit

    @route.delete("/{int:account_id}")
    @log_audit(action="account.delete")
    def soft_delete_account(self, request, account_id):
        ...

The decorator automatically captures:
    - user_id from request.sattabase_user
    - IP address from request
    - User-Agent from request
    - HTTP method and path
    - Before/after state snapshots (for updates)
    - Timestamp

The model stores all of this in a single table with JSON details,
making it easy to query and filter without complex JOINs.
"""

import json
import logging
from functools import wraps
from datetime import datetime

from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel

logger = logging.getLogger(__name__)


class AuditLog(TimeStampedModel):
    """Structured audit log for Ledger domain actions.

    Every destructive or financial action (create, update, delete,
    transfer, etc.) should be logged here. The ``details`` JSON field
    captures before/after state and any additional context.

    Querying examples::

        # All actions by a user
        AuditLog.objects.filter(user_id=42)

        # All account deletions
        AuditLog.objects.filter(action="account.delete")

        # Actions from a specific IP
        AuditLog.objects.filter(ip_address="192.168.1.1")

        # Actions on a specific object
        AuditLog.objects.filter(model="account", object_id=42)
    """

    user_id = models.PositiveIntegerField(
        db_index=True,
        help_text="Sattabase User.id — who performed the action",
    )
    action = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Dot-separated action identifier, e.g. 'account.create', 'transaction.delete'",
    )
    model = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Model name, e.g. 'account', 'transaction'",
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Primary key of the affected object",
    )

    # ── Request context ───────────────────────────────────────────────
    method = models.CharField(
        max_length=10,
        blank=True,
        help_text="HTTP method (GET, POST, PATCH, DELETE)",
    )
    path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Request path",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address",
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        help_text="Client User-Agent header",
    )

    # ── State capture ─────────────────────────────────────────────────
    before_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Object state before the action (for updates/deletes)",
    )
    after_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Object state after the action (for creates/updates)",
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured context (e.g. transfer amounts, bill generation)",
    )

    class Meta:
        db_table = "audit_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "action"], name="idx_audit_user_action"),
            models.Index(fields=["user_id", "model"], name="idx_audit_user_model"),
            models.Index(fields=["action", "created_at"], name="idx_audit_action_date"),
        ]

    def __str__(self) -> str:
        return f"AuditLog(user_id={self.user_id}, action={self.action}, object_id={self.object_id})"


def _get_client_ip(request) -> str | None:
    """Extract client IP from request."""
    from django.conf import settings

    remote_addr = request.META.get("REMOTE_ADDR", "")
    if remote_addr:
        return remote_addr

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return None


def _serialize_model_instance(obj) -> dict:
    """Serialize a model instance to a dict for audit storage.

    Handles Decimal, datetime, and other non-JSON-serializable types.
    """
    if obj is None:
        return {}

    data = {}
    for field in obj._meta.get_fields():
        if hasattr(field, "attname") and hasattr(obj, field.attname):
            value = getattr(obj, field.attname)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif hasattr(value, "isoformat"):
                value = value.isoformat()
            elif isinstance(value, bytes):
                value = "<binary>"
            data[field.attname] = str(value) if value is not None else None
    return data


def write_audit(
    *,
    user_id: int,
    action: str,
    model: str,
    object_id: int | None = None,
    method: str = "",
    path: str = "",
    ip_address: str | None = None,
    user_agent: str = "",
    before_state: dict | None = None,
    after_state: dict | None = None,
    details: dict | None = None,
) -> AuditLog:
    """Write an audit log entry. Can be called directly or via the decorator.

    This is a synchronous function designed to be called from controller code
    or signal handlers.

    Args:
        user_id: The Sattabase user who performed the action.
        action: Dot-separated action (e.g. "account.create").
        model: Model name (e.g. "account").
        object_id: Primary key of the affected object.
        method: HTTP method.
        path: Request path.
        ip_address: Client IP.
        user_agent: Client User-Agent.
        before_state: Object state before the action.
        after_state: Object state after the action.
        details: Additional context.

    Returns:
        The created AuditLog instance.
    """
    return AuditLog.objects.create(
        user_id=user_id,
        action=action,
        model=model,
        object_id=object_id,
        method=method.upper() if method else "",
        path=path[:500] if path else "",
        ip_address=ip_address or None,
        user_agent=user_agent[:500] if user_agent else "",
        before_state=before_state or {},
        after_state=after_state or {},
        details=details or {},
    )


def log_audit(action: str, model: str = "", capture_state: bool = False):
    """Decorator to automatically log audit entries for controller endpoints.

    Usage::

        @route.delete("/{int:account_id}")
        @log_audit(action="account.delete", model="account")
        def soft_delete_account(self, request, account_id):
            ...

    When ``capture_state=True``, the decorator attempts to capture the
    object's before-state by looking it up before the endpoint executes.
    This is useful for update and delete operations.

    The decorator extracts user_id, IP, user-agent, method, and path
    from the request automatically. If the endpoint returns an object
    with an ``id`` attribute, it's captured as ``object_id``.

    Args:
        action: Dot-separated action identifier.
        model: Model name. If empty, extracted from action prefix.
        capture_state: If True, capture object state before the action.
    """
    if not model:
        # Extract model from action: "account.delete" → "account"
        model = action.split(".")[0] if "." in action else action

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract request from args (self, request, ...)
            request = None
            for arg in args:
                if hasattr(arg, "META"):
                    request = arg
                    break

            # Capture before-state if requested
            before_state = None
            if capture_state and request:
                try:
                    from api.rate_limit import _get_client_ip
                    # Try to get the object ID from kwargs
                    obj_id = kwargs.get("account_id") or kwargs.get("transaction_id") or \
                             kwargs.get("bill_id") or kwargs.get("card_id") or \
                             kwargs.get("budget_id") or kwargs.get("debt_id") or \
                             kwargs.get("document_id") or kwargs.get("invoice_id") or \
                             kwargs.get("policy_id") or kwargs.get("goal_id") or \
                             kwargs.get("category_id") or kwargs.get("tag_id") or \
                             kwargs.get("note_id") or kwargs.get("pk")

                    if obj_id:
                        model_class = _get_model_class(model)
                        if model_class:
                            try:
                                obj = model_class.all_objects.get(id=obj_id)
                                before_state = _serialize_model_instance(obj)
                            except model_class.DoesNotExist:
                                pass
                except Exception as exc:
                    logger.debug("Failed to capture before-state: %s", exc)

            # Execute the endpoint
            result = func(*args, **kwargs)

            # Write audit log
            if request:
                try:
                    user = getattr(request, "sattabase_user", None)
                    user_id = getattr(user, "id", None) if user else None

                    if user_id:
                        # Extract object_id from result
                        object_id = None
                        if hasattr(result, "id"):
                            object_id = result.id
                        elif isinstance(result, dict):
                            object_id = result.get("id")

                        # Extract after-state from result
                        after_state = None
                        if capture_state and hasattr(result, "_meta"):
                            after_state = _serialize_model_instance(result)

                        write_audit(
                            user_id=user_id,
                            action=action,
                            model=model,
                            object_id=object_id or kwargs.get("pk"),
                            method=request.method or "",
                            path=request.path or "",
                            ip_address=_get_client_ip(request),
                            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                            before_state=before_state,
                            after_state=after_state,
                        )
                except Exception as exc:
                    # Audit logging should never break the endpoint
                    logger.error("Audit logging failed: %s", exc)

            return result

        return wrapper
    return decorator


def _get_model_class(model_name: str):
    """Resolve a model name to a Django model class."""
    from django.apps import apps

    # Try the api app first
    try:
        return apps.get_model("api", model_name)
    except LookupError:
        pass

    # Try common variations
    name_map = {
        "account": "Account",
        "transaction": "Transaction",
        "transaction_split": "TransactionSplit",
        "category": "Category",
        "tag": "Tag",
        "card": "Card",
        "bill": "Bill",
        "bill_payment": "BillPayment",
        "debt": "DebtFacility",
        "debt_facility": "DebtFacility",
        "debt_payment": "DebtPayment",
        "budget": "Budget",
        "investment_account": "InvestmentAccount",
        "holding": "Holding",
        "savings_goal": "SavingsGoal",
        "insurance_policy": "InsurancePolicy",
        "invoice": "Invoice",
        "invoice_line_item": "InvoiceLineItem",
        "document_vault": "DocumentVault",
        "institution": "Institution",
    }

    resolved = name_map.get(model_name.lower())
    if resolved:
        try:
            return apps.get_model("api", resolved)
        except LookupError:
            pass

    return None
