"""Document Vault controller — CRUD for secure document storage with file upload."""

import logging

from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from ninja import Query, UploadedFile, File
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

# ── Per-endpoint file size limits ──────────────────────────────────────
# 10 MB max for vault uploads. Django's DATA_UPLOAD_MAX_MEMORY_SIZE (2.5 MB)
# controls in-memory threshold, but FILE_UPLOAD_MAX_MEMORY_SIZE only controls
# when Django switches to temp-file storage, NOT the max upload size.
MAX_VAULT_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


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

    # ── Create (metadata only) ────────────────────────────────────────────

    @route.post("", response=DocumentVaultOut)
    def create_document(self, request, payload: DocumentVaultCreate):
        """Create a new document record in the vault.

        Note: File upload is handled via the separate /vault/upload endpoint.
        This endpoint creates the metadata record. Use /vault/{id}/upload
        to attach the actual file after creation.
        """
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_vault_documents", DocumentVault.objects.filter(user_id=user_id).count())
        # Validate content_type + object_id ownership (S1 fix)
        data = payload.model_dump()
        content_type_id = data.get("content_type_id")
        object_id = data.get("object_id")
        self._validate_content_object_ownership(user_id, content_type_id, object_id)
        data["content_type_id"] = data.pop("content_type_id")
        obj = DocumentVault.objects.create(user_id=user_id, **data)
        logger.info("Document created: id=%s user_id=%s title=%s", obj.id, user_id, obj.title)
        return obj

    # ── File Upload ──────────────────────────────────────────────────────

    @route.post("/{int:document_id}/upload", response=DocumentVaultOut)
    def upload_file(self, request, document_id: int, file: UploadedFile = File(...)):
        """Upload a file for an existing document record.

        Size limit: 10 MB per file.
        Allowed types: PDF, PNG, JPG, Excel, CSV, Word.
        """
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        obj = self.get_or_404(DocumentVault, user_id, document_id)

        # ── Validate file size ───────────────────────────────────────────
        if file.size > MAX_VAULT_FILE_SIZE_BYTES:
            from ninja.errors import ValidationError as NinjaValidationError
            raise NinjaValidationError(
                f"File too large: {file.size} bytes. "
                f"Maximum allowed: {MAX_VAULT_FILE_SIZE_BYTES} bytes (10 MB)."
            )

        # ── Validate content type ────────────────────────────────────────
        content_type = getattr(file, "content_type", "") or ""
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            from ninja.errors import ValidationError as NinjaValidationError
            raise NinjaValidationError(
                f"File type '{content_type}' not allowed. "
                f"Allowed types: PDF, PNG, JPG, Excel, CSV, Word."
            )

        # Save the file
        obj.file = file
        obj.save()  # Auto-detects file_type and file_size via save() override

        logger.info(
            "File uploaded for document: id=%s user_id=%s file_size=%s file_type=%s",
            obj.id, user_id, obj.file_size, obj.file_type,
        )
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:document_id}", response=DocumentVaultOut)
    def update_document(self, request, document_id: int, payload: DocumentVaultUpdate):
        """Update document metadata. The file itself cannot be updated — delete and re-upload."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "vault")
        obj = self.get_or_404(DocumentVault, user_id, document_id)

        # If content_type or object_id is being updated, validate ownership
        data = payload.model_dump(exclude_unset=True)
        if "content_type_id" in data or "object_id" in data:
            ct_id = data.get("content_type_id", obj.content_type_id)
            obj_id = data.get("object_id", obj.object_id)
            self._validate_content_object_ownership(user_id, ct_id, obj_id)

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
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_vault_documents",
                            DocumentVault.objects.filter(user_id=user_id).count())
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

    # ── Helpers ────────────────────────────────────────────────────────────

    def _validate_content_object_ownership(self, user_id: int, content_type_id: int, object_id: int):
        """Validate that a ContentType + object_id points to an existing object
        owned by the current user. Raises Http404 if invalid.

        This prevents users from attaching documents to objects they don't own,
        or from using content_types that aren't allowed (e.g., auth.User).
        """
        if not content_type_id or not object_id:
            raise Http404  # Both are required

        try:
            ct = ContentType.objects.get_for_id(content_type_id)
        except ContentType.DoesNotExist:
            raise Http404  # Invalid content type

        model_class = ct.model_class()
        if model_class is None:
            raise Http404  # Content type doesn't resolve to a model

        # Only allow models that have user_id (sister domain models)
        if not hasattr(model_class, "user_id"):
            raise Http404  # Cannot attach documents to non-user-owned models

        try:
            obj = model_class.objects.get(id=object_id)
        except model_class.DoesNotExist:
            raise Http404  # Object doesn't exist

        if obj.user_id != user_id:
            raise Http404  # Object doesn't belong to this user
