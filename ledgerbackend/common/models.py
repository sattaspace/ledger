from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model that provides created_at and updated_at timestamps."""

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        db_index=True,
        verbose_name="Created At",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
        db_index=True,
        verbose_name="Updated At",
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Abstract base model that provides soft delete functionality.

    Instead of permanently deleting records, marks them as deleted
    with a timestamp. Use `soft_delete()` and `restore()` methods.
    """

    is_deleted = models.BooleanField(
        default=False, db_index=True, verbose_name="Is Deleted"
    )
    deleted_at = models.DateTimeField(
        null=True, blank=True, editable=False, verbose_name="Deleted At"
    )

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class ActivatorModel(models.Model):
    """Abstract base model that provides is_active status tracking."""

    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name="Is Active"
    )
    activated_at = models.DateTimeField(
        null=True, blank=True, editable=False, verbose_name="Activated At"
    )

    class Meta:
        abstract = True

    def activate(self):
        from django.utils import timezone

        self.is_active = True
        self.activated_at = timezone.now()
        self.save(update_fields=["is_active", "activated_at"])

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=["is_active"])


# ---------------------------------------------------------------------------
# Active Manager — filters out soft-deleted records by default
# ---------------------------------------------------------------------------


class ActiveManager(models.Manager):
    """Default manager that excludes soft-deleted records.

    Use ``Model.objects`` for normal queries (excludes deleted).
    Use ``Model.all_objects`` when you need deleted records (admin, audit).
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


# ---------------------------------------------------------------------------
# UserOwnedModel — abstract base for all Ledger entities
# ---------------------------------------------------------------------------


class UserOwnedModel(TimeStampedModel, SoftDeleteModel, ActivatorModel):
    """Abstract base for all user-owned entities in Ledger.

    Inheritance chain:
        UserOwnedModel
          ├─ TimeStampedModel   → created_at, updated_at
          ├─ SoftDeleteModel    → is_deleted, deleted_at, soft_delete(), restore()
          └─ ActivatorModel     → is_active, activated_at, activate(), deactivate()

    Plus:
        user_id    → Integer reference to Sattabase User.id (NOT a Django FK)
        objects    → ActiveManager (excludes soft-deleted)
        all_objects → raw Manager (includes soft-deleted, for admin/audit)

    Why user_id as int, not FK?
        The User model lives in the Sattabase base backend. Ledger has no local
        User table. The Sattabase SDK middleware populates request.sattabase_user
        with the user's profile. All sister-domain data ties to Sattabase User.id
        via a plain integer — the same pattern used by the existing TestNote model.
    """

    user_id = models.PositiveIntegerField(
        db_index=True,
        help_text="Sattabase User.id — the central identity reference",
    )

    # Default manager excludes soft-deleted; all_objects includes everything.
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
