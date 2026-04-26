from typing import Optional

from django.contrib.auth.models import BaseUserManager


class CustomUserManager(BaseUserManager):
    """Custom manager for the User model with email-based authentication.

    All user creation goes through this manager. It enforces that
    email is always the primary identifier and handles password hashing.

    Provides both synchronous and asynchronous methods for full compatibility
    with Django 5.2's async ORM.
    """

    use_in_migrations = True

    # =========================================================================
    # Synchronous Methods
    # =========================================================================

    def _create_user(self, email, password=None, **extra_fields):
        """Internal method to create and save a user with the given email and password."""
        if not email:
            raise ValueError("Email address is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user.

        Args:
            email: The user's email address (required).
            password: The user's password. If None, an unusable password is set
                      (used for OAuth-only users).
            **extra_fields: Additional fields (first_name, last_name, etc.)

        Returns:
            The created User instance.
        """
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", False)
        extra_fields.setdefault("is_email_verified", False)

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser.

        Args:
            email: The superuser's email address.
            password: The superuser's password.
            **extra_fields: Additional fields.

        Returns:
            The created superuser instance.

        Raises:
            ValueError: If is_staff or is_superuser is not True.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        """Allow authentication by email as the natural key."""
        return self.get(email=email)

    def email_exists(self, email: str) -> bool:
        """Check if a user with the given email exists."""
        return self.filter(email=email).exists()

    def active(self):
        """Return queryset of active (not soft-deleted, is_active) users."""
        return self.filter(is_deleted=False, is_active=True)

    def get_by_slug(self, slug) -> Optional["User"]:
        """Get a user by their public slug. Returns None if not found."""
        return self.filter(slug=slug, is_deleted=False).first()

    # =========================================================================
    # Asynchronous Methods (Django 5.2+ async ORM)
    # =========================================================================
    # These methods mirror their sync counterparts but use Django's async ORM
    # (aget, acount, afirst, etc.). Use these in async controller/service
    # methods to avoid blocking the event loop.
    #
    # Usage in async contexts:
    #   async def my_async_view(request):
    #       user = await User.objects.acreate_user(email=..., password=...)
    #       exists = await User.objects.aemail_exists(email=...)
    #       user = await User.objects.aget_by_slug(slug)

    async def acreate_user(self, email, password=None, **extra_fields):
        """Async version of create_user()."""
        if not email:
            raise ValueError("Email address is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        await user.asave(using=self._db)
        return user

    async def acreate_superuser(self, email, password=None, **extra_fields):
        """Async version of create_superuser()."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return await self.acreate_user(email, password, **extra_fields)

    async def aget_by_natural_key(self, email):
        """Async version of get_by_natural_key()."""
        return await self.aget(email=email)

    async def aemail_exists(self, email: str) -> bool:
        """Async version of email_exists()."""
        return await self.filter(email=email).aexists()

    async def aget_by_slug(self, slug):
        """Async version of get_by_slug(). Returns None if not found."""
        return await self.filter(slug=slug, is_deleted=False).afirst()

    async def aget_by_id(self, user_id: int):
        """Get a user by primary key (async). Raises User.DoesNotExist."""
        return await self.aget(id=user_id)

    async def aget_by_email(self, email: str):
        """Get a user by email (async). Returns None if not found."""
        try:
            return await self.aget(email=email)
        except self.model.DoesNotExist:
            return None

    async def aget_active_by_id(self, user_id: int):
        """Get an active, non-deleted user by ID (async). Returns None if not found."""
        return await self.filter(id=user_id, is_active=True, is_deleted=False).afirst()

    async def aget_active_by_email(self, email: str):
        """Get an active, non-deleted user by email (async). Returns None if not found."""
        return await self.filter(email=email, is_active=True, is_deleted=False).afirst()

    async def aget_by_oauth(self, provider: str, oauth_uid: str):
        """Get a user by OAuth provider and UID (async). Returns None if not found."""
        return await self.filter(oauth_provider=provider, oauth_uid=oauth_uid).afirst()
