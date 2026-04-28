"""Ninja Extra controllers for the billing app.

Controllers handle HTTP routing and delegate business logic to
``BillingService``.  They are auto-discovered by ninja_extra's
``auto_discover_controllers()``.

Three controllers are defined:

- **BillingPublicController** — public endpoints (no auth required):
  product & plan discovery for landing pages and registration flow.

- **BillingProtectedController** — authenticated endpoints (JWT required):
  auth/me with domain-aware subscription data, subscription listing,
  and subscription mutation actions (cancel, reactivate, change-plan,
  Stripe checkout/portal).

- **BillingWebhookController** — webhook endpoints (no JWT auth):
  receives Stripe events verified by request signature.

Security features utilised from ``common``:

- **Exceptions**: ``NotFoundException``, ``BadRequestException``,
  ``TooManyRequestsException``, ``AccountNotActiveException`` — raised
  instead of returning tuple responses, caught by registered exception
  handlers in ``api/views.py``.
- **Permissions**: ``IsAuthenticated`` at controller class level.
  Email verification checked per-method via ``require_verified_email()``
  for sensitive billing actions.
- **Rate limiting**: ``check_rate_limit_or_raise()`` from
  ``common.rate_limit`` — raises ``TooManyRequestsException`` when
  exceeded.
- **Schemas**: ``MessageResponse`` from ``common.schemas`` for
  standardised success responses.
"""

import logging

import stripe
from ninja import Query
from ninja_extra import api_controller, http_get, http_post
from django.http import HttpRequest

from common.exceptions import (
    NotFoundException,
    BadRequestException,
    AccountNotActiveException,
)
from common.permissions import IsAuthenticated
from common.schemas import MessageResponse, PaginatedResponse, PaginationInput
from common.rate_limit import check_rate_limit_or_raise

# Import JWTAuth from users controllers — single auth class shared across apps
from users.controllers import JWTAuth

from .schemas import (
    ProductOutputSchema,
    ProductDetailSchema,
    PlanOutputSchema,
    SubscriptionOutputSchema,
    SubscriptionDetailSchema,
    AuthMeSchema,
    CheckoutOutputSchema,
    CheckoutConfirmInputSchema,
    CheckoutConfirmOutputSchema,
    PortalOutputSchema,
    ChangePlanInputSchema,
    CheckoutInputSchema,
)
from .services import BillingService
from .stripe_service import (
    create_checkout_session,
    confirm_checkout_session,
    create_portal_session,
    verify_and_parse_webhook,
    record_webhook_event,
    process_webhook_event,
    update_stripe_subscription_plan,
    cancel_stripe_subscription,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Helpers
# =============================================================================


def require_verified_email(request: HttpRequest) -> None:
    """Enforce email verification for sensitive billing actions.

    Raises ``AccountNotActiveException`` (403) with a clear message if
    the user's email has not been verified.  This is used as a
    method-level guard rather than a class-level permission so that
    read-only endpoints (listing, detail) remain accessible without
    verification while mutation endpoints are gated.

    Note: ``common.permissions.IsVerified`` could be used at the
    controller class level instead, but the permission-denied response
    from ninja_extra is generic (``\"Permission denied\"``).  Raising
    ``AccountNotActiveException`` gives a specific error code and
    message via our registered exception handler.
    """
    if not getattr(request.user, "is_email_verified", False):
        raise AccountNotActiveException(
            "Please verify your email address to perform billing actions."
        )


# =============================================================================
# Billing Public Controller — Product & Plan Discovery
# =============================================================================


@api_controller("/billing", tags=["Billing"], auth=None)
class BillingPublicController:
    """Public billing endpoints — no authentication required.

    These endpoints allow unauthenticated access to product and plan
    information, which is needed on marketing / landing pages and in
    the registration flow.  They are safe to expose publicly because
    they contain no user-specific data.
    """

    @http_get(
        "/products",
        response=list[ProductOutputSchema],
        summary="List products",
        description="Return all active products ordered by name.",
    )
    async def list_products(self):
        """List all active products."""
        products = await BillingService.aget_products(active_only=True)
        return products

    @http_get(
        "/products/{slug}",
        response={200: ProductDetailSchema, 404: dict},
        summary="Get product detail",
        description=(
            "Return a product with its plans and service domains. "
            "Raises 404 if the product slug does not match an active product."
        ),
    )
    async def get_product(self, slug: str):
        """Get product detail by slug, including plans and service domains."""
        product = await BillingService.aget_product_by_slug(slug)
        if not product:
            raise NotFoundException("Product not found.")

        plans = await BillingService.aget_plans_for_product(slug)
        domains = await BillingService.aget_service_domains_for_product(product)

        return {
            "id": product.id,
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "home_url": product.home_url,
            "is_active": product.is_active,
            "created_at": product.created_at,
            "plans": plans or [],
            "service_domains": domains,
        }

    @http_get(
        "/products/{slug}/plans",
        response={200: list[PlanOutputSchema], 404: dict},
        summary="List plans for a product",
        description=(
            "Return all active plans for a given product, "
            "ordered by price ascending then sort order."
        ),
    )
    async def list_plans(self, slug: str):
        """List plans for a product."""
        plans = await BillingService.aget_plans_for_product(slug)
        if plans is None:
            raise NotFoundException("Product not found.")
        return plans


# =============================================================================
# Billing Protected Controller — Auth Me + Subscriptions
# =============================================================================


@api_controller(
    "/billing",
    tags=["Billing — Subscriptions"],
    auth=JWTAuth(),
    permissions=[IsAuthenticated],
)
class BillingProtectedController:
    """Authenticated billing endpoints — JWT Bearer token required.

    Read endpoints (auth/me, subscription listing/detail) are available
    to any authenticated user.  Mutation endpoints (cancel, reactivate,
    change-plan, checkout, portal) additionally require email
    verification, enforced via ``require_verified_email()``.
    """

    # =========================================================================
    # Enhanced Auth Me (Domain-Aware)
    # =========================================================================

    @http_get(
        "/auth/me",
        response=AuthMeSchema,
        summary="Get user info with subscription and access",
        description=(
            "Enhanced auth/me endpoint.  Returns user profile, "
            "subscription info, and a domain-specific access map.  "
            "Requires the ``X-Service-Domain`` header to return "
            "subscription data.  Without the header, returns plain "
            "user profile with ``null`` subscription."
        ),
    )
    async def get_auth_me(self, request: HttpRequest):
        """Return user info + subscription + access for the requesting domain."""
        domain = request.headers.get("X-Service-Domain", "").strip()
        return await BillingService.aget_auth_me_data(request.user, domain or None)

    # =========================================================================
    # Subscription Listing
    # =========================================================================

    @http_get(
        "/subscriptions",
        response=list[SubscriptionOutputSchema],
        summary="List user subscriptions",
        description=(
            "Return all subscriptions for the authenticated user "
            "across all products."
        ),
    )
    async def list_subscriptions(self, request: HttpRequest):
        """List all subscriptions for the current user."""
        subscriptions = await BillingService.aget_user_subscriptions(request.user)
        return [
            {
                "id": sub.id,
                "user_id": sub.user_id,
                "status": sub.status,
                "current_period_start": sub.current_period_start,
                "current_period_end": sub.current_period_end,
                "trial_start": sub.trial_start,
                "trial_end": sub.trial_end,
                "canceled_at": sub.canceled_at,
                "expires_at": sub.expires_at,
                "created_at": sub.created_at,
                "updated_at": sub.updated_at,
                "plan_name": sub.plan.name,
                "plan_slug": sub.plan.slug,
                "product_name": sub.product.name,
                "product_slug": sub.product.slug,
            }
            for sub in subscriptions
        ]

    @http_get(
        "/subscriptions/{product_slug}",
        response={200: SubscriptionDetailSchema, 404: dict},
        summary="Get subscription for a product",
        description=(
            "Return the user's subscription detail for a specific "
            "product, including plan and access entries."
        ),
    )
    async def get_subscription(self, request: HttpRequest, product_slug: str):
        """Get subscription detail for a specific product."""
        subscription = await BillingService.aget_subscription_for_product(
            request.user, product_slug
        )
        if not subscription:
            raise NotFoundException("No subscription found for this product.")

        return await BillingService.aget_subscription_detail(subscription)

    # =========================================================================
    # Subscription Actions (require verified email)
    # =========================================================================

    @http_post(
        "/subscriptions/{product_slug}/cancel",
        response={200: MessageResponse, 400: dict, 404: dict},
        summary="Cancel subscription",
        description=(
            "Cancel the subscription at the end of the current billing "
            "period.  Access continues until the period end date.  "
            "Requires email verification."
        ),
    )
    async def cancel_subscription(self, request: HttpRequest, product_slug: str):
        """Cancel a subscription at period end."""
        require_verified_email(request)

        subscription = await BillingService.aget_subscription_for_product(
            request.user, product_slug
        )
        if not subscription:
            raise NotFoundException("No subscription found for this product.")

        if subscription.status not in ("active", "trialing"):
            raise BadRequestException(
                f"Cannot cancel a subscription with status '{subscription.status}'."
            )

        await BillingService.acancel_subscription(subscription)

        # If the subscription has a Stripe subscription, cancel it on Stripe
        if subscription.stripe_subscription_id:
            try:
                from asgiref.sync import sync_to_async

                await sync_to_async(cancel_stripe_subscription)(subscription)
            except Exception as e:
                logger.warning(
                    f"Stripe cancel sync failed for sub {subscription.id}: {e}"
                )

        return MessageResponse(
            message=(
                "Subscription canceled. You will retain access until "
                "the end of your current billing period."
            )
        )

    @http_post(
        "/subscriptions/{product_slug}/reactivate",
        response={200: MessageResponse, 400: dict, 404: dict},
        summary="Reactivate subscription",
        description=(
            "Reactivate a previously canceled subscription.  "
            "Requires email verification."
        ),
    )
    async def reactivate_subscription(self, request: HttpRequest, product_slug: str):
        """Reactivate a canceled subscription."""
        require_verified_email(request)

        subscription = await BillingService.aget_subscription_for_product(
            request.user, product_slug
        )
        if not subscription:
            raise NotFoundException("No subscription found for this product.")

        if subscription.status != "canceled":
            raise BadRequestException("Only canceled subscriptions can be reactivated.")

        await BillingService.areactivate_subscription(subscription)
        return MessageResponse(message="Subscription reactivated successfully.")

    @http_post(
        "/subscriptions/{product_slug}/change-plan",
        response={200: MessageResponse, 400: dict, 404: dict},
        summary="Change subscription plan",
        description=(
            "Switch to a different plan within the same product.  "
            "Requires email verification."
        ),
    )
    async def change_plan(
        self,
        request: HttpRequest,
        product_slug: str,
        payload: ChangePlanInputSchema,
    ):
        """Change the subscription plan."""
        require_verified_email(request)

        subscription = await BillingService.aget_subscription_for_product(
            request.user, product_slug
        )
        if not subscription:
            raise NotFoundException("No subscription found for this product.")

        new_plan = await BillingService.aget_plan_by_slug(
            product_slug, payload.plan_slug
        )
        if not new_plan:
            raise NotFoundException(f"Plan '{payload.plan_slug}' not found.")

        try:
            await BillingService.achange_subscription_plan(subscription, new_plan)
        except ValueError as e:
            raise BadRequestException(str(e))

        # Sync the change with Stripe
        if subscription.stripe_subscription_id:
            from asgiref.sync import sync_to_async

            if new_plan.is_free:
                # Paid → Free: cancel the Stripe subscription at period end
                try:
                    await sync_to_async(cancel_stripe_subscription)(subscription)
                except Exception as e:
                    logger.warning(
                        f"Stripe cancel failed for sub {subscription.id}: {e}"
                    )
            else:
                # Paid → Paid: swap the plan's price on Stripe
                try:
                    await sync_to_async(update_stripe_subscription_plan)(
                        subscription, new_plan
                    )
                except Exception as e:
                    logger.warning(
                        f"Stripe plan sync failed for sub {subscription.id}: {e}"
                    )

        return MessageResponse(message=f"Plan changed to {new_plan.name} successfully.")

    # =========================================================================
    # Stripe Checkout & Portal
    # =========================================================================

    @http_post(
        "/subscriptions/{product_slug}/checkout",
        response={200: CheckoutOutputSchema, 400: dict, 429: dict},
        summary="Create Stripe checkout session",
        description=(
            "Create a Stripe Checkout session for the given plan.  "
            "Returns the checkout URL to redirect the user to.  "
            "Requires email verification and a plan with a Stripe Price ID."
        ),
    )
    async def create_checkout(
        self,
        request: HttpRequest,
        product_slug: str,
        payload: CheckoutInputSchema,
    ):
        """Create a Stripe checkout session.

        Flow:
        1. Validate the plan exists, is active, and is not free
        2. Create/retrieve a Stripe Customer for the user
        3. Create a Stripe Checkout Session
        4. Return the checkout_url
        """
        require_verified_email(request)
        check_rate_limit_or_raise(request, "checkout")

        plan = await BillingService.aget_plan_by_slug(product_slug, payload.plan_slug)
        if not plan:
            raise NotFoundException(f"Plan '{payload.plan_slug}' not found.")

        if plan.is_free:
            raise BadRequestException(
                "Cannot checkout a free plan. Use the change-plan endpoint."
            )

        product = await BillingService.aget_product_by_slug(product_slug)
        if not product:
            raise NotFoundException("Product not found.")

        try:
            from asgiref.sync import sync_to_async

            checkout_url = await sync_to_async(create_checkout_session)(
                user=request.user,
                plan=plan,
                product=product,
                billing_cycle=payload.billing_cycle,
            )
        except ValueError as e:
            raise BadRequestException(str(e))

        return {"checkout_url": checkout_url}

    @http_post(
        "/checkout/confirm",
        response={200: CheckoutConfirmOutputSchema, 400: dict},
        summary="Confirm Stripe checkout and activate subscription",
        description=(
            "Called by the frontend after a successful Stripe redirect. "
            "Fetches the checkout session from Stripe, validates payment "
            "status and user ownership, then activates the local subscription. "
            "This is the PRIMARY activation path — does NOT depend on webhooks."
        ),
    )
    async def confirm_checkout(
        self, request: HttpRequest, payload: CheckoutConfirmInputSchema
    ):
        """Confirm a Stripe checkout and activate the subscription.

        Flow:
        1. Fetch the Stripe checkout session by session_id
        2. Validate payment_status == 'paid' and user ownership
        3. Update the local subscription (plan, status, Stripe IDs, period dates)
        4. Return the activated subscription data
        """
        try:
            from asgiref.sync import sync_to_async

            result = await sync_to_async(confirm_checkout_session)(
                session_id=payload.session_id,
                user=request.user,
            )
        except ValueError as e:
            raise BadRequestException(str(e))

        return result

    @http_post(
        "/portal",
        response={200: PortalOutputSchema, 400: dict},
        summary="Create Stripe Customer Portal session",
        description=(
            "Create a Stripe Customer Portal session for managing "
            "billing.  Returns the portal URL to redirect the user to.  "
            "Requires the user to have at least one Stripe subscription."
        ),
    )
    async def create_portal(self, request: HttpRequest):
        """Create a Stripe Customer Portal session.

        Flow:
        1. Get the user's Stripe Customer ID
        2. Create a Customer Portal session
        3. Return the portal_url
        """
        require_verified_email(request)

        try:
            from asgiref.sync import sync_to_async

            portal_url = await sync_to_async(create_portal_session)(
                user=request.user,
            )
        except ValueError as e:
            raise BadRequestException(str(e))

        return {"portal_url": portal_url}


# =============================================================================
# Billing Webhook Controller — Stripe Webhooks
# =============================================================================


@api_controller(
    "/billing",
    tags=["Billing — Webhooks"],
    auth=None,
)
class BillingWebhookController:
    """Webhook endpoints — no JWT auth (uses request signature verification).

    These endpoints receive and process webhook events from external
    services like Stripe.  Authentication is handled via request
    signature verification (e.g. Stripe-Signature header), not JWT
    tokens.  This is why ``auth=None`` is set — the endpoint is
    publicly accessible but verified by signature.
    """

    @http_post(
        "/webhooks/stripe",
        response={200: MessageResponse},
        summary="Stripe webhook handler",
        description=(
            "Handle Stripe webhook events.  Verifies the Stripe-Signature "
            "header, logs the event for audit, then routes to the "
            "appropriate handler to update subscription state."
        ),
    )
    async def stripe_webhook(self, request: HttpRequest):
        """Handle incoming Stripe webhooks.

        Flow:
        1. Read raw request body and Stripe-Signature header
        2. Verify the webhook signature
        3. Record the event in WebhookEventLog (idempotent)
        4. Process the event (update subscription status)
        """
        from asgiref.sync import sync_to_async

        payload = request.body
        sig_header = request.headers.get("Stripe-Signature", "")

        if not sig_header:
            raise BadRequestException("Missing Stripe-Signature header.")

        try:
            event = await sync_to_async(verify_and_parse_webhook)(payload, sig_header)
        except ValueError as e:
            raise BadRequestException(str(e))
        except stripe.error.SignatureVerificationError:
            raise BadRequestException("Invalid webhook signature.")

        # Record the event for audit (best-effort — never blocks processing)
        log_entry = await sync_to_async(record_webhook_event)(event)

        # Process the event if:
        #   - Recording succeeded AND it hasn't been processed yet, OR
        #   - Recording failed (log_entry is None) — process anyway as fallback
        if log_entry is None or not log_entry.processed:
            await sync_to_async(process_webhook_event)(event)

        return MessageResponse(message="Webhook processed successfully.")
