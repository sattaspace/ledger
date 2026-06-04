"""
DEALERCORE v3.0 — DSR API Router
-----------------------------------
Django Ninja async endpoints for DSR management.

Endpoints:
  GET  /api/dsrs  → list all DSRs (with active_sales_count)
  POST /api/dsrs  → create a new DSR / Order Collector
"""

from django.db.models import Count, Q, F
from ninja import Router

from dsr.models import DSR
from dsr.schemas import CreateDSRIn, DSROut
from sales.models import SaleRecord

router = Router(tags=["DSR"])


@router.get("", response=list[DSROut], summary="List all DSRs")
async def list_dsrs(request):
    """Return all DSRs with annotated active_sales_count
    (count of sales with collection_status != 'Fully Paid')."""
    qs = DSR.objects.prefetch_related("subordinates").annotate(
        active_sales_count=Count(
            "sales",
            filter=~Q(sales__collection_status=SaleRecord.STATUS_FULLY_PAID),
        ),
    )
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


@router.post("", response=DSROut, summary="Create a DSR")
async def create_dsr(request, payload: CreateDSRIn):
    """Create a new DSR or Order Collector."""
    parent_dsr_name = ""
    if payload.parent_dsr_id:
        try:
            parent = await DSR.objects.aget(id=payload.parent_dsr_id)
            parent_dsr_name = parent.name
        except DSR.DoesNotExist:
            pass

    dsr = await DSR.objects.acreate(
        id=await _generate_id(),
        name=payload.name,
        phone=payload.phone,
        role=payload.role or "DSR",
        parent_dsr_id=payload.parent_dsr_id,
        parent_dsr_name=parent_dsr_name,
    )

    return DSROut(
        id=dsr.id,
        name=dsr.name,
        phone=dsr.phone,
        active_sales_count=0,
        role=dsr.role,
        parent_dsr_id=dsr.parent_dsr_id,
        parent_dsr_name=dsr.parent_dsr_name,
    )


# ─── Helpers ────────────────────────────────────────────

async def _generate_id() -> str:
    """Generate a unique DSR ID (format: dsr-{n})."""
    from django.db.models import Max

    last = await DSR.objects.all().aaggregate(_max=Max("id"))["_max"]
    if last:
        try:
            num = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    return f"dsr-{num}"
