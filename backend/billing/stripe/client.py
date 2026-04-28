"""Low-level Stripe SDK adapter.

This is the ONLY module that imports ``stripe``.  Every function accepts
and returns plain ``dict`` / ``list`` / primitive types — never raw
``StripeObject`` instances.  This eliminates all ``.get()`` vs bracket-
access issues and makes the rest of the codebase completely decoupled
from the Stripe SDK version.

All functions are synchronous (the SDK is sync).  Wrap with
``sync_to_async`` from async callers.
"""

import logging
import time
from typing import Optional

import stripe
from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def get_api_key() -> str:
    """Return the Stripe secret key or raise."""
    key = getattr(settings, "STRIPE_SECRET_KEY", None)
    if not key:
        raise ValueError("Stripe is not configured.  Set STRIPE_SECRET_KEY in .env.")
    return key


def get_webhook_secret() -> str:
    """Return the Stripe webhook secret or raise."""
    secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)
    if not secret:
        raise ValueError(
            "Stripe webhook secret not configured.  "
            "Set STRIPE_WEBHOOK_SECRET in .env."
        )
    return secret


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def to_dict(obj) -> dict:
    """Convert a Stripe SDK object to a plain dict (idempotent for dicts)."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return dict(obj)


def ts_to_dt(timestamp) -> Optional["datetime"]:
    """Convert a Unix epoch (int/float) to a timezone-aware UTC datetime."""
    if not timestamp:
        return None
    try:
        from datetime import timezone as _tz, datetime as _dt

        return _dt.fromtimestamp(int(timestamp), tz=_tz.utc)
    except (ValueError, TypeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Products & Prices
# ---------------------------------------------------------------------------


def create_product(
    name: str, description: str = "", metadata: Optional[dict] = None
) -> dict:
    product = stripe.Product.create(
        api_key=get_api_key(),
        name=name,
        description=description or None,
        metadata=metadata or {},
    )
    return to_dict(product)


def create_price(
    product_id: str,
    unit_amount: int,
    currency: str,
    recurring_interval: Optional[str] = None,
    tax_behavior: str = "exclusive",
    metadata: Optional[dict] = None,
) -> dict:
    params: dict = {
        "api_key": get_api_key(),
        "product": product_id,
        "unit_amount": unit_amount,
        "currency": currency.lower(),
        "metadata": metadata or {},
        "tax_behavior": tax_behavior,
    }
    if recurring_interval:
        params["recurring"] = {"interval": recurring_interval}
    price = stripe.Price.create(**params)
    return to_dict(price)


def list_prices(
    product_id: str,
    currency: Optional[str] = None,
    active: bool = True,
    limit: int = 100,
) -> list[dict]:
    params: dict = {
        "api_key": get_api_key(),
        "product": product_id,
        "active": active,
        "limit": limit,
    }
    if currency:
        params["currency"] = currency.lower()
    prices = stripe.Price.list(**params)
    return [to_dict(p) for p in prices.auto_paging_iter()]


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


def create_customer(email: str, name: str, metadata: Optional[dict] = None) -> dict:
    customer = stripe.Customer.create(
        api_key=get_api_key(),
        email=email,
        name=name,
        metadata=metadata or {},
    )
    return to_dict(customer)


def retrieve_customer(customer_id: str) -> dict:
    customer = stripe.Customer.retrieve(customer_id, api_key=get_api_key())
    return to_dict(customer)


def modify_customer(customer_id: str, **params) -> dict:
    params["api_key"] = get_api_key()
    customer = stripe.Customer.modify(customer_id, **params)
    return to_dict(customer)


def delete_customer(customer_id: str) -> dict:
    result = stripe.Customer.delete(customer_id, api_key=get_api_key())
    return to_dict(result)


# ---------------------------------------------------------------------------
# Checkout Sessions
# ---------------------------------------------------------------------------


def create_checkout_session(**params) -> dict:
    params["api_key"] = get_api_key()
    session = stripe.checkout.Session.create(**params)
    return to_dict(session)


def retrieve_checkout_session(session_id: str) -> dict:
    session = stripe.checkout.Session.retrieve(session_id, api_key=get_api_key())
    return to_dict(session)


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


def create_subscription(**params) -> dict:
    params["api_key"] = get_api_key()
    sub = stripe.Subscription.create(**params)
    return to_dict(sub)


def retrieve_subscription(sub_id: str) -> dict:
    sub = stripe.Subscription.retrieve(sub_id, api_key=get_api_key())
    return to_dict(sub)


def modify_subscription(sub_id: str, **params) -> dict:
    params["api_key"] = get_api_key()
    sub = stripe.Subscription.modify(sub_id, **params)
    return to_dict(sub)


def retrieve_upcoming_invoice(**params) -> dict:
    params["api_key"] = get_api_key()
    invoice = stripe.Invoice.retrieve_upcoming(**params)
    return to_dict(invoice)


def list_invoices(
    customer_id: str,
    limit: int = 25,
    starting_after: Optional[str] = None,
    expand: Optional[list] = None,
) -> dict:
    params: dict = {
        "api_key": get_api_key(),
        "customer": customer_id,
        "limit": limit,
    }
    if starting_after:
        params["starting_after"] = starting_after
    if expand:
        params["expand"] = expand
    invoices = stripe.Invoice.list(**params)
    return {
        "data": [to_dict(inv) for inv in invoices.auto_paging_iter()],
        "has_more": invoices.has_more,
    }


# ---------------------------------------------------------------------------
# Portal
# ---------------------------------------------------------------------------


def create_portal_session(customer_id: str, return_url: str) -> dict:
    session = stripe.billing_portal.Session.create(
        api_key=get_api_key(),
        customer=customer_id,
        return_url=return_url,
    )
    return to_dict(session)


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------


def create_refund(
    payment_intent: str,
    amount: Optional[int] = None,
    reason: str = "requested_by_customer",
    metadata: Optional[dict] = None,
    idempotency_key: Optional[str] = None,
) -> dict:
    params: dict = {
        "api_key": get_api_key(),
        "payment_intent": payment_intent,
        "reason": reason,
        "metadata": metadata or {},
    }
    if amount is not None:
        params["amount"] = amount
    if idempotency_key:
        params["idempotency_key"] = idempotency_key
    refund = stripe.Refund.create(**params)
    return to_dict(refund)


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


def retrieve_invoice(invoice_id: str) -> dict:
    invoice = stripe.Invoice.retrieve(invoice_id, api_key=get_api_key())
    return to_dict(invoice)


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
    """Verify signature and return parsed event dict."""
    stripe.Webhook.construct_event(payload, sig_header, get_webhook_secret())
    import json

    return json.loads(payload.decode("utf-8"))


# ---------------------------------------------------------------------------
# Subscription item helpers (plain dict access)
# ---------------------------------------------------------------------------


def get_subscription_items(sub_dict: dict) -> list[dict]:
    """Return list of subscription item dicts from a subscription dict."""
    items = sub_dict.get("items") or {}
    if not isinstance(items, dict):
        items = {}
    return items.get("data") or []


def get_first_item_id(sub_dict: dict) -> Optional[str]:
    """Return the first subscription item's ID, or None."""
    items = get_subscription_items(sub_dict)
    if items:
        return items[0].get("id")
    return None


def get_subscription_currency(sub_dict: dict) -> str:
    """Return the subscription's currency (lowercase), default 'usd'."""
    return (sub_dict.get("currency") or "usd").lower()
