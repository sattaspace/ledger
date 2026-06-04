"""
DEALERCORE v3.0 — Reports API Router
---------------------------------------
Django Ninja async endpoints for computed reports.

Endpoints:
  GET   /api/reports/summary              → dashboard summary
  POST  /api/reports/ai-reconciliation    → AI-generated reconciliation text
"""

from decimal import Decimal
from typing import List

from django.db.models import Sum, Count, F, Q, DecimalField
from django.db.models.functions import Coalesce
from ninja import Router

from inventory.models import Product, RestockRecord
from sales.models import SaleRecord, CreditPayment
from dsr.models import DSR
from reports.schemas import (
    AiReconciliationOut,
    DsrPerformanceRow,
    LowStockItem,
    ProductPerformanceRow,
    SummaryOut,
)

router = Router(tags=["Reports"])


@router.get("summary", response=SummaryOut, summary="Dashboard summary")
async def get_summary(request):
    """Compute and return full dashboard summary data.
    Aggregates revenue, COGS, gross profit, credit status,
    low stock alerts, DSR performance, and product performance."""

    # ── Revenue & COGS ──
    totals = await SaleRecord.objects.aaggregate(
        revenue=Coalesce(Sum("total_amount"), Decimal("0")),
        cogs=Coalesce(
            Sum(
                "quantity",
            ),
            Decimal("0"),
        ),
    )

    # ── Credit metrics ──
    credit_stats = await SaleRecord.objects.filter(
        payment_type=SaleRecord.PAYMENT_CREDIT
    ).aaggregate(
        credit_pending=Coalesce(
            Sum("total_amount") - Sum("amount_paid"), Decimal("0")
        ),
        credit_collected=Coalesce(Sum("amount_paid"), Decimal("0")),
    )

    # ── Gross profit (revenue - COGS using restock cost_price weighted avg) ──
    cogs_total = await RestockRecord.objects.aaggregate(
        total=Coalesce(Sum("total_cost"), Decimal("0"))
    )
    cogs = cogs_total["total"]
    revenue = totals["revenue"]
    gross_profit = revenue - cogs

    # ── Low stock items ──
    low_stock_qs = Product.objects.filter(stock__lt=F("min_stock_alert"))
    low_stock_items: List[LowStockItem] = []
    async for p in low_stock_qs:
        low_stock_items.append(
            LowStockItem(
                id=p.id,
                name=p.name,
                stock=p.stock,
                min_stock_alert=p.min_stock_alert,
                category=p.category,
            )
        )

    # ── DSR performance ──
    dsr_performance: List[DsrPerformanceRow] = []
    dsr_qs = DSR.objects.all()
    async for dsr in dsr_qs:
        sales_agg = await SaleRecord.objects.filter(dsr=dsr).aaggregate(
            total_sales=Coalesce(Sum("total_amount"), Decimal("0")),
            collected=Coalesce(Sum("amount_paid"), Decimal("0")),
            pending=Coalesce(
                Sum("total_amount") - Sum("amount_paid"), Decimal("0")
            ),
            count=Count("id"),
        )
        dsr_performance.append(
            DsrPerformanceRow(
                id=dsr.id,
                name=dsr.name,
                role=dsr.role,
                parent_dsr_id=dsr.parent_dsr_id,
                parent_dsr_name=dsr.parent_dsr_name,
                total_sales=sales_agg["total_sales"],
                collected=sales_agg["collected"],
                pending=sales_agg["pending"],
                count=sales_agg["count"],
            )
        )

    # ── Product performance ──
    from django.db.models import F
    product_agg = (
        SaleRecord.objects.values("product_name")
        .annotate(quantity=Sum("quantity"), total=Sum("total_amount"))
        .order_by("-total")
    )
    product_performance: List[ProductPerformanceRow] = []
    async for row in product_agg:
        product_performance.append(
            ProductPerformanceRow(
                name=row["product_name"],
                quantity=row["quantity"],
                total=row["total"],
            )
        )

    # ── Counts ──
    total_sales_count = await SaleRecord.objects.acount()
    total_products_count = await Product.objects.acount()

    return SummaryOut(
        revenue=revenue,
        cogs=cogs,
        gross_profit=gross_profit,
        credit_pending=credit_stats["credit_pending"],
        credit_collected=credit_stats["credit_collected"],
        low_stock_count=len(low_stock_items),
        low_stock_items=low_stock_items,
        dsr_performance=dsr_performance,
        product_performance=product_performance,
        total_sales_count=total_sales_count,
        total_products_count=total_products_count,
    )


@router.post(
    "ai-reconciliation",
    response=AiReconciliationOut,
    summary="AI-powered reconciliation",
)
async def get_ai_reconciliation(request):
    """Generate an AI-powered reconciliation report.
    In production, this would call an LLM (e.g., Gemini/GPT) with
    the current sales, payments, and credit data as context.

    For now, returns a placeholder markdown string.
    """
    # ── Gather data for AI context ──
    pending_sales = await SaleRecord.objects.filter(
        collection_status__in=[
            SaleRecord.STATUS_PENDING,
            SaleRecord.STATUS_PARTIAL,
        ]
    ).acount()

    total_pending = await SaleRecord.objects.filter(
        collection_status__in=[
            SaleRecord.STATUS_PENDING,
            SaleRecord.STATUS_PARTIAL,
        ]
    ).aaggregate(
        amount=Coalesce(Sum("total_amount") - Sum("amount_paid"), Decimal("0"))
    )

    placeholder = (
        f"# AI Reconciliation Report\n\n"
        f"## Outstanding Credit Summary\n\n"
        f"- **Pending/Partial sales count:** {pending_sales}\n"
        f"- **Total outstanding amount:** {total_pending['amount']}\n\n"
        f"## Notes\n\n"
        f"This is a placeholder response. In production, integrate with "
        f"your preferred LLM (Gemini, GPT, etc.) to generate a detailed "
        f"reconciliation analysis with recommendations for follow-up actions "
        f"on overdue payments.\n"
    )

    return AiReconciliationOut(text=placeholder)
