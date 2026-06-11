"""
SattaBase API Client for DealerBackend

Handles authentication communication with SattaBase central system.
All auth calls are proxied through this client.
"""

import os
from typing import Optional, Dict, Any, Tuple
import aiohttp
from datetime import datetime, timedelta

# Configuration from environment
SATTABASE_API_URL = os.getenv("SB_API_BASE_URL", "http://localhost:8086/api/v1")
SERVICE_DOMAIN = os.getenv("SB_SERVICE_DOMAIN", "dealer.sattaspace.com")
API_KEY = os.getenv("SB_API_KEY", "")


class SattaBaseAuthError(Exception):
    """SattaBase authentication error"""
    def __init__(self, message: str, code: str = "auth_error", status_code: int = 401):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class SattaBaseClient:
    """
    Async client for SattaBase authentication API.
    
    Handles:
    - Login proxy
    - Token refresh
    - Auth/me retrieval
    - SSO authorization
    """
    
    def __init__(self):
        self.base_url = SATTABASE_API_URL.rstrip("/")
        self.service_domain = SERVICE_DOMAIN
        self.api_key = API_KEY
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                    "X-Service-Domain": self.service_domain,
                }
            )
        return self._session
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Proxy login request to SattaBase.
        
        Returns:
            {
                "access": "jwt_access_token",
                "refresh": "jwt_refresh_token",
                "user": { ... }
            }
        """
        session = await self._get_session()
        
        url = f"{self.base_url}/auth/login"
        payload = {
            "email": email,
            "password": password,
        }
        
        try:
            async with session.post(url, json=payload) as response:
                data = await response.json()
                
                if response.status != 200:
                    raise SattaBaseAuthError(
                        message=data.get("detail", "Login failed"),
                        code=data.get("code", "login_failed"),
                        status_code=response.status
                    )
                
                return {
                    "access": data.get("access"),
                    "refresh": data.get("refresh"),
                    "user": data.get("user"),
                }
                
        except aiohttp.ClientError as e:
            raise SattaBaseAuthError(
                message=f"Connection error: {str(e)}",
                code="connection_error",
                status_code=503
            )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh access token using refresh token.
        
        Returns:
            {
                "access": "new_jwt_access_token",
                "refresh": "new_jwt_refresh_token"
            }
        """
        session = await self._get_session()
        
        url = f"{self.base_url}/auth/token/refresh"
        payload = {"refresh": refresh_token}
        
        try:
            async with session.post(url, json=payload) as response:
                data = await response.json()
                
                if response.status != 200:
                    raise SattaBaseAuthError(
                        message=data.get("detail", "Token refresh failed"),
                        code=data.get("code", "refresh_failed"),
                        status_code=response.status
                    )
                
                return {
                    "access": data.get("access"),
                    "refresh": data.get("refresh"),
                }
                
        except aiohttp.ClientError as e:
            raise SattaBaseAuthError(
                message=f"Connection error: {str(e)}",
                code="connection_error",
                status_code=503
            )
    
    async def get_me(self, access_token: str) -> Dict[str, Any]:
        """
        Get current user info from SattaBase.
        
        Returns user profile with subscription info.
        """
        session = await self._get_session()
        
        url = f"{self.base_url}/billing/auth/me"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                
                if response.status != 200:
                    raise SattaBaseAuthError(
                        message=data.get("detail", "Failed to get user info"),
                        code=data.get("code", "me_failed"),
                        status_code=response.status
                    )
                
                return data
                
        except aiohttp.ClientError as e:
            raise SattaBaseAuthError(
                message=f"Connection error: {str(e)}",
                code="connection_error",
                status_code=503
            )
    
    async def logout(self, refresh_token: str) -> None:
        """
        Logout user by blacklisting refresh token.
        Returns True if successful.
        """
        session = await self._get_session()
        
        url = f"{self.base_url}/auth/token/blacklist"
        payload = {"refresh": refresh_token}
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status not in (200, 401):  # 401 is ok - token already expired
                    data = await response.json()
                    raise SattaBaseAuthError(
                        message=data.get("detail", "Logout failed"),
                        code=data.get("code", "logout_failed"),
                        status_code=response.status
                    )
                
        except aiohttp.ClientError:
            # Don't raise on logout - just log and continue
            pass
    
    async def generate_auth_code(self, access_token: str) -> str:
        """
        Generate SSO authorization code for cross-domain auth.
        
        Returns:
            Authorization code (30 second expiry)
        """
        session = await self._get_session()
        
        url = f"{self.base_url}/auth/authorize"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with session.post(url, headers=headers) as response:
                data = await response.json()
                
                if response.status != 200:
                    raise SattaBaseAuthError(
                        message=data.get("detail", "Authorization failed"),
                        code=data.get("code", "authorize_failed"),
                        status_code=response.status
                    )
                
                return data.get("code")
                
        except aiohttp.ClientError as e:
            raise SattaBaseAuthError(
                message=f"Connection error: {str(e)}",
                code="connection_error",
                status_code=503
            )
    
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()


# Singleton instance
sattabase_client = SattaBaseClient()
