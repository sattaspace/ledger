"""Business logic services for the users app.

Services encapsulate all business logic, keeping controllers thin and
testable. Controllers should only handle HTTP concerns (request parsing,
response formatting) and delegate to services.

Each service class provides both synchronous and asynchronous methods.
Use async methods in async controller endpoints to avoid blocking the
event loop.
"""

import random
import string
import logging
from datetime import timedelta
from typing import Optional, Tuple

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, hashers
from django.core.mail import send_mail
from django.utils import timezone

from .models import User, OTP

logger = logging.getLogger(__name__)
UserModel = get_user_model()


# =============================================================================
# OTP Service
# =============================================================================


class OTPService:
    """Handles OTP generation, verification, and delivery."""

    @staticmethod
    def generate_code(length: int = 6) -> str:
        """Generate a random numeric OTP code."""
        return "".join(random.choices(string.digits, k=length))

    @staticmethod
    def create_otp(user: User, purpose: str, ip_address: str = None) -> OTP:
        """Create a new OTP and invalidate any existing unused OTPs for the same purpose.

        Args:
            user: The User to create OTP for.
            purpose: Purpose string (registration, login, password_reset, email_verification).
            ip_address: Optional IP address of the requester.

        Returns:
            The created OTP instance.
        """
        # Invalidate existing unused OTPs for this user+purpose
        OTP.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).update(is_used=True)

        code = OTPService.generate_code()
        otp = OTP.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=timezone.now()
            + timedelta(minutes=getattr(settings, "OTP_EXPIRY_MINUTES", 10)),
            ip_address=ip_address,
        )
        logger.info(f"OTP created: user={user.email}, purpose={purpose}")
        return otp

    @staticmethod
    async def acreate_otp(user: User, purpose: str, ip_address: str = None) -> OTP:
        """Async version of create_otp().

        Invalidates existing unused OTPs and creates a new one using async ORM.
        """
        await OTP.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).aupdate(is_used=True)

        code = OTPService.generate_code()
        otp = OTP(
            user=user,
            code=code,
            purpose=purpose,
            expires_at=timezone.now()
            + timedelta(minutes=getattr(settings, "OTP_EXPIRY_MINUTES", 10)),
            ip_address=ip_address,
        )
        await otp.asave()
        logger.info(f"OTP created (async): user={user.email}, purpose={purpose}")
        return otp

    @staticmethod
    def verify_otp(
        email: str, code: str, purpose: str
    ) -> Tuple[bool, str, Optional[User]]:
        """Verify an OTP code for the given email and purpose.

        Args:
            email: The user's email address.
            code: The 6-digit OTP code.
            purpose: The OTP purpose.

        Returns:
            Tuple of (success, message, user_instance).
        """
        try:
            user = UserModel.objects.get(email=email)
        except User.DoesNotExist:
            return False, "No account found with this email address.", None

        # Get the most recent unused OTP for this purpose
        otp = (
            OTP.objects.filter(user=user, purpose=purpose, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if not otp:
            return False, "No active OTP found. Please request a new one.", user

        if otp.expires_at < timezone.now():
            otp.mark_used()
            return (
                False,
                "OTP has expired. Please request a new one.",
                user,
            )

        otp.increment_attempts()

        if otp.attempts >= 3:
            return False, "Too many failed attempts. Please request a new OTP.", user

        if otp.code != code:
            return False, "Invalid OTP code. Please try again.", user

        # Success
        otp.mark_used()
        logger.info(f"OTP verified: user={user.email}, purpose={purpose}")
        return True, "OTP verified successfully.", user

    @staticmethod
    async def averify_otp(
        email: str, code: str, purpose: str
    ) -> Tuple[bool, str, Optional[User]]:
        """Async version of verify_otp().

        Uses Django's async ORM to fetch user and OTP records without
        blocking the event loop.
        """
        try:
            user = await UserModel.objects.aget(email=email)
        except User.DoesNotExist:
            return False, "No account found with this email address.", None

        # Get the most recent unused OTP for this purpose
        otp = (
            await OTP.objects.filter(user=user, purpose=purpose, is_used=False)
            .order_by("-created_at")
            .afirst()
        )

        if not otp:
            return False, "No active OTP found. Please request a new one.", user

        if otp.expires_at < timezone.now():
            otp.is_used = True
            await otp.asave(update_fields=["is_used"])
            return False, "OTP has expired. Please request a new one.", user

        # Increment attempts
        otp.attempts += 1
        if otp.attempts >= 3:
            otp.is_used = True
            await otp.asave(update_fields=["attempts", "is_used"])
            return False, "Too many failed attempts. Please request a new OTP.", user
        else:
            await otp.asave(update_fields=["attempts"])

        if otp.code != code:
            return False, "Invalid OTP code. Please try again.", user

        # Success
        otp.is_used = True
        await otp.asave(update_fields=["is_used"])
        logger.info(f"OTP verified (async): user={user.email}, purpose={purpose}")
        return True, "OTP verified successfully.", user

    @staticmethod
    def check_rate_limit(user: User) -> Tuple[bool, str]:
        """Check if the user has exceeded the OTP request rate limit.

        Returns:
            Tuple of (allowed, error_message). If allowed is True, error_message is empty.
        """
        max_requests = getattr(settings, "OTP_MAX_REQUESTS_PER_HOUR", 5)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_count = user.otps.filter(created_at__gte=one_hour_ago).count()

        if recent_count >= max_requests:
            return (
                False,
                f"Too many OTP requests. Please try again in an hour. (Max {max_requests}/hour)",
            )
        return True, ""

    @staticmethod
    async def acheck_rate_limit(user: User) -> Tuple[bool, str]:
        """Async version of check_rate_limit()."""
        max_requests = getattr(settings, "OTP_MAX_REQUESTS_PER_HOUR", 5)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_count = await user.otps.filter(created_at__gte=one_hour_ago).acount()

        if recent_count >= max_requests:
            return (
                False,
                f"Too many OTP requests. Please try again in an hour. (Max {max_requests}/hour)",
            )
        return True, ""

    @staticmethod
    def send_otp_email(user: User, otp: OTP) -> bool:
        """Send the OTP code to the user's email.

        In DEBUG mode, emails go to the console. In production, configure
        a proper email backend (SMTP, SendGrid, etc.).

        Args:
            user: The User to send OTP to.
            otp: The OTP instance containing the code.

        Returns:
            True if email was sent successfully.
        """
        expiry_minutes = getattr(settings, "OTP_EXPIRY_MINUTES", 10)
        subject = f"Satta Ledger - {otp.get_purpose_display()}"
        body = (
            f"Hello {user.display_name},\n\n"
            f"Your verification code is: {otp.code}\n\n"
            f"This code expires in {expiry_minutes} minutes.\n"
            f"If you did not request this code, please ignore this email.\n\n"
            f"Best regards,\nSatta Ledger Team"
        )

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=getattr(
                    settings, "DEFAULT_FROM_EMAIL", "noreply@sattaledger.com"
                ),
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"OTP email sent: user={user.email}, purpose={otp.purpose}")
            return True
        except Exception as e:
            logger.error(f"Failed to send OTP email: user={user.email}, error={e}")
            return False


# =============================================================================
# Auth Service
# =============================================================================


class AuthService:
    """Handles user authentication operations (registration, login, password management)."""

    @staticmethod
    def register_user(
        email: str, password: str, first_name: str, last_name: str = ""
    ) -> User:
        """Register a new user account.

        The user is created with is_active=False and must verify their email
        via OTP before they can log in.

        Args:
            email: User's email address.
            password: User's chosen password.
            first_name: User's first name.
            last_name: User's last name (optional).

        Returns:
            The created User instance (not yet active).

        Raises:
            ValueError: If email already exists.
        """
        if UserModel.objects.email_exists(email):
            raise ValueError("A user with this email address already exists.")

        user = UserModel.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=False,
        )
        logger.info(f"User registered: {user.email}")
        return user

    @staticmethod
    async def aregister_user(
        email: str, password: str, first_name: str, last_name: str = ""
    ) -> User:
        """Async version of register_user().

        Creates a new user using the async manager method. The user is
        created with is_active=False and must verify their email via OTP.
        """
        if await UserModel.objects.aemail_exists(email):
            raise ValueError("A user with this email address already exists.")

        user = await UserModel.objects.acreate_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=False,
        )
        logger.info(f"User registered (async): {user.email}")
        return user

    @staticmethod
    def authenticate_user(email: str, password: str) -> User:
        """Authenticate a user with email and password.

        Args:
            email: User's email address.
            password: User's password.

        Returns:
            The authenticated User instance.

        Raises:
            ValueError: If credentials are invalid or account is inactive.
        """
        user = authenticate(request=None, username=email, password=password)

        if not user:
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError(
                "Your account is not active. Please verify your email address."
            )

        if user.is_deleted:
            raise ValueError("This account has been deactivated.")

        return user

    @staticmethod
    async def aauthenticate_user(email: str, password: str) -> User:
        """Async version of authenticate_user().

        Note: Django's built-in authenticate() is synchronous. This method
        fetches the user via async ORM and checks the password manually
        to avoid blocking the event loop.
        """
        user = await UserModel.objects.aget_by_email(email)

        if not user:
            raise ValueError("Invalid email or password.")

        if not hashers.check_password(password, user.password):
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError(
                "Your account is not active. Please verify your email address."
            )

        if user.is_deleted:
            raise ValueError("This account has been deactivated.")

        return user

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> None:
        """Change a user's password.

        Args:
            user: The authenticated User instance.
            current_password: The user's current password.
            new_password: The new password to set.

        Raises:
            ValueError: If current password is incorrect.
        """
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

    @staticmethod
    def reset_password(email: str, new_password: str) -> User:
        """Reset a user's password (after OTP verification in the controller).

        Args:
            email: User's email address.
            new_password: The new password.

        Returns:
            The User instance.

        Raises:
            ValueError: If user not found.
        """
        try:
            user = UserModel.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError("No account found with this email address.")

        user.set_password(new_password)
        user.save(update_fields=["password"])
        logger.info(f"Password reset: user={user.email}")
        return user

    @staticmethod
    async def areset_password(email: str, new_password: str) -> User:
        """Async version of reset_password()."""
        try:
            user = await UserModel.objects.aget(email=email)
        except User.DoesNotExist:
            raise ValueError("No account found with this email address.")

        user.set_password(new_password)
        await user.asave(update_fields=["password"])
        logger.info(f"Password reset (async): user={user.email}")
        return user

    @staticmethod
    def activate_user(user: User) -> None:
        """Activate a user account (after email verification).

        Args:
            user: The User to activate.
        """
        user.is_active = True
        user.is_email_verified = True
        user.save(update_fields=["is_active", "is_email_verified"])
        logger.info(f"User activated: {user.email}")

    @staticmethod
    async def aactivate_user(user: User) -> None:
        """Async version of activate_user()."""
        user.is_active = True
        user.is_email_verified = True
        await user.asave(update_fields=["is_active", "is_email_verified"])
        logger.info(f"User activated (async): {user.email}")


# =============================================================================
# User Service
# =============================================================================


class UserService:
    """Handles user profile operations."""

    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """Get a user by ID.

        Args:
            user_id: The user's primary key.

        Returns:
            The User instance.

        Raises:
            ValueError: If user not found.
        """
        try:
            return UserModel.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found.")

    @staticmethod
    async def aget_user_by_id(user_id: int) -> User:
        """Async version of get_user_by_id()."""
        try:
            return await UserModel.objects.aget(id=user_id)
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
    def get_user_by_slug(slug: str) -> Optional[User]:
        """Get a user by their public slug. Returns None if not found."""
        return UserModel.objects.filter(slug=slug, is_deleted=False).first()

    @staticmethod
    async def aget_user_by_slug(slug: str) -> Optional[User]:
        """Async version of get_user_by_slug()."""
        return await UserModel.objects.filter(slug=slug, is_deleted=False).afirst()

    @staticmethod
    def update_profile(user: User, **kwargs) -> User:
        """Update a user's profile fields.

        Only whitelisted fields are allowed to prevent mass assignment.

        Args:
            user: The User instance to update.
            **kwargs: Fields to update (first_name, last_name, phone, timezone, currency, language).

        Returns:
            The updated User instance.
        """
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


# =============================================================================
# OAuth Service
# =============================================================================


class OAuthService:
    """Handles OAuth authentication flows.

    Supports Google and GitHub as OAuth providers. The flow is:
    1. Frontend authenticates with the provider
    2. Frontend sends the provider's access_token to our API
    3. We validate the token with the provider's userinfo API
    4. We find or create the user
    5. We return our JWT tokens
    """

    PROVIDERS = {
        "google": {
            "userinfo_url": "https://www.googleapis.com/oauth2/v1/userinfo",
            "token_param": "access_token",
            "email_key": "email",
            "name_key": "name",
            "picture_key": "picture",
            "id_key": "id",
        },
        "github": {
            "userinfo_url": "https://api.github.com/user",
            "token_header": "token",
            "email_key": "email",
            "name_key": "name",
            "picture_key": "avatar_url",
            "id_key": "id",
        },
    }

    @staticmethod
    async def avalidate_provider_token(
        provider: str, access_token: str
    ) -> Optional[dict]:
        """Async version of validate_provider_token().

        Uses httpx for non-blocking HTTP requests to the OAuth provider.
        Falls back to synchronous requests if httpx is not available.
        """
        import requests as sync_requests

        try:
            import httpx

            config = OAuthService.PROVIDERS.get(provider)
            if not config:
                logger.error(f"Unsupported OAuth provider: {provider}")
                return None

            async with httpx.AsyncClient(timeout=10) as client:
                if "token_header" in config:
                    headers = {
                        "Authorization": f"{config['token_header']} {access_token}"
                    }
                    response = await client.get(config["userinfo_url"], headers=headers)
                else:
                    params = {config["token_param"]: access_token}
                    response = await client.get(config["userinfo_url"], params=params)

                response.raise_for_status()
                data = response.json()

        except ImportError:
            # httpx not installed — fall back to sync (blocks event loop)
            logger.warning(
                "httpx not installed, falling back to sync OAuth validation. "
                "Install httpx for full async support."
            )
            return OAuthService.validate_provider_token(provider, access_token)
        except Exception as e:
            logger.error(
                f"OAuth validation failed (async): provider={provider}, error={e}"
            )
            return None

        return {
            "email": data.get(config["email_key"], "").lower().strip(),
            "name": data.get(config["name_key"], ""),
            "picture": data.get(config["picture_key"], ""),
            "provider_id": str(data.get(config["id_key"], "")),
        }

    @staticmethod
    def validate_provider_token(provider: str, access_token: str) -> Optional[dict]:
        """Validate an OAuth access token with the provider and fetch user info.

        Args:
            provider: Provider name ('google' or 'github').
            access_token: The provider's access token.

        Returns:
            Dict with 'email', 'name', 'picture', 'provider_id' or None on failure.
        """
        import requests

        config = OAuthService.PROVIDERS.get(provider)
        if not config:
            logger.error(f"Unsupported OAuth provider: {provider}")
            return None

        try:
            if "token_header" in config:
                # GitHub style: token in Authorization header
                headers = {"Authorization": f"{config['token_header']} {access_token}"}
                response = requests.get(
                    config["userinfo_url"], headers=headers, timeout=10
                )
            else:
                # Google style: token as query parameter
                params = {config["token_param"]: access_token}
                response = requests.get(
                    config["userinfo_url"], params=params, timeout=10
                )

            response.raise_for_status()
            data = response.json()

            return {
                "email": data.get(config["email_key"], "").lower().strip(),
                "name": data.get(config["name_key"], ""),
                "picture": data.get(config["picture_key"], ""),
                "provider_id": str(data.get(config["id_key"], "")),
            }

        except requests.RequestException as e:
            logger.error(f"OAuth validation failed: provider={provider}, error={e}")
            return None
        except Exception as e:
            logger.error(f"OAuth error: provider={provider}, error={e}")
            return None

    @staticmethod
    def oauth_login_or_signup(provider: str, access_token: str) -> User:
        """Authenticate a user via OAuth, creating the account if needed.

        Args:
            provider: Provider name ('google' or 'github').
            access_token: The provider's access token.

        Returns:
            The authenticated User instance.

        Raises:
            ValueError: If token validation fails or email is missing.
        """
        user_info = OAuthService.validate_provider_token(provider, access_token)
        if not user_info:
            raise ValueError(f"Failed to validate {provider} access token.")

        if not user_info["email"]:
            raise ValueError(
                "Could not retrieve email from OAuth provider. "
                "Please ensure email access is permitted in your OAuth app settings."
            )

        email = user_info["email"]

        # Try to find existing user by OAuth UID first
        user = UserModel.objects.filter(
            oauth_provider=provider, oauth_uid=user_info["provider_id"]
        ).first()

        if not user:
            # Try to find by email
            user = UserModel.objects.filter(email=email).first()

            if user:
                # Link the OAuth provider to the existing account
                user.oauth_provider = provider
                user.oauth_uid = user_info["provider_id"]
                user.save(update_fields=["oauth_provider", "oauth_uid"])
                logger.info(f"OAuth linked to existing account: {email} via {provider}")
            else:
                # Create new user from OAuth data
                name_parts = (
                    user_info["name"].split(" ", 1) if user_info["name"] else ["", ""]
                )
                first_name = name_parts[0] if len(name_parts) > 0 else ""
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                user = UserModel.objects.create_user(
                    email=email,
                    password=None,  # OAuth users have no password
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                    is_email_verified=True,  # Verified by OAuth provider
                    oauth_provider=provider,
                    oauth_uid=user_info["provider_id"],
                )
                logger.info(f"OAuth account created: {email} via {provider}")

        if not user.is_active:
            raise ValueError("This account is not active. Please contact support.")

        return user

    @staticmethod
    async def aoauth_login_or_signup(provider: str, access_token: str) -> User:
        """Async version of oauth_login_or_signup().

        Uses async token validation and async ORM for user lookup/creation.
        """
        user_info = await OAuthService.avalidate_provider_token(provider, access_token)
        if not user_info:
            raise ValueError(f"Failed to validate {provider} access token.")

        if not user_info["email"]:
            raise ValueError(
                "Could not retrieve email from OAuth provider. "
                "Please ensure email access is permitted in your OAuth app settings."
            )

        email = user_info["email"]

        # Try to find existing user by OAuth UID first
        user = await UserModel.objects.aget_by_oauth(provider, user_info["provider_id"])

        if not user:
            # Try to find by email
            user = await UserModel.objects.aget_by_email(email)

            if user:
                # Link the OAuth provider to the existing account
                user.oauth_provider = provider
                user.oauth_uid = user_info["provider_id"]
                await user.asave(update_fields=["oauth_provider", "oauth_uid"])
                logger.info(
                    f"OAuth linked to existing account (async): {email} via {provider}"
                )
            else:
                # Create new user from OAuth data
                name_parts = (
                    user_info["name"].split(" ", 1) if user_info["name"] else ["", ""]
                )
                first_name = name_parts[0] if len(name_parts) > 0 else ""
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                user = await UserModel.objects.acreate_user(
                    email=email,
                    password=None,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                    is_email_verified=True,
                    oauth_provider=provider,
                    oauth_uid=user_info["provider_id"],
                )
                logger.info(f"OAuth account created (async): {email} via {provider}")

        if not user.is_active:
            raise ValueError("This account is not active. Please contact support.")

        return user
