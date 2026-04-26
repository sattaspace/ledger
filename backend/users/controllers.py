"""Ninja Extra controllers for the users app."""

import logging

from asgiref.sync import sync_to_async

from ninja_extra import api_controller, http_post, http_get, http_put
from ninja.security import HttpBearer
from ninja_jwt.tokens import AccessToken, RefreshToken

from django.http import HttpRequest
from django.conf import settings

from common.permissions import IsAuthenticated, IsAdmin
from common.rate_limit import check_rate_limit, get_client_ip
from common.exceptions import TooManyRequestsException

from .schemas import (
    RegisterInputSchema,
    LoginInputSchema,
    TokenOutputSchema,
    TokenRefreshInputSchema,
    TokenVerifyInputSchema,
    TokenBlacklistInputSchema,
    PasswordResetRequestSchema,
    PasswordResetConfirmSchema,
    PasswordConfirmSchema,
    ChangeEmailRequestSchema,
    ChangeEmailConfirmSchema,
    DeleteAccountRequestSchema,
    UserOutputSchema,
    UserProfileUpdateInputSchema,
    ChangePasswordInputSchema,
    MessageSchema,
)
from .services import AuthService, UserService
from .models import User

logger = logging.getLogger(__name__)

async_token_for_user = sync_to_async(AccessToken.for_user)
async_refresh_for_user = sync_to_async(RefreshToken.for_user)
async_decode_refresh = sync_to_async(lambda t: RefreshToken(t))
async_blacklist = sync_to_async(lambda r: r.blacklist())


# =============================================================================
# JWT Authentication
# =============================================================================


class JWTAuth(HttpBearer):
    """HTTP Bearer authentication using JWT access tokens."""

    async def authenticate(self, request, token):
        try:
            access_token = AccessToken(token)
            user_id = access_token.get("user_id")
            if not user_id:
                return None
            user = await User.objects.filter(
                id=user_id, is_active=True, is_deleted=False
            ).afirst()
            if user:
                request.user = user
                return user
            return None
        except Exception as e:
            logger.debug(f"JWT auth failed: {e}")
            return None


# =============================================================================
# Auth Controller
# =============================================================================


@api_controller("/auth", tags=["Authentication"], auth=None)
class AuthController:
    """Public authentication endpoints."""

    @http_post(
        "/register",
        response={
            201: MessageSchema,
            409: MessageSchema,
            400: MessageSchema,
            429: MessageSchema,
        },
        summary="Register a new account",
    )
    async def register(self, request: HttpRequest, payload: RegisterInputSchema):
        client_ip = get_client_ip(request)
        rl_key = f"register:{client_ip}"

        if not check_rate_limit(
            rl_key,
            max_attempts=getattr(settings, "RATE_LIMIT_REGISTER_ATTEMPTS", 5),
            window_seconds=getattr(settings, "RATE_LIMIT_REGISTER_WINDOW", 3600),
        ):
            return 429, {
                "message": "Too many registration attempts. Please try again later.",
                "success": False,
            }

        try:
            user = await AuthService.aregister_user(
                email=payload.email,
                password=payload.password,
                first_name=payload.first_name,
                last_name=payload.last_name or "",
            )
            return 201, {
                "message": "Registration successful. You can now log in.",
                "success": True,
            }
        except ValueError as e:
            msg = str(e)
            if "already exists" in msg:
                return 409, {"message": msg, "success": False}
            return 400, {"message": msg, "success": False}
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return 400, {
                "message": "Registration failed. Please try again.",
                "success": False,
            }

    @http_post(
        "/login",
        response={
            200: TokenOutputSchema,
            401: MessageSchema,
            403: MessageSchema,
            429: MessageSchema,
        },
        summary="Login with email and password",
    )
    async def login(self, request: HttpRequest, payload: LoginInputSchema):
        client_ip = get_client_ip(request)
        rl_key = f"login:{client_ip}"

        if not check_rate_limit(
            rl_key,
            max_attempts=getattr(settings, "RATE_LIMIT_LOGIN_ATTEMPTS", 10),
            window_seconds=getattr(settings, "RATE_LIMIT_LOGIN_WINDOW", 900),
        ):
            return 429, {
                "message": "Too many login attempts. Please try again later.",
                "success": False,
            }

        try:
            user = await AuthService.aauthenticate_user(payload.email, payload.password)
            access = await async_token_for_user(user)
            refresh = await async_refresh_for_user(user)

            try:
                user.last_login_ip = client_ip
                await user.asave(update_fields=["last_login_ip"])
            except Exception:
                pass

            return 200, {"access": str(access), "refresh": str(refresh)}
        except ValueError as e:
            msg = str(e)
            if "Invalid" in msg:
                return 401, {"message": msg, "success": False}
            return 403, {"message": msg, "success": False}

    @http_post("/token/refresh", response={200: TokenOutputSchema, 401: MessageSchema})
    async def refresh_token(self, payload: TokenRefreshInputSchema):
        try:
            refresh = await async_decode_refresh(payload.refresh)
            user_id = refresh.get("user_id")
            if not user_id:
                raise ValueError("Invalid token payload")
            user = await User.objects.filter(
                id=user_id, is_active=True, is_deleted=False
            ).afirst()
            if not user:
                raise ValueError("User not found or inactive")
            new_access = await async_token_for_user(user)
            new_refresh = await async_refresh_for_user(user)
            return 200, {"access": str(new_access), "refresh": str(new_refresh)}
        except ValueError as e:
            logger.debug(f"Token refresh failed: {e}")
            return 401, {
                "message": "Invalid or expired refresh token.",
                "success": False,
            }

    @http_post("/token/verify", response={200: MessageSchema, 401: MessageSchema})
    async def verify_token(self, payload: TokenVerifyInputSchema):
        try:
            AccessToken(payload.token)
            return 200, {"message": "Token is valid.", "success": True}
        except Exception:
            return 401, {"message": "Token is invalid or expired.", "success": False}

    @http_post("/token/blacklist", response={200: MessageSchema, 401: MessageSchema})
    async def blacklist_token(self, payload: TokenBlacklistInputSchema):
        try:
            refresh = await async_decode_refresh(payload.refresh)
            await async_blacklist(refresh)
            return 200, {"message": "Token blacklisted successfully.", "success": True}
        except Exception as e:
            logger.debug(f"Token blacklist failed: {e}")
            return 401, {"message": "Failed to blacklist token.", "success": False}

    # =========================================================================
    # Password Reset
    # =========================================================================

    @http_post(
        "/password-reset/request", response={200: MessageSchema, 429: MessageSchema}
    )
    async def request_password_reset(
        self, request: HttpRequest, payload: PasswordResetRequestSchema
    ):
        client_ip = get_client_ip(request)
        if not check_rate_limit(
            f"pwreset_req:{client_ip}", max_attempts=5, window_seconds=3600
        ):
            return 429, {
                "message": "Too many password reset requests.",
                "success": False,
            }
        try:
            await AuthService.arequest_password_reset(payload.email)
        except ValueError:
            pass
        return 200, {
            "message": "If an account with this email exists, a reset link has been sent.",
            "success": True,
        }

    @http_post(
        "/password-reset/confirm",
        response={200: MessageSchema, 400: MessageSchema, 429: MessageSchema},
    )
    async def confirm_password_reset(
        self, request: HttpRequest, payload: PasswordResetConfirmSchema
    ):
        client_ip = get_client_ip(request)
        if not check_rate_limit(
            f"pwreset_confirm:{client_ip}", max_attempts=5, window_seconds=3600
        ):
            return 429, {
                "message": "Too many password reset attempts.",
                "success": False,
            }
        try:
            await AuthService.aconfirm_password_reset(
                token=payload.token, new_password=payload.new_password
            )
            return 200, {"message": "Password reset successfully.", "success": True}
        except ValueError as e:
            return 400, {"message": str(e), "success": False}

    # =========================================================================
    # Email Change Confirm (Public)
    # =========================================================================

    @http_post(
        "/email-change/confirm",
        response={200: MessageSchema, 400: MessageSchema, 429: MessageSchema},
    )
    async def confirm_email_change_public(
        self, request: HttpRequest, payload: ChangeEmailConfirmSchema
    ):
        client_ip = get_client_ip(request)
        if not check_rate_limit(
            f"email_change_confirm:{client_ip}", max_attempts=10, window_seconds=3600
        ):
            return 429, {"message": "Too many attempts.", "success": False}
        try:
            new_email = await AuthService.aconfirm_email_change(payload.token)
            return 200, {
                "message": f"Email changed successfully. You can now log in with {new_email}.",
                "success": True,
            }
        except ValueError as e:
            return 400, {"message": str(e), "success": False}


# =============================================================================
# User Controller (Authenticated)
# =============================================================================


@api_controller("/users", tags=["Users"], auth=JWTAuth(), permissions=[IsAuthenticated])
class UserController:
    """Authenticated user profile endpoints."""

    @http_get("/me", response=UserOutputSchema, summary="Get current user profile")
    def get_profile(self, request: HttpRequest):
        return request.user

    @http_get(
        "/{slug}",
        response={200: UserOutputSchema, 404: MessageSchema},
        summary="Get user by slug",
    )
    async def get_user_by_slug(self, slug: str):
        user = await UserService.aget_user_by_slug(slug)
        if not user:
            return 404, {"detail": "User not found.", "code": "not_found"}
        return user

    @http_put("/me", response=UserOutputSchema, summary="Update user profile")
    async def update_profile(
        self, request: HttpRequest, payload: UserProfileUpdateInputSchema
    ):
        user = await UserService.aupdate_profile(
            request.user, **payload.model_dump(exclude_none=True)
        )
        return user

    @http_post(
        "/me/change-password",
        response={200: MessageSchema, 400: MessageSchema},
        summary="Change password",
    )
    async def change_password(
        self, request: HttpRequest, payload: ChangePasswordInputSchema
    ):
        try:
            await AuthService.achange_password(
                request.user,
                current_password=payload.current_password,
                new_password=payload.new_password,
            )
            return 200, {"message": "Password changed successfully.", "success": True}
        except ValueError as e:
            return 400, {"message": str(e), "success": False}

    # =========================================================================
    # Sensitive Actions — Current Password Re-Confirmation
    # =========================================================================

    @http_post(
        "/me/confirm-identity",
        response={200: MessageSchema, 401: MessageSchema, 429: MessageSchema},
    )
    async def confirm_identity(
        self, request: HttpRequest, payload: PasswordConfirmSchema
    ):
        client_ip = get_client_ip(request)
        if not check_rate_limit(
            f"confirm_identity:{request.user.id}:{client_ip}",
            max_attempts=10,
            window_seconds=3600,
        ):
            return 429, {
                "message": "Too many identity confirmation attempts.",
                "success": False,
            }
        try:
            await AuthService.aconfirm_identity(
                request.user, current_password=payload.current_password
            )
            return 200, {"message": "Identity confirmed.", "success": True}
        except ValueError as e:
            return 401, {"message": str(e), "success": False}

    @http_post(
        "/me/change-email",
        response={
            200: MessageSchema,
            400: MessageSchema,
            401: MessageSchema,
            429: MessageSchema,
        },
    )
    async def request_email_change(
        self, request: HttpRequest, payload: ChangeEmailRequestSchema
    ):
        client_ip = get_client_ip(request)
        if not check_rate_limit(
            f"email_change:{request.user.id}:{client_ip}",
            max_attempts=5,
            window_seconds=3600,
        ):
            return 429, {"message": "Too many email change requests.", "success": False}
        try:
            await AuthService.arequest_email_change(
                request.user,
                current_password=payload.current_password,
                new_email=payload.new_email,
            )
            return 200, {
                "message": "Email change confirmation sent to your current email.",
                "success": True,
            }
        except ValueError as e:
            msg = str(e)
            if "password" in msg.lower():
                return 401, {"message": msg, "success": False}
            return 400, {"message": msg, "success": False}

    @http_post(
        "/me/delete-account",
        response={200: MessageSchema, 401: MessageSchema, 429: MessageSchema},
    )
    async def delete_account(
        self, request: HttpRequest, payload: DeleteAccountRequestSchema
    ):
        client_ip = get_client_ip(request)
        if not check_rate_limit(
            f"delete_account:{request.user.id}:{client_ip}",
            max_attempts=3,
            window_seconds=3600,
        ):
            return 429, {"message": "Too many attempts.", "success": False}
        try:
            await AuthService.adelete_account(
                request.user, current_password=payload.current_password
            )
            return 200, {
                "message": "Account deleted successfully. Please discard your tokens.",
                "success": True,
            }
        except ValueError as e:
            return 401, {"message": str(e), "success": False}

    # =========================================================================
    # Session
    # =========================================================================

    @http_post("/me/logout", response={200: MessageSchema}, summary="Logout")
    def logout(self, request: HttpRequest):
        logger.info(f"User logout: {request.user.email}")
        return 200, {
            "message": "Logged out successfully. Please discard your tokens.",
            "success": True,
        }
