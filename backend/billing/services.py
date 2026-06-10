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
    CreditPool,
    CreditInvoice,
    CreditTransaction,
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
            prefetch_related_objects([plan], "access_entries")
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
        user, product_slug: str, select_for_update: bool = False
    ) -> Optional[Subscription]:
        """Async version of get_subscription_for_product().

        Args:
            user: The user to get subscription for
            product_slug: The product slug
            select_for_update: DEPRECATED — do not use. select_for_update()
                requires transaction.atomic() which cannot be used in async
                context. If you need row locking, use the sync
                get_subscription_for_product() inside a sync_to_async wrapper
                with a proper transaction.atomic() block.

        .. deprecated::
            The ``select_for_update`` parameter is deprecated and will be
            removed in a future version. It does not work correctly in async
            context because Django's transaction.atomic() is synchronous-only.
        """
        if select_for_update:
            logger.warning(
                "aget_subscription_for_product(select_for_update=True) is "
                "deprecated — select_for_update() requires a transaction "
                "that cannot exist in async context. Use the sync "
                "get_subscription_for_product() inside a sync_to_async "
                "wrapper with transaction.atomic() instead."
            )

        product = await BillingService.aget_product_by_slug(product_slug)
        if not product:
            return None

        try:
            qs = Subscription.objects.select_related("plan", "product")
            sub = await qs.aget(user=user, product=product)
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
                    Subscription.objects.select_related("plan")
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
        return await sync_to_async(BillingService.sync_user_subscriptions_from_stripe)(
            user
        )

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
            Subscription.objects.filter(user=user, product=product)
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
        # prefetch_related_objects requires an iterable of model instances,
        # not a single instance.  Wrap in a list to avoid TypeError.
        prefetch_related_objects(
            [subscription.plan],
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
            await Subscription.objects.filter(user=user, product=product)
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
        # prefetch_related_objects requires an iterable of model instances,
        # not a single instance.  Wrap in a list to avoid TypeError.
        await sync_to_async(prefetch_related_objects)(
            [subscription.plan],
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
                "is_credit_based": False,
            },
            "access": access_map,
        }

    # =========================================================================
    # Unified Access Check (Subscription + Credit)
    # =========================================================================

    @staticmethod
    def is_user_active_for_product(user, product) -> dict:
        """
        Check if a user has active access to a product via subscription OR credits.

        Stripe subscription takes precedence. Credit pool is the fallback.

        Returns:
            {
                "is_active": bool,
                "source": "subscription" | "credit" | None,
                "plan": Plan | None,
                "access_map": dict,
                "current_period_end": datetime | None,
                "expires_at": datetime | None,
                "is_credit_based": bool,
            }
        """
        now = timezone.now()

        # 1. Check Stripe subscription first (takes precedence)
        # Only ACTIVE and TRIALING subscriptions take precedence.
        # PAST_DUE / CANCELED subscriptions do NOT mask an active credit pool.
        sub = Subscription.objects.select_related("plan").filter(
            user=user,
            product=product,
            status__in=[
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
            ],
            current_period_end__gt=now,
        ).first()

        if sub:
            prefetch_related_objects(
                [sub.plan],
                Prefetch("access_entries", queryset=AccessEntry.objects.all()),
            )
            return {
                "is_active": True,
                "source": "subscription",
                "plan": sub.plan,
                "access_map": sub.get_access_map(),
                "current_period_end": sub.current_period_end,
                "expires_at": sub.current_period_end,
                "is_credit_based": False,
            }

        # 2. Check credit pool
        # BUG-FIX: Include pools in their 24-hour grace period (expires_at recently
        # passed but within CREDIT_EXPIRY_GRACE_HOURS). The is_effectively_active
        # property on CreditPool already handles this, but the ORM filter here
        # excluded such pools before we even checked. We now fetch pools that are
        # either: (a) no hard deadline, (b) not yet expired, or (c) within grace period.
        from .tasks import CREDIT_EXPIRY_GRACE_HOURS
        grace_cutoff = now - timezone.timedelta(hours=CREDIT_EXPIRY_GRACE_HOURS)

        credit_pool = CreditPool.objects.select_related("plan").filter(
            user=user,
            product=product,
            status=CreditPool.CreditPoolStatus.ACTIVE,
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=grace_cutoff)
        ).order_by("-created_at").first()

        if credit_pool and credit_pool.is_effectively_active:
            prefetch_related_objects(
                [credit_pool.plan],
                Prefetch("access_entries", queryset=AccessEntry.objects.all()),
            )
            access_map = {
                e.key: e.typed_value
                for e in credit_pool.plan.access_entries.all()
            }
            return {
                "is_active": True,
                "source": "credit",
                "plan": credit_pool.plan,
                "access_map": access_map,
                "current_period_end": credit_pool.current_period_end,
                # ENHANCEMENT-5: Return hard expiry (expires_at) and soft expiry
                # (commitment_end) separately. expires_at is an admin override
                # for promotional deadlines; commitment_end is the natural end
                # based on activated_at + credit_periods. When expires_at is None,
                # only soft expiry applies.
                "expires_at": credit_pool.expires_at,
                "commitment_end": credit_pool.commitment_end,
                "is_credit_based": True,
            }

        # 3. OPEN-Q4: Data retention after credit expiry
        # When no active credit pool exists but one recently expired (within
        # CREDIT_DATA_RETENTION_DAYS), grant free-tier access with the free
        # plan's access matrix. Integer values in the access matrix limit the
        # number of data entries (rows) the user can maintain. This ensures
        # data is not lost but is soft-locked to the free tier's limits.
        from .tasks import CREDIT_DATA_RETENTION_DAYS
        retention_cutoff = now - timezone.timedelta(days=CREDIT_DATA_RETENTION_DAYS)
        recently_expired_pool = CreditPool.objects.filter(
            user=user,
            product=product,
            status__in=[
                CreditPool.CreditPoolStatus.EXPIRED,
                CreditPool.CreditPoolStatus.EXHAUSTED,
            ],
            updated_at__gte=retention_cutoff,
        ).order_by("-updated_at").first()

        if recently_expired_pool:
            # User data is within retention window — grant free-plan access
            free_plan = product.get_free_plan()
            if free_plan:
                prefetch_related_objects(
                    [free_plan],
                    Prefetch("access_entries", queryset=AccessEntry.objects.all()),
                )
                free_access_map = {
                    e.key: e.typed_value
                    for e in free_plan.access_entries.all()
                }
                return {
                    "is_active": True,
                    "source": "credit_retention",
                    "plan": free_plan,
                    "access_map": free_access_map,
                    "current_period_end": None,
                    "expires_at": None,
                    "is_credit_based": False,
                    "is_data_retention": True,  # Signal to frontend that data may be soft-locked
                }

        return {
            "is_active": False,
            "source": None,
            "plan": None,
            "access_map": {},
            "current_period_end": None,
            "expires_at": None,
            "is_credit_based": False,
        }

    @staticmethod
    def _compute_next_invoice_id() -> int:
        """Return the next safe invoice ID based on DB max id + 1."""
        last = CreditInvoice.objects.order_by("-id").first()
        return (last.id + 1) if last else 1

    @staticmethod
    def _compute_period_end(start, billing_cycle: str, periods: int):
        """Compute the end date given a start, cycle type, and number of periods."""
        from dateutil.relativedelta import relativedelta

        if billing_cycle == "monthly":
            return start + relativedelta(months=periods)
        elif billing_cycle == "yearly":
            return start + relativedelta(years=periods)
        elif billing_cycle == "lifetime":
            # Cap lifetime credits at 2 years for compliance/liability management
            return start + relativedelta(years=2)
        return start + relativedelta(months=periods)

    @staticmethod
    @transaction.atomic
    def create_credit_pool(user, plan, amount_cents, source="manual",
                           payment_reference="", created_by=None,
                           currency="USD", tax_cents=0, notes="",
                           credit_periods=None, expires_at=None):
        """
        Create a credit pool and its associated invoice.

        Returns:
            (CreditPool, CreditInvoice)

        Raises:
            ValueError: if plan price is 0 or amount is invalid.
        
        CRIT-10 FIX: Added verification that all objects were created successfully
        to prevent partial state where pool exists without invoice.
        
        ENHANCEMENT-1: Added credit_periods parameter. When provided (e.g. from
        a credit request with explicit commitment), it is used directly instead
        of deriving periods from amount_cents // plan.price_cents.

        ENHANCEMENT-5: Added expires_at parameter for admin hard-expiry override.
        When set, the pool will expire on this date regardless of remaining
        periods (e.g., promotional credits with a calendar deadline). When None
        (default), only soft expiry via period consumption applies.

        OPEN-Q7: Mid-cycle credit purchase handling.
        When the user has an ACTIVE credit pool for the same product+plan,
        the new periods are APPENDED to the existing pool (extending
        credit_periods and current_period_end). When no active pool exists
        (expired/exhausted), a new pool is created starting from the payment
        date. This ensures continuity of access and avoids duplicate pools.
        """
        from django.core.exceptions import ValidationError

        if plan.price_cents <= 0 and amount_cents > 0:
            raise ValueError("Cannot buy credits for a free plan.")

        now = timezone.now()
        # ENHANCEMENT-1: Use explicit credit_periods when provided (from credit request),
        # otherwise derive from amount (for admin manual creation backward compat)
        if credit_periods is not None:
            pass  # Use the explicitly provided value
        else:
            credit_periods = max(1, amount_cents // plan.price_cents) if plan.price_cents > 0 else 1

        # ── OPEN-Q7: Mid-cycle credit purchase handling ──────────────────────
        # If the user has an ACTIVE credit pool for the same product+plan,
        # APPEND the new periods to the existing pool instead of creating a
        # separate one. This extends current_period_end and credit_periods,
        # giving the user seamless continuity. When no active pool exists
        # (expired, exhausted, etc.), a new pool starts from the payment date.
        existing_pool = CreditPool.objects.filter(
            user=user,
            product=plan.product,
            plan=plan,
            status=CreditPool.CreditPoolStatus.ACTIVE,
        ).select_for_update().first()

        if existing_pool:
            # Append periods to the existing pool
            old_credit_periods = existing_pool.credit_periods
            old_period_end = existing_pool.current_period_end
            new_credit_periods = old_credit_periods + credit_periods

            # Extend current_period_end by the new periods
            # If the current period hasn't ended yet, extend from current_period_end.
            # If somehow past (edge case), extend from now.
            extension_start = existing_pool.current_period_end or now
            from dateutil.relativedelta import relativedelta as _rd
            if plan.billing_cycle == "yearly":
                extension_delta = _rd(years=credit_periods)
            elif plan.billing_cycle == "lifetime":
                extension_delta = _rd(years=2 * credit_periods)
            else:
                extension_delta = _rd(months=credit_periods)
            new_period_end = extension_start + extension_delta

            existing_pool.credit_periods = new_credit_periods
            existing_pool.amount_cents += amount_cents
            existing_pool.current_period_end = new_period_end
            # If an expires_at was provided and the existing pool doesn't have one,
            # set it. If the existing pool already has expires_at, keep the later one.
            if expires_at:
                if not existing_pool.expires_at or expires_at > existing_pool.expires_at:
                    existing_pool.expires_at = expires_at
            existing_pool.save(update_fields=[
                "credit_periods", "amount_cents", "current_period_end",
                "expires_at", "updated_at",
            ])

            # Create invoice for the appended purchase
            invoice_number = "SB-CRED-%010d" % existing_pool.id
            invoice = CreditInvoice.objects.create(
                credit_pool=existing_pool,
                user=user,
                product=plan.product,
                plan=plan,
                invoice_number=f"{invoice_number}-{existing_pool.credit_periods}",
                status=CreditInvoice.CreditInvoiceStatus.PAID,
                amount_cents=amount_cents,
                currency=currency,
                tax_cents=tax_cents,
                total_cents=amount_cents + tax_cents,
                period_start=now,
                period_end=new_period_end,
                payment_reference=payment_reference,
                notes=notes or f"Appended {credit_periods} period(s) to existing pool #{existing_pool.id}",
                issued_at=now,
            )

            # Create transaction record
            CreditTransaction.objects.create(
                credit_pool=existing_pool,
                invoice=invoice,
                action=CreditTransaction.TransactionType.PURCHASE,
                periods_delta=credit_periods,
                amount_cents_delta=amount_cents,
                periods_balance=existing_pool.periods_remaining,
                reason=f"Appended {credit_periods} period(s) to existing commitment (was {old_credit_periods}, now {new_credit_periods})",
                created_by=created_by,
            )

            logger.info(
                "CREDIT_POOL_APPENDED: user=%s, plan=%s, pool_id=%s, "
                "+%d periods (was %d, now %d), amount=+%sc, source=%s",
                user.email, plan.slug, existing_pool.id,
                credit_periods, old_credit_periods, new_credit_periods,
                amount_cents, source,
            )
            return existing_pool, invoice

        # ── No existing active pool: create a new one ──────────────────────
        period_start = now
        period_end = BillingService._compute_period_end(
            now, plan.billing_cycle, credit_periods
        )

        # Create pool first to get a stable DB ID, then use it for invoice numbering.
        # This guarantees collision-free invoice numbers for tax compliance.
        #
        # ENHANCEMENT-5: expires_at is passed as a parameter for admin overrides
        # (promotional deadlines, accounting year-end, etc.). Default is None,
        # meaning only soft expiry via period consumption applies. The pool's
        # natural end is tracked via the `commitment_end` computed property.
        pool = CreditPool.objects.create(
            user=user,
            product=plan.product,
            plan=plan,
            amount_cents=amount_cents,
            currency=currency,
            credit_periods=credit_periods,
            source=source,
            payment_reference=payment_reference,
            created_by=created_by,
            status=CreditPool.CreditPoolStatus.ACTIVE,
            activated_at=now,
            current_period_start=period_start,
            current_period_end=period_end,
            expires_at=expires_at,  # ENHANCEMENT-5: Admin hard-expiry override (None = soft expiry only)
        )

        # CRIT-10 FIX: Verify pool was created successfully
        if not pool.pk:
            raise ValueError("Failed to create credit pool - rolling back transaction")

        # LOW-12 FIX: Changed from %05d to %010d to support larger pool IDs
        # The previous format limited to 99,999 pools; new format supports up to
        # 9,999,999,999 pools which is sufficient for any scale.
        invoice_number = "SB-CRED-%010d" % pool.id
        invoice = CreditInvoice.objects.create(
            credit_pool=pool,
            user=user,
            product=plan.product,
            plan=plan,
            invoice_number=invoice_number,
            status=CreditInvoice.CreditInvoiceStatus.PAID,
            amount_cents=amount_cents,
            currency=currency,
            tax_cents=tax_cents,
            total_cents=amount_cents + tax_cents,
            period_start=period_start,
            period_end=period_end,
            payment_reference=payment_reference,
            notes=notes,
            issued_at=now,
        )

        # CRIT-10 FIX: Verify invoice was created successfully
        if not invoice.pk:
            raise ValueError("Failed to create invoice - rolling back transaction")

        CreditTransaction.objects.create(
            credit_pool=pool,
            invoice=invoice,
            action=CreditTransaction.TransactionType.PURCHASE,
            periods_delta=credit_periods,
            amount_cents_delta=amount_cents,
            periods_balance=credit_periods,
            reason=f"Credit purchase via {source}",
            created_by=created_by,
        )

        logger.info(
            "CREDIT_POOL_CREATED: user=%s, plan=%s, amount=%sc, "
            "periods=%s, source=%s, invoice=%s",
            user.email,
            plan.slug,
            amount_cents,
            credit_periods,
            source,
            invoice_number,
        )

        return pool, invoice

    @staticmethod
    @transaction.atomic
    def cancel_credit_pools_for_subscription(user, product):
        """
        Cancel all active credit pools for a user+product when they
        start a Stripe subscription. Prevents double-access.
        """
        now = timezone.now()
        active_pools = CreditPool.objects.filter(
            user=user,
            product=product,
            status=CreditPool.CreditPoolStatus.ACTIVE,
        )

        cancelled_count = 0
        for pool in active_pools:
            remaining = pool.periods_remaining
            pool.status = CreditPool.CreditPoolStatus.CANCELLED
            pool.expires_at = now
            pool.current_period_end = now
            pool.save(update_fields=["status", "expires_at", "current_period_end", "updated_at"])

            CreditTransaction.objects.create(
                credit_pool=pool,
                action=CreditTransaction.TransactionType.ADJUST,
                periods_delta=-remaining if remaining > 0 else 0,
                amount_cents_delta=0,
                periods_balance=0,
                reason="Cancelled: user converted to Stripe subscription",
            )
            cancelled_count += 1

        if cancelled_count:
            logger.info(
                "CREDIT_POOLS_CANCELLED_FOR_SUB: user=%s, product=%s, count=%d",
                user.email,
                product.slug,
                cancelled_count,
            )

        return cancelled_count

    @staticmethod
    @transaction.atomic
    def change_credit_plan(pool, new_plan):
        """
        Change the plan of an active credit pool within the same product.

        OPEN-Q3: Credits are transferable between plans. When upgrading,
        the remaining periods are recalculated based on the new plan's price.
        The user's existing payment is treated as credit toward the new plan.

        Logic:
        - Compute remaining value = periods_remaining * old_plan.price_cents
        - Compute new periods = remaining_value // new_plan.price_cents
        - If new_plan.price_cents == 0 (free), mark remaining as 1 period
        - Update pool with new plan, credit_periods, and current_period_end

        Raises:
            ValueError: if new_plan belongs to a different product, or pool
                is not active, or new plan is free (cannot buy credits for free).
        """
        now = timezone.now()
        from dateutil.relativedelta import relativedelta

        if new_plan.product_id != pool.product_id:
            raise ValueError(
                f"Cannot change to plan '{new_plan.slug}' — it belongs to a "
                f"different product. Current product: {pool.product.slug}, "
                f"new plan's product: {new_plan.product.slug}."
            )

        if pool.status != CreditPool.CreditPoolStatus.ACTIVE:
            raise ValueError(
                f"Cannot change plan for a pool with status '{pool.status}'. "
                f"Only active pools can be changed."
            )

        if new_plan.price_cents <= 0:
            raise ValueError(
                "Cannot change to a free plan within a credit commitment. "
                "Cancel the credit pool and subscribe to the free plan instead."
            )

        old_plan = pool.plan
        periods_remaining = pool.periods_remaining

        # Compute the remaining monetary value based on the old plan's price
        remaining_value_cents = periods_remaining * old_plan.price_cents

        # Compute how many periods the remaining value buys on the new plan
        new_periods = max(1, remaining_value_cents // new_plan.price_cents)
        # Check for leftover cents that don't fit a full period
        leftover_cents = remaining_value_cents % new_plan.price_cents

        # Recalculate total credit_periods for the pool
        new_total_periods = pool.periods_consumed + new_periods

        # Recalculate current_period_end based on new plan's billing cycle
        # Start from the current period start and add new_periods
        period_start = pool.current_period_start or now
        if new_plan.billing_cycle == "yearly":
            total_delta = relativedelta(years=new_total_periods)
        elif new_plan.billing_cycle == "lifetime":
            total_delta = relativedelta(years=new_total_periods * 2)
        else:
            total_delta = relativedelta(months=new_total_periods)

        new_period_end = (pool.activated_at or period_start) + total_delta

        old_plan_slug = pool.plan.slug
        pool.plan = new_plan
        pool.credit_periods = new_total_periods
        pool.current_period_end = new_period_end
        pool.save(update_fields=[
            "plan", "credit_periods", "current_period_end", "updated_at",
        ])

        # Create transaction record for the plan change
        CreditTransaction.objects.create(
            credit_pool=pool,
            action=CreditTransaction.TransactionType.ADJUST,
            periods_delta=new_periods - periods_remaining,  # May be negative for upgrades
            amount_cents_delta=0,  # No additional payment — credit transfer
            periods_balance=pool.periods_remaining,
            reason=(
                f"Plan changed from '{old_plan_slug}' to '{new_plan.slug}': "
                f"{periods_remaining} remaining period(s) at {old_plan.price_cents}c/period "
                f"= {remaining_value_cents}c → {new_periods} period(s) at "
                f"{new_plan.price_cents}c/period"
                + (f" ({leftover_cents}c unused)" if leftover_cents > 0 else "")
            ),
        )

        logger.info(
            "CREDIT_PLAN_CHANGE: user=%s, pool_id=%s, old_plan=%s, new_plan=%s, "
            "old_remaining=%d, new_remaining=%d, value=%dc, leftover=%dc",
            pool.user.email, pool.id, old_plan_slug, new_plan.slug,
            periods_remaining, new_periods, remaining_value_cents, leftover_cents,
        )

        return {
            "old_plan": old_plan_slug,
            "new_plan": new_plan.slug,
            "old_periods_remaining": periods_remaining,
            "new_periods_remaining": new_periods,
            "remaining_value_cents": remaining_value_cents,
            "leftover_cents": leftover_cents,
        }

    # =========================================================================
    # Async wrappers for credit methods
    # =========================================================================

    @staticmethod
    async def aget_user_active_for_product(user, product) -> dict:
        return await sync_to_async(BillingService.is_user_active_for_product)(user, product)

    @staticmethod
    async def acancel_credit_pools_for_subscription(user, product):
        return await sync_to_async(BillingService.cancel_credit_pools_for_subscription)(user, product)

    @staticmethod
    async def achange_credit_plan(pool, new_plan):
        return await sync_to_async(BillingService.change_credit_plan)(pool, new_plan)
