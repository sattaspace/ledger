"""Business logic services for the users app.

Services encapsulate all business logic, keeping controllers thin and
testable. Controllers should only handle HTTP concerns (request parsing,
response formatting) and delegate to services.

Each service class provides both synchronous and asynchronous methods.
Use async methods in async controller endpoints to avoid blocking the
event loop.
"""

import logging
from typing import Optional

from asgiref.sync import sync_to_async
from django.contrib.auth import authenticate, get_user_model, hashers
from django.utils import timezone
from django.core.mail import send_mail

from .models import User, PasswordResetToken, EmailChangeToken

logger = logging.getLogger(__name__)
UserModel = get_user_model()


# =============================================================================
# Auth Service
# =============================================================================


class AuthService:
    """Handles user authentication operations (registration, login, password management)."""

    @staticmethod
    def register_user(
        email: str, password: str, first_name: str, last_name: str = ""
    ) -> User:
        """Register a new user account."""
        if UserModel.objects.email_exists(email):
            raise ValueError("A user with this email address already exists.")

        user = UserModel.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_email_verified=False,
        )
        logger.info(f"User registered: {user.email}")
        return user

    @staticmethod
    async def aregister_user(
        email: str, password: str, first_name: str, last_name: str = ""
    ) -> User:
        """Async version of register_user()."""
        if await UserModel.objects.aemail_exists(email):
            raise ValueError("A user with this email address already exists.")

        user = await UserModel.objects.acreate_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_email_verified=False,
        )
        logger.info(f"User registered (async): {user.email}")
        return user

    @staticmethod
    def authenticate_user(email: str, password: str) -> User:
        """Authenticate a user with email and password."""
        user = authenticate(request=None, username=email, password=password)

        if not user:
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError("Your account is not active. Please contact support.")

        if user.is_deleted:
            raise ValueError("This account has been deactivated.")

        return user

    @staticmethod
    async def aauthenticate_user(email: str, password: str) -> User:
        """Async version of authenticate_user()."""
        user = await UserModel.objects.aget_by_email(email)

        if not user:
            raise ValueError("Invalid email or password.")

        if not hashers.check_password(password, user.password):
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError("Your account is not active. Please contact support.")

        if user.is_deleted:
            raise ValueError("This account has been deactivated.")

        return user

    # =========================================================================
    # Password Change
    # =========================================================================

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> None:
        """Change a user's password. Requires current password."""
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

        user.set_password(new_password)
        user.save(update_fields=["password"])
        logger.info(f"Password changed: user={user.email}")

    @staticmethod
    async def achange_password(
        user: User, current_password: str, new_password: str
    ) -> None:
        """Async version of change_password()."""
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

        user.set_password(new_password)
        await user.asave(update_fields=["password"])
        logger.info(f"Password changed (async): user={user.email}")

    # =========================================================================
    # Password Reset (Token-Based)
    # =========================================================================

    @staticmethod
    def request_password_reset(email: str) -> str:
        """Request a password reset. Generates UUID4 token, invalidates old ones."""
        try:
            user = UserModel.objects.get(email=email, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            raise ValueError(
                "If an account with this email exists, a reset link has been sent."
            )

        PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(
            used_at=timezone.now()
        )
        reset_token = PasswordResetToken.objects.create(user=user)

        try:
            from django.conf import settings

            send_mail(
                subject="Password Reset - Satta Ledger",
                message=(
                    f"You requested a password reset.\n\n"
                    f"Your reset token: {reset_token.token}\n\n"
                    f"This token expires in 15 minutes.\n"
                    f"If you didn't request this, ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")

        logger.info(f"Password reset requested: user={user.email}")
        return str(reset_token.token)

    @staticmethod
    async def arequest_password_reset(email: str) -> str:
        """Async version of request_password_reset()."""
        try:
            user = await UserModel.objects.aget(
                email=email, is_active=True, is_deleted=False
            )
        except User.DoesNotExist:
            logger.warning(f"Password reset requested for non-existent email: {email}")
            raise ValueError(
                "If an account with this email exists, a reset link has been sent."
            )

        await PasswordResetToken.objects.filter(
            user=user, used_at__isnull=True
        ).aupdate(used_at=timezone.now())

        reset_token = await PasswordResetToken.objects.acreate(user=user)

        try:
            from django.conf import settings

            await sync_to_async(send_mail)(
                subject="Password Reset - Satta Ledger",
                message=(
                    f"You requested a password reset.\n\n"
                    f"Your reset token: {reset_token.token}\n\n"
                    f"This token expires in 15 minutes.\n"
                    f"If you didn't request this, ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")

        logger.info(f"Password reset requested (async): user={user.email}")
        return str(reset_token.token)

    @staticmethod
    def confirm_password_reset(token: str, new_password: str) -> None:
        """Confirm a password reset using the token."""
        try:
            reset_token = PasswordResetToken.objects.select_related("user").get(
                token=token
            )
        except PasswordResetToken.DoesNotExist:
            raise ValueError("Invalid or expired reset token.")

        if not reset_token.is_valid:
            if reset_token.is_used:
                raise ValueError("This reset token has already been used.")
            else:
                raise ValueError("This reset token has expired.")

        user = reset_token.user
        if not user.is_active or user.is_deleted:
            raise ValueError("This account is no longer active.")

        user.set_password(new_password)
        user.save(update_fields=["password"])
        reset_token.mark_used()
        logger.info(f"Password reset confirmed: user={user.email}")

    @staticmethod
    async def aconfirm_password_reset(token: str, new_password: str) -> None:
        """Async version of confirm_password_reset()."""
        try:
            reset_token = await PasswordResetToken.objects.select_related("user").aget(
                token=token
            )
        except PasswordResetToken.DoesNotExist:
            raise ValueError("Invalid or expired reset token.")

        if not reset_token.is_valid:
            if reset_token.is_used:
                raise ValueError("This reset token has already been used.")
            else:
                raise ValueError("This reset token has expired.")

        user = reset_token.user
        if not user.is_active or user.is_deleted:
            raise ValueError("This account is no longer active.")

        user.set_password(new_password)
        await user.asave(update_fields=["password"])
        await sync_to_async(reset_token.mark_used)()
        logger.info(f"Password reset confirmed (async): user={user.email}")

    # =========================================================================
    # Sensitive Actions — Identity Confirmation
    # =========================================================================

    @staticmethod
    def confirm_identity(user: User, current_password: str) -> None:
        """Verify the user's identity by checking their current password.

        This is a reusable gate for sensitive operations (email change,
        account deletion, etc.). Returns None on success, raises ValueError
        on failure.
        """
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

    @staticmethod
    async def aconfirm_identity(user: User, current_password: str) -> None:
        """Async version of confirm_identity()."""
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

    # =========================================================================
    # Email Change (Password + Email Confirmation)
    # =========================================================================

    @staticmethod
    def request_email_change(user: User, current_password: str, new_email: str) -> str:
        """Request an email change after verifying current password.

        Steps:
        1. Verify current password
        2. Check new email isn't already taken
        3. Invalidate any previous pending email change tokens
        4. Create new token and send confirmation to CURRENT email

        Args:
            user: The authenticated user.
            current_password: User's current password (identity confirmation).
            new_email: The desired new email address.

        Returns:
            The confirmation token string.

        Raises:
            ValueError: If password is wrong, email is same, or already taken.
        """
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

        if user.email == new_email.lower().strip():
            raise ValueError("New email must be different from current email.")

        if UserModel.objects.email_exists(new_email):
            raise ValueError("An account with this email address already exists.")

        # Invalidate any previous pending tokens
        EmailChangeToken.objects.filter(user=user, used_at__isnull=True).update(
            used_at=timezone.now()
        )

        # Create new token
        change_token = EmailChangeToken.objects.create(
            user=user, new_email=new_email.lower().strip()
        )

        # Send confirmation to CURRENT email (not the new one)
        try:
            from django.conf import settings

            send_mail(
                subject="Confirm Email Change - Satta Ledger",
                message=(
                    f"You requested to change your email to: {change_token.new_email}\n\n"
                    f"If this was you, use this token to confirm:\n"
                    f"{change_token.token}\n\n"
                    f"This token expires in 1 hour.\n"
                    f"If you didn't request this, ignore this email — your email will NOT be changed."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send email change confirmation: {e}")

        logger.info(
            f"Email change requested: user={user.email} -> {change_token.new_email}"
        )
        return str(change_token.token)

    @staticmethod
    async def arequest_email_change(
        user: User, current_password: str, new_email: str
    ) -> str:
        """Async version of request_email_change()."""
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

        new_email = new_email.lower().strip()

        if user.email == new_email:
            raise ValueError("New email must be different from current email.")

        if await UserModel.objects.aemail_exists(new_email):
            raise ValueError("An account with this email address already exists.")

        # Invalidate any previous pending tokens
        await EmailChangeToken.objects.filter(user=user, used_at__isnull=True).aupdate(
            used_at=timezone.now()
        )

        # Create new token
        change_token = await EmailChangeToken.objects.acreate(
            user=user, new_email=new_email
        )

        # Send confirmation to CURRENT email
        try:
            from django.conf import settings

            await sync_to_async(send_mail)(
                subject="Confirm Email Change - Satta Ledger",
                message=(
                    f"You requested to change your email to: {change_token.new_email}\n\n"
                    f"If this was you, use this token to confirm:\n"
                    f"{change_token.token}\n\n"
                    f"This token expires in 1 hour.\n"
                    f"If you didn't request this, ignore this email — your email will NOT be changed."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send email change confirmation: {e}")

        logger.info(
            f"Email change requested (async): user={user.email} -> {change_token.new_email}"
        )
        return str(change_token.token)

    @staticmethod
    def confirm_email_change(token: str) -> str:
        """Confirm an email change using the token.

        Args:
            token: The UUID4 confirmation token.

        Returns:
            The new email address.

        Raises:
            ValueError: If token is invalid, expired, or email already taken.
        """
        try:
            change_token = EmailChangeToken.objects.select_related("user").get(
                token=token
            )
        except EmailChangeToken.DoesNotExist:
            raise ValueError("Invalid or expired email change token.")

        if not change_token.is_valid:
            if change_token.is_used:
                raise ValueError("This email change token has already been used.")
            else:
                raise ValueError("This email change token has expired.")

        user = change_token.user
        new_email = change_token.new_email

        # Double-check the new email isn't taken (could have been registered since request)
        if UserModel.objects.email_exists(new_email):
            raise ValueError(
                "An account with this email address already exists. "
                "Please request a new email change."
            )

        # Verify user account is still active
        if not user.is_active or user.is_deleted:
            raise ValueError("This account is no longer active.")

        # Apply the change
        old_email = user.email
        user.email = new_email
        user.is_email_verified = True  # They confirmed via token = verified
        user.save(update_fields=["email", "is_email_verified"])
        change_token.mark_used()

        logger.info(f"Email changed: user={old_email} -> {new_email}")
        return new_email

    @staticmethod
    async def aconfirm_email_change(token: str) -> str:
        """Async version of confirm_email_change()."""
        try:
            change_token = await EmailChangeToken.objects.select_related("user").aget(
                token=token
            )
        except EmailChangeToken.DoesNotExist:
            raise ValueError("Invalid or expired email change token.")

        if not change_token.is_valid:
            if change_token.is_used:
                raise ValueError("This email change token has already been used.")
            else:
                raise ValueError("This email change token has expired.")

        user = change_token.user
        new_email = change_token.new_email

        if await UserModel.objects.aemail_exists(new_email):
            raise ValueError(
                "An account with this email address already exists. "
                "Please request a new email change."
            )

        if not user.is_active or user.is_deleted:
            raise ValueError("This account is no longer active.")

        old_email = user.email
        user.email = new_email
        user.is_email_verified = True
        await user.asave(update_fields=["email", "is_email_verified"])
        await sync_to_async(change_token.mark_used)()

        logger.info(f"Email changed (async): user={old_email} -> {new_email}")
        return new_email

    # =========================================================================
    # Email Verification (OTP-Based)
    # =========================================================================

    # Cache settings for OTP storage
    OTP_CACHE_PREFIX = "email_verify_otp"
    OTP_CACHE_ATTEMPTS_PREFIX = "email_verify_attempts"
    OTP_EXPIRY_SECONDS = 600  # 10 minutes
    MAX_OTP_ATTEMPTS = 5

    @staticmethod
    def _generate_otp() -> str:
        """Generate a cryptographically random 6-digit OTP."""
        import secrets

        return secrets.randbelow(1_000_000)

    @staticmethod
    def _get_otp_cache_key(email: str) -> str:
        return f"{AuthService.OTP_CACHE_PREFIX}:{email.lower().strip()}"

    @staticmethod
    def _get_attempts_cache_key(email: str) -> str:
        return f"{AuthService.OTP_CACHE_ATTEMPTS_PREFIX}:{email.lower().strip()}"

    @classmethod
    def request_email_verification(cls, email: str) -> None:
        """Request an email verification OTP.

        Generates a 6-digit OTP, stores it in cache with expiry,
        and sends it via email.

        Args:
            email: The email address to verify.

        Raises:
            ValueError: If no account exists with this email.
        """
        try:
            user = UserModel.objects.get(email=email, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            logger.warning(f"Email verify requested for non-existent email: {email}")
            raise ValueError("No account found with this email address.")

        if user.is_email_verified:
            raise ValueError("This email is already verified.")

        # Generate and store OTP in cache
        otp = cls._generate_otp()
        cache_key = cls._get_otp_cache_key(email)

        from django.core.cache import cache

        cache.set(cache_key, str(otp), cls.OTP_EXPIRY_SECONDS)

        # Reset attempt counter
        attempts_key = cls._get_attempts_cache_key(email)
        cache.delete(attempts_key)

        # Send OTP via email
        otp_padded = str(otp).zfill(6)
        try:
            from django.conf import settings

            send_mail(
                subject="Verify Your Email - Satta Ledger",
                message=(
                    f"Your email verification code is: {otp_padded}\n\n"
                    f"This code expires in 10 minutes.\n\n"
                    f"If you didn't request this, ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send email verification OTP: {e}")

        logger.info(f"Email verification OTP sent: user={user.email}")

    @classmethod
    async def arequest_email_verification(cls, email: str) -> None:
        """Async version of request_email_verification()."""
        try:
            user = await UserModel.objects.aget(
                email=email, is_active=True, is_deleted=False
            )
        except User.DoesNotExist:
            logger.warning(f"Email verify requested for non-existent email: {email}")
            raise ValueError("No account found with this email address.")

        if user.is_email_verified:
            raise ValueError("This email is already verified.")

        otp = cls._generate_otp()
        cache_key = cls._get_otp_cache_key(email)

        from django.core.cache import cache

        await sync_to_async(cache.set)(cache_key, str(otp), cls.OTP_EXPIRY_SECONDS)

        attempts_key = cls._get_attempts_cache_key(email)
        await sync_to_async(cache.delete)(attempts_key)

        otp_padded = str(otp).zfill(6)
        try:
            from django.conf import settings

            await sync_to_async(send_mail)(
                subject="Verify Your Email - Satta Ledger",
                message=(
                    f"Your email verification code is: {otp_padded}\n\n"
                    f"This code expires in 10 minutes.\n\n"
                    f"If you didn't request this, ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send email verification OTP: {e}")

        logger.info(f"Email verification OTP sent (async): user={user.email}")

    @classmethod
    def confirm_email_verification(cls, email: str, otp: str) -> None:
        """Confirm email verification using OTP.

        Validates the OTP against cached value, checks attempts limit,
        and marks the user as verified.

        Args:
            email: The email address being verified.
            otp: The 6-digit OTP code.

        Raises:
            ValueError: If OTP is invalid, expired, too many attempts, or user not found.
        """
        from django.core.cache import cache

        cache_key = cls._get_otp_cache_key(email)
        attempts_key = cls._get_attempts_cache_key(email)

        # Check attempt limit
        attempts = cache.get(attempts_key, 0)
        if attempts >= cls.MAX_OTP_ATTEMPTS:
            cache.delete(cache_key)  # Invalidate OTP after too many attempts
            raise ValueError(
                "Too many failed attempts. Please request a new verification code."
            )

        # Get cached OTP
        cached_otp = cache.get(cache_key)
        if not cached_otp:
            raise ValueError("Verification code has expired. Please request a new one.")

        # Validate OTP
        if str(otp).strip() != str(cached_otp):
            cache.set(attempts_key, attempts + 1, cls.OTP_EXPIRY_SECONDS)
            remaining = cls.MAX_OTP_ATTEMPTS - (attempts + 1)
            raise ValueError(
                f"Invalid verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
            )

        # OTP is correct — verify the user
        try:
            user = UserModel.objects.get(email=email, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            raise ValueError("No account found with this email address.")

        if user.is_email_verified:
            # Already verified, just clean up cache
            cache.delete(cache_key)
            cache.delete(attempts_key)
            return

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        # Clean up cache
        cache.delete(cache_key)
        cache.delete(attempts_key)

        logger.info(f"Email verified: user={user.email}")

    @classmethod
    async def aconfirm_email_verification(cls, email: str, otp: str) -> None:
        """Async version of confirm_email_verification()."""
        from django.core.cache import cache

        cache_key = cls._get_otp_cache_key(email)
        attempts_key = cls._get_attempts_cache_key(email)

        attempts = await sync_to_async(cache.get)(attempts_key, 0)
        if attempts >= cls.MAX_OTP_ATTEMPTS:
            await sync_to_async(cache.delete)(cache_key)
            raise ValueError(
                "Too many failed attempts. Please request a new verification code."
            )

        cached_otp = await sync_to_async(cache.get)(cache_key)
        if not cached_otp:
            raise ValueError("Verification code has expired. Please request a new one.")

        if str(otp).strip() != str(cached_otp):
            await sync_to_async(cache.set)(
                attempts_key, attempts + 1, cls.OTP_EXPIRY_SECONDS
            )
            remaining = cls.MAX_OTP_ATTEMPTS - (attempts + 1)
            raise ValueError(
                f"Invalid verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."
            )

        try:
            user = await UserModel.objects.aget(
                email=email, is_active=True, is_deleted=False
            )
        except User.DoesNotExist:
            raise ValueError("No account found with this email address.")

        if user.is_email_verified:
            await sync_to_async(cache.delete)(cache_key)
            await sync_to_async(cache.delete)(attempts_key)
            return

        user.is_email_verified = True
        await user.asave(update_fields=["is_email_verified"])

        await sync_to_async(cache.delete)(cache_key)
        await sync_to_async(cache.delete)(attempts_key)

        logger.info(f"Email verified (async): user={user.email}")

    # =========================================================================
    # Account Deletion
    # =========================================================================

    @staticmethod
    def delete_account(user: User, current_password: str) -> None:
        """Soft-delete a user account after confirming current password.

        The user is marked as is_deleted=True and is_active=False.
        All JWT tokens should be discarded by the client after this.

        Args:
            user: The authenticated user.
            current_password: User's current password (identity confirmation).

        Raises:
            ValueError: If password is incorrect.
        """
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

        user.is_active = False
        user.is_deleted = True
        user.save(update_fields=["is_active", "is_deleted"])
        logger.info(f"Account deleted (soft): user={user.email}")

    @staticmethod
    async def adelete_account(user: User, current_password: str) -> None:
        """Async version of delete_account()."""
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

        user.is_active = False
        user.is_deleted = True
        await user.asave(update_fields=["is_active", "is_deleted"])
        logger.info(f"Account deleted (soft, async): user={user.email}")


# =============================================================================
# User Service
# =============================================================================


class UserService:
    """Handles user profile operations."""

    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """Get a user by ID. Filters out soft-deleted users."""
        try:
            return UserModel.objects.get(id=user_id, is_deleted=False)
        except User.DoesNotExist:
            raise ValueError("User not found.")

    @staticmethod
    async def aget_user_by_id(user_id: int) -> User:
        """Async version of get_user_by_id()."""
        try:
            return await UserModel.objects.aget(id=user_id, is_deleted=False)
        except User.DoesNotExist:
            raise ValueError("User not found.")

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get a user by email. Returns None if not found."""
        try:
            return UserModel.objects.get(email=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    async def aget_user_by_email(email: str) -> Optional[User]:
        """Async version of get_user_by_email()."""
        try:
            return await UserModel.objects.aget(email=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_active_user_by_email(email: str) -> Optional[User]:
        """Get an active, non-deleted user by email."""
        try:
            return UserModel.objects.get(email=email, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            return None

    @staticmethod
    async def aget_active_user_by_email(email: str) -> Optional[User]:
        """Async version of get_active_user_by_email()."""
        try:
            return await UserModel.objects.aget(
                email=email, is_active=True, is_deleted=False
            )
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_slug(slug: str) -> Optional[User]:
        """Get a user by their public slug. Returns None if not found."""
        return UserModel.objects.filter(slug=slug, is_deleted=False).first()

    @staticmethod
    async def aget_user_by_slug(slug: str) -> Optional[User]:
        """Async version of get_user_by_slug()."""
        return await UserModel.objects.filter(slug=slug, is_deleted=False).afirst()

    @staticmethod
    def update_profile(user: User, **kwargs) -> User:
        """Update a user's profile fields. Only whitelisted fields allowed."""
        allowed_fields = [
            "first_name",
            "last_name",
            "phone",
            "timezone",
            "currency",
            "language",
        ]
        updated_fields = []
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(user, field, value)
                updated_fields.append(field)

        if updated_fields:
            user.save(update_fields=updated_fields)
            logger.info(f"Profile updated: user={user.email}, fields={updated_fields}")

        return user

    @staticmethod
    async def aupdate_profile(user: User, **kwargs) -> User:
        """Async version of update_profile()."""
        allowed_fields = [
            "first_name",
            "last_name",
            "phone",
            "timezone",
            "currency",
            "language",
        ]
        updated_fields = []
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(user, field, value)
                updated_fields.append(field)

        if updated_fields:
            await user.asave(update_fields=updated_fields)
            logger.info(
                f"Profile updated (async): user={user.email}, fields={updated_fields}"
            )

        return user
