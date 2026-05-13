"""Test controller — verifies Sattabase SDK integration.

Every endpoint reads ``request.sattabase_user`` (set by
``SattabaseAuthMiddleware``) and scopes data by ``user_id``.
If the middleware didn't attach a user (no JWT / invalid token),
the endpoints return 401.
"""

import logging

from ninja_extra import ControllerBase, api_controller, route

from api.models import TestNote
from api.schemas import TestNoteCreate, TestNoteOut, TestNoteUpdate

logger = logging.getLogger(__name__)


def _get_sattabase_user_id(request) -> int | None:
    """Extract user_id from the Sattabase middleware attributes.

    Returns None if the user is not authenticated via Sattabase.
    """
    user = getattr(request, "sattabase_user", None)
    if user is not None and hasattr(user, "id"):
        return user.id
    return None


@api_controller("/test-notes", tags=["Test Notes"])
class TestNoteController(ControllerBase):

    @route.get("", response=list[TestNoteOut])
    def list_notes(self, request):
        """List all test notes for the authenticated Sattabase user."""
        user_id = _get_sattabase_user_id(request)
        if user_id is None:
            return self.create_response(
                {"detail": "Authentication required via Sattabase."},
                status_code=401,
            )
        notes = TestNote.objects.filter(user_id=user_id)
        return list(notes)

    @route.post("", response=TestNoteOut)
    def create_note(self, request, payload: TestNoteCreate):
        """Create a test note for the authenticated Sattabase user."""
        user_id = _get_sattabase_user_id(request)
        if user_id is None:
            return self.create_response(
                {"detail": "Authentication required via Sattabase."},
                status_code=401,
            )
        note = TestNote.objects.create(
            user_id=user_id,
            title=payload.title,
            content=payload.content,
        )
        logger.info("TestNote created: id=%s user_id=%s", note.id, user_id)
        return note

    @route.get("/{int:note_id}", response=TestNoteOut)
    def get_note(self, request, note_id: int):
        """Get a single test note (must belong to the authenticated user)."""
        user_id = _get_sattabase_user_id(request)
        if user_id is None:
            return self.create_response(
                {"detail": "Authentication required via Sattabase."},
                status_code=401,
            )
        try:
            note = TestNote.objects.get(id=note_id, user_id=user_id)
        except TestNote.DoesNotExist:
            return self.create_response(
                {"detail": "Not found."},
                status_code=404,
            )
        return note

    @route.patch("/{int:note_id}", response=TestNoteOut)
    def update_note(self, request, note_id: int, payload: TestNoteUpdate):
        """Update a test note (must belong to the authenticated user)."""
        user_id = _get_sattabase_user_id(request)
        if user_id is None:
            return self.create_response(
                {"detail": "Authentication required via Sattabase."},
                status_code=401,
            )
        try:
            note = TestNote.objects.get(id=note_id, user_id=user_id)
        except TestNote.DoesNotExist:
            return self.create_response(
                {"detail": "Not found."},
                status_code=404,
            )
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(note, field, value)
        note.save()
        return note

    @route.delete("/{int:note_id}")
    def delete_note(self, request, note_id: int):
        """Delete a test note (must belong to the authenticated user)."""
        user_id = _get_sattabase_user_id(request)
        if user_id is None:
            return self.create_response(
                {"detail": "Authentication required via Sattabase."},
                status_code=401,
            )
        try:
            note = TestNote.objects.get(id=note_id, user_id=user_id)
        except TestNote.DoesNotExist:
            return self.create_response(
                {"detail": "Not found."},
                status_code=404,
            )
        note.delete()
        return {"detail": "Deleted."}

    @route.get("/me", response=dict)
    def me(self, request):
        """Return the Sattabase user profile from the middleware.

        Useful for quickly checking SDK integration — if this returns
        user data, the full Sattabase auth chain is working:
        JWT → middleware → auth/me → user + access + subscription + exchange_rates + currencies.
        """
        user = getattr(request, "sattabase_user", None)
        access = getattr(request, "sattabase_access", {})
        subscription = getattr(request, "sattabase_subscription", None)
        exchange_rates = getattr(request, "sattabase_exchange_rates", None)
        currencies = getattr(request, "sattabase_currencies", None)

        if user is None:
            return self.create_response(
                {"detail": "Not authenticated via Sattabase."},
                status_code=401,
            )

        # Cache currency metadata from auth/me piggyback if available
        if currencies:
            from api.currency import cache_currencies_from_auth_me
            cache_currencies_from_auth_me(currencies)

        result = {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "display_name": user.display_name,
            "role": user.role,
            "currency": getattr(user, "currency", None),
            "timezone": getattr(user, "timezone", None),
            "language": getattr(user, "language", None),
            "access": access,
        }
        if exchange_rates:
            result["exchange_rates_count"] = len(exchange_rates)
        if currencies:
            result["currencies_count"] = len(currencies)
        if subscription:
            result["subscription"] = {
                "plan_name": subscription.plan_name,
                "status": subscription.status,
                "is_active": subscription.is_active,
            }
        return result
