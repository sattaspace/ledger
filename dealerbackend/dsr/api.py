"""
DEALERCORE v3.0 — DSR API Controller
----------------------------------------
Class-based controller using django-ninja-extra.

Endpoints:
  GET    /api/dsrs        → list all DSRs (with active_sales_count)
  GET    /api/dsrs/{id}   → get a single DSR
  POST   /api/dsrs        → create a new DSR / Order Collector
  PATCH  /api/dsrs/{id}   → update a DSR (name, phone, role, parent)
  DELETE /api/dsrs/{id}   → delete a DSR

BUSINESS RULES:
  - active_sales_count: Only counts sales that are NOT fully paid,
    NOT voided, and NOT written off. Previously this included voided
    and written-off sales, inflating DSR workload metrics.
  - collection_sales_count: Counts sales where this DSR is the CURRENT
    collector (dsr field), regardless of who originally made the sale.
  - original_sales_count: Counts sales where this DSR MADE the sale
    (original_dsr field), for sales attribution/performance.
"""

from django.db.models import Count, Q

from ninja_extra import api_controller, route
from ninja.errors import HttpError

from users.models import DsrUser
from dsr.schemas import CreateDSRIn, DSROut, UpdateDSRIn
from dsr.invitation_models import DsrDealerAssignment
from sales.models import SaleRecord

# ─── Reusable Filters ──────────────────────────────────────
# Active sales = not voided, not written-off, not fully paid
# These filters ensure DSR workload metrics are accurate.

# For use in annotate() — prefix with "sales__" for reverse FK resolution
COLLECTION_SALES_FOR_DSR = Q(
    sales__is_voided=False,
    sales__is_closed_with_due=False,
    sales__collection_status__in=[
        SaleRecord.STATUS_PENDING,
        SaleRecord.STATUS_PARTIAL,
    ],
)


@api_controller("/dsrs", tags=["DSR"])
class DSRController:
    """DSR API Controller with dealer-scoped data isolation.
    
    All DSR queries are filtered by the authenticated dealer's context.
    DSRs are linked to dealers via DsrDealerAssignment junction table.
    """
    
    # Maximum records per page to prevent memory exhaustion
    MAX_PAGE_LIMIT = 1000

    def _validate_pagination(self, limit: int, offset: int) -> None:
        """Common pagination validation to prevent memory exhaustion."""
        if limit > self.MAX_PAGE_LIMIT:
            raise HttpError(400, f"Limit cannot exceed {self.MAX_PAGE_LIMIT}. Use pagination with offset.")
        if limit < 1:
            raise HttpError(400, "Limit must be at least 1.")
        if offset < 0:
            raise HttpError(400, "Offset cannot be negative.")
    
    def _get_dealer_username(self, request) -> str:
        """Extract dealer username from request context."""
        dealer_username = getattr(request, 'dealer_username', None)
        if not dealer_username:
            raise HttpError(401, "Authentication required - dealer context not found")
        return dealer_username

    @route.get("", response=list[DSROut], summary="List all DSRs for current dealer")
    async def list_dsrs(self, request, limit: int = 100, offset: int = 0):
        """Return DSRs assigned to the current dealer with annotated active_sales_count.
        
        DSRs are filtered by DsrDealerAssignment for the authenticated dealer.
        active_sales_count excludes voided, written-off, and fully paid sales.
        
        Query Parameters:
            limit: Max records to return (default: 100, max: 1000)
            offset: Number of records to skip (for pagination)
        """
        self._validate_pagination(limit, offset)
        dealer_username = self._get_dealer_username(request)
        
        # Get DSR IDs that have an active assignment with this dealer
        assigned_dsr_ids = DsrDealerAssignment.objects.filter(
            dealer__username=dealer_username,
            status=DsrDealerAssignment.STATUS_ACTIVE
        ).values_list('dsr_id', flat=True)
        
        # Filter DsrUsers by the assignment
        qs = DsrUser.objects.filter(
            id__in=assigned_dsr_ids
        ).annotate(
            active_sales_count=Count(
                "sales",
                filter=Q(
                    sales__is_voided=False,
                    sales__is_closed_with_due=False,
                    sales__collection_status__in=[
                        SaleRecord.STATUS_PENDING,
                        SaleRecord.STATUS_PARTIAL,
                    ],
                ),
            ),
        ).order_by("full_name")[offset:offset+limit]
        
        # Build a map of dsr_id → {role, parent_dsr_id, parent_dsr_name} from assignments
        assignment_info = {}
        async for assignment in DsrDealerAssignment.objects.filter(
            dealer__username=dealer_username,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).select_related('parent_dsr'):
            assignment_info[assignment.dsr_id] = {
                'role': assignment.role,
                'parent_dsr_id': str(assignment.parent_dsr_id) if assignment.parent_dsr_id else None,
                'parent_dsr_name': (assignment.parent_dsr.full_name or assignment.parent_dsr.email) if assignment.parent_dsr else "",
            }

        results = []
        async for dsr in qs:
            info = assignment_info.get(dsr.id, {})
            results.append(
                DSROut(
                    id=str(dsr.id),
                    name=dsr.full_name or dsr.email,
                    phone=dsr.phone,
                    active_sales_count=dsr.active_sales_count,
                    role=info.get('role', "DSR"),
                    parent_dsr_id=info.get('parent_dsr_id'),
                    parent_dsr_name=info.get('parent_dsr_name', ""),
                )
            )
        return results

    @route.get("{dsr_id}", response=DSROut, summary="Get a DSR")
    async def get_dsr(self, request, dsr_id: str):
        """Return a single DSR by ID with active_sales_count.
        
        Only returns DSRs that are assigned to the current dealer.
        """
        dealer_username = self._get_dealer_username(request)
        
        # Verify DSR is assigned to this dealer
        is_assigned = await DsrDealerAssignment.objects.filter(
            dsr_id=dsr_id,
            dealer__username=dealer_username,
            status=DsrDealerAssignment.STATUS_ACTIVE
        ).aexists()
        
        if not is_assigned:
            raise HttpError(404, f"DSR with id '{dsr_id}' not found or not assigned to you")
        
        try:
            dsr = await DsrUser.objects.annotate(
                active_sales_count=Count(
                    "sales",
                    filter=Q(
                        sales__is_voided=False,
                        sales__is_closed_with_due=False,
                        sales__collection_status__in=[
                            SaleRecord.STATUS_PENDING,
                            SaleRecord.STATUS_PARTIAL,
                        ],
                    ),
                ),
            ).aget(id=dsr_id)
        except DsrUser.DoesNotExist:
            raise HttpError(404, f"DSR with id '{dsr_id}' not found")
        # Get role and parent info from assignment
        assignment = await DsrDealerAssignment.objects.filter(
            dsr_id=dsr_id,
            dealer__username=dealer_username,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).select_related('parent_dsr').afirst()

        return DSROut(
            id=str(dsr.id),
            name=dsr.full_name or dsr.email,
            phone=dsr.phone,
            active_sales_count=dsr.active_sales_count,
            role=assignment.role if assignment else "DSR",
            parent_dsr_id=str(assignment.parent_dsr_id) if assignment and assignment.parent_dsr_id else None,
            parent_dsr_name=(assignment.parent_dsr.full_name or assignment.parent_dsr.email) if assignment and assignment.parent_dsr else "",
        )

    # NOTE: Manual DSR creation endpoint REMOVED.
    # DSRs must be invited via /dealer/dsr/invite endpoint (see dealer_dsr_api.py).
    # This ensures all DSRs are properly linked to DsrUser accounts through the invitation flow.
    # Legacy DSRs created before this change may still exist but won't have login access.

    @route.patch("{dsr_id}", response=DSROut, summary="Update a DSR")
    async def update_dsr(self, request, dsr_id: str, payload: UpdateDSRIn):
        """Partial update on a DSR — name, phone, role, parent reassignment.
        
        Only allows updates to DSRs assigned to the current dealer.
        """
        dealer_username = self._get_dealer_username(request)
        
        # Verify DSR is assigned to this dealer
        is_assigned = await DsrDealerAssignment.objects.filter(
            dsr_id=dsr_id,
            dealer__username=dealer_username,
            status=DsrDealerAssignment.STATUS_ACTIVE
        ).aexists()
        
        if not is_assigned:
            raise HttpError(404, f"DSR with id '{dsr_id}' not found or not assigned to you")
        
        try:
            dsr = await DsrUser.objects.aget(id=dsr_id)
        except DsrUser.DoesNotExist:
            raise HttpError(404, f"DSR with id '{dsr_id}' not found")

        update_data = payload.model_dump(exclude_unset=True)

        # Remap 'name' → 'full_name' for DsrUser model
        if "name" in update_data:
            update_data["full_name"] = update_data.pop("name")

        # Handle parent_dsr_id → update on DsrDealerAssignment, not DsrUser
        if "parent_dsr_id" in update_data:
            parent_id = update_data["parent_dsr_id"]
            # Find the active assignment for this DSR-dealer pair
            assignment = await DsrDealerAssignment.objects.filter(
                dsr_id=dsr_id,
                dealer__username=dealer_username,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            ).afirst()
            if not assignment:
                raise HttpError(404, f"No active assignment found for DSR '{dsr_id}'")

            if parent_id:
                # Prevent self-referential parent assignment (circular reference)
                if parent_id == dsr_id:
                    raise HttpError(
                        400, 
                        f"DSR cannot be its own parent. Choose a different parent DSR."
                    )
                # Prevent circular hierarchy (parent cannot be a descendant)
                if await self._is_circular_parent(dsr_id, parent_id, dealer_username):
                    raise HttpError(
                        400,
                        f"Cannot set parent: would create circular hierarchy. "
                        f"The selected parent is already a subordinate of this DSR."
                    )
                try:
                    parent = await DsrUser.objects.aget(id=parent_id)
                    # Verify parent DSR is assigned to this dealer
                    parent_is_assigned = await DsrDealerAssignment.objects.filter(
                        dsr=parent,
                        dealer__username=dealer_username,
                        status=DsrDealerAssignment.STATUS_ACTIVE
                    ).aexists()
                    if not parent_is_assigned:
                        raise HttpError(400, f"Parent DSR with id '{parent_id}' is not assigned to you")
                    assignment.parent_dsr = parent
                except DsrUser.DoesNotExist:
                    raise HttpError(400, f"Parent DSR with id '{parent_id}' not found")
            else:
                assignment.parent_dsr = None

            await assignment.asave(update_fields=["parent_dsr", "updated_at"])
            # Remove from update_data so it doesn't get set on DsrUser
            del update_data["parent_dsr_id"]

        for field, value in update_data.items():
            setattr(dsr, field, value)
        await dsr.asave(update_fields=list(update_data.keys()) + ["updated_at"])

        # Return with active_sales_count (excluding voided/written-off)
        await dsr.arefresh_from_db()
        active_count = await dsr.sales.filter(
            is_voided=False,
            is_closed_with_due=False,
        ).exclude(
            collection_status=SaleRecord.STATUS_FULLY_PAID
        ).acount()
        # Get role and parent info from assignment
        assignment = await DsrDealerAssignment.objects.filter(
            dsr_id=dsr_id,
            dealer__username=dealer_username,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).select_related('parent_dsr').afirst()

        return DSROut(
            id=str(dsr.id),
            name=dsr.full_name or dsr.email,
            phone=dsr.phone,
            active_sales_count=active_count,
            role=assignment.role if assignment else "DSR",
            parent_dsr_id=str(assignment.parent_dsr_id) if assignment and assignment.parent_dsr_id else None,
            parent_dsr_name=(assignment.parent_dsr.full_name or assignment.parent_dsr.email) if assignment and assignment.parent_dsr else "",
        )

    @route.delete("{dsr_id}", summary="Delete a DSR")
    async def delete_dsr(self, request, dsr_id: str):
        """Delete a DSR. Sales linked to this DSR will have dsr set to NULL (SET_NULL).
        Note: original_dsr on sales will also be set to NULL.
        
        Only allows deletion of DSRs assigned to the current dealer.
        """
        dealer_username = self._get_dealer_username(request)
        
        # Verify DSR is assigned to this dealer
        assignment = await DsrDealerAssignment.objects.filter(
            dsr_id=dsr_id,
            dealer__username=dealer_username
        ).afirst()
        
        if not assignment:
            raise HttpError(404, f"DSR with id '{dsr_id}' not found or not assigned to you")
        
        try:
            dsr = await DsrUser.objects.aget(id=dsr_id)
        except DsrUser.DoesNotExist:
            raise HttpError(404, f"DSR with id '{dsr_id}' not found")
        
        # Delete the assignment first
        await assignment.adelete()
        
        # If DsrUser has no other assignments, delete the user entirely
        other_assignments = await DsrDealerAssignment.objects.filter(dsr=dsr).aexists()
        if not other_assignments:
            await dsr.adelete()
        
        return {"message": f"DSR '{dsr.full_name or dsr.email}' removed from your team successfully"}

    # ─── Helpers ────────────────────────────────────────

    async def _is_circular_parent(self, dsr_id: str, potential_parent_id: str, dealer_username: str) -> bool:
        """Check if assigning potential_parent_id as parent of dsr_id would create
        a circular hierarchy (where the parent is already a descendant of dsr).
        
        After DSR→DsrUser merge, parent relationships are per-dealer via
        DsrDealerAssignment.parent_dsr, not on the user model itself.
        This prevents A → B → C → A type cycles in the DSR hierarchy.
        """
        current_id = potential_parent_id
        visited = set()
        max_depth = 100  # Safety limit to prevent infinite loops
        
        for _ in range(max_depth):
            if not current_id:
                return False
            if current_id == dsr_id:
                return True  # Found cycle!
            if current_id in visited:
                return True  # Already visited - cycle detected
            visited.add(current_id)
            
            # Walk up the parent chain via DsrDealerAssignment for this dealer
            parent_id = await DsrDealerAssignment.objects.filter(
                dsr_id=current_id,
                dealer__username=dealer_username,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            ).values_list('parent_dsr_id', flat=True).afirst()
            
            if not parent_id:
                return False
            current_id = str(parent_id)
        
        return False  # Hit depth limit, assume safe


