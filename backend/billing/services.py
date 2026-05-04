"""Business logic services for the billing app.

Services encapsulate all business logic for subscription management,
product/plan queries, and the enhanced auth/me response. Controllers
should only handle HTTP concerns and delegate to services.

Each method has both sync and async variants (prefixed with ``a``)
for use in async controller endpoints.

Methods return ``None`` for "not found" cases (callers decide whether
that is an error). Validation errors raise ``ValueError`` (callers
catch and re-raise as ``BadRequestException``).
"""

import logging
from typing import Optional

from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import prefetch_related_objects, Prefetch
from django.db.models import Q

from .models import (
    ServiceDomain,
    Product,
    Plan,
    AccessEntry,
    Subscription,
    SubscriptionStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Billing Service
# =============================================================================


class BillingService:
    """Handles all billing-related business logic.

    Methods are organized into:
    - Product queries (public)
    - Plan queries (public)
    - Subscription management (authenticated)
    - Auth me data (authenticated, domain-aware)
    """

    # =========================================================================
    # Product Queries
    # =========================================================================

    @staticmethod
    def get_products_queryset(active_only: bool = True):
        """Return a queryset of products for pagination or further filtering.

        Unlike ``get_products`` which evaluates immediately, this returns
        an unevaluated queryset that can be passed to pagination utilities.
        """
        qs = Product.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by("name")

    @staticmethod
    def get_products(active_only: bool = True) -> list[Product]:
        """Return list of products, optionally filtering to active only."""
        return list(BillingService.get_products_queryset(active_only))

    @staticmethod
    async def aget_products(active_only: bool = True) -> list[Product]:
        """Async version of get_products()."""
        return [p async for p in BillingService.get_products_queryset(active_only)]

    @staticmethod
    def get_product_by_slug(slug: str) -> Optional[Product]:
        """Get a product by its slug. Returns None if not found or inactive."""
        try:
            return Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return None

    @staticmethod
    async def aget_product_by_slug(slug: str) -> Optional[Product]:
        """Async version of get_product_by_slug()."""
        try:
            return await Product.objects.aget(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return None

    # =========================================================================
    # Plan Queries
    # =========================================================================

    @staticmethod
    def get_plans_for_product(
        product_slug: str, active_only: bool = True
    ) -> Optional[list[Plan]]:
        """Return plans for a product, ordered by price ascending."""
        product = BillingService.get_product_by_slug(product_slug)
        if not product:
            return None

        qs = product.plans.all()
        if active_only:
            qs = qs.filter(is_active=True)
        return list(qs.order_by("price_cents", "sort_order"))

    @staticmethod
    async def aget_plans_for_product(
        product_slug: str, active_only: bool = True
    ) -> Optional[list[Plan]]:
        """Async version of get_plans_for_product()."""
        product = await BillingService.aget_product_by_slug(product_slug)
        if not product:
            return None

        qs = product.plans.all()
        if active_only:
            qs = qs.filter(is_active=True)
        return [p async for p in qs.order_by("price_cents", "sort_order")]

    @staticmethod
    def get_plan_detail(plan_id: int) -> Optional[Plan]:
        """Get a plan with its access entries prefetched."""
        try:
            plan = Plan.objects.select_related("product").get(
                id=plan_id, is_active=True
            )
            prefetch_related_objects(plan, "access_entries")
            return plan
        except Plan.DoesNotExist:
            return None

    @staticmethod
    async def aget_plan_detail(plan_id: int) -> Optional[Plan]:
        """Async version of get_plan_detail()."""
        try:
            plan = await Plan.objects.select_related("product").aget(
                id=plan_id, is_active=True
            )
            await plan.access_entries.all()
            return plan
        except Plan.DoesNotExist:
            return None

    @staticmethod
    def get_plan_by_slug(product_slug: str, plan_slug: str) -> Optional[Plan]:
        """Get a plan by product slug + plan slug."""
        product = BillingService.get_product_by_slug(product_slug)
        if not product:
            return None
        try:
            return product.plans.select_related("product").get(
                slug=plan_slug, is_active=True
            )
        except Plan.DoesNotExist:
            return None

    @staticmethod
    async def aget_plan_by_slug(product_slug: str, plan_slug: str) -> Optional[Plan]:
        """Async version of get_plan_by_slug()."""
        product = await BillingService.aget_product_by_slug(product_slug)
        if not product:
            return None
        try:
            return await product.plans.select_related("product").aget(
                slug=plan_slug, is_active=True
            )
        except Plan.DoesNotExist:
            return None

    # =========================================================================
    # Subscription Management
    # =========================================================================

    @staticmethod
    def get_subscriptions_queryset(user):
        """Return a queryset of user subscriptions for pagination.

        Annotates with plan and product names/slugs so the queryset
        can be serialized directly with ``SubscriptionOutputSchema``.
        """
        return (
            Subscription.objects.filter(user=user)
            .select_related("plan", "product")
            .order_by("-created_at")
        )

    @staticmethod
    def get_user_subscriptions(user) -> list[Subscription]:
        """Return all subscriptions for a user."""
        return list(BillingService.get_subscriptions_queryset(user))

    @staticmethod
    async def aget_user_subscriptions(user) -> list[Subscription]:
        """Async version of get_user_subscriptions()."""
        return [s async for s in BillingService.get_subscriptions_queryset(user)]

    @staticmethod
    def get_subscription_for_product(user, product_slug: str) -> Optional[Subscription]:
        """Get user's subscription for a specific product."""
        product = BillingService.get_product_by_slug(product_slug)
        if not product:
            return None

        try:
            sub = Subscription.objects.select_related("plan").get(
                user=user, product=product
            )
            return sub
        except Subscription.DoesNotExist:
            return None

    @staticmethod
    async def aget_subscription_for_product(
        user, product_slug: str
    ) -> Optional[Subscription]:
        """Async version of get_subscription_for_product()."""
        product = await BillingService.aget_product_by_slug(product_slug)
        if not product:
            return None

        try:
            sub = await Subscription.objects.select_related("plan", "product").aget(
                user=user, product=product
            )
            return sub
        except Subscription.DoesNotExist:
            return None

    @staticmethod
    def get_or_create_free_subscription(user, product: Product) -> Subscription:
        """Get existing subscription or create with the product's free plan.

        If the user has no subscription for this product, automatically
        creates one with the free plan (price_cents=0). This ensures
        every user always has access to at least the free tier.

        SVC-01 Fix: Uses select_for_update() + transaction.atomic() to
        prevent the TOCTOU race condition where concurrent requests both
        see DoesNotExist and both create duplicate subscriptions.
        """
        with transaction.atomic():
            try:
                sub = (
                    Subscription.objects
                    .select_related("plan")
                    .select_for_update()
                    .get(user=user, product=product)
                )
                return sub
            except Subscription.DoesNotExist:
                free_plan = product.get_free_plan()
                if not free_plan:
                    # No free plan configured — cannot auto-create
                    logger.warning(
                        f"No free plan found for product '{product.slug}'. "
                        f"Cannot auto-create subscription for user {user.email}."
                    )
                    return None

                sub = Subscription.objects.create(
                    user=user,
                    plan=free_plan,
                    product=product,
                    status=SubscriptionStatus.ACTIVE,
                )
                logger.info(
                    f"Free subscription created: user={user.email}, "
                    f"product={product.slug}, plan={free_plan.slug}"
                )
                return sub

    @staticmethod
    async def aget_or_create_free_subscription(
        user, product: Product
    ) -> Optional[Subscription]:
        """Async version of get_or_create_free_subscription().

        SVC-01 Fix: Wraps the sync implementation in sync_to_async() with
        transaction.atomic() and select_for_update() to prevent duplicate
        subscription creation under concurrent requests.
        """
        return await sync_to_async(BillingService.get_or_create_free_subscription)(
            user, product
        )

    @staticmethod
    def cancel_subscription(subscription: Subscription) -> None:
        """Cancel a subscription at the end of the current billing period."""
        subscription.schedule_cancellation()
        logger.info(
            f"Subscription canceled: user={subscription.user.email}, "
            f"plan={subscription.plan.slug}"
        )

    @staticmethod
    async def acancel_subscription(subscription: Subscription) -> None:
        """Async version of cancel_subscription()."""
        await sync_to_async(BillingService._do_cancel)(subscription)

    @staticmethod
    def _do_cancel(subscription: Subscription) -> None:
        subscription.schedule_cancellation()
        logger.info(
            f"Subscription canceled: user={subscription.user.email}, "
            f"plan={subscription.plan.slug}"
        )

    @staticmethod
    def sync_user_subscriptions_from_stripe(user) -> list[Subscription]:
        """Force-sync all user subscriptions from Stripe.

        Iterates all user subscriptions that have a stripe_subscription_id
        and calls sync_subscription_from_stripe() for each.  This ensures
        the local DB reflects the latest Stripe state after portal visits
        or external changes.

        Returns the refreshed list of subscriptions.
        """
        from .stripe.webhooks.sync import sync_subscription_from_stripe

        subs = Subscription.objects.filter(
            user=user,
            stripe_subscription_id__isnull=False,
        ).exclude(stripe_subscription_id="")

        synced = []
        for sub in subs:
            try:
                updated = sync_subscription_from_stripe(
                    sub.stripe_subscription_id, subscription=sub
                )
                synced.append(updated)
            except Exception as e:
                logger.warning(
                    f"Failed to sync sub {sub.id} "
                    f"(stripe={sub.stripe_subscription_id}): {e}"
                )

        # Also return subscriptions without Stripe IDs (free plans)
        all_subs = list(
            Subscription.objects.filter(user=user)
            .select_related("plan", "product")
            .order_by("-created_at")
        )
        return all_subs

    @staticmethod
    async def async_sync_user_subscriptions_from_stripe(user) -> list:
        """Async version of sync_user_subscriptions_from_stripe."""
        return await sync_to_async(BillingService.sync_user_subscriptions_from_stripe)(user)

    @staticmethod
    def reactivate_subscription(subscription: Subscription) -> None:
        """Reactivate a previously canceled subscription."""
        subscription.reactivate()
        logger.info(
            f"Subscription reactivated: user={subscription.user.email}, "
            f"plan={subscription.plan.slug}"
        )

    @staticmethod
    async def areactivate_subscription(subscription: Subscription) -> None:
        """Async version of reactivate_subscription()."""
        await sync_to_async(BillingService._do_reactivate)(subscription)

    @staticmethod
    def _do_reactivate(subscription: Subscription) -> None:
        subscription.reactivate()
        logger.info(
            f"Subscription reactivated: user={subscription.user.email}, "
            f"plan={subscription.plan.slug}"
        )

    @staticmethod
    def change_subscription_plan(subscription: Subscription, new_plan: Plan) -> None:
        """Switch a subscription to a different plan within the same product."""
        if new_plan.product_id != subscription.product_id:
            raise ValueError("Cannot switch to a plan from a different product.")

        subscription.change_plan(new_plan)
        logger.info(
            f"Plan changed: user={subscription.user.email}, "
            f"old_plan={subscription.plan.slug} → new_plan={new_plan.slug}"
        )

    @staticmethod
    async def achange_subscription_plan(
        subscription: Subscription, new_plan: Plan
    ) -> None:
        """Async version of change_subscription_plan()."""
        if new_plan.product_id != subscription.product_id:
            raise ValueError("Cannot switch to a plan from a different product.")
        await sync_to_async(BillingService._do_change_plan)(subscription, new_plan)

    @staticmethod
    def _do_change_plan(subscription: Subscription, new_plan: Plan) -> None:
        # SVC-03 Fix: Capture old_plan BEFORE change_plan() modifies
        # subscription.plan. Previously, the log line read subscription.plan.slug
        # AFTER the mutation, so both old_plan and new_plan appeared as the
        # same slug — useless for debugging.
        old_plan_slug = subscription.plan.slug
        subscription.change_plan(new_plan)
        logger.info(
            f"Plan changed: user={subscription.user.email}, "
            f"old_plan={old_plan_slug} → new_plan={new_plan.slug}"
        )

    # =========================================================================
    # Service Domain Queries
    # =========================================================================

    @staticmethod
    async def aget_service_domains_for_product(product: Product) -> list[dict]:
        """Get service domains for a product as serialized dicts.

        Returns domains ordered by primary first, then alphabetically.
        Used in product detail responses.
        """
        domains = [
            d
            async for d in ServiceDomain.objects.filter(product=product).order_by(
                "-is_primary", "domain"
            )
        ]
        return [
            {
                "id": d.id,
                "domain": d.domain,
                "product_id": d.product_id,
                "is_primary": d.is_primary,
                "is_active": d.is_active,
            }
            for d in domains
        ]

    @staticmethod
    async def aget_subscription_detail(subscription: Subscription) -> dict:
        """Build full subscription detail response with plan and access map.

        Prefetches the plan's access entries to avoid N+1 queries.
        Returns a dict matching ``SubscriptionDetailSchema``.
        """
        await sync_to_async(prefetch_related_objects)(
            [subscription.plan],
            Prefetch("access_entries", queryset=AccessEntry.objects.all()),
        )

        access_map = subscription.get_access_map()
        plan = subscription.plan

        return {
            "id": subscription.id,
            "user_id": subscription.user_id,
            "status": subscription.status,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "trial_start": subscription.trial_start,
            "trial_end": subscription.trial_end,
            "canceled_at": subscription.canceled_at,
            "expires_at": subscription.expires_at,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at,
            "plan_name": plan.name,
            "plan_slug": plan.slug,
            "product_name": subscription.product.name,
            "product_slug": subscription.product.slug,
            "plan": {
                "id": plan.id,
                "name": plan.name,
                "slug": plan.slug,
                "description": plan.description,
                "price_cents": plan.price_cents,
                "currency": plan.currency,
                "billing_cycle": plan.billing_cycle,
                "trial_days": plan.trial_days,
                "features": plan.features,
                "sort_order": plan.sort_order,
                "is_active": plan.is_active,
                "is_featured": plan.is_featured,
                "display_price": plan.display_price,
                "is_free": plan.is_free,
                "access_entries": [
                    {
                        "key": e.key,
                        "value": e.typed_value,
                        "description": e.description,
                    }
                    for e in plan.access_entries.all()
                ],
            },
            "access": access_map,
        }

    # =========================================================================
    # Auth Me Data (Domain-Aware)
    # =========================================================================

    @staticmethod
    def _get_account_status(user) -> str:
        """Return the user's account status string.

        Returns ``"deleted"``, ``"inactive"``, or ``"active"``.
        This is included in the auth/me response so SDK consumers can
        perform defensive status checks even when the 401 error code
        is not reliably propagated through their HTTP client.
        """
        if getattr(user, "is_deleted", False):
            return "deleted"
        if not getattr(user, "is_active", True):
            return "inactive"
        return "active"

    @staticmethod
    def get_auth_me_data(user, domain: Optional[str] = None) -> dict:
        """Build the enhanced auth/me response.

        When a domain header is provided:
        1. Look up ServiceDomain by domain
        2. Get user's subscription for that product (or free plan)
        3. Build access map from plan's access entries

        When no domain header:
        Returns plain user data with null subscription and empty access.

        Args:
            user: The authenticated user (already validated by JWTAuth).
            domain: The X-Service-Domain header value.

        Returns:
            Dict with 'user', 'account_status', 'subscription', and 'access' keys.
        """
        account_status = BillingService._get_account_status(user)

        if not domain:
            return {
                "user": user,
                "account_status": account_status,
                "subscription": None,
                "access": {},
            }

        # Look up service domain → product
        try:
            service_domain = ServiceDomain.objects.select_related("product").get(
                domain=domain, is_active=True
            )
        except ServiceDomain.DoesNotExist:
            logger.warning(f"Unknown service domain in auth/me: {domain}")
            return {
                "user": user,
                "account_status": account_status,
                "subscription": None,
                "access": {},
            }

        product = service_domain.product
        if not product.is_active:
            return {
                "user": user,
                "account_status": account_status,
                "subscription": None,
                "access": {},
            }

        # SVC-02 Fix: Attempt to find existing subscription first without
        # creating.  Only call get_or_create_free_subscription if no
        # subscription exists.  This makes the GET endpoint read-only in
        # the common case (users who already have a subscription).
        subscription = (
            Subscription.objects
            .filter(user=user, product=product)
            .select_related("plan")
            .first()
        )
        if not subscription:
            # Only create when genuinely missing
            subscription = BillingService.get_or_create_free_subscription(user, product)
        if not subscription:
            return {
                "user": user,
                "account_status": account_status,
                "subscription": None,
                "access": {},
            }

        # Build access map
        prefetch_related_objects(
            subscription.plan,
            Prefetch(
                "access_entries",
                queryset=AccessEntry.objects.all(),
            ),
        )
        access_map = subscription.get_access_map()

        return {
            "user": user,
            "account_status": account_status,
            "subscription": {
                "plan_name": subscription.plan.name,
                "plan_slug": subscription.plan.slug,
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "current_period_end": subscription.current_period_end,
                "trial_end": subscription.trial_end,
                "is_active": subscription.is_effectively_active(),
            },
            "access": access_map,
        }

    @staticmethod
    async def aget_auth_me_data(user, domain: Optional[str] = None) -> dict:
        """Async version of get_auth_me_data()."""
        account_status = BillingService._get_account_status(user)

        if not domain:
            return {
                "user": user,
                "account_status": account_status,
                "subscription": None,
                "access": {},
            }

        # Look up service domain → product
        try:
            service_domain = await ServiceDomain.objects.select_related("product").aget(
                domain=domain, is_active=True
            )
        except ServiceDomain.DoesNotExist:
            logger.warning(f"Unknown service domain in auth/me: {domain}")
            return {
                "user": user,
                "account_status": account_status,
                "subscription": None,
                "access": {},
            }

        product = service_domain.product
        if not product.is_active:
            return {
                "user": user,
                "account_status": account_status,
                "subscription": None,
                "access": {},
            }

        # SVC-02 Fix: Attempt to find existing subscription first without
        # creating.  Only call aget_or_create_free_subscription if no
        # subscription exists.  This makes the GET endpoint read-only in
        # the common case (users who already have a subscription).
        subscription = (
            await Subscription.objects
            .filter(user=user, product=product)
            .select_related("plan")
            .afirst()
        )
        if not subscription:
            subscription = await BillingService.aget_or_create_free_subscription(
                user, product
            )
        if not subscription:
            return {
                "user": user,
                "account_status": account_status,
                "subscription": None,
                "access": {},
            }

        # Build access map
        await sync_to_async(prefetch_related_objects)(
            subscription.plan,
            Prefetch(
                "access_entries",
                queryset=AccessEntry.objects.all(),
            ),
        )
        access_map = subscription.get_access_map()

        return {
            "user": user,
            "account_status": account_status,
            "subscription": {
                "plan_name": subscription.plan.name,
                "plan_slug": subscription.plan.slug,
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "current_period_end": subscription.current_period_end,
                "trial_end": subscription.trial_end,
                "is_active": subscription.is_effectively_active(),
            },
            "access": access_map,
        }
