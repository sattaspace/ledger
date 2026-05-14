"""Document Vault model — Secure document storage linked to financial items."""

from django.db import models

from common.models import UserOwnedModel


class DocumentVault(UserOwnedModel):
    """Secure document storage linked to financial items.

    Uses Django's ContentType framework for generic relations — a document
    can be attached to any model (Account, InsurancePolicy, Transaction, etc.).
    """

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="vault/%Y/%m/")
    file_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Auto-detected: PDF, PNG, JPG, etc.",
    )
    file_size = models.PositiveIntegerField(
        default=0, help_text="File size in bytes"
    )

    # ── Expiry tracking ───────────────────────────────────────────────
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="For documents that expire: IDs, insurance policies, certificates.",
    )
    remind_before_expiry = models.BooleanField(default=False)
    days_before_expiry_reminder = models.IntegerField(default=30)

    # ── Generic relation ──────────────────────────────────────────────
    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        on_delete=models.CASCADE,
    )
    object_id = models.PositiveIntegerField()

    class Meta:
        db_table = "vault_document"

    def __str__(self) -> str:
        return f"{self.title} ({self.file_type or 'file'})"

    def save(self, *args, **kwargs):
        """Auto-detect file type and size."""
        if self.file:
            self.file_size = self.file.size
            name = self.file.name.lower()
            if name.endswith(".pdf"):
                self.file_type = "PDF"
            elif name.endswith((".png", ".jpg", ".jpeg")):
                self.file_type = "IMAGE"
            elif name.endswith((".xlsx", ".xls")):
                self.file_type = "EXCEL"
            elif name.endswith(".csv"):
                self.file_type = "CSV"
            elif name.endswith(".docx"):
                self.file_type = "WORD"
            else:
                self.file_type = "OTHER"
        super().save(*args, **kwargs)
