"""
DEALERCORE v3.0 — Dealer Context Helper
----------------------------------------
Provides dealer context extraction and validation for multi-tenancy.

This module handles the complex logic of determining which dealer's data
a user can access based on their role:
- Dealers: Can only access their own data
- DSRs/Collectors: Can access data from dealers they're assigned to

Dealer Detection Logic:
1. If JWT has is_dealer=true → User is a dealer
2. If user_id from JWT matches a DealerConfig.username → User is a dealer
3. Otherwise → User is a DSR/Collector (needs dealer assignment)

Usage in controllers:
    from common.dealer_context import get_dealer_context, validate_dsr_access

    @route.get("", response=list[ProductOut])
    async def list_products(self, request):
        dealer_username = await get_dealer_context(request)
        products = Product.objects.filter(dealer_id=dealer_username)
        return [p async for p in products]
"""

import logging
from typing import Optional
from ninja.errors import HttpError

logger = logging.getLogger(__name__)


async def _check_is_dealer_by_user_id(user_id: Optional[str]) -> bool:
    """
    Async check if the user_id matches a DealerConfig record.
    This allows auto-detection of dealers based on their config.
    
    Args:
        user_id: The user_id from JWT (stored as DealerConfig.username)
    
    Returns:
        bool: True if user_id matches a dealer config
    """
    if not user_id:
        logger.debug("_check_is_dealer_by_user_id: No user_id provided")
        return False
    
    try:
        from dealer.models import DealerConfig
        user_id_str = str(user_id)
        exists = await DealerConfig.objects.filter(username=user_id_str).aexists()
        logger.debug(f"_check_is_dealer_by_user_id: Checking user_id={user_id_str}, exists={exists}")
        return exists
    except Exception as e:
        logger.warning(f"_check_is_dealer_by_user_id: Exception checking dealer config: {e}")
        return False


async def get_dealer_context(request, dealer_username: Optional[str] = None) -> str:
    """
    Get the dealer context for the current request.
    
    For Dealers:
        - Returns their own username (request.dealer_username)
        - If dealer_username param is provided, validates it matches their own
    
    For DSRs/Collectors:
        - Uses X-Dealer-Username header (set by frontend dealer selector)
        - Validates they have an active assignment to this dealer
    
    Dealer Detection:
        - First checks request.is_dealer from middleware
        - Then checks if user_id matches a DealerConfig (async DB lookup)
    
    Note: The middleware already extracts the X-Dealer-Username header and
    sets request.dealer_username appropriately. This function provides
    additional validation for DSRs.
    
    Args:
        request: The HTTP request with dealer context attributes
        dealer_username: Optional explicit dealer context override
    
    Returns:
        str: The dealer_username to scope queries by
    
    Raises:
        HttpError 400: If dealer context cannot be determined
        HttpError 403: If user doesn't have access to the specified dealer
    """
    is_dealer = getattr(request, 'is_dealer', False)
    user_dealer_username = getattr(request, 'dealer_username', None)
    # FIX DSR-007: selected_dealer is the X-Dealer-Username header set by
    # the middleware, NOT the removed DsrUser.selected_dealer FK.
    selected_dealer = getattr(request, 'selected_dealer', None)
    user_email = getattr(request, 'user_email', None)
    
    logger.debug(
        f"get_dealer_context: is_dealer={is_dealer}, user_dealer_username={user_dealer_username}, "
        f"selected_dealer={selected_dealer}, user_email={user_email}"
    )
    
    # Use explicit param if provided, otherwise use context from middleware
    effective_dealer = dealer_username or user_dealer_username
    
    # If middleware didn't set is_dealer=True, check via DealerConfig
    # This handles the case where SattaBase doesn't send is_dealer flag
    if not is_dealer and user_dealer_username:
        is_dealer = await _check_is_dealer_by_user_id(user_dealer_username)
        # Update request attribute for downstream use
        if is_dealer:
            request.is_dealer = True
            logger.info(f"Dealer detected via DealerConfig lookup: {user_dealer_username}")
    
    # Case 1: User is a Dealer
    if is_dealer:
        # Dealers can only access their own data
        # The middleware already enforces this, but double-check if param was provided
        if dealer_username and dealer_username != user_dealer_username:
            raise HttpError(
                403, 
                f"Dealer '{user_dealer_username}' cannot access data for dealer '{dealer_username}'"
            )
        
        if not user_dealer_username:
            raise HttpError(400, "Cannot determine dealer context: missing dealer username")
        
        logger.debug(f"get_dealer_context: Returning dealer context for {user_dealer_username}")
        return user_dealer_username
    
    # Case 2: User is DSR/Collector
    # They must have a selected dealer (from X-Dealer-Username header)
    if not effective_dealer:
        raise HttpError(
            400, 
            "Dealer context required. Please select a dealer to work with."
        )
    
    # Validate DSR has access to this dealer
    if selected_dealer:
        await validate_dsr_access(request, selected_dealer)
    
    return effective_dealer


async def validate_dsr_access(request, dealer_username: str) -> bool:
    """
    Validate that a DSR/Collector has an active assignment to the specified dealer.
    
    Args:
        request: The HTTP request with user identity attributes
        dealer_username: The dealer to check access for
    
    Returns:
        bool: True if access is granted
    
    Raises:
        HttpError 403: If DSR doesn't have access to this dealer
    """
    from dsr.invitation_models import DsrDealerAssignment
    
    is_dealer = getattr(request, 'is_dealer', False)
    user_email = getattr(request, 'user_email', None)
    user_dealer_username = getattr(request, 'dealer_username', None)
    
    logger.debug(
        f"validate_dsr_access: is_dealer={is_dealer}, user_email={user_email}, "
        f"dealer_username={dealer_username}, user_dealer_username={user_dealer_username}"
    )
    
    # Dealers always have access to their own data
    if is_dealer:
        logger.debug("validate_dsr_access: User is dealer, access granted")
        return True
    
    # IMPORTANT: If the user's dealer_username matches the requested dealer_username,
    # they might be a dealer whose DealerConfig check failed.
    # Re-check using DealerConfig as a fallback.
    if user_dealer_username and user_dealer_username == dealer_username:
        is_dealer_by_config = await _check_is_dealer_by_user_id(user_dealer_username)
        if is_dealer_by_config:
            logger.info(f"validate_dsr_access: Dealer detected via fallback check for {user_dealer_username}")
            request.is_dealer = True
            return True
    
    if not user_email:
        # Provide a more helpful error message
        logger.warning(
            f"validate_dsr_access: No email in JWT. user_dealer_username={user_dealer_username}, "
            f"dealer_username={dealer_username}. If you're a dealer, ensure DealerConfig exists "
            f"with username='{user_dealer_username}'"
        )
        raise HttpError(
            400, 
            f"Cannot verify access: missing user email in JWT. "
            f"If you're a dealer (user_id={user_dealer_username}), ensure DealerConfig exists "
            f"with username='{user_dealer_username}'. Run: python manage.py seed_data"
        )
    
    # Check for active assignment
    # FIX S-2: filter on `status` DB field, not the `is_active` @property
    # (which raises FieldError when used in a queryset filter).
    has_access = await DsrDealerAssignment.objects.filter(
        dsr__email=user_email,  # DSR is matched by email
        dealer_id=dealer_username,
        status=DsrDealerAssignment.STATUS_ACTIVE,
    ).aexists()
    
    if not has_access:
        raise HttpError(
            403, 
            f"You are not assigned to dealer '{dealer_username}' or your assignment is inactive."
        )
    
    return True


async def get_dealer_choices(request) -> list[str]:
    """
    Get the list of dealers a user can work with.
    
    For Dealers:
        - Returns a list with just their own username
    
    For DSRs/Collectors:
        - Returns list of dealers they have active assignments to
    
    Args:
        request: The HTTP request with user identity attributes
    
    Returns:
        list[str]: List of dealer_username values the user can access
    """
    from dsr.invitation_models import DsrDealerAssignment
    
    is_dealer = getattr(request, 'is_dealer', False)
    user_dealer_username = getattr(request, 'dealer_username', None)
    user_email = getattr(request, 'user_email', None)
    
    # Case 1: User is a Dealer
    if is_dealer:
        if user_dealer_username:
            return [user_dealer_username]
        return []
    
    # Case 2: User is DSR/Collector
    if not user_email:
        return []
    
    # Get all active dealer assignments
    # FIX S-2: filter on `status` DB field, not the `is_active` @property.
    assignments = DsrDealerAssignment.objects.filter(
        dsr__email=user_email,
        status=DsrDealerAssignment.STATUS_ACTIVE,
    ).select_related('dealer').only('dealer_id')
    
    return [assignment.dealer_id async for assignment in assignments]


def get_dealer_context_sync(request, dealer_username: Optional[str] = None) -> str:
    """
    Synchronous version of get_dealer_context for use in sync contexts.
    
    Note: This doesn't validate DSR access. Use the async version when possible.
    """
    is_dealer = getattr(request, 'is_dealer', False)
    user_dealer_username = getattr(request, 'dealer_username', None)
    
    # Use explicit param if provided, otherwise use context from middleware
    effective_dealer = dealer_username or user_dealer_username
    
    if is_dealer:
        if dealer_username and dealer_username != user_dealer_username:
            raise HttpError(
                403, 
                f"Dealer '{user_dealer_username}' cannot access data for dealer '{dealer_username}'"
            )
        
        if not user_dealer_username:
            raise HttpError(400, "Cannot determine dealer context: missing dealer username")
        
        return user_dealer_username
    
    if not effective_dealer:
        raise HttpError(
            400, 
            "Dealer context required. Please select a dealer to work with."
        )
    
    return effective_dealer
