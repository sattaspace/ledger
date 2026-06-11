"""
Authentication Controller for DealerBackend

Handles login, logout, token refresh, and user info.
Proxies all auth calls to SattaBase.
"""

from ninja_extra import api_controller, http_post, http_get
from ninja_extra.permissions import AllowAny
from ninja import Schema
from typing import Optional
from django.http import HttpRequest, JsonResponse
from django.conf import settings

from common.sattabase_client import sattabase_client, SattaBaseAuthError


# ─── Schemas ─────────────────────────────────────────────────────────

class LoginInput(Schema):
    email: str
    password: str


class LoginOutput(Schema):
    access: str
    user: dict
    message: str = "Login successful"


class RefreshInput(Schema):
    refresh: str


class RefreshOutput(Schema):
    access: str
    message: str = "Token refreshed"


class UserOutput(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    is_active: bool
    subscription: Optional[dict] = None
    access_map: Optional[dict] = None


class MessageOutput(Schema):
    message: str


# ─── Controller ──────────────────────────────────────────────────────

@api_controller("/auth", tags=["Authentication"], permissions=[AllowAny])
class AuthController:
    """
    Authentication endpoints that proxy to SattaBase.
    
    All auth flows go through SattaBase:
    - Login validates credentials and returns JWT
    - Refresh gets new access token
    - Me returns user profile with subscription
    """
    
    @http_post("/login", response=LoginOutput)
    async def login(self, request: HttpRequest, data: LoginInput):
        """
        Login dealer with email/password.
        
        Proxies to SattaBase and returns JWT access token.
        Refresh token should be handled client-side or in httpOnly cookie.
        """
        try:
            result = await sattabase_client.login(data.email, data.password)
            
            # Create response with access token
            response = JsonResponse({
                "access": result["access"],
                "user": result["user"],
                "message": "Login successful"
            })
            
            # Set refresh token in httpOnly cookie if present
            if result.get("refresh"):
                response.set_cookie(
                    key="dealer_refresh_token",
                    value=result["refresh"],
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite="Lax",
                    max_age=7 * 24 * 60 * 60,  # 7 days
                )
            
            return response
            
        except SattaBaseAuthError as e:
            return JsonResponse(
                {"detail": e.message, "code": e.code},
                status=e.status_code
            )
    
    @http_post("/refresh", response=RefreshOutput)
    async def refresh(self, request: HttpRequest, data: Optional[RefreshInput] = None):
        """
        Refresh access token using refresh token.
        
        Checks cookie first, then request body.
        Returns new access token.
        """
        # Get refresh token from cookie or request body
        refresh_token = None
        
        if data and data.refresh:
            refresh_token = data.refresh
        else:
            refresh_token = request.COOKIES.get("dealer_refresh_token")
        
        if not refresh_token:
            return JsonResponse(
                {"detail": "Refresh token required", "code": "refresh_required"},
                status=401
            )
        
        try:
            result = await sattabase_client.refresh_token(refresh_token)
            
            response = JsonResponse({
                "access": result["access"],
                "message": "Token refreshed"
            })
            
            # Update refresh token cookie if new one provided
            if result.get("refresh"):
                response.set_cookie(
                    key="dealer_refresh_token",
                    value=result["refresh"],
                    httponly=True,
                    secure=not settings.DEBUG,
                    samesite="Lax",
                    max_age=7 * 24 * 60 * 60,
                )
            
            return response
            
        except SattaBaseAuthError as e:
            return JsonResponse(
                {"detail": e.message, "code": e.code},
                status=e.status_code
            )
    
    @http_post("/logout", response=MessageOutput)
    async def logout(self, request: HttpRequest):
        """
        Logout user by blacklisting refresh token.
        Clears the httpOnly cookie.
        """
        refresh_token = request.COOKIES.get("dealer_refresh_token")
        
        if refresh_token:
            try:
                await sattabase_client.logout(refresh_token)
            except SattaBaseAuthError:
                pass  # Continue even if logout fails on SattaBase
        
        response = JsonResponse({"message": "Logout successful"})
        response.delete_cookie("dealer_refresh_token")
        
        return response
    
    @http_get("/me", response=UserOutput)
    async def me(self, request: HttpRequest):
        """
        Get current user info from SattaBase.
        
        Requires valid access token in Authorization header.
        Returns user profile with subscription for this dealer domain.
        """
        # Extract access token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"detail": "Authentication required", "code": "auth_required"},
                status=401
            )
        
        access_token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            user_data = await sattabase_client.get_me(access_token)
            return user_data
            
        except SattaBaseAuthError as e:
            return JsonResponse(
                {"detail": e.message, "code": e.code},
                status=e.status_code
            )
    
    @http_get("/sso/authorize")
    async def sso_authorize(self, request: HttpRequest):
        """
        Generate SSO authorization code for cross-domain auth.
        
        Returns code that can be used to authenticate on SattaBase.
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"detail": "Authentication required", "code": "auth_required"},
                status=401
            )
        
        access_token = auth_header[7:]
        
        try:
            code = await sattabase_client.generate_auth_code(access_token)
            return {"code": code, "expires_in": 30}
            
        except SattaBaseAuthError as e:
            return JsonResponse(
                {"detail": e.message, "code": e.code},
                status=e.status_code
            )


# Cleanup function for graceful shutdown
async def close_sattabase_client():
    """Close SattaBase client connections"""
    await sattabase_client.close()
