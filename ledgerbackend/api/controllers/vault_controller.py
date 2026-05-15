"""Document Vault controller — CRUD for secure document storage."""

import logging

from ninja import Query
from ninja_extra import api_controller, route

from api.models import DocumentVault
from api.schemas.vault import (
    DocumentVaultCreate,
    DocumentVaultFilter,
    DocumentVaultListOut,
    DocumentVaultOut,
    DocumentVaultUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/vault", tags=["Document Vault"])
class VaultController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[DocumentVaultOut])
    def list_documents(self, request, filters: DocumentVaultFilter = Query(...)):
        """List all documents for the authenticated user."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        qs = DocumentVault.objects.filter(user_id=user_id)

        # Handle special filters
        filter_dict = filters.model_dump(exclude_unset=True)
        limit = filter_dict.pop("limit", 50)
        offset = filter_dict.pop("offset", 0)
        expiring_within = filter_dict.pop("expiring_within_days", None)
        search = filter_dict.pop("search", None)

        for field, value in filter_dict.items():
            if value is not None:
                qs = qs.filter(**{field: value})

        if expiring_within:
            from django.utils import timezone
            from datetime import timedelta
            today = timezone.now().date()
            future = today + timedelta(days=expiring_within)
            qs = qs.filter(
                expiry_date__lte=future,
                remind_before_expiry=True,
            )

        if search:
            qs = qs.filter(title__icontains=search)

        return self.paginate(qs, limit, offset)

    @route.get("/expiring", response=list[DocumentVaultListOut])
    def list_expiring(self, request, days: int = 30):
        """Get documents expiring within N days (for dashboard/alerts)."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        future = today + timedelta(days=days)
        return list(
            DocumentVault.objects.filter(
                user_id=user_id,
                expiry_date__lte=future,
                remind_before_expiry=True,
            )
        )

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:document_id}", response=DocumentVaultOut)
    def get_document(self, request, document_id: int):
        """Get a single document by ID."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        return self.get_or_404(DocumentVault, user_id, document_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=DocumentVaultOut)
    def create_document(self, request, payload: DocumentVaultCreate):
        """Create a new document record in the vault.

        Note: File upload is handled via multipart form data.
        The file field is set separately from the metadata.
        """
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        data = payload.model_dump()
        data["content_type_id"] = data.pop("content_type_id")
        obj = DocumentVault.objects.create(user_id=user_id, **data)
        logger.info("Document created: id=%s user_id=%s title=%s", obj.id, user_id, obj.title)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:document_id}", response=DocumentVaultOut)
    def update_document(self, request, document_id: int, payload: DocumentVaultUpdate):
        """Update document metadata. The file itself cannot be updated — delete and re-upload."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        obj = self.get_or_404(DocumentVault, user_id, document_id)
        self.update_object(obj, payload)
        return obj

    # ── Soft Delete / Restore ─────────────────────────────────────────────

    @route.delete("/{int:document_id}", response=MessageOut)
    def soft_delete_document(self, request, document_id: int):
        """Soft-delete a document."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        obj = self.get_or_404(DocumentVault, user_id, document_id)
        obj.soft_delete()
        return {"detail": "Document deleted."}

    @route.post("/{int:document_id}/restore", response=MessageOut)
    def restore_document(self, request, document_id: int):
        """Restore a soft-deleted document."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        obj = self.get_with_deleted_or_404(DocumentVault, user_id, document_id)
        obj.restore()
        return {"detail": "Document restored."}

    # ── Activate / Deactivate ─────────────────────────────────────────────

    @route.post("/{int:document_id}/activate", response=MessageOut)
    def activate_document(self, request, document_id: int):
        """Activate a document."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        obj = self.get_or_404(DocumentVault, user_id, document_id)
        obj.activate()
        return {"detail": "Document activated."}

    @route.post("/{int:document_id}/deactivate", response=MessageOut)
    def deactivate_document(self, request, document_id: int):
        """Deactivate a document."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        obj = self.get_or_404(DocumentVault, user_id, document_id)
        obj.deactivate()
        return {"detail": "Document deactivated."}
