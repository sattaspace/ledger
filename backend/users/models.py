import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from common.models import TimeStampedModel, SoftDeleteModel

# Import custom manager (set on User below)
from .managers import CustomUserManager  # noqa: E402


class User(AbstractUser, TimeStampedModel, SoftDeleteModel):
    """Custom User model with email-based authentication.

    Designed for SaaS use with:
    - Email as primary identifier (USERNAME_FIELD)
    - Profile fields for personalization
    - OAuth provider support (Google, GitHub)
    - Email verification tracking
    - Soft delete support (is_deleted)
    - TimestampedModel (created_at, updated_at)
    """

    # --- Remove username, use email ---
    username = None
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

    # --- OAuth ---
    oauth_provider = models.CharField(
        _("OAuth Provider"),
        max_length=50,
        blank=True,
        default="",
        help_text=_("e.g. google, github"),
    )
    oauth_uid = models.CharField(
        _("OAuth Provider UID"),
        max_length=255,
        blank=True,
        default="",
        db_index=True,
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

        # Unique constraint for OAuth providers
        constraints = [
            models.UniqueConstraint(
                fields=["oauth_provider", "oauth_uid"],
                condition=models.Q(oauth_provider__gt=""),
                name="unique_oauth_provider_uid",
            ),
        ]

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


class OTP(TimeStampedModel):
    """One-Time Password model for email-based verification.

    Supports multiple purposes:
    - registration: Verify email during signup
    - login: OTP-based passwordless login
    - password_reset: Verify identity before password change
    - email_verification: Verify a new email address
    """

    PURPOSE_CHOICES = [
        ("registration", _("Registration")),
        ("login", _("Login")),
        ("password_reset", _("Password Reset")),
        ("email_verification", _("Email Verification")),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="otps",
        verbose_name=_("User"),
    )
    code = models.CharField(_("OTP Code"), max_length=6)
    purpose = models.CharField(
        _("Purpose"),
        max_length=30,
        choices=PURPOSE_CHOICES,
        db_index=True,
    )
    expires_at = models.DateTimeField(_("Expires At"), db_index=True)
    is_used = models.BooleanField(_("Is Used"), default=False)
    attempts = models.PositiveSmallIntegerField(_("Attempts"), default=0)
    ip_address = models.GenericIPAddressField(_("IP Address"), null=True, blank=True)

    class Meta:
        db_table = "users_otp"
        verbose_name = _("OTP")
        verbose_name_plural = _("OTPs")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.email} | {self.get_purpose_display()} | {self.code}"

    def is_valid(self) -> bool:
        """Check if the OTP is still valid (not used, not expired, under attempt limit)."""
        from django.utils import timezone

        return (
            not self.is_used and self.attempts < 3 and self.expires_at > timezone.now()
        )

    def mark_used(self):
        """Mark the OTP as used."""
        self.is_used = True
        self.save(update_fields=["is_used"])

    def increment_attempts(self):
        """Increment the attempt counter and save."""
        self.attempts += 1
        if self.attempts >= 3:
            self.is_used = True
            self.save(update_fields=["attempts", "is_used"])
        else:
            self.save(update_fields=["attempts"])
