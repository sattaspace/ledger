"""
DEALERCORE v3.0 — Sales API Router
-------------------------------------
Django Ninja async endpoints for sales management.

Endpoints:
  GET  /api/sales                   → list all sales
  POST /api/sales                   → create a single sale
  POST /api/sales/bulk              → create multiple sales at once
  POST /api/sales/{id}/collect      → collect payment on a credit sale
  POST /api/sales/{id}/close-with-due → close a sale with outstanding due (write-off)
"""

from datetime import datetime, date as date_type
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import F, Sum
from ninja import Router

from inventory.models import Product
from dsr.models import DSR
from sales.models import SaleRecord, CreditPayment
from sales.schemas import (
    BulkSaleIn,
    CollectPaymentIn,
    CreateSaleIn,
    SaleRecordOut,
    CreditPaymentOut,
)

router = Router(tags=["Sales"])


@router.get("", response=list[SaleRecordOut], summary="List all sales")
async def list_sales(request):
    """Return all sales ordered by date descending."""
    return list(SaleRecord.objects.select_related("dsr").all())


@router.post("", response=SaleRecordOut, summary="Create a sale")
@transaction.atomic
async def create_sale(request, payload: CreateSaleIn):
    """Create a single sale. Decreases product stock, handles cash/credit logic."""
    return await _process_single_sale(payload)


@router.post("bulk", response=list[SaleRecordOut], summary="Create bulk sales")
@transaction.atomic
async def create_bulk_sales(request, payload: BulkSaleIn):
    """Create multiple sales in one transaction. Shares vehicle_number and dsr_id."""
    results = []
    for row in payload.rows:
        sale_data = CreateSaleIn(
            product_id=row.product_id,
            quantity=row.quantity,
            customer_name=row.customer_name,
            customer_phone=row.customer_phone,
            is_vehicle=payload.vehicle_number != "",
            vehicle_number=payload.vehicle_number if payload.vehicle_number else None,
            dsr_id=payload.dsr_id,
            payment_type=row.payment_type,
            amount_paid=row.amount_paid,
            due_date=row.due_date,
        )
        sale = await _process_single_sale(sale_data)
        results.append(sale)
    return results


@router.post("{sale_id}/collect", response=SaleRecordOut, summary="Collect payment")
@transaction.atomic
async def collect_payment(request, sale_id: str, payload: CollectPaymentIn):
    """Collect a payment against a credit sale. Updates amount_paid and status."""
    sale = await SaleRecord.objects.aget(id=sale_id)

    payment = await CreditPayment.objects.acreate(
        id=await _generate_id("pay"),
        sale=sale,
        amount=payload.amount,
        date=datetime.now(),
        received_by=payload.received_by,
    )

    sale.amount_paid = F("amount_paid") + payload.amount
    await sale.asave()
    await sale.arefresh_from_db()

    # Recalculate collection status
    sale.collection_status = _calc_collection_status(
        float(sale.total_amount), float(sale.amount_paid)
    )
    await sale.asave()

    return await _serialize_sale(sale)


@router.post(
    "{sale_id}/close-with-due", response=SaleRecordOut, summary="Close sale with due"
)
@transaction.atomic
async def close_sale_with_due(request, sale_id: str):
    """Write off a sale as bad debt. Sets is_closed_with_due flag."""
    sale = await SaleRecord.objects.aget(id=sale_id)
    sale.is_closed_with_due = True
    sale.collection_status = SaleRecord.STATUS_FULLY_PAID
    await sale.asave()
    return await _serialize_sale(sale)


# ─── Helpers ────────────────────────────────────────────


async def _process_single_sale(payload: CreateSaleIn) -> SaleRecordOut:
    """Core sale creation logic — shared between single and bulk endpoints."""
    product = await Product.objects.aget(id=payload.product_id)

    # Decrease stock
    product.stock = F("stock") - payload.quantity
    await product.asave()

    # Resolve DSR if provided
    dsr_name = ""
    if payload.dsr_id:
        try:
            dsr = await DSR.objects.aget(id=payload.dsr_id)
            dsr_name = dsr.name
        except DSR.DoesNotExist:
            pass

    # Compute totals
    total_amount = payload.quantity * product.selling_price
    amount_paid = payload.amount_paid or Decimal("0")

    # Determine initial collection status
    payment_type = payload.payment_type
    if payment_type == "Cash":
        collection_status = SaleRecord.STATUS_FULLY_PAID
        amount_paid = total_amount
    else:
        collection_status = _calc_collection_status(
            float(total_amount), float(amount_paid)
        )

    # Parse due_date
    due_date = None
    if payload.due_date:
        try:
            due_date = date_type.fromisoformat(payload.due_date)
        except ValueError:
            pass

    # Determine if vehicle
    is_vehicle = payload.is_vehicle or False
    vehicle_number = payload.vehicle_number or ""

    sale = await SaleRecord.objects.acreate(
        id=await _generate_id("sale"),
        product=product,
        product_name=product.name,
        quantity=payload.quantity,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone or "",
        is_vehicle=is_vehicle,
        vehicle_number=vehicle_number,
        dsr_id=payload.dsr_id,
        dsr_name=dsr_name,
        selling_price=product.selling_price,
        total_amount=total_amount,
        payment_type=payment_type,
        amount_paid=amount_paid,
        collection_status=collection_status,
        due_date=due_date,
        date=datetime.now(),
    )

    return await _serialize_sale(sale)


def _calc_collection_status(total: float, paid: float) -> str:
    """Determine collection status based on total vs paid amounts."""
    if paid <= 0:
        return SaleRecord.STATUS_PENDING
    elif paid >= total:
        return SaleRecord.STATUS_FULLY_PAID
    else:
        return SaleRecord.STATUS_PARTIAL


async def _serialize_sale(sale: SaleRecord) -> SaleRecordOut:
    """Serialize a SaleRecord with its embedded payments list."""
    payments = await sale.payments.all()
    return SaleRecordOut(
        id=sale.id,
        product_id=sale.product_id,
        product_name=sale.product_name,
        quantity=sale.quantity,
        customer_name=sale.customer_name,
        customer_phone=sale.customer_phone,
        is_vehicle=sale.is_vehicle,
        vehicle_number=sale.vehicle_number,
        dsr_id=sale.dsr_id,
        dsr_name=sale.dsr_name,
        selling_price=sale.selling_price,
        total_amount=sale.total_amount,
        payment_type=sale.payment_type,
        amount_paid=sale.amount_paid,
        collection_status=sale.collection_status,
        due_date=sale.due_date,
        date=sale.date,
        payments=[
            CreditPaymentOut(
                id=p.id,
                amount=p.amount,
                date=p.date,
                received_by=p.received_by,
            )
            for p in payments
        ],
        is_closed_with_due=sale.is_closed_with_due,
    )


async def _generate_id(prefix: str) -> str:
    """Generate a unique string ID with given prefix."""
    from django.db.models import Max

    last = await SaleRecord.objects.filter(id__startswith=prefix).aaggregate(
        _max=Max("id")
    )["_max"]

    if last:
        try:
            num = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1

    return f"{prefix}-{num}"
