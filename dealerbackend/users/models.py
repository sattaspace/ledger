"""
DEALERCORE v3.0 — Custom User Model
------------------------------------
DSR User model for DealerBackend authentication.

This model is SEPARATE from SattaBase's user system:
- SattaBase Users = Dealers (subscribers)
- DealerBackend Users = DSRs, Collectors, Managers (independent profiles)

Design Philosophy:
- DSRs are INDEPENDENT entities who own their profile
- DSRs can work for multiple dealers (many-to-many)
- Each dealer sets different permissions per DSR
- DSR can accept/reject invitations
- System ready for future freelance marketplace

User Types:
- DSR: Daily Sales Representative
- COLLECTOR: Order Collector (reports to DSR)
- MANAGER: Can manage junior DSRs
- ADMIN: Dealer admin with elevated permissions
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from .managers import DsrUserManager


class DsrUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for DealerBackend - Independent DSR Profiles.
    
    DSRs register independently and can serve multiple dealers.
    
    Authentication:
    - Email is the primary identifier (USERNAME_FIELD)
    - Phone is optional, for contact purposes
    
    Future-Ready:
    - Reserved fields for freelance marketplace
    - Skills, experience, rating, portfolio
    """
    
    # User type choices
    TYPE_DSR = "DSR"
    TYPE_COLLECTOR = "Collector"
    TYPE_MANAGER = "Manager"
    TYPE_ADMIN = "ADMIN"
    USER_TYPE_CHOICES = [
        (TYPE_DSR, "DSR"),
        (TYPE_COLLECTOR, "Order Collector"),
        (TYPE_MANAGER, "Manager"),
        (TYPE_ADMIN, "Admin"),
    ]
    
    # Primary fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Authentication identifiers
    # Email is PRIMARY (required, unique) - used for login
    email = models.EmailField(
        _("email address"),
        unique=True,
        db_index=True,
        help_text=_("Primary identifier for login (required)"),
    )
    
    # Phone is optional (for contact purposes)
    phone = models.CharField(
        _("phone number"),
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        help_text=_("Phone number for contact (optional)"),
    )
    
    # User type
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default=TYPE_DSR,
        db_index=True,
        help_text=_("Type of user: DSR, Collector, Manager, or Admin"),
    )
    
    # Profile fields
    full_name = models.CharField(
        _("full name"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Full display name"),
    )
    avatar_url = models.URLField(
        _("avatar URL"),
        max_length=500,
        blank=True,
        default="",
    )
    bio = models.TextField(
        _("biography"),
        blank=True,
        default="",
        help_text=_("Short bio for public profile"),
    )
    
    # Deprecated fields (kept for backward compatibility)
    first_name = models.CharField(_("first name"), max_length=100, blank=True, default="")
    last_name = models.CharField(_("last name"), max_length=100, blank=True, default="")
    
    # Status fields
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active."),
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    
    # Verification
    phone_verified = models.BooleanField(
        default=False,
        help_text=_("Phone number verified via OTP"),
    )
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(_("last login"), blank=True, null=True)

    # FIX H-7: tracks when the password was last changed. JWTs issued by
    # the dealer backend embed this value as a `pwd_changed_at` claim;
    # on every protected request we compare it to the current value in
    # the DB and reject the token if it predates the last change. This
    # means a token issued before a password change is automatically
    # invalid once the user updates their password.
    password_changed_at = models.DateTimeField(null=True, blank=True)

    # Password reset
    password_reset_token = models.CharField(max_length=64, blank=True, default="")
    password_reset_expires = models.DateTimeField(null=True, blank=True)
    
    # JWT refresh token (for token blacklisting)
    refresh_token = models.TextField(blank=True, default="")
    
    # Selected dealer context (for multi-dealer DSRs)
    selected_dealer = models.ForeignKey(
        "dealer.DealerConfig",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_dsr_sessions",
        help_text=_("Currently selected dealer context for this DSR"),
    )
    
    # ═══════════════════════════════════════════════════════════════════
    # FUTURE FREELANCE MARKETPLACE FIELDS (Reserved for enhancement)
    # ═══════════════════════════════════════════════════════════════════
    
    # Profile visibility
    is_public = models.BooleanField(
        default=False,
        help_text=_("Profile visible in freelance marketplace"),
    )
    availability_status = models.CharField(
        max_length=20,
        choices=[
            ("available", "Available for work"),
            ("busy", "Currently busy"),
            ("unavailable", "Not available"),
        ],
        default="available",
        help_text=_("Availability status for freelance marketplace"),
    )
    
    # Skills and experience
    skills = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of skills: ['sales', 'inventory', 'collections']"),
    )
    experience_years = models.PositiveIntegerField(
        default=0,
        help_text=_("Years of experience"),
    )
    
    # Rating and reputation
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        help_text=_("Average rating from dealers (0.00-5.00)"),
    )
    total_jobs = models.PositiveIntegerField(
        default=0,
        help_text=_("Total completed jobs/assignments"),
    )
    total_reviews = models.PositiveIntegerField(
        default=0,
        help_text=_("Total reviews received"),
    )
    
    # Rate (for freelance pricing)
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Hourly rate for freelance work"),
    )
    daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Daily rate for freelance work"),
    )
    
    # Portfolio
    portfolio_url = models.URLField(
        blank=True,
        default="",
        help_text=_("External portfolio or LinkedIn URL"),
    )
    certifications = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of certifications"),
    )
    
    objects = DsrUserManager()
    
    # Email is the primary identifier
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    
    class Meta:
        db_table = "users_dsr_user"
        verbose_name = _("DSR User")
        verbose_name_plural = _("DSR Users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["email"]),
            models.Index(fields=["user_type", "is_active"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_public", "availability_status"]),
        ]
    
    def __str__(self):
        return f"{self.full_name or self.phone} ({self.user_type})"
    
    @property
    def display_name(self) -> str:
        """Return the display name (full_name or phone)."""
        return self.full_name or self.phone
    
    @property
    def is_dsr(self) -> bool:
        """Check if user is a DSR."""
        return self.user_type == self.TYPE_DSR
    
    @property
    def is_collector(self) -> bool:
        """Check if user is a Collector."""
        return self.user_type == self.TYPE_COLLECTOR
    
    @property
    def is_manager(self) -> bool:
        """Check if user is a Manager."""
        return self.user_type == self.TYPE_MANAGER
    
    @property
    def is_admin_user(self) -> bool:
        """Check if user is an Admin."""
        return self.user_type == self.TYPE_ADMIN
    
    def verify_phone(self):
        """Mark phone as verified."""
        self.phone_verified = True
        self.phone_verified_at = timezone.now()
        self.save(update_fields=["phone_verified", "phone_verified_at"])
    
    def verify_email(self):
        """Mark email as verified."""
        self.email_verified = True
        self.email_verified_at = timezone.now()
        self.save(update_fields=["email_verified", "email_verified_at"])
    
    @staticmethod
    def _hash_reset_token(token: str) -> str:
        """FIX M-4: store a SHA-256 hash of the token instead of the raw value.
        A DB dump can no longer be used to take over accounts with outstanding
        reset requests. Hashing is sufficient because the token already has
        256 bits of entropy (secrets.token_urlsafe(32)) — no need for bcrypt.
        """
        import hashlib
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    # FIX H-7: override Django's set_password so every password change
    # (including via set_password() called by the admin or by an external
    # flow) bumps `password_changed_at`. The token claim check in
    # `decode_token()` then automatically invalidates any token that was
    # issued before the new value.
    def set_password(self, raw_password: str) -> None:
        super().set_password(raw_password)
        self.password_changed_at = timezone.now()

    async def aset_password(self, raw_password: str) -> None:
        """FIX H-7: async variant used by async views so callers don't have
        to wrap in sync_to_async."""
        from asgiref.sync import sync_to_async
        await sync_to_async(self.set_password)(raw_password)

    def set_password_reset_token(self, token: str, expires_hours: int = 24):
        """Set password reset token with expiration (sync)."""
        from datetime import timedelta
        self.password_reset_token = self._hash_reset_token(token)
        self.password_reset_expires = timezone.now() + timedelta(hours=expires_hours)
        self.save(update_fields=["password_reset_token", "password_reset_expires"])

    async def aset_password_reset_token(self, token: str, expires_hours: int = 24):
        """FIX H-9: async variant for async views."""
        from datetime import timedelta
        self.password_reset_token = self._hash_reset_token(token)
        self.password_reset_expires = timezone.now() + timedelta(hours=expires_hours)
        await self.asave(update_fields=["password_reset_token", "password_reset_expires"])

    def clear_password_reset_token(self):
        """Clear password reset token (sync)."""
        self.password_reset_token = ""
        self.password_reset_expires = None
        self.save(update_fields=["password_reset_token", "password_reset_expires"])

    async def aclear_password_reset_token(self):
        """FIX H-9: async variant for async views."""
        self.password_reset_token = ""
        self.password_reset_expires = None
        await self.asave(update_fields=["password_reset_token", "password_reset_expires"])

    def is_password_reset_valid(self, token: str) -> bool:
        """Check if password reset token is valid (constant-time compare)."""
        if not self.password_reset_token or not self.password_reset_expires:
            return False
        # FIX M-4: compare hashed token.
        import hmac
        expected = self._hash_reset_token(token)
        if not hmac.compare_digest(expected, self.password_reset_token):
            return False
        return timezone.now() < self.password_reset_expires
    
    async def get_assigned_dealers(self):
        """
        Get all dealers this DSR is assigned to.
        Returns list of DealerConfig objects.
        """
        from dsr.invitation_models import DsrDealerAssignment
        
        assignments = DsrDealerAssignment.objects.filter(
            dsr__user=self,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).select_related("dealer")
        
        return [assignment.dealer async for assignment in assignments]
    
    async def get_dealer_choices(self):
        """
        Get list of dealers for selection UI.
        Returns list of dicts with dealer info.
        """
        dealers = await self.get_assigned_dealers()
        return [
            {
                "username": dealer.username,
                "full_name": dealer.full_name,
                "business_name": dealer.business_name,
            }
            for dealer in dealers
        ]
    
    async def get_pending_invitations(self):
        """
        Get pending invitations for this DSR.
        """
        from dsr.invitation_models import DsrInvitation
        from dsr.models import DSR
        
        try:
            dsr = await DSR.objects.aget(user=self)
            invitations = DsrInvitation.objects.filter(
                dsr=dsr,
                status=DsrInvitation.STATUS_PENDING,
            ).select_related("dealer")
            return [inv async for inv in invitations]
        except DSR.DoesNotExist:
            return []
    
    def update_rating(self, new_rating: float):
        """
        Update average rating with new review.
        Uses weighted average calculation.
        """
        if self.total_reviews == 0:
            self.rating = new_rating
        else:
            # Weighted average
            total_points = float(self.rating) * self.total_reviews
            self.rating = (total_points + new_rating) / (self.total_reviews + 1)
            # Round to 2 decimal places
            self.rating = round(self.rating, 2)
        
        self.total_reviews += 1
        self.save(update_fields=["rating", "total_reviews"])
