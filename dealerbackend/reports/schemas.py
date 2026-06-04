"""
DEALERCORE v3.0 — Reports Schemas (Pydantic)
----------------------------------------------
Response schemas for computed report data.
All data here is aggregated — no database models needed.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from ninja import Schema


# ─── Low Stock ──────────────────────────────────────────

class LowStockItem(Schema):
    """Product below its minimum stock alert threshold."""

    id: str
    name: str
    stock: int
    min_stock_alert: int
    category: str


# ─── DSR Performance ───────────────────────────────────

class DsrPerformanceRow(Schema):
    """Aggregated performance metrics for a DSR."""

    id: str
    name: str
    role: str
    parent_dsr_id: Optional[str] = None
    parent_dsr_name: Optional[str] = None
    total_sales: Decimal
    collected: Decimal
    pending: Decimal
    count: int


# ─── Product Performance ───────────────────────────────

class ProductPerformanceRow(Schema):
    """Aggregated sales performance for a product."""

    name: str
    quantity: int
    total: Decimal


# ─── Summary Response ──────────────────────────────────

class SummaryOut(Schema):
    """Complete dashboard summary data."""

    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    credit_pending: Decimal
    credit_collected: Decimal
    low_stock_count: int
    low_stock_items: List[LowStockItem]
    dsr_performance: List[DsrPerformanceRow]
    product_performance: List[ProductPerformanceRow]
    total_sales_count: int
    total_products_count: int


# ─── AI Reconciliation Response ────────────────────────

class AiReconciliationOut(Schema):
    """AI-generated reconciliation text (Markdown string)."""

    text: str
