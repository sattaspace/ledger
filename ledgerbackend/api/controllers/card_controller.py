"""Card controller — CRUD for debit and credit cards linked to accounts."""

import logging

from ninja import Query
from ninja_extra import api_controller, route

from api.models import Card
from api.schemas.cards import (
    CardCreate,
    CardFilter,
    CardListOut,
    CardOut,
    CardUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/cards", tags=["Cards"])
class CardController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[CardOut])
    def list_cards(self, request, filters: CardFilter = Query(...)):
        """List all cards for the authenticated user."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "cards")
        qs = Card.objects.filter(user_id=user_id).select_related("account")
        qs, limit, offset = self.apply_filters(qs, filters)
        return self.paginate(qs, limit, offset)

    @route.get("/dropdown", response=list[CardListOut])
    def list_dropdown(self, request):
        """Lightweight list for card selection components."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "cards")
        return list(Card.objects.filter(user_id=user_id).select_related("account"))

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:card_id}", response=CardOut)
    def get_card(self, request, card_id: int):
        """Get a single card by ID."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "cards")
        return self.get_or_404(Card, user_id, card_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=CardOut)
    def create_card(self, request, payload: CardCreate):
        """Create a new card linked to an account."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "cards")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_cards", Card.objects.filter(user_id=user_id).count())
        data = payload.model_dump()
        data["account_id"] = data.pop("account_id")
        obj = Card.objects.create(user_id=user_id, **data)
        logger.info("Card created: id=%s user_id=%s name=%s", obj.id, user_id, obj.card_name)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:card_id}", response=CardOut)
    def update_card(self, request, card_id: int, payload: CardUpdate):
        """Update an existing card."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "cards")
        obj = self.get_or_404(Card, user_id, card_id)
        self.update_object(obj, payload)
        return obj

    # ── Soft Delete / Restore ─────────────────────────────────────────────

    @route.delete("/{int:card_id}", response=MessageOut)
    def soft_delete_card(self, request, card_id: int):
        """Soft-delete a card."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "cards")
        obj = self.get_or_404(Card, user_id, card_id)
        obj.soft_delete()
        return {"detail": "Card deleted."}

    @route.post("/{int:card_id}/restore", response=MessageOut)
    def restore_card(self, request, card_id: int):
        """Restore a soft-deleted card."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "cards")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_cards",
                            Card.objects.filter(user_id=user_id).count())
        obj = self.get_with_deleted_or_404(Card, user_id, card_id)
        obj.restore()
        return {"detail": "Card restored."}

    # ── Activate / Deactivate ─────────────────────────────────────────────

    @route.post("/{int:card_id}/activate", response=MessageOut)
    def activate_card(self, request, card_id: int):
        """Activate a card."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "cards")
        obj = self.get_or_404(Card, user_id, card_id)
        obj.activate()
        return {"detail": "Card activated."}

    @route.post("/{int:card_id}/deactivate", response=MessageOut)
    def deactivate_card(self, request, card_id: int):
        """Deactivate a card."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "cards")
        obj = self.get_or_404(Card, user_id, card_id)
        obj.deactivate()
        return {"detail": "Card deactivated."}
