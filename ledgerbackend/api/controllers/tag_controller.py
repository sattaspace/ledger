"""Tag controller — CRUD for flat, additive transaction tags."""

import logging

from ninja import Query
from ninja_extra import api_controller, route

from api.models import Tag, TransactionTag
from api.schemas.categories import (
    TagCreate,
    TagFilter,
    TagListOut,
    TagOut,
    TagUpdate,
    TransactionTagBulkCreate,
    TransactionTagBulkOut,
    TransactionTagCreate,
    TransactionTagOut,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/tags", tags=["Tags"])
class TagController(LedgerControllerBase):

    # ── Tag CRUD ──────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[TagOut])
    def list_tags(self, request, filters: TagFilter = Query(...)):
        """List all tags for the authenticated user."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        qs = Tag.objects.filter(user_id=user_id)
        qs, limit, offset = self.apply_filters(qs, filters)
        return self.paginate(qs, limit, offset)

    @route.get("/dropdown", response=list[TagListOut])
    def list_dropdown(self, request):
        """Lightweight list for tag chips/autocomplete."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        return list(Tag.objects.filter(user_id=user_id))

    @route.get("/{int:tag_id}", response=TagOut)
    def get_tag(self, request, tag_id: int):
        """Get a single tag by ID."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        return self.get_or_404(Tag, user_id, tag_id)

    @route.post("", response=TagOut)
    def create_tag(self, request, payload: TagCreate):
        """Create a new tag. Name must be unique per user."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_tags", Tag.objects.filter(user_id=user_id).count())
        obj = Tag.objects.create(user_id=user_id, **payload.model_dump())
        logger.info("Tag created: id=%s user_id=%s name=%s", obj.id, user_id, obj.name)
        return obj

    @route.patch("/{int:tag_id}", response=TagOut)
    def update_tag(self, request, tag_id: int, payload: TagUpdate):
        """Update an existing tag."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        obj = self.get_or_404(Tag, user_id, tag_id)
        self.update_object(obj, payload)
        return obj

    @route.delete("/{int:tag_id}", response=MessageOut)
    def soft_delete_tag(self, request, tag_id: int):
        """Soft-delete a tag."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        obj = self.get_or_404(Tag, user_id, tag_id)
        obj.soft_delete()
        return {"detail": "Tag deleted."}

    @route.post("/{int:tag_id}/restore", response=MessageOut)
    def restore_tag(self, request, tag_id: int):
        """Restore a soft-deleted tag."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_tags",
                            Tag.objects.filter(user_id=user_id).count())
        obj = self.get_with_deleted_or_404(Tag, user_id, tag_id)
        obj.restore()
        return {"detail": "Tag restored."}


@api_controller("/transactions", tags=["Transaction Tags"])
class TransactionTagController(LedgerControllerBase):
    """Tag attachment/detachment for transactions.

    Endpoints live under /transactions for RESTful nesting.
    """

    # ── List tags on a transaction ────────────────────────────────────────

    @route.get("/{int:transaction_id}/tags", response=list[TransactionTagOut])
    def list_transaction_tags(self, request, transaction_id: int):
        """List all tags attached to a transaction."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        return list(
            TransactionTag.objects.filter(
                user_id=user_id,
                transaction_id=transaction_id,
            )
        )

    # ── Attach a single tag ───────────────────────────────────────────────

    @route.post("/{int:transaction_id}/tags", response=TransactionTagOut)
    def attach_tag(self, request, transaction_id: int, payload: TransactionTagCreate):
        """Attach a tag to a transaction."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        self.require_subscription_active(request)
        obj = TransactionTag.objects.create(
            user_id=user_id,
            transaction_id=transaction_id,
            tag_id=payload.tag_id,
        )
        logger.info(
            "Tag attached: transaction=%s tag=%s user=%s",
            transaction_id, payload.tag_id, user_id,
        )
        return obj

    # ── Bulk set tags ─────────────────────────────────────────────────────

    @route.post("/{int:transaction_id}/tags/bulk", response=TransactionTagBulkOut)
    def bulk_set_tags(self, request, transaction_id: int, payload: TransactionTagBulkCreate):
        """Replace all tags on a transaction with the provided tag IDs.

        Deletes existing tag links and creates new ones.
        """
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        self.require_subscription_active(request)
        # Check per-transaction tag limit
        self.check_plan_limit(request, "max_tags",
                            TransactionTag.objects.filter(user_id=user_id, transaction_id=transaction_id).count())
        # Remove existing tags
        TransactionTag.objects.filter(
            user_id=user_id,
            transaction_id=transaction_id,
        ).delete()
        # Create new tags
        for tag_id in payload.tag_ids:
            TransactionTag.objects.create(
                user_id=user_id,
                transaction_id=transaction_id,
                tag_id=tag_id,
            )
        logger.info(
            "Tags bulk-set: transaction=%s tags=%s user=%s",
            transaction_id, payload.tag_ids, user_id,
        )
        return {
            "transaction_id": transaction_id,
            "tag_ids": payload.tag_ids,
            "detail": f"Set {len(payload.tag_ids)} tags on transaction {transaction_id}.",
        }

    # ── Detach a tag ──────────────────────────────────────────────────────

    @route.delete("/{int:transaction_id}/tags/{int:tag_id}", response=MessageOut)
    def detach_tag(self, request, transaction_id: int, tag_id: int):
        """Detach a tag from a transaction."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "tags")
        try:
            link = TransactionTag.objects.get(
                user_id=user_id,
                transaction_id=transaction_id,
                tag_id=tag_id,
            )
            link.delete()
            return {"detail": "Tag detached."}
        except TransactionTag.DoesNotExist:
            from django.http import Http404
            raise Http404
