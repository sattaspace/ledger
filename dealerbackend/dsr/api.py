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

from django.db.models import Count, Q, Max

from ninja_extra import api_controller, route
from ninja.errors import HttpError

from dealercore.async_db import async_aggregate, async_exists
from dsr.models import DSR
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
        
        # Filter DSRs by the assignment
        qs = DSR.objects.filter(
            id__in=assigned_dsr_ids
        ).prefetch_related("subordinates").annotate(
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
        ).order_by("name")[offset:offset+limit]
        
        results = []
        async for dsr in qs:
            results.append(
                DSROut(
                    id=dsr.id,
                    name=dsr.name,
                    phone=dsr.phone,
                    active_sales_count=dsr.active_sales_count,
                    role=dsr.role,
                    parent_dsr_id=dsr.parent_dsr_id,
                    parent_dsr_name=dsr.parent_dsr_name,
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
            dsr = await DSR.objects.annotate(
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
        except DSR.DoesNotExist:
            raise HttpError(404, f"DSR with id '{dsr_id}' not found")
        return DSROut(
            id=dsr.id,
            name=dsr.name,
            phone=dsr.phone,
            active_sales_count=dsr.active_sales_count,
            role=dsr.role,
            parent_dsr_id=dsr.parent_dsr_id,
            parent_dsr_name=dsr.parent_dsr_name,
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
            dsr = await DSR.objects.aget(id=dsr_id)
        except DSR.DoesNotExist:
            raise HttpError(404, f"DSR with id '{dsr_id}' not found")

        update_data = payload.model_dump(exclude_unset=True)

        # Handle parent_dsr_id → resolve parent_dsr_name
        if "parent_dsr_id" in update_data:
            parent_id = update_data["parent_dsr_id"]
            if parent_id:
                # BUG FIX: Prevent self-referential parent assignment (circular reference)
                if parent_id == dsr_id:
                    raise HttpError(
                        400, 
                        f"DSR cannot be its own parent. Choose a different parent DSR."
                    )
                # BUG FIX: Prevent circular hierarchy (parent cannot be a descendant)
                if await self._is_circular_parent(dsr_id, parent_id):
                    raise HttpError(
                        400,
                        f"Cannot set parent: would create circular hierarchy. "
                        f"The selected parent is already a subordinate of this DSR."
                    )
                try:
                    parent = await DSR.objects.aget(id=parent_id)
                    # Verify parent DSR is assigned to this dealer
                    parent_is_assigned = await DsrDealerAssignment.objects.filter(
                        dsr=parent,
                        dealer__username=dealer_username,
                        status=DsrDealerAssignment.STATUS_ACTIVE
                    ).aexists()
                    if not parent_is_assigned:
                        raise HttpError(400, f"Parent DSR with id '{parent_id}' is not assigned to you")
                    update_data["parent_dsr_name"] = parent.name
                    update_data["parent_dsr"] = parent
                except DSR.DoesNotExist:
                    raise HttpError(400, f"Parent DSR with id '{parent_id}' not found")
            else:
                update_data["parent_dsr_name"] = ""
                update_data["parent_dsr"] = None
            # Remove raw FK id from update_data (use the model instance instead)
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
        return DSROut(
            id=dsr.id,
            name=dsr.name,
            phone=dsr.phone,
            active_sales_count=active_count,
            role=dsr.role,
            parent_dsr_id=dsr.parent_dsr_id,
            parent_dsr_name=dsr.parent_dsr_name,
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
            dsr = await DSR.objects.aget(id=dsr_id)
        except DSR.DoesNotExist:
            raise HttpError(404, f"DSR with id '{dsr_id}' not found")
        
        # Delete the assignment first
        await assignment.adelete()
        
        # If DSR has no other assignments, delete the DSR entirely
        other_assignments = await DsrDealerAssignment.objects.filter(dsr=dsr).aexists()
        if not other_assignments:
            await dsr.adelete()
        
        return {"message": f"DSR '{dsr.name}' removed from your team successfully"}

    # ─── Helpers ────────────────────────────────────────

    async def _is_circular_parent(self, dsr_id: str, potential_parent_id: str) -> bool:
        """Check if assigning potential_parent_id as parent of dsr_id would create
        a circular hierarchy (where the parent is already a descendant of dsr).
        
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
            
            try:
                parent = await DSR.objects.aget(id=current_id)
                current_id = parent.parent_dsr_id
            except DSR.DoesNotExist:
                return False
        
        return False  # Hit depth limit, assume safe

    async def _generate_id(self) -> str:
        """Generate a unique DSR ID (format: dsr-{n})."""
        prefix = "dsr"
        max_retries = 5
        for attempt in range(max_retries):
            result = await async_aggregate(
                DSR.objects.filter(id__startswith=prefix),
                _max=Max("id"),
            )
            last = result.get("_max")

            num = 1
            if last:
                try:
                    num = int(last.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    num = 1

            num += attempt
            candidate_id = f"{prefix}-{num}"

            exists = await async_exists(
                DSR.objects.filter(id=candidate_id),
            )
            if not exists:
                return candidate_id

        import time
        return f"{prefix}-{int(time.time() * 1000)}"
