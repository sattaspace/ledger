"""
DEALERCORE v3.0 — SSO Controller
---------------------------------
Cross-domain Single Sign-On for SattaBase integration.

Enables seamless navigation from dealer app to SattaBase
without requiring re-authentication.
"""

from ninja_extra import api_controller, http_get
from ninja_extra.permissions import IsAuthenticated
from ninja import Schema
from django.http import HttpRequest, JsonResponse, HttpResponseRedirect
from django.conf import settings
import os

from common.sattabase_client import sattabase_client, SattaBaseAuthError


# ─── Configuration ─────────────────────────────────────────────────────────

SATTABASE_FRONTEND_URL = os.getenv(
    "SB_FRONTEND_URL", 
    "http://localhost:4321"
)
SATTABASE_AUTH_CALLBACK_PATH = "/auth/callback"


# ─── Schemas ───────────────────────────────────────────────────────────────

class SSOOutput(Schema):
    sattaBaseUrl: str
    message: str = "Redirect to SattaBase for billing management"


class SSORedirectOutput(Schema):
    redirectUrl: str


# ─── Controller ────────────────────────────────────────────────────────────

@api_controller("/sso", tags=["SSO"], permissions=[IsAuthenticated])
class SSOController:
    """
    Single Sign-On endpoints for cross-domain authentication.
    
    Flow:
    1. User clicks "Manage Billing" in dealer app
    2. Frontend calls GET /sso/sattabase
    3. Backend calls SattaBase /auth/authorize to get one-time code
    4. Backend returns redirect URL with auth code
    5. Frontend redirects user to SattaBase
    6. SattaBase validates code and logs user in
    7. User can manage billing, then return to dealer app
    """
    
    @http_get("/sattabase", response=SSORedirectOutput)
    async def sso_to_sattabase(self, request: HttpRequest):
        """
        Generate SSO redirect URL for SattaBase.
        
        Returns a redirect URL containing a one-time authorization code.
        The code expires in 30 seconds and can only be used once.
        
        Response:
            { "redirectUrl": "https://sattabase.com/auth/callback?code=xxx" }
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
            # Generate authorization code from SattaBase
            auth_code = await sattabase_client.generate_auth_code(access_token)
            
            # Build redirect URL to SattaBase callback
            redirect_url = (
                f"{SATTABASE_FRONTEND_URL}{SATTABASE_AUTH_CALLBACK_PATH}"
                f"?code={auth_code}"
            )
            
            return {"redirectUrl": redirect_url}
            
        except SattaBaseAuthError as e:
            return JsonResponse(
                {"detail": e.message, "code": e.code},
                status=e.status_code
            )
    
    @http_get("/sattabase/redirect")
    async def sso_to_sattabase_redirect(self, request: HttpRequest):
        """
        Direct redirect endpoint for SSO to SattaBase.
        
        Performs HTTP 302 redirect to SattaBase with auth code.
        Useful for direct links or server-side redirects.
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"detail": "Authentication required", "code": "auth_required"},
                status=401
            )
        
        access_token = auth_header[7:]
        
        try:
            auth_code = await sattabase_client.generate_auth_code(access_token)
            
            redirect_url = (
                f"{SATTABASE_FRONTEND_URL}{SATTABASE_AUTH_CALLBACK_PATH}"
                f"?code={auth_code}"
            )
            
            return HttpResponseRedirect(redirect_url)
            
        except SattaBaseAuthError as e:
            return JsonResponse(
                {"detail": e.message, "code": e.code},
                status=e.status_code
            )


# ─── Public Callback Handler ───────────────────────────────────────────────
# Note: This would be on SattaBase, not dealerbackend
# But we include documentation here for completeness

"""
SattaBase Callback Handler (on SattaBase frontend):

Route: GET /auth/callback?code=<auth_code>

1. Extract code from query params
2. POST to SattaBase backend: /auth/token/exchange
   Body: { "code": "<auth_code>" }
3. SattaBase returns: { "access": "jwt_token" }
4. Store access token (in memory or localStorage)
5. User is now logged in on SattaBase
6. Show billing dashboard
7. Provide "Return to Dealer App" button linking back to dealer app
"""
