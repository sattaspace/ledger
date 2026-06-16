"""
DEALERCORE v3.0 — Reports API Controller
-------------------------------------------
Class-based controller using django-ninja-extra.

Endpoints:
  GET   /api/reports/summary              → dashboard summary
  GET   /api/reports/customer-due         → customer-wise due report
  GET   /api/reports/vehicle-due          → vehicle-wise due report
  GET   /api/reports/dsr-due              → DSR/collector-wise due report
  POST  /api/reports/ai-reconciliation    → AI-generated reconciliation text

FINANCIAL REPORTING RULES:
  - Revenue excludes written-off sales (is_closed_with_due=True) and
    voided sales (is_voided=True) to accurately reflect collectible income.
  - Written-off amounts report only the OUTSTANDING balance (total - paid),
    not the full total_amount, to avoid double-counting partial payments.
  - COGS includes all restock costs regardless of sale status.
  - Gross Profit = Revenue (excl. written-off & voided) - COGS (all).
  - DSR performance excludes written-off and voided sales.
  - Due reports (customer/vehicle/DSR) show net_amount after returns and
    balance_due = net_amount - amount_paid.
  - Voided sales are excluded from ALL due and revenue calculations.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Union

from django.db.models import Sum, Count, F, Q
from django.db.models.functions import Coalesce

from ninja_extra import api_controller, route
from ninja.errors import HttpError

from dealercore.async_db import async_aggregate
from common.dealer_context import get_dealer_context
from dealer.models import DealerConfig
from inventory.models import Product, RestockRecord
from sales.models import SaleRecord, CreditPayment
from users.models import DsrUser
from dsr.invitation_models import DsrDealerAssignment
from reports.schemas import (
    AiReconciliationOut,
    CustomerDueRow,
    CustomerDueSale,
    DealerInfo,
    DsrDueRow,
    DsrDueSale,
    DsrPerformanceRow,
    DueReportOut,
    LowStockItem,
    ProductPerformanceRow,
    SummaryOut,
    VehicleDueRow,
    VehicleDueSale,
)


# ─── Reusable Queryset Filters ──────────────────────────────────────────
# These filters ensure consistent treatment of written-off and voided sales
# across all report calculations.

# Direct filters — for use on SaleRecord.objects directly
ACTIVE_SALES_FILTER = Q(is_closed_with_due=False, is_voided=False)
ACTIVE_CREDIT_FILTER = Q(
    payment_type=SaleRecord.PAYMENT_CREDIT,
    is_closed_with_due=False,
    is_voided=False,
)
WRITTEN_OFF_CREDIT_FILTER = Q(
    payment_type=SaleRecord.PAYMENT_CREDIT,
    is_closed_with_due=True,
)

# Due filters — for pending/partial credit sales that are still active
DUE_CREDIT_FILTER = Q(
    payment_type=SaleRecord.PAYMENT_CREDIT,
    is_closed_with_due=False,
    is_voided=False,
    collection_status__in=[SaleRecord.STATUS_PENDING, SaleRecord.STATUS_PARTIAL],
)

# Relation-aware filters — for use on DsrUser.objects via sales__ reverse FK
DSR_ACTIVE_SALES_FILTER = Q(
    sales__is_closed_with_due=False,
    sales__is_voided=False,
)


def _dealer_info(dealer) -> Optional[DealerInfo]:
    """Helper to build DealerInfo from a DealerConfig instance."""
    if not dealer:
        return None
    return DealerInfo(
        business_name=dealer.business_name,
        address=dealer.address,
        phone_number=dealer.phone_number,
        email=dealer.email,
        gst_number=dealer.gst_number,
        google_map_url=dealer.google_map_url,
        communication_number=dealer.communication_number,
        default_currency=dealer.default_currency,
        default_locale=dealer.default_locale,
    )


@api_controller("/reports", tags=["Reports"])
class ReportsController:
    # Maximum records per page to prevent memory exhaustion in report detail views
    MAX_PAGE_LIMIT = 1000

    def _validate_pagination(self, limit: int, offset: int) -> None:
        """Common pagination validation to prevent memory exhaustion."""
        if limit > self.MAX_PAGE_LIMIT:
            raise HttpError(400, f"Limit cannot exceed {self.MAX_PAGE_LIMIT}. Use pagination with offset.")
        if limit < 1:
            raise HttpError(400, "Limit must be at least 1.")
        if offset < 0:
            raise HttpError(400, "Offset cannot be negative.")

    @route.get("summary", response=SummaryOut, summary="Dashboard summary")
    async def get_summary(self, request):
        """Compute and return full dashboard summary data.

        FINANCIAL MODEL:
          - Revenue: Sum of total_amount for ACTIVE sales only (excl. written-off & voided)
          - COGS: Sum of total_cost for ALL restock records (costs incurred)
          - Gross Profit: Revenue - COGS
          - Credit Pending: Outstanding on active credit sales (net of returns)
          - Credit Collected: amount_paid on active credit sales
          - Written-off Outstanding: Uncollected balance on written-off sales

        Dealer Context:
            Uses X-Dealer-Username header to scope all data to the current dealer.
        """
        # Get dealer context from request (set by middleware)
        dealer_username = await get_dealer_context(request)

        # ── Fetch dealer info ──
        dealer_info: Optional[DealerInfo] = None
        try:
            dealer = await DealerConfig.objects.aget(username=dealer_username)
            if dealer:
                dealer_info = _dealer_info(dealer)
        except DealerConfig.DoesNotExist:
            pass

        # ── Revenue (excludes written-off & voided sales) ──
        # All queries are filtered by dealer_id for multi-tenancy
        active_totals = await async_aggregate(
            SaleRecord.objects.filter(ACTIVE_SALES_FILTER, dealer_id=dealer_username),
            revenue=Coalesce(Sum("total_amount"), Decimal("0")),
        )
        revenue = active_totals["revenue"]

        # ── Written-off outstanding (only the uncollected portion) ──
        # Previously this reported full total_amount which double-counted
        # partial payments already collected before write-off.
        written_off_stats = await async_aggregate(
            SaleRecord.objects.filter(is_closed_with_due=True, is_voided=False, dealer_id=dealer_username),
            written_off_total=Coalesce(Sum("total_amount"), Decimal("0")),
            written_off_paid=Coalesce(Sum("amount_paid"), Decimal("0")),
        )
        written_off_amount = written_off_stats["written_off_total"]
        written_off_outstanding = written_off_stats["written_off_total"] - written_off_stats["written_off_paid"]

        # ── Credit metrics (active credit sales only) ──
        # Use net_amount (after returns) for accurate pending calculation:
        # pending = total_amount - return_total_amount - amount_paid
        active_credit_stats = await async_aggregate(
            SaleRecord.objects.filter(ACTIVE_CREDIT_FILTER, dealer_id=dealer_username),
            credit_pending=Coalesce(
                Sum("total_amount") - Sum("return_total_amount") - Sum("amount_paid"), Decimal("0")
            ),
            credit_collected=Coalesce(Sum("amount_paid"), Decimal("0")),
        )

        # Count of active credit invoices with outstanding balance (for badge)
        credit_pending_count = await SaleRecord.objects.filter(
            DUE_CREDIT_FILTER, dealer_id=dealer_username
        ).acount()

        # ── COGS (from ALL restock records — costs were incurred) ──
        cogs_total = await async_aggregate(
            RestockRecord.objects.filter(dealer_id=dealer_username),
            total=Coalesce(Sum("total_cost"), Decimal("0"))
        )
        cogs = cogs_total["total"]
        gross_profit = revenue - cogs

        # ── Low stock items ──
        low_stock_qs = Product.objects.filter(stock__lt=F("min_stock_alert"), dealer_id=dealer_username)
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

        # ── DSR performance (excludes written-off & voided sales) ──
        # FIX DSR-004: Role was removed from the DSR model. It is now
        # per-dealer via DsrDealerAssignment.role. We build a lookup map
        # from the dealer's active assignments so each DSR row can include
        # their role for THIS dealer (a DSR may have different roles with
        # different dealers). Parent DSR info also comes from the assignment
        # now, since the hierarchy is per-dealer.
        active_assignments = DsrDealerAssignment.objects.filter(
            dealer_id=dealer_username,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).select_related("parent_dsr")
        assignment_map: dict = {}  # dsr_id → {role, parent_dsr_id, parent_dsr_name}
        async for assignment in active_assignments:
            if assignment.dsr_id:
                assignment_map[assignment.dsr_id] = {
                    "role": assignment.role,
                    "parent_dsr_id": (
                        str(assignment.parent_dsr_id) if assignment.parent_dsr_id else None
                    ),
                    "parent_dsr_name": (
                        assignment.parent_dsr.full_name if assignment.parent_dsr else ""
                    ),
                }

        dsr_performance: List[DsrPerformanceRow] = []
        async for dsr in DsrUser.objects.filter(id__in=assignment_map.keys()).annotate(
            total_sales=Coalesce(
                Sum("sales__total_amount", filter=DSR_ACTIVE_SALES_FILTER, default=Decimal("0")),
                Decimal("0"),
            ),
            collected=Coalesce(
                Sum("sales__amount_paid", filter=DSR_ACTIVE_SALES_FILTER, default=Decimal("0")),
                Decimal("0"),
            ),
            count=Count("sales", filter=DSR_ACTIVE_SALES_FILTER),
        ).order_by("-total_sales"):
            pending = dsr.total_sales - dsr.collected
            assignment_info = assignment_map.get(dsr.id, {})
            dsr_performance.append(
                DsrPerformanceRow(
                    id=str(dsr.id),
                    name=dsr.full_name or dsr.email,
                    role=assignment_info.get("role", DsrUser.ROLE_DSR),
                    parent_dsr_id=assignment_info.get("parent_dsr_id"),
                    parent_dsr_name=assignment_info.get("parent_dsr_name", ""),
                    total_sales=dsr.total_sales,
                    collected=dsr.collected,
                    pending=pending,
                    count=dsr.count,
                )
            )

        # ── Product performance (excludes written-off & voided sales from total) ──
        product_agg = (
            SaleRecord.objects.filter(ACTIVE_SALES_FILTER, dealer_id=dealer_username)
            .values("product_name")
            .annotate(
                quantity=Sum("quantity"),
                total=Sum("total_amount"),
            )
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
        total_sales_count = await SaleRecord.objects.filter(dealer_id=dealer_username).acount()
        total_products_count = await Product.objects.filter(dealer_id=dealer_username).acount()

        return SummaryOut(
            revenue=revenue,
            cogs=cogs,
            gross_profit=gross_profit,
            credit_pending=active_credit_stats["credit_pending"],
            credit_pending_count=credit_pending_count,
            credit_collected=active_credit_stats["credit_collected"],
            written_off_amount=written_off_amount,
            written_off_outstanding=written_off_outstanding,
            low_stock_count=len(low_stock_items),
            low_stock_items=low_stock_items,
            dsr_performance=dsr_performance,
            product_performance=product_performance,
            total_sales_count=total_sales_count,
            total_products_count=total_products_count,
            dealer=dealer_info,
        )

    @route.get("customer-due", response=DueReportOut, summary="Customer-wise due report")
    async def get_customer_due(self, request):
        """Customer-wise breakdown of pending credit collections.

        Groups all active (non-voided, non-written-off) credit sales with
        outstanding balances by customer. Shows net_amount after returns
        and balance_due = net_amount - amount_paid.

        Suitable for print: includes dealer header, generation timestamp.

        Dealer Context:
            Uses X-Dealer-Username header to scope all data to the current dealer.
        """
        # Get dealer context from request
        dealer_username = await get_dealer_context(request)

        dealer_info = None
        try:
            dealer = await DealerConfig.objects.aget(username=dealer_username)
            if dealer:
                dealer_info = _dealer_info(dealer)
        except DealerConfig.DoesNotExist:
            pass

        rows: List[CustomerDueRow] = []
        # Group by customer_name (filtered by dealer)
        customer_agg = (
            SaleRecord.objects.filter(DUE_CREDIT_FILTER, dealer_id=dealer_username)
            .values("customer_name")
            .annotate(
                total_amount=Coalesce(Sum("total_amount"), Decimal("0")),
                total_paid=Coalesce(Sum("amount_paid"), Decimal("0")),
                total_returns=Coalesce(Sum("return_total_amount"), Decimal("0")),
                sale_count=Count("id"),
            )
            .order_by("-total_amount")
        )
        async for cust in customer_agg:
            net = cust["total_amount"] - cust["total_returns"]
            due = net - cust["total_paid"]
            if due <= 0:
                continue  # Skip if no actual balance due

            # Fetch individual sales for this customer (filtered by dealer)
            sales_list: List[CustomerDueSale] = []
            async for sale in SaleRecord.objects.filter(
                DUE_CREDIT_FILTER, customer_name=cust["customer_name"], dealer_id=dealer_username
            ).order_by("-date"):
                sale_due = sale.net_amount - sale.amount_paid
                if sale_due <= 0:
                    continue
                sales_list.append(
                    CustomerDueSale(
                        sale_id=sale.id,
                        product_name=sale.product_name,
                        quantity=sale.quantity,
                        total_amount=sale.total_amount,
                        return_total_amount=sale.return_total_amount,
                        net_amount=sale.net_amount,
                        amount_paid=sale.amount_paid,
                        balance_due=sale.balance_due,
                        collection_status=sale.collection_status,
                        due_date=str(sale.due_date) if sale.due_date else None,
                        date=str(sale.date),
                        dsr_name=sale.dsr_name,
                        original_dsr_name=sale.original_dsr_name,
                    )
                )

            # Get phone from first sale (filtered by dealer)
            phone = ""
            first_sale = await SaleRecord.objects.filter(
                DUE_CREDIT_FILTER, customer_name=cust["customer_name"], dealer_id=dealer_username
            ).afirst()
            if first_sale:
                phone = first_sale.customer_phone

            rows.append(
                CustomerDueRow(
                    customer_name=cust["customer_name"],
                    customer_phone=phone,
                    total_sales=cust["total_amount"],
                    total_paid=cust["total_paid"],
                    total_returns=cust["total_returns"],
                    total_due=due,
                    sale_count=cust["sale_count"],
                    sales=sales_list,
                )
            )

        total_outstanding = sum(r.total_due for r in rows)
        return DueReportOut(
            dealer=dealer_info,
            generated_at=datetime.now().isoformat(),
            report_type="customer",
            total_outstanding=total_outstanding,
            rows=rows,
        )

    @route.get("vehicle-due", response=DueReportOut, summary="Vehicle-wise due report")
    async def get_vehicle_due(self, request):
        """Vehicle-wise breakdown of pending credit collections.

        Groups all active credit sales with outstanding balances by
        vehicle_number. Only includes sales where is_vehicle=True.
        Voided and written-off sales are excluded.

        Dealer Context:
            Uses X-Dealer-Username header to scope all data to the current dealer.
        """
        # Get dealer context from request
        dealer_username = await get_dealer_context(request)

        dealer_info = None
        try:
            dealer = await DealerConfig.objects.aget(username=dealer_username)
            if dealer:
                dealer_info = _dealer_info(dealer)
        except DealerConfig.DoesNotExist:
            pass

        rows: List[VehicleDueRow] = []
        vehicle_agg = (
            SaleRecord.objects.filter(
                DUE_CREDIT_FILTER,
                is_vehicle=True,
                vehicle_number__gt="",  # non-empty vehicle number
                dealer_id=dealer_username,
            )
            .values("vehicle_number")
            .annotate(
                total_amount=Coalesce(Sum("total_amount"), Decimal("0")),
                total_paid=Coalesce(Sum("amount_paid"), Decimal("0")),
                total_returns=Coalesce(Sum("return_total_amount"), Decimal("0")),
                sale_count=Count("id"),
            )
            .order_by("-total_amount")
        )
        async for veh in vehicle_agg:
            net = veh["total_amount"] - veh["total_returns"]
            due = net - veh["total_paid"]
            if due <= 0:
                continue

            sales_list: List[VehicleDueSale] = []
            async for sale in SaleRecord.objects.filter(
                DUE_CREDIT_FILTER,
                is_vehicle=True,
                vehicle_number=veh["vehicle_number"],
                dealer_id=dealer_username,
            ).order_by("-date"):
                sale_due = sale.net_amount - sale.amount_paid
                if sale_due <= 0:
                    continue
                sales_list.append(
                    VehicleDueSale(
                        sale_id=sale.id,
                        customer_name=sale.customer_name,
                        product_name=sale.product_name,
                        quantity=sale.quantity,
                        total_amount=sale.total_amount,
                        return_total_amount=sale.return_total_amount,
                        net_amount=sale.net_amount,
                        amount_paid=sale.amount_paid,
                        balance_due=sale.balance_due,
                        collection_status=sale.collection_status,
                        due_date=str(sale.due_date) if sale.due_date else None,
                        date=str(sale.date),
                        dsr_name=sale.dsr_name,
                        original_dsr_name=sale.original_dsr_name,
                    )
                )

            rows.append(
                VehicleDueRow(
                    vehicle_number=veh["vehicle_number"],
                    total_sales=veh["total_amount"],
                    total_paid=veh["total_paid"],
                    total_returns=veh["total_returns"],
                    total_due=due,
                    sale_count=veh["sale_count"],
                    sales=sales_list,
                )
            )

        total_outstanding = sum(r.total_due for r in rows)
        return DueReportOut(
            dealer=dealer_info,
            generated_at=datetime.now().isoformat(),
            report_type="vehicle",
            total_outstanding=total_outstanding,
            rows=rows,
        )

    @route.get("dsr-due", response=DueReportOut, summary="DSR/Collector-wise due report")
    async def get_dsr_due(self, request):
        """DSR/Collector-wise breakdown of pending credit collections.

        Groups sales by the CURRENT collector (dsr field), not the original
        seller (original_dsr). This shows collection workload by DSR.

        If dsr is null, sales are grouped under "Unassigned".
        The original_dsr_name is shown per-sale for attribution tracking.

        Dealer Context:
            Uses X-Dealer-Username header to scope all data to the current dealer.
        """
        # Get dealer context from request
        dealer_username = await get_dealer_context(request)

        dealer_info = None
        try:
            dealer = await DealerConfig.objects.aget(username=dealer_username)
            if dealer:
                dealer_info = _dealer_info(dealer)
        except DealerConfig.DoesNotExist:
            pass

        rows: List[DsrDueRow] = []

        # First get all DSRs that have active due sales (filtered by dealer)
        dsr_ids_with_due = set()
        async for sale in SaleRecord.objects.filter(
            DUE_CREDIT_FILTER, dealer_id=dealer_username
        ).values_list("dsr_id", flat=True):
            dsr_ids_with_due.add(sale)

        # Process each DSR + unassigned
        all_dsr_ids = list(dsr_ids_with_due)

        # FIX DSR-004: Pre-fetch DSR assignments for this dealer so we can
        # look up per-dealer role without hitting dsr_obj.role (removed).
        dsr_assignment_roles: dict = {}  # dsr_id → role
        async for assignment in DsrDealerAssignment.objects.filter(
            dealer_id=dealer_username,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ):
            if assignment.dsr_id:
                dsr_assignment_roles[assignment.dsr_id] = assignment.role

        for dsr_id in all_dsr_ids:
            filter_q = Q(DUE_CREDIT_FILTER, dsr_id=dsr_id, dealer_id=dealer_username)

            # Get DSR info
            dsr_name = "Unassigned"
            dsr_role = ""
            if dsr_id:
                try:
                    dsr_obj = await DsrUser.objects.aget(id=dsr_id)
                    dsr_name = dsr_obj.full_name or dsr_obj.email
                    # FIX DSR-004: role is per-dealer, not on DSR model
                    dsr_role = dsr_assignment_roles.get(dsr_id, "")
                except DsrUser.DoesNotExist:
                    dsr_name = f"Unknown (ID: {dsr_id})"

            # Aggregate
            agg = await async_aggregate(
                SaleRecord.objects.filter(filter_q),
                total_amount=Coalesce(Sum("total_amount"), Decimal("0")),
                total_paid=Coalesce(Sum("amount_paid"), Decimal("0")),
                total_returns=Coalesce(Sum("return_total_amount"), Decimal("0")),
                sale_count=Count("id"),
            )

            net = agg["total_amount"] - agg["total_returns"]
            due = net - agg["total_paid"]
            if due <= 0:
                continue

            # Individual sales
            sales_list: List[DsrDueSale] = []
            async for sale in SaleRecord.objects.filter(filter_q).order_by("-date"):
                sale_due = sale.net_amount - sale.amount_paid
                if sale_due <= 0:
                    continue
                sales_list.append(
                    DsrDueSale(
                        sale_id=sale.id,
                        customer_name=sale.customer_name,
                        product_name=sale.product_name,
                        quantity=sale.quantity,
                        total_amount=sale.total_amount,
                        return_total_amount=sale.return_total_amount,
                        net_amount=sale.net_amount,
                        amount_paid=sale.amount_paid,
                        balance_due=sale.balance_due,
                        collection_status=sale.collection_status,
                        due_date=str(sale.due_date) if sale.due_date else None,
                        date=str(sale.date),
                        original_dsr_name=sale.original_dsr_name,
                    )
                )

            rows.append(
                DsrDueRow(
                    dsr_id=str(dsr_id) if dsr_id else None,
                    dsr_name=dsr_name,
                    role=dsr_role,
                    total_sales=agg["total_amount"],
                    total_paid=agg["total_paid"],
                    total_returns=agg["total_returns"],
                    total_due=due,
                    sale_count=agg["sale_count"],
                    sales=sales_list,
                )
            )

        total_outstanding = sum(r.total_due for r in rows)
        return DueReportOut(
            dealer=dealer_info,
            generated_at=datetime.now().isoformat(),
            report_type="dsr",
            total_outstanding=total_outstanding,
            rows=rows,
        )

    @route.post(
        "ai-reconciliation",
        response=AiReconciliationOut,
        summary="AI-powered reconciliation",
    )
    async def get_ai_reconciliation(self, request):
        """Generate an AI-powered reconciliation report.

        This endpoint provides a structured financial summary suitable for
        LLM analysis. To enable true AI recommendations, integrate with
        Gemini/OpenAI by setting GEMINI_API_KEY or OPENAI_API_KEY env var.

        Current implementation returns a structured text report based on
        actual database metrics (pending sales, written-off amounts, etc.).

        Dealer Context:
            Uses X-Dealer-Username header to scope all data to the current dealer.
        """
        # FIX A-1 (Phase A — CRIT-1): server-side enforcement of the
        # `ai_insights` feature flag. Frontend-only checks were bypassable
        # via direct API calls.
        from common.plan_limits import check_feature
        check_feature(request, "ai_insights")

        # Get dealer context from request
        dealer_username = await get_dealer_context(request)

        # Active pending/partial only (excludes written-off and voided)
        pending_sales = await SaleRecord.objects.filter(
            collection_status__in=[
                SaleRecord.STATUS_PENDING,
                SaleRecord.STATUS_PARTIAL,
            ],
            is_voided=False,
            is_closed_with_due=False,
            dealer_id=dealer_username,
        ).acount()

        total_pending = await async_aggregate(
            SaleRecord.objects.filter(
                collection_status__in=[
                    SaleRecord.STATUS_PENDING,
                    SaleRecord.STATUS_PARTIAL,
                ],
                is_voided=False,
                is_closed_with_due=False,
                dealer_id=dealer_username,
            ),
            amount=Coalesce(Sum("total_amount") - Sum("amount_paid"), Decimal("0"))
        )

        # Written-off stats
        written_off_stats = await async_aggregate(
            SaleRecord.objects.filter(is_closed_with_due=True, is_voided=False, dealer_id=dealer_username),
            total=Coalesce(Sum("total_amount"), Decimal("0")),
            outstanding=Coalesce(
                Sum("total_amount") - Sum("amount_paid"), Decimal("0")
            ),
        )

        # Additional metrics for richer reports
        total_revenue = await async_aggregate(
            SaleRecord.objects.filter(is_voided=False, is_closed_with_due=False, dealer_id=dealer_username),
            revenue=Coalesce(Sum("total_amount"), Decimal("0")),
        )

        # Count DSRs assigned to this dealer via junction table
        dsr_count = await DsrDealerAssignment.objects.filter(
            dealer_id=dealer_username,
            status=DsrDealerAssignment.STATUS_ACTIVE
        ).acount()
        customer_count = await SaleRecord.objects.filter(
            is_voided=False, dealer_id=dealer_username
        ).values("customer_name").distinct().acount()

        # Generate structured report text
        # Using INR prefix and avoiding complex format specifiers for compatibility
        recovery_rate = ((written_off_stats['total'] - written_off_stats['outstanding']) / written_off_stats['total'] * 100 if written_off_stats['total'] else 100)
        avg_outstanding = (float(total_pending['amount']) / pending_sales if pending_sales else 0)
        
        # Format numbers without thousand separators to avoid f-string issues
        pending_amt = float(total_pending['amount'])
        revenue_amt = float(total_revenue['revenue'])
        wo_total = float(written_off_stats['total'])
        wo_outstanding = float(written_off_stats['outstanding'])
        
        report_parts = [
            "# DEALERCORE Financial Reconciliation Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Outstanding Credit Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Active pending/partial sales | {pending_sales} invoices |",
            f"| Total outstanding amount | INR {pending_amt:.2f} |",
            f"| Avg outstanding per invoice | INR {avg_outstanding:.2f} |",
            "",
            "## Overall Financial Health",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Revenue (active sales) | INR {revenue_amt:.2f} |",
            f"| Active DSRs | {dsr_count} |",
            f"| Unique customers | {customer_count} |",
            "",
            "## Written-off Bad Debt",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total written-off sales | INR {wo_total:.2f} |",
            f"| Unrecovered balance | INR {wo_outstanding:.2f} |",
            f"| Recovery rate | {recovery_rate:.1f}% |",
            "",
            "## Recommendations",
            "",
            "Based on current metrics:",
            "",
            f"1. Collection Focus: Prioritize the {pending_sales} pending invoices worth INR {pending_amt:.2f}",
            f"2. DSR Performance: Monitor {dsr_count} active DSRs for collection efficiency",
            f"3. Customer Base: Maintain relationships with {customer_count} active customers",
            "",
            "---",
            "To enable AI-powered analysis, configure GEMINI_API_KEY or OPENAI_API_KEY"
        ]
        report_text = "\n".join(report_parts)

        return AiReconciliationOut(text=report_text)
