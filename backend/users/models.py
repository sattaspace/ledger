import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from common.models import TimeStampedModel, SoftDeleteModel

# Import custom manager (set on User below)
from .managers import CustomUserManager  # noqa: E402


class User(AbstractUser, TimeStampedModel, SoftDeleteModel):
    """Custom User model with email-based authentication.

    Designed for SaaS use with:
    - Email as primary identifier (USERNAME_FIELD)
    - Profile fields for personalization
    - Email verification tracking
    - Soft delete support (is_deleted)
    - TimestampedModel (created_at, updated_at)
    """

    # --- Remove username, use email ---
    username = models.CharField(
        max_length=150, null=True, blank=True, unique=False
    )  # Not used for auth
    slug = models.UUIDField(
        _("Slug"),
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
        help_text=_("Public unique identifier (UUID4). Used in URLs and references."),
    )
    email = models.EmailField(
        _("Email Address"),
        unique=True,
        db_index=True,
        max_length=255,
        error_messages={
            "unique": _("A user with this email address already exists."),
        },
    )

    # --- Profile ---
    first_name = models.CharField(_("First Name"), max_length=150, blank=True)
    last_name = models.CharField(_("Last Name"), max_length=150, blank=True)
    phone = models.CharField(_("Phone Number"), max_length=30, blank=True, default="")
    avatar = models.ImageField(
        _("Avatar"),
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
    )

    # --- Preferences ---
    timezone = models.CharField(_("Timezone"), max_length=50, default="UTC")
    currency = models.CharField(_("Preferred Currency"), max_length=3, default="USD")
    language = models.CharField(_("Language"), max_length=10, default="en")

    # --- Auth Status ---
    is_email_verified = models.BooleanField(
        _("Email Verified"), default=False, db_index=True
    )
    last_login_ip = models.GenericIPAddressField(
        _("Last Login IP"), null=True, blank=True
    )

    # --- SaaS / Tenant fields (foundation for future) ---
    role = models.CharField(
        _("Role"),
        max_length=20,
        default="member",
        db_index=True,
        help_text=_("User role: owner, admin, member"),
    )

    # --- Django config ---
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]

    objects = CustomUserManager()

    class Meta:
        db_table = "users_user"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]

        constraints = []

    def __str__(self) -> str:
        return str(self.slug)

    @property
    def full_name(self) -> str:
        """Return the user's full name, or email if empty."""
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email

    @property
    def display_name(self) -> str:
        """Return the user's display name (first name or email prefix)."""
        return self.first_name.strip() or self.email.split("@")[0]


# =============================================================================
# Token Models
# =============================================================================


class PasswordResetToken(models.Model):
    """Token for password reset flow.

    When a user requests a password reset, a unique token is generated and stored.
    The token is single-use and expires after PASSWORD_RESET_TOKEN_EXPIRY_SECONDS.
    """

    id = models.BigAutoField(primary_key=True)
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Unique reset token (UUID4). Sent to user's email.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users_password_reset_token"
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ResetToken({self.token}, user={self.user.email})"

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        from django.utils import timezone

        expiry_seconds = getattr(settings, "PASSWORD_RESET_TOKEN_EXPIRY_SECONDS", 900)
        return (timezone.now() - self.created_at).total_seconds() > expiry_seconds

    @property
    def is_used(self) -> bool:
        """Check if the token has already been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid (not expired and not used)."""
        return not self.is_expired and not self.is_used

    def mark_used(self) -> None:
        """Mark the token as used."""
        from django.utils import timezone

        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])


class EmailChangeToken(models.Model):
    """Token for email change confirmation.

    When a user requests an email change (with current password verification),
    a token is generated and sent to their CURRENT email. The user must
    confirm by clicking the link or entering the token within the expiry window.

    This prevents an attacker with a stolen session from silently changing
    the email (and thus taking over the account via password reset).
    """

    id = models.BigAutoField(primary_key=True)
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Unique email change token (UUID4). Sent to current email.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_change_tokens",
        db_index=True,
    )
    new_email = models.EmailField(
        _("New Email"),
        max_length=255,
        help_text="The pending new email address.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "users_email_change_token"
        verbose_name = "Email Change Token"
        verbose_name_plural = "Email Change Tokens"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"EmailChangeToken({self.token}, user={self.user.email} -> {self.new_email})"

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        from django.utils import timezone

        expiry_seconds = getattr(settings, "EMAIL_CHANGE_TOKEN_EXPIRY_SECONDS", 3600)
        return (timezone.now() - self.created_at).total_seconds() > expiry_seconds

    @property
    def is_used(self) -> bool:
        """Check if the token has already been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if the token is still valid (not expired and not used)."""
        return not self.is_expired and not self.is_used

    def mark_used(self) -> None:
        """Mark the token as used."""
        from django.utils import timezone

        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])
