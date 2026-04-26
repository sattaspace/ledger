"""Business logic services for the users app."""

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
    """Handles user authentication operations."""

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
            is_email_verified=True,
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
            is_email_verified=True,
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
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")
        user.set_password(new_password)
        user.save(update_fields=["password"])
        logger.info(f"Password changed: user={user.email}")

    @staticmethod
    async def achange_password(
        user: User, current_password: str, new_password: str
    ) -> None:
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
        """Reusable gate for sensitive operations."""
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

    @staticmethod
    async def aconfirm_identity(user: User, current_password: str) -> None:
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

    # =========================================================================
    # Email Change (Password + Email Confirmation)
    # =========================================================================

    @staticmethod
    def request_email_change(user: User, current_password: str, new_email: str) -> str:
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

        if user.email == new_email.lower().strip():
            raise ValueError("New email must be different from current email.")

        if UserModel.objects.email_exists(new_email):
            raise ValueError("An account with this email address already exists.")

        EmailChangeToken.objects.filter(user=user, used_at__isnull=True).update(
            used_at=timezone.now()
        )
        change_token = EmailChangeToken.objects.create(
            user=user, new_email=new_email.lower().strip()
        )

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
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

        new_email = new_email.lower().strip()
        if user.email == new_email:
            raise ValueError("New email must be different from current email.")

        if await UserModel.objects.aemail_exists(new_email):
            raise ValueError("An account with this email address already exists.")

        await EmailChangeToken.objects.filter(user=user, used_at__isnull=True).aupdate(
            used_at=timezone.now()
        )
        change_token = await EmailChangeToken.objects.acreate(
            user=user, new_email=new_email
        )

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

        if UserModel.objects.email_exists(new_email):
            raise ValueError(
                "An account with this email address already exists. Please request a new email change."
            )

        if not user.is_active or user.is_deleted:
            raise ValueError("This account is no longer active.")

        old_email = user.email
        user.email = new_email
        user.is_email_verified = True
        user.save(update_fields=["email", "is_email_verified"])
        change_token.mark_used()
        logger.info(f"Email changed: user={old_email} -> {new_email}")
        return new_email

    @staticmethod
    async def aconfirm_email_change(token: str) -> str:
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
                "An account with this email address already exists. Please request a new email change."
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
    # Account Deletion
    # =========================================================================

    @staticmethod
    def delete_account(user: User, current_password: str) -> None:
        if not user.check_password(current_password):
            raise ValueError("Current password is incorrect.")

        user.is_active = False
        user.is_deleted = True
        user.save(update_fields=["is_active", "is_deleted"])
        logger.info(f"Account deleted (soft): user={user.email}")

    @staticmethod
    async def adelete_account(user: User, current_password: str) -> None:
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
        try:
            return UserModel.objects.get(id=user_id, is_deleted=False)
        except User.DoesNotExist:
            raise ValueError("User not found.")

    @staticmethod
    async def aget_user_by_id(user_id: int) -> User:
        try:
            return await UserModel.objects.aget(id=user_id, is_deleted=False)
        except User.DoesNotExist:
            raise ValueError("User not found.")

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        try:
            return UserModel.objects.get(email=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    async def aget_user_by_email(email: str) -> Optional[User]:
        try:
            return await UserModel.objects.aget(email=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_active_user_by_email(email: str) -> Optional[User]:
        try:
            return UserModel.objects.get(email=email, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            return None

    @staticmethod
    async def aget_active_user_by_email(email: str) -> Optional[User]:
        try:
            return await UserModel.objects.aget(
                email=email, is_active=True, is_deleted=False
            )
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_slug(slug: str) -> Optional[User]:
        return UserModel.objects.filter(slug=slug, is_deleted=False).first()

    @staticmethod
    async def aget_user_by_slug(slug: str) -> Optional[User]:
        return await UserModel.objects.filter(slug=slug, is_deleted=False).afirst()

    @staticmethod
    def update_profile(user: User, **kwargs) -> User:
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
