"""Ninja Extra controllers for the users app.

Controllers handle HTTP routing and delegate business logic to services.
They are auto-discovered by ninja_extra's `auto_discover_controllers()`.

Each controller is decorated with @api_controller() which:
- Registers it with the API router
- Sets the URL prefix
- Applies default auth and permissions
- Generates OpenAPI documentation

Controllers use async def where ORM operations are needed (via service
async methods). This ensures non-blocking I/O when running under Daphne/uvicorn.
"""

import logging

from ninja_extra import api_controller, http_post, http_get, http_put, http_patch
from ninja.security import HttpBearer
from ninja_jwt.tokens import AccessToken, RefreshToken
from ninja_jwt.controller import NinjaJWTDefaultController

from django.http import HttpRequest
from django.conf import settings

from common.permissions import IsAuthenticated, IsAdmin
from common.exceptions import (
    BadRequestException,
    NotFoundException,
    TooManyRequestsException,
)

from .schemas import (
    RegisterInputSchema,
    LoginInputSchema,
    TokenOutputSchema,
    TokenRefreshInputSchema,
    OTPRequestInputSchema,
    OTPVerifyInputSchema,
    OTPLoginInputSchema,
    UserOutputSchema,
    UserProfileUpdateInputSchema,
    ChangePasswordInputSchema,
    ResetPasswordInputSchema,
    OAuthLoginInputSchema,
    MessageSchema,
)
from .services import AuthService, OTPService, UserService, OAuthService
from .models import User

logger = logging.getLogger(__name__)


# =============================================================================
# JWT Authentication (for protecting endpoints)
# =============================================================================


class JWTAuth(HttpBearer):
    """HTTP Bearer authentication using JWT access tokens.

    Validates the Bearer token from the Authorization header,
    decodes it, and returns the authenticated user.
    """

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
# Auth Controller — Registration, Login, OTP, Token Management
# =============================================================================


@api_controller("/auth", tags=["Authentication"], auth=None)
class AuthController:
    """Public authentication endpoints.

    All endpoints in this controller are public (no auth required).
    They handle user registration, login (email/password and OTP),
    token management, and OAuth flows.

    Note: Standard JWT token obtain/refresh/verify endpoints are also
    available via NinjaJWTDefaultController at /token/.
    """

    @http_post(
        "/register",
        response={201: MessageSchema, 409: MessageSchema, 400: MessageSchema},
        summary="Register a new account",
        description="Create a new user account. An OTP will be sent to the email for verification.",
    )
    async def register(self, payload: RegisterInputSchema):
        try:
            user = await AuthService.aregister_user(
                email=payload.email,
                password=payload.password,
                first_name=payload.first_name,
                last_name=payload.last_name or "",
            )
            # Send OTP for email verification
            otp = await OTPService.acreate_otp(user, "registration")
            OTPService.send_otp_email(user, otp)

            return 201, {
                "message": "Registration successful. Please check your email for the verification OTP.",
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
        response={200: TokenOutputSchema, 401: MessageSchema, 403: MessageSchema},
        summary="Login with email and password",
        description="Authenticate with email/password and receive JWT tokens.",
    )
    async def login(self, payload: LoginInputSchema):
        try:
            user = await AuthService.aauthenticate_user(payload.email, payload.password)
            access = AccessToken.for_user(user)
            refresh = RefreshToken.for_user(user)

            # Track login IP
            try:
                user.last_login_ip = self.request.META.get("REMOTE_ADDR", None)
                await user.asave(update_fields=["last_login_ip"])
            except Exception:
                pass  # Don't fail login just because we can't log the IP

            return 200, {
                "access": str(access),
                "refresh": str(refresh),
            }

        except ValueError as e:
            msg = str(e)
            if "Invalid" in msg:
                return 401, {"message": msg, "success": False}
            return 403, {"message": msg, "success": False}

    @http_post(
        "/token/refresh",
        response={200: TokenOutputSchema, 401: MessageSchema},
        summary="Refresh access token",
        description="Exchange a valid refresh token for a new access token pair.",
    )
    async def refresh_token(self, payload: TokenRefreshInputSchema):
        try:
            refresh = RefreshToken(payload.refresh)

            # Verify user still exists and is active
            user_id = refresh.get("user_id")
            if not user_id:
                raise Exception("Invalid token payload")

            user = await User.objects.filter(
                id=user_id, is_active=True, is_deleted=False
            ).afirst()
            if not user:
                raise Exception("User not found or inactive")

            # Generate new token pair
            new_access = AccessToken.for_user(user)
            new_refresh = RefreshToken.for_user(user)

            return 200, {
                "access": str(new_access),
                "refresh": str(new_refresh),
            }

        except Exception as e:
            logger.debug(f"Token refresh failed: {e}")
            return 401, {
                "message": "Invalid or expired refresh token.",
                "success": False,
            }

    # -------------------------------------------------------------------------
    # OTP Endpoints
    # -------------------------------------------------------------------------

    @http_post(
        "/otp/request",
        response={200: MessageSchema, 429: MessageSchema, 400: MessageSchema},
        summary="Request an OTP code",
        description="Request a one-time password via email. Supports registration, login, password_reset, and email_verification purposes.",
    )
    async def request_otp(self, payload: OTPRequestInputSchema):
        try:
            purpose = payload.purpose.value

            # For registration, create inactive user if needed
            if purpose == "registration":
                user, created = await User.objects.aupdate_or_create(
                    email=payload.email,
                    defaults={
                        "is_active": False,
                        "first_name": "",
                        "last_name": "",
                    },
                )
            else:
                user = await UserService.aget_user_by_email(payload.email)
                if not user:
                    return 400, {
                        "message": "No account found with this email address.",
                        "success": False,
                    }

            # Rate limit check
            allowed, error_msg = await OTPService.acheck_rate_limit(user)
            if not allowed:
                return 429, {"message": error_msg, "success": False}

            # Create and send OTP
            try:
                ip_address = self.request.META.get("REMOTE_ADDR", None)
            except Exception:
                ip_address = None
            otp = await OTPService.acreate_otp(user, purpose, ip_address=ip_address)
            sent = OTPService.send_otp_email(user, otp)

            if not sent:
                return 400, {
                    "message": "Failed to send OTP. Please try again.",
                    "success": False,
                }

            return 200, {"message": "OTP sent to your email.", "success": True}

        except Exception as e:
            logger.error(f"OTP request error: {e}")
            return 400, {
                "message": "Failed to process OTP request.",
                "success": False,
            }

    @http_post(
        "/otp/verify",
        response={200: MessageSchema, 400: MessageSchema},
        summary="Verify an OTP code",
        description="Verify a one-time password. For registration, this also activates the account.",
    )
    async def verify_otp(self, payload: OTPVerifyInputSchema):
        success, message, user = await OTPService.averify_otp(
            email=payload.email,
            code=payload.code,
            purpose=payload.purpose.value,
        )

        if success and user:
            purpose = payload.purpose.value
            if purpose == "registration":
                await AuthService.aactivate_user(user)
                return 200, {
                    "message": "Email verified. Your account is now active. You can log in.",
                    "success": True,
                }
            elif purpose == "email_verification":
                user.is_email_verified = True
                await user.asave(update_fields=["is_email_verified"])
                return 200, {
                    "message": "Email verified successfully.",
                    "success": True,
                }
            elif purpose == "password_reset":
                return 200, {
                    "message": "OTP verified. You can now reset your password.",
                    "success": True,
                }

        return 200 if success else 400, {"message": message, "success": success}

    @http_post(
        "/otp/login",
        response={200: TokenOutputSchema, 401: MessageSchema, 400: MessageSchema},
        summary="Login with OTP (passwordless)",
        description="Authenticate using only an OTP code. User must request an OTP first via /auth/otp/request with purpose=login.",
    )
    async def otp_login(self, payload: OTPLoginInputSchema):
        success, message, user = await OTPService.averify_otp(
            email=payload.email, code=payload.code, purpose="login"
        )

        if not success or not user:
            return 401, {"message": message or "Invalid OTP.", "success": False}

        if not user.is_active:
            return 403, {
                "message": "Account is not active. Please verify your email first.",
                "success": False,
            }

        access = AccessToken.for_user(user)
        refresh = RefreshToken.for_user(user)

        return 200, {"access": str(access), "refresh": str(refresh)}

    @http_post(
        "/password/reset",
        response={200: MessageSchema, 400: MessageSchema},
        summary="Reset password with OTP",
        description="Reset password. Requires a verified OTP first (request OTP with purpose=password_reset, then verify).",
    )
    async def reset_password(self, payload: ResetPasswordInputSchema):
        # Verify OTP for password_reset
        success, message, user = await OTPService.averify_otp(
            email=payload.email, code=payload.code, purpose="password_reset"
        )

        if not success or not user:
            return 400, {"message": message, "success": False}

        try:
            await AuthService.areset_password(payload.email, payload.new_password)
            return 200, {
                "message": "Password reset successfully. You can now log in with your new password.",
                "success": True,
            }
        except ValueError as e:
            return 400, {"message": str(e), "success": False}

    # -------------------------------------------------------------------------
    # OAuth Endpoints
    # -------------------------------------------------------------------------

    @http_post(
        "/oauth/login",
        response={200: TokenOutputSchema, 400: MessageSchema},
        summary="Login or signup with OAuth",
        description="Authenticate using a Google or GitHub access token. If the user doesn't exist, a new account is created.",
    )
    async def oauth_login(self, payload: OAuthLoginInputSchema):
        try:
            user = await OAuthService.aoauth_login_or_signup(
                provider=payload.provider.value,
                access_token=payload.access_token,
            )

            access = AccessToken.for_user(user)
            refresh = RefreshToken.for_user(user)

            return 200, {"access": str(access), "refresh": str(refresh)}

        except ValueError as e:
            return 400, {"message": str(e), "success": False}

        except Exception as e:
            logger.error(f"OAuth login error: {e}")
            return 400, {
                "message": "OAuth authentication failed. Please try again.",
                "success": False,
            }


# =============================================================================
# User Controller — Profile Management (authenticated)
# =============================================================================


@api_controller(
    "/users",
    tags=["Users"],
    auth=JWTAuth(),
    permissions=[IsAuthenticated],
)
class UserController:
    """Authenticated user profile endpoints.

    All endpoints require a valid JWT access token.
    """

    @http_get(
        "/me",
        response=UserOutputSchema,
        summary="Get current user profile",
        description="Return the authenticated user's profile information.",
    )
    def get_profile(self, request: HttpRequest):
        return request.user

    @http_get(
        "/{slug}",
        response=UserOutputSchema,
        summary="Get user by slug",
        description="Look up a user's public profile by their UUID slug.",
    )
    async def get_user_by_slug(self, slug: str):
        user = await UserService.aget_user_by_slug(slug)
        if not user:
            return 404, {"detail": "User not found.", "code": "not_found"}
        return user

    @http_put(
        "/me",
        response=UserOutputSchema,
        summary="Update user profile",
        description="Update the authenticated user's profile fields.",
    )
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
        description="Change the authenticated user's password. Requires current password.",
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
            return 200, {
                "message": "Password changed successfully.",
                "success": True,
            }
        except ValueError as e:
            return 400, {"message": str(e), "success": False}

    @http_post(
        "/me/logout",
        response={200: MessageSchema},
        summary="Logout (client-side)",
        description="Notify the server of logout. Client should discard JWT tokens.",
    )
    def logout(self, request: HttpRequest):
        # In a stateless JWT setup, logout is handled client-side by
        # discarding the tokens. This endpoint exists for future token
        # blacklisting support and audit logging.
        logger.info(f"User logout: {request.user.email}")
        return 200, {
            "message": "Logged out successfully. Please discard your tokens.",
            "success": True,
        }
