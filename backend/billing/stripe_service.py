"""Stripe service — handles all Stripe API interactions.

This module encapsulates the Stripe Python SDK calls for checkout,
customer management, portal sessions, and webhook event processing.
All methods are synchronous (Stripe SDK is sync) and should be called
via ``sync_to_async`` from async controller endpoints.

Configuration is read from Django settings:

- ``STRIPE_SECRET_KEY`` — required for API calls
- ``STRIPE_WEBHOOK_SECRET`` — required for webhook signature verification
- ``STRIPE_SUCCESS_URL`` — redirect after successful checkout
- ``STRIPE_CANCEL_URL`` — redirect when user cancels checkout
- ``STRIPE_PORTAL_RETURN_URL`` — redirect after portal session
"""

import json
import logging
from typing import Optional

import stripe
from django.conf import settings
from django.utils import timezone

from .models import (
    Product,
    Plan,
    BillingCycle,
    Subscription,
    SubscriptionStatus,
    WebhookEventLog,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Stripe Client Initialization
# =============================================================================


def _get_stripe_api_key() -> str:
    """Return the Stripe API key or raise if not configured."""
    key = settings.STRIPE_SECRET_KEY
    if not key:
        raise ValueError(
            "Stripe is not configured. Set SF_STRIPE_SECRET_KEY in your .env file."
        )
    return key


# =============================================================================
# Stripe Product & Price Auto-Creation
# =============================================================================


def ensure_stripe_product_and_price(plan: Plan) -> str:
    """Get or create the Stripe Product and Price for this plan.

    Auto-creates the Stripe Product (if the ``Product.stripe_product_id``
    is blank) and the Stripe Price (if ``Plan.stripe_price_id`` is blank).
    Both IDs are persisted to the database so subsequent checkouts
    reuse the same Stripe objects.

    This eliminates the need to manually create Products and Prices in
    the Stripe Dashboard and copy IDs into Django admin.

    Returns:
        The ``stripe_price_id`` string (``price_...``).

    Raises:
        stripe.StripeError: If any Stripe API call fails.
    """
    if plan.stripe_price_id:
        return plan.stripe_price_id

    api_key = _get_stripe_api_key()
    product = plan.product

    # --- Ensure Stripe Product exists -----------------------------------------
    if not product.stripe_product_id:
        stripe_product = stripe.Product.create(
            api_key=api_key,
            name=product.name,
            description=product.description or f"{product.name} subscription",
            metadata={"product_slug": product.slug},
        )
        product.stripe_product_id = stripe_product.id
        product.save(update_fields=["stripe_product_id"])
        logger.info(
            f"Created Stripe product {stripe_product.id} for "
            f"product '{product.slug}'"
        )

    # --- Create Stripe Price ---------------------------------------------------
    interval_map = {
        BillingCycle.MONTHLY: "month",
        BillingCycle.YEARLY: "year",
        BillingCycle.LIFETIME: None,  # one-time payment
    }

    interval = interval_map.get(plan.billing_cycle)
    is_recurring = interval is not None

    price_params = {
        "api_key": api_key,
        "product": product.stripe_product_id,
        "unit_amount": plan.price_cents,
        "currency": plan.currency.lower(),
        "metadata": {
            "plan_slug": plan.slug,
            "product_slug": product.slug,
        },
    }

    if is_recurring:
        price_params["recurring"] = {"interval": interval}

    stripe_price = stripe.Price.create(**price_params)

    plan.stripe_price_id = stripe_price.id
    plan.save(update_fields=["stripe_price_id"])
    logger.info(
        f"Created Stripe price {stripe_price.id} for plan '{plan.slug}' "
        f"(product '{product.slug}', {plan.price_cents/100:.2f} {plan.currency})"
    )

    return plan.stripe_price_id


# =============================================================================
# Stripe Subscription Sync (for local plan changes)
# =============================================================================


def update_stripe_subscription_plan(subscription: Subscription, new_plan: Plan) -> None:
    """Update the Stripe subscription's plan item to match a local plan change.

    Called when a user switches between paid plans via the local
    ``change-plan`` endpoint.  Modifies the Stripe subscription item
    to use the new plan's price (creating the price first if needed).

    Raises:
        ValueError: If the subscription has no ``stripe_subscription_id``.
        stripe.StripeError: If the Stripe API call fails.
    """
    if not subscription.stripe_subscription_id:
        return  # Nothing to sync — no Stripe subscription yet

    api_key = _get_stripe_api_key()
    price_id = ensure_stripe_product_and_price(new_plan)

    stripe_sub = stripe.Subscription.retrieve(
        subscription.stripe_subscription_id, api_key=api_key
    )
    items = stripe_sub.get("items", {}).get("data", [])

    if not items:
        logger.warning(
            f"Stripe subscription {subscription.stripe_subscription_id} "
            f"has no items — cannot update plan"
        )
        return

    stripe.Subscription.modify(
        subscription.stripe_subscription_id,
        api_key=api_key,
        items=[{"id": items[0].id, "price": price_id}],
        metadata={
            "plan_slug": new_plan.slug,
            "product_slug": new_plan.product.slug,
        },
        proration_behavior="create_prorations",
    )

    logger.info(
        f"Updated Stripe subscription {subscription.stripe_subscription_id} "
        f"plan → {new_plan.slug} (price {price_id})"
    )


def cancel_stripe_subscription(subscription: Subscription) -> None:
    """Cancel the Stripe subscription at the end of the billing period.

    Called when a paid subscriber downgrades to the free plan via the
    local ``cancel`` endpoint.  Sets ``cancel_at_period_end=True`` on
    the Stripe side so access continues until the period ends.

    Raises:
        stripe.StripeError: If the Stripe API call fails.
    """
    if not subscription.stripe_subscription_id:
        return  # Nothing to cancel — no Stripe subscription

    api_key = _get_stripe_api_key()

    stripe.Subscription.modify(
        subscription.stripe_subscription_id,
        api_key=api_key,
        cancel_at_period_end=True,
    )

    logger.info(
        f"Canceled Stripe subscription {subscription.stripe_subscription_id} "
        f"at period end (user downgraded to free plan)"
    )


# =============================================================================
# Customer Management
# =============================================================================


def create_or_get_customer(user) -> str:
    """Create a Stripe Customer for the user, or return existing one.

    Looks up any subscription the user has with a ``stripe_customer_id``
    set. If found, retrieves the customer from Stripe. Otherwise creates
    a new Stripe Customer record.

    Returns:
        The Stripe customer ID string (``cus_...``).

    Raises:
        stripe.StripeError: If the Stripe API call fails.
    """
    api_key = _get_stripe_api_key()

    # Check existing subscriptions for a customer ID
    existing_sub = (
        Subscription.objects.filter(user=user)
        .exclude(stripe_customer_id="")
        .exclude(stripe_customer_id__isnull=True)
        .first()
    )

    if existing_sub and existing_sub.stripe_customer_id:
        # Verify the customer still exists in Stripe
        try:
            stripe.Customer.retrieve(
                existing_sub.stripe_customer_id,
                api_key=api_key,
            )
            return existing_sub.stripe_customer_id
        except stripe.InvalidRequestError:
            # Customer was deleted in Stripe — fall through to create new
            pass

    # Create new Stripe Customer
    customer = stripe.Customer.create(
        api_key=api_key,
        email=user.email,
        name=user.get_full_name() or user.email,
        metadata={
            "user_id": user.id,
            "user_email": user.email,
        },
    )

    logger.info(f"Created Stripe customer {customer.id} for user {user.email}")
    return customer.id


# =============================================================================
# Checkout Session
# =============================================================================


def create_checkout_session(
    user,
    plan: Plan,
    product: Product,
    billing_cycle: Optional[str] = None,
) -> str:
    """Create a Stripe Checkout session for the given plan.

    Args:
        user: The Django user initiating checkout.
        plan: The Plan to subscribe to (auto-creates Stripe Price if needed).
        product: The Product the plan belongs to.
        billing_cycle: Optional billing cycle override.

    Returns:
        The Stripe Checkout Session URL.

    Raises:
        ValueError: If the plan is free.
        stripe.StripeError: If the Stripe API call fails.
    """
    api_key = _get_stripe_api_key()

    if plan.is_free:
        raise ValueError("Cannot checkout a free plan. Use change-plan instead.")

    # Auto-create Stripe Product & Price if not already linked
    price_id = ensure_stripe_product_and_price(plan)

    # Get or create Stripe Customer
    customer_id = create_or_get_customer(user)

    # --- Trial guard: only grant trial ONCE per product --------------------------
    # Check if this user has already used a trial for this product.
    # This prevents the exploit: Free → Standard (trial) → cancel → Free → Standard (trial again)
    existing_sub = (
        Subscription.objects.filter(user=user, product=product)
        .order_by("-created_at")
        .first()
    )
    trial_days = plan.trial_days if plan.trial_days > 0 else None
    if existing_sub and existing_sub.has_used_trial:
        trial_days = None  # No trial — they've already had one for this product
        logger.info(
            f"Trial skipped for user={user.email}, product={product.slug} "
            f"— has_used_trial=True (previous trial consumed)"
        )

    # Build success/cancel URLs with product context
    # Use urllib.parse to correctly merge params with existing query string.
    # IMPORTANT: {CHECKOUT_SESSION_ID} is a Stripe template placeholder —
    # Stripe replaces it at redirect time. It must NOT be URL-encoded,
    # so we append it as raw text after encoding our own params.
    from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

    # --- Success URL ---
    base_success = settings.STRIPE_SUCCESS_URL.rstrip("/")
    parsed = urlparse(base_success)
    existing_params = parse_qs(parsed.query, keep_blank_values=True)
    flat_params = {
        k: v[0] if isinstance(v, list) else v for k, v in existing_params.items()
    }
    flat_params["product"] = product.slug
    flat_params["plan"] = plan.slug
    # Build URL with product/plan/checkout params encoded, then append the
    # Stripe template placeholder as raw text (NOT urlencoded).
    encoded_qs = urlencode(flat_params)
    success_url = urlunparse(parsed._replace(query=encoded_qs))
    if "?" in success_url:
        success_url += "&session_id={CHECKOUT_SESSION_ID}"
    else:
        success_url += "?session_id={CHECKOUT_SESSION_ID}"

    # --- Cancel URL ---
    base_cancel = settings.STRIPE_CANCEL_URL.rstrip("/")
    parsed_cancel = urlparse(base_cancel)
    cancel_params = {
        k: v[0] if isinstance(v, list) else v
        for k, v in parse_qs(parsed_cancel.query, keep_blank_values=True).items()
    }
    cancel_params["product"] = product.slug
    cancel_url = urlunparse(parsed_cancel._replace(query=urlencode(cancel_params)))

    session = stripe.checkout.Session.create(
        api_key=api_key,
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user.id),
            "product_slug": product.slug,
            "plan_slug": plan.slug,
        },
        subscription_data={
            "trial_period_days": trial_days,
            "metadata": {
                "user_id": str(user.id),
                "product_slug": product.slug,
                "plan_slug": plan.slug,
            },
        },
        allow_promotion_codes=True,
        automatic_tax={"enabled": True},
    )

    logger.info(
        f"Created Stripe checkout session {session.id} for "
        f"user={user.email}, plan={plan.slug}, product={product.slug}"
    )
    return session.url


# =============================================================================
# Checkout Confirmation (direct activation — no webhook dependency)
# =============================================================================


def confirm_checkout_session(session_id: str, user) -> dict:
    """Fetch a Stripe Checkout Session and activate the local subscription.

    This is the PRIMARY activation path — called by the frontend when the
    user is redirected back after successful checkout. It does NOT depend
    on webhooks, making it reliable in all environments (local dev, behind
    NAT, containerized, etc.).

    The webhook handler (``_handle_checkout_completed``) remains as a
    fallback/sync mechanism for edge cases where the redirect is interrupted.

    Returns:
        Dict with subscription data: ``{plan_name, status, trial_end, ...}``

    Raises:
        ValueError: If session is not found, not paid, or user mismatch.
        stripe.StripeError: If the Stripe API call fails.
    """
    api_key = _get_stripe_api_key()

    # 1. Retrieve the checkout session from Stripe
    try:
        raw_session = stripe.checkout.Session.retrieve(session_id, api_key=api_key)
    except stripe.InvalidRequestError:
        raise ValueError(f"Invalid checkout session: {session_id}")

    # Convert Stripe object → plain dict (Stripe SDK returns objects, not dicts)
    session = (
        raw_session.to_dict() if hasattr(raw_session, "to_dict") else dict(raw_session)
    )

    # 2. Validate payment status
    payment_status = session.get("payment_status")
    if payment_status != "paid":
        raise ValueError(
            f"Checkout session {session_id} has not been paid "
            f"(status: {payment_status})"
        )

    # 3. Validate user ownership (prevent session hijacking)
    metadata = session.get("metadata") or {}
    session_user_id = metadata.get("user_id")
    if not session_user_id or str(session_user_id) != str(user.id):
        raise ValueError("Checkout session does not belong to this user.")

    product_slug = metadata.get("product_slug")
    plan_slug = metadata.get("plan_slug")
    if not product_slug or not plan_slug:
        raise ValueError(f"Checkout session {session_id} is missing required metadata.")

    # 4. Find the local subscription
    from .services import BillingService

    product = BillingService.get_product_by_slug(product_slug)
    if not product:
        raise ValueError(f"Product not found: {product_slug}")

    plan = BillingService.get_plan_by_slug(product_slug, plan_slug)
    if not plan:
        raise ValueError(f"Plan not found: {product_slug}/{plan_slug}")

    sub = BillingService.get_or_create_free_subscription(user, product)
    if not sub:
        raise ValueError(
            f"Could not get/create subscription for user={user.email}, "
            f"product={product_slug}"
        )

    # 5. Fetch the Stripe subscription for full details
    stripe_sub_id = session.get("subscription")
    stripe_customer_id = session.get("customer") or ""

    if stripe_sub_id:
        raw_stripe_sub = stripe.Subscription.retrieve(stripe_sub_id, api_key=api_key)
        # Convert to dict
        stripe_sub = (
            raw_stripe_sub.to_dict()
            if hasattr(raw_stripe_sub, "to_dict")
            else dict(raw_stripe_sub)
        )

        # Detect trial
        is_trialing = bool(
            stripe_sub.get("trial_start") and stripe_sub.get("trial_end")
        )

        sub.plan = plan
        sub.status = (
            SubscriptionStatus.TRIALING if is_trialing else SubscriptionStatus.ACTIVE
        )
        sub.stripe_subscription_id = stripe_sub_id
        sub.stripe_customer_id = stripe_customer_id
        sub.current_period_start = _ts_to_datetime(
            stripe_sub.get("current_period_start")
        )
        sub.current_period_end = _ts_to_datetime(stripe_sub.get("current_period_end"))

        if is_trialing:
            sub.trial_start = _ts_to_datetime(stripe_sub.get("trial_start"))
            sub.trial_end = _ts_to_datetime(stripe_sub.get("trial_end"))
            sub.has_used_trial = True

        sub.save()
    else:
        # No subscription ID (one-time payment or setup) — just update plan
        sub.plan = plan
        sub.status = SubscriptionStatus.ACTIVE
        sub.stripe_customer_id = stripe_customer_id
        sub.save()

    logger.info(
        f"Checkout confirmed: user={user.email}, plan={plan_slug}, "
        f"sub={sub.id}, status={sub.status}, session={session_id}"
    )

    return {
        "plan_name": plan.name,
        "plan_slug": plan.slug,
        "status": sub.status,
        "trial_end": sub.trial_end,
        "current_period_end": sub.current_period_end,
    }


# =============================================================================
# Customer Portal
# =============================================================================


def create_portal_session(user, return_url: Optional[str] = None) -> str:
    """Create a Stripe Customer Portal session.

    The portal allows users to manage their payment methods, view invoices,
    and cancel subscriptions directly in Stripe's hosted UI.

    Args:
        user: The Django user.
        return_url: Override return URL (defaults to settings).

    Returns:
        The Stripe Customer Portal URL.

    Raises:
        ValueError: If the user has no Stripe customer ID.
        stripe.StripeError: If the Stripe API call fails.
    """
    api_key = _get_stripe_api_key()
    _return_url = return_url or settings.STRIPE_PORTAL_RETURN_URL

    # Find user's Stripe customer ID
    sub = (
        Subscription.objects.filter(user=user)
        .exclude(stripe_customer_id="")
        .exclude(stripe_customer_id__isnull=True)
        .first()
    )

    if not sub or not sub.stripe_customer_id:
        raise ValueError(
            "No Stripe customer found for this user. " "Complete a checkout first."
        )

    session = stripe.billing_portal.Session.create(
        api_key=api_key,
        customer=sub.stripe_customer_id,
        return_url=_return_url,
    )

    logger.info(f"Created Stripe portal session {session.id} for user {user.email}")
    return session.url


# =============================================================================
# Webhook Processing
# =============================================================================


# Events we handle — others are logged but ignored
HANDLED_EVENT_TYPES = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
    "customer.subscription.trial_will_end",
}


def verify_and_parse_webhook(payload: bytes, sig_header: str) -> dict:
    """Verify the Stripe webhook signature and return the event dict.

    Args:
        payload: Raw request body bytes.
        sig_header: Value of the ``Stripe-Signature`` header.

    Returns:
        The parsed Stripe event as a plain ``dict`` (JSON-serializable).

    Raises:
        ValueError: If webhook secret is not configured.
        stripe.SignatureVerificationError: If signature verification fails.
    """
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    if not webhook_secret:
        raise ValueError(
            "Stripe webhook secret not configured. "
            "Set SF_STRIPE_WEBHOOK_SECRET in your .env file."
        )

    # Verify the signature (raises on failure)
    stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

    # Parse the raw payload as a plain dict — guaranteed JSON-serializable
    # because it comes straight from Stripe's JSON body.
    return json.loads(payload.decode("utf-8"))


def record_webhook_event(event: dict) -> Optional[WebhookEventLog]:
    """Record a webhook event in the audit log.

    If the event ID already exists (duplicate delivery), returns the
    existing record without creating a new one.

    Args:
        event: Parsed Stripe event dict.

    Returns:
        The WebhookEventLog instance (new or existing), or None if
        there was a DB error.
    """
    event_id = event["id"]
    event_type = event["type"]

    try:
        log_entry, created = WebhookEventLog.objects.get_or_create(
            event_id=event_id,
            defaults={
                "event_type": event_type,
                "payload": event,
            },
        )

        if created:
            logger.info(f"Recorded new webhook event: {event_type} ({event_id})")
        else:
            logger.info(f"Duplicate webhook event skipped: {event_type} ({event_id})")

        return log_entry
    except Exception as e:
        logger.error(f"Failed to record webhook event {event_id}: {e}")
        return None


def process_webhook_event(event: dict) -> None:
    """Route a verified webhook event to the appropriate handler.

    Called after signature verification and event logging. Only events
    in ``HANDLED_EVENT_TYPES`` are processed — others are silently
    ignored (but already logged).

    Args:
        event: Parsed Stripe event dict.
    """
    event_type = event["type"]
    event_id = event["id"]

    if event_type not in HANDLED_EVENT_TYPES:
        logger.info(f"Ignoring unhandled event type: {event_type}")
        return

    try:
        handler = EVENT_HANDLERS.get(event_type)
        if handler:
            handler(event)
            # Mark as processed
            WebhookEventLog.objects.filter(event_id=event_id).update(processed=True)
            logger.info(f"Successfully processed webhook: {event_type} ({event_id})")
        else:
            logger.warning(f"No handler for event type: {event_type}")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(
            f"Failed to process webhook {event_type} ({event_id}): {error_msg}",
            exc_info=True,
        )
        WebhookEventLog.objects.filter(event_id=event_id).update(
            processed=False,
            error_message=error_msg[:500],
        )


# =============================================================================
# Individual Event Handlers
# =============================================================================


def _handle_checkout_completed(event: dict) -> None:
    """Handle checkout.session.completed — activate subscription after payment.

    Creates or updates the subscription with the Stripe subscription data.
    If a trial was started, sets status to trialing.
    """
    session = event["data"]["object"]
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    product_slug = metadata.get("product_slug")
    plan_slug = metadata.get("plan_slug")

    if not all([user_id, product_slug, plan_slug]):
        logger.warning(
            f"checkout.session.completed missing metadata: {session.get('id')}"
        )
        return

    stripe_sub = session.get("subscription_details", {})
    stripe_sub_id = session.get("subscription") or stripe_sub.get("id")

    if not stripe_sub_id:
        logger.warning(
            f"checkout.session.completed has no subscription ID: {session.get('id')}"
        )
        return

    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(id=int(user_id))
    except (User.DoesNotExist, ValueError):
        logger.error(f"User not found for checkout webhook: user_id={user_id}")
        return

    from .services import BillingService

    # Get or create subscription for this user+product
    product = BillingService.get_product_by_slug(product_slug)
    if not product:
        logger.error(f"Product not found: {product_slug}")
        return

    plan = BillingService.get_plan_by_slug(product_slug, plan_slug)
    if not plan:
        logger.error(f"Plan not found: {product_slug}/{plan_slug}")
        return

    sub = BillingService.get_or_create_free_subscription(user, product)
    if not sub:
        logger.error(
            f"Could not get/create subscription for user={user.email}, "
            f"product={product_slug}"
        )
        return

    # Update subscription with Stripe data
    sub.plan = plan
    sub.status = (
        SubscriptionStatus.TRIALING
        if session.get("setup_intent")
        else SubscriptionStatus.ACTIVE
    )
    sub.stripe_subscription_id = stripe_sub_id
    sub.stripe_customer_id = session.get("customer", "")

    # Set billing period from the Stripe subscription
    stripe_subscription = stripe.Subscription.retrieve(
        stripe_sub_id, api_key=_get_stripe_api_key()
    )
    sub.current_period_start = _ts_to_datetime(stripe_subscription.current_period_start)
    sub.current_period_end = _ts_to_datetime(stripe_subscription.current_period_end)

    if stripe_subscription.trial_start and stripe_subscription.trial_end:
        sub.trial_start = _ts_to_datetime(stripe_subscription.trial_start)
        sub.trial_end = _ts_to_datetime(stripe_subscription.trial_end)
        sub.status = SubscriptionStatus.TRIALING
        sub.has_used_trial = True  # Mark trial as consumed — one trial per product ever

    sub.save()
    logger.info(
        f"Checkout completed: user={user.email}, plan={plan_slug}, "
        f"sub={sub.id}, status={sub.status}"
    )


def _handle_subscription_created(event: dict) -> None:
    """Handle customer.subscription.created — log new subscription."""
    stripe_sub = event["data"]["object"]
    metadata = stripe_sub.get("metadata", {})
    user_id = metadata.get("user_id")
    logger.info(
        f"Stripe subscription created: {stripe_sub.get('id')} "
        f"for user={user_id}, status={stripe_sub.get('status')}"
    )


def _handle_subscription_updated(event: dict) -> None:
    """Handle customer.subscription.updated — sync status and period dates.

    This is the primary webhook for keeping local state in sync with Stripe.
    Handles plan changes, cancellations, past_due, and period updates.
    """
    stripe_sub = event["data"]["object"]
    stripe_sub_id = stripe_sub["id"]
    metadata = stripe_sub.get("metadata", {})

    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
    except Subscription.DoesNotExist:
        logger.warning(
            f"subscription.updated: local subscription not found for "
            f"stripe_sub={stripe_sub_id}"
        )
        return

    # Map Stripe status to our status
    stripe_status = stripe_sub.get("status", "")
    status_map = {
        "active": SubscriptionStatus.ACTIVE,
        "trialing": SubscriptionStatus.TRIALING,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELED,
        "paused": SubscriptionStatus.PAUSED,
        "unpaid": SubscriptionStatus.PAST_DUE,
    }
    new_status = status_map.get(stripe_status, sub.status)

    # Detect plan change by stripe price ID
    items = stripe_sub.get("items", {}).get("data", [])
    if items:
        stripe_price_id = items[0].get("price", {}).get("id")
        if stripe_price_id and stripe_price_id != sub.plan.stripe_price_id:
            new_plan = (
                Plan.objects.filter(stripe_price_id=stripe_price_id)
                .select_related("product")
                .first()
            )
            if new_plan:
                sub.plan = new_plan
                logger.info(
                    f"Plan changed via webhook: {sub.plan.slug} -> {new_plan.slug}"
                )

    sub.status = new_status
    sub.current_period_start = _ts_to_datetime(stripe_sub.get("current_period_start"))
    sub.current_period_end = _ts_to_datetime(stripe_sub.get("current_period_end"))

    if stripe_sub.get("trial_start") and stripe_sub.get("trial_end"):
        sub.trial_start = _ts_to_datetime(stripe_sub.get("trial_start"))
        sub.trial_end = _ts_to_datetime(stripe_sub.get("trial_end"))

    if stripe_sub.get("canceled_at"):
        sub.canceled_at = _ts_to_datetime(stripe_sub.get("canceled_at"))

    sub.stripe_customer_id = stripe_sub.get("customer", sub.stripe_customer_id)
    sub.save()

    logger.info(
        f"Subscription updated via webhook: sub={sub.id}, "
        f"status={new_status}, stripe_sub={stripe_sub_id}"
    )


def _handle_subscription_deleted(event: dict) -> None:
    """Handle customer.subscription.deleted — mark subscription as expired."""
    stripe_sub = event["data"]["object"]
    stripe_sub_id = stripe_sub["id"]

    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
    except Subscription.DoesNotExist:
        logger.warning(
            f"subscription.deleted: local subscription not found for "
            f"stripe_sub={stripe_sub_id}"
        )
        return

    sub.status = SubscriptionStatus.EXPIRED
    sub.current_period_end = (
        _ts_to_datetime(stripe_sub.get("ended_at")) or timezone.now()
    )
    sub.save()

    logger.info(
        f"Subscription expired via webhook: sub={sub.id}, stripe_sub={stripe_sub_id}"
    )


def _handle_invoice_payment_succeeded(event: dict) -> None:
    """Handle invoice.payment_succeeded — mark subscription as active."""
    invoice = event["data"]["object"]
    stripe_sub_id = invoice.get("subscription")

    if not stripe_sub_id:
        return

    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
    except Subscription.DoesNotExist:
        return

    # If subscription was past_due, reactivate it
    if sub.status in (SubscriptionStatus.PAST_DUE,):
        sub.status = SubscriptionStatus.ACTIVE

    # Update period dates from the invoice's lines
    sub.current_period_start = _ts_to_datetime(invoice.get("period_start"))
    sub.current_period_end = _ts_to_datetime(invoice.get("period_end"))
    sub.save()

    logger.info(f"Payment succeeded: sub={sub.id}, status={sub.status}")


def _handle_invoice_payment_failed(event: dict) -> None:
    """Handle invoice.payment_failed — mark subscription as past_due."""
    invoice = event["data"]["object"]
    stripe_sub_id = invoice.get("subscription")

    if not stripe_sub_id:
        return

    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub_id)
    except Subscription.DoesNotExist:
        return

    sub.status = SubscriptionStatus.PAST_DUE
    sub.save()

    logger.warning(f"Payment failed: sub={sub.id}, stripe_sub={stripe_sub_id}")


def _handle_trial_will_end(event: dict) -> None:
    """Handle customer.subscription.trial_will_end — log notification.

    Actual email notification is handled by the Celery task in Phase 5.
    For now we just log it.
    """
    stripe_sub = event["data"]["object"]
    trial_end = stripe_sub.get("trial_end")

    try:
        sub = Subscription.objects.get(stripe_subscription_id=stripe_sub["id"])
        logger.info(
            f"Trial ending soon: user_id={sub.user_id}, "
            f"plan={sub.plan.slug}, trial_end={trial_end}"
        )
    except Subscription.DoesNotExist:
        logger.warning(
            f"trial_will_end: subscription not found for {stripe_sub.get('id')}"
        )


# =============================================================================
# Event Handler Dispatch Map
# =============================================================================

EVENT_HANDLERS = {
    "checkout.session.completed": _handle_checkout_completed,
    "customer.subscription.created": _handle_subscription_created,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.payment_succeeded": _handle_invoice_payment_succeeded,
    "invoice.payment_failed": _handle_invoice_payment_failed,
    "customer.subscription.trial_will_end": _handle_trial_will_end,
}


# =============================================================================
# Helpers
# =============================================================================


def _ts_to_datetime(timestamp) -> Optional[timezone.datetime]:
    """Convert a Unix timestamp to a timezone-aware datetime, or None."""
    if not timestamp:
        return None
    try:
        from datetime import timezone as dt_tz, datetime as dt

        return dt.fromtimestamp(int(timestamp), tz=dt_tz.utc)
    except (ValueError, TypeError, OSError):
        return None
