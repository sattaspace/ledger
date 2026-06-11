"""
Access Control Controller

Provides endpoints to check user permissions from SattaBase access matrix.
Maps SattaBase access entries to DealerCore permissions.
"""

from ninja_extra import api_controller, http_get
from ninja import Schema
from typing import Dict, Any, Optional
from django.http import HttpRequest, JsonResponse

from common.sattabase_client import sattabase_client, SattaBaseAuthError


# ─── Schemas ─────────────────────────────────────────────────────────

class AccessMatrixOutput(Schema):
    """Full access matrix from SattaBase"""
    access_map: Dict[str, Any]
    product_slug: str
    plan_name: Optional[str] = None
    is_trial: bool = False
    trial_ends_at: Optional[str] = None


class AccessCheckOutput(Schema):
    """Single permission check result"""
    key: str
    has_access: bool
    value: Any
    message: str


class SubscriptionOutput(Schema):
    """Subscription status"""
    status: str  # active, trialing, past_due, canceled, expired
    plan_name: Optional[str] = None
    current_period_end: Optional[str] = None
    days_remaining: Optional[int] = None
    is_active: bool


# ─── Controller ──────────────────────────────────────────────────────

@api_controller("/access", tags=["Access Control"])
class AccessController:
    """
    Access control endpoints that proxy to SattaBase.
    
    Returns user's subscription status and access matrix
    from their SattaBase subscription.
    """
    
    @http_get("/matrix", response=AccessMatrixOutput)
    async def get_access_matrix(self, request: HttpRequest):
        """
        Get current user's access matrix from SattaBase.
        
        Returns the access_map from the user's subscription,
        showing which features they can use.
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"detail": "Authentication required", "code": "auth_required"},
                status=401
            )
        
        access_token = auth_header[7:]
        
        try:
            # Get user data including access_map from SattaBase
            user_data = await sattabase_client.get_me(access_token)
            
            subscription = user_data.get("subscription", {})
            access_map = user_data.get("access_map", {})
            
            return {
                "access_map": access_map,
                "product_slug": "dealercore",
                "plan_name": subscription.get("plan_name"),
                "is_trial": subscription.get("is_trial", False),
                "trial_ends_at": subscription.get("trial_ends_at"),
            }
            
        except SattaBaseAuthError as e:
            return JsonResponse(
                {"detail": e.message, "code": e.code},
                status=e.status_code
            )
    
    @http_get("/check/{key}", response=AccessCheckOutput)
    async def check_access(self, request: HttpRequest, key: str):
        """
        Check if user has specific access key.
        
        Example keys:
        - can_export_csv
        - can_access_dsr
        - max_inventory_items
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"detail": "Authentication required", "code": "auth_required"},
                status=401
            )
        
        access_token = auth_header[7:]
        
        try:
            user_data = await sattabase_client.get_me(access_token)
            access_map = user_data.get("access_map", {})
            
            value = access_map.get(key)
            
            # Determine has_access based on value type
            if value is None:
                has_access = False
            elif isinstance(value, bool):
                has_access = value
            elif isinstance(value, str):
                has_access = value.lower() not in ("false", "no", "0", "", "none")
                # Check for unlimited
                if value.lower() == "unlimited":
                    has_access = True
            elif isinstance(value, (int, float)):
                has_access = value > 0
            else:
                has_access = True
            
            return {
                "key": key,
                "has_access": has_access,
                "value": value,
                "message": f"Access key '{key}' is {'granted' if has_access else 'denied'}"
            }
            
        except SattaBaseAuthError as e:
            return JsonResponse(
                {"detail": e.message, "code": e.code},
                status=e.status_code
            )
    
    @http_get("/subscription", response=SubscriptionOutput)
    async def get_subscription(self, request: HttpRequest):
        """
        Get current user's subscription status.
        
        Returns active status, plan details, and days remaining.
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"detail": "Authentication required", "code": "auth_required"},
                status=401
            )
        
        access_token = auth_header[7:]
        
        try:
            user_data = await sattabase_client.get_me(access_token)
            subscription = user_data.get("subscription", {})
            
            status = subscription.get("status", "unknown")
            is_active = status in ("active", "trialing")
            
            # Calculate days remaining
            days_remaining = None
            current_period_end = subscription.get("current_period_end")
            if current_period_end:
                from datetime import datetime
                try:
                    end_date = datetime.fromisoformat(current_period_end.replace("Z", "+00:00"))
                    now = datetime.now(end_date.tzinfo)
                    days_remaining = max(0, (end_date - now).days)
                except:
                    pass
            
            return {
                "status": status,
                "plan_name": subscription.get("plan_name"),
                "current_period_end": current_period_end,
                "days_remaining": days_remaining,
                "is_active": is_active,
            }
            
        except SattaBaseAuthError as e:
            return JsonResponse(
                {"detail": e.message, "code": e.code},
                status=e.status_code
            )
