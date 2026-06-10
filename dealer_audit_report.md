# DEALERCORE v3.0 — Independent System Audit Report

**Audit Date:** 2026-06-06  
**Auditor:** Automated Out-of-the-Box Audit  
**Scope:** Full-stack synchronization check — Django Ninja backend ↔ Vue.js/Astro frontend  
**Repository:** `dealertemp` (Django 5.2 + Django Ninja + Astro + Vue 3 + TypeScript)

---

## Executive Summary

The DEALERCORE v3.0 dealer management system is a well-architected full-stack application with **17 REST API endpoints** serving a Vue.js SPA frontend. The frontend-backend contract is **fully synchronized** — all API endpoints have matching frontend service methods, all TypeScript types align with Pydantic schemas, and the camelCase/snake_case key transformation pipeline works correctly in both directions.

However, the audit uncovered **5 critical bugs**, **6 moderate issues**, **8 minor issues**, and **6 security concerns** that should be addressed before production deployment. The most severe issues are: (1) a synchronous ORM call in async context that can crash the server, (2) missing stock validation allowing negative inventory, (3) a semantically incorrect "Fully Paid" status when writing off bad debt, and (4) complete absence of authentication on all endpoints.

**Overall System Health: 🟡 Functional but Needs Fixes**

| Category | Count | Severity |
|----------|-------|----------|
| Critical Bugs | 5 | 🔴 Must Fix |
| Moderate Issues | 6 | 🟡 Should Fix |
| Minor Issues | 8 | 🟢 Nice to Fix |
| Security Concerns | 6 | 🔴 Production Blockers |
| Frontend-Backend Sync | ✅ 17/17 | All Endpoints Match |
| Type Alignment | ✅ 100% | All Types Match |

---

## 1. System Architecture Overview

### 1.1 Backend Stack
- **Framework:** Django 5.2.13 + Django Ninja Extra (async class-based controllers)
- **Database:** SQLite3 (development default)
- **Server:** Daphne (ASGI)
- **API Style:** REST, JSON, snake_case with camelCase aliases via Pydantic

### 1.2 Frontend Stack
- **Framework:** Astro (islands) + Vue 3 (`<script setup>`, Composition API)
- **Styling:** Tailwind CSS v4
- **Charts:** Chart.js v4
- **Type System:** TypeScript with strict mode
- **API Client:** Custom `ApiClient` singleton with automatic key transformation

### 1.3 Data Flow
```
Frontend (Vue) → apiClient.ts → snake_case transform → HTTP → Django Ninja
                                                              ↓
Frontend (Vue) ← camelCase transform ← JSON response ← Pydantic (alias=to_camel)
```

---

## 2. API Endpoint Catalog & Sync Status

### 2.1 Complete Endpoint Inventory

| # | Method | Backend Path | Frontend Service Method | Sync? |
|---|--------|-------------|------------------------|-------|
| 1 | GET | `/api/inventory` | `inventoryService.getAllProducts()` | ✅ |
| 2 | GET | `/api/inventory/restocks` | `inventoryService.getAllRestocks()` | ✅ |
| 3 | POST | `/api/inventory/add` | `inventoryService.addProduct()` | ✅ |
| 4 | POST | `/api/inventory/restock` | `inventoryService.restockProduct()` | ✅ |
| 5 | POST | `/api/inventory/{id}/edit` | `inventoryService.editProduct()` | ✅ |
| 6 | GET | `/api/sales` | `salesService.getAllSales()` | ✅ |
| 7 | POST | `/api/sales` | `salesService.createSale()` | ✅ |
| 8 | POST | `/api/sales/bulk` | `salesService.createBulkSales()` | ✅ |
| 9 | POST | `/api/sales/{id}/collect` | `salesService.collectPayment()` | ✅ |
| 10 | POST | `/api/sales/{id}/close-with-due` | `salesService.closeSaleWithDue()` | ✅ |
| 11 | GET | `/api/dsrs` | `dsrService.getAllDsrs()` | ✅ |
| 12 | POST | `/api/dsrs` | `dsrService.createDsr()` | ✅ |
| 13 | GET | `/api/suppliers` | `supplierService.getAllSuppliers()` | ✅ |
| 14 | GET | `/api/dealers` | `dealerService.getAllDealers()` | ✅ |
| 15 | POST | `/api/dealers/update` | `dealerService.updateDealerSettings()` | ✅ |
| 16 | GET | `/api/reports/summary` | `reportsService.getSummary()` | ✅ |
| 17 | POST | `/api/reports/ai-reconciliation` | `reportsService.getAiReconciliation()` | ✅ |

**Result: 17/17 endpoints fully synchronized. No orphaned endpoints in either direction.**

### 2.2 Missing CRUD Operations (Feature Gaps)

| Entity | List | Create | Read One | Update | Delete |
|--------|------|--------|----------|--------|--------|
| Product | ✅ | ✅ | ❌ | ✅ (PATCH) | ❌ |
| RestockRecord | ✅ | ✅ | ❌ | ❌ | ❌ |
| SaleRecord | ✅ | ✅ | ❌ | Partial* | ❌ |
| DSR | ✅ | ✅ | ❌ | ❌ | ❌ |
| Supplier | ✅ | ❌ | ❌ | ❌ | ❌ |
| DealerConfig | ✅ | ❌ | ❌ | ✅ (partial) | ❌ |

\* SaleRecord has specialized update endpoints (collect payment, close with due) but no general edit.

**Key Gaps:**
- Supplier is read-only — no create/update/delete via API (frontend has no Supplier management UI either)
- DSR cannot be updated after creation (phone, name, role reassignment all impossible)
- No single-record GET on any entity
- No delete on any entity (may be intentional for audit trail on sales)

---

## 3. TypeScript ↔ Pydantic Type Alignment

### 3.1 Type Match Matrix

| Frontend Type | Backend Schema | Field Match | Key Transform |
|---------------|---------------|-------------|---------------|
| `Product` | `ProductOut` | ✅ 10/10 | camelCase aliases correct |
| `RestockRecord` | `RestockRecordOut` | ✅ 9/9 | camelCase aliases correct |
| `CreditPayment` | `CreditPaymentOut` | ✅ 4/4 | camelCase aliases correct |
| `SaleRecord` | `SaleRecordOut` | ✅ 17/17 | camelCase aliases correct |
| `DSR` | `DSROut` | ✅ 7/7 | camelCase aliases correct |
| `Supplier` | `SupplierOut` | ✅ 4/4 | camelCase aliases correct |
| `DealerConfig` | `DealerConfigOut` | ✅ 5/5 | camelCase aliases correct |
| `SummaryData` | `SummaryOut` | ✅ 11/11 | camelCase aliases correct |

### 3.2 Type Precision Notes

| Field | Frontend Type | Backend Type | Runtime Impact |
|-------|--------------|-------------|----------------|
| `unitPrice`, `sellingPrice` | `number` | `Decimal(12,2)` | None — JSON serializes Decimal as number |
| `totalAmount`, `amountPaid` | `number` | `Decimal(14,2)` | None — same as above |
| `costPrice`, `totalCost` | `number` | `Decimal(12-14,2)` | None — same as above |
| `DSR.role` | `'DSR' \| 'Order Collector'` | `str` | Minor — backend is open string |
| `dueDate` | `string` (optional) | `Optional[date]` | None — ISO string format |

**Precision Warning:** JavaScript `number` is IEEE 754 double-precision (15-17 significant digits). Python `Decimal` supports arbitrary precision. For financial calculations exceeding ₹9,007,199,254,740,991 (9 quadrillion), floating-point precision loss is possible. For a dealer management system, this is unlikely to be a practical concern.

---

## 4. Critical Bugs (🔴 Must Fix)

### BUG-1: Synchronous ORM Call in Async Context — Runtime Crash

**File:** `sales/api.py`, line 194  
**Severity:** 🔴 Critical — Can crash the server with `SynchronousOnlyOperation` error

```python
@staticmethod
async def _serialize_sale(sale: SaleRecord) -> SaleRecordOut:
    payments = list(sale.payments.all())  # ← SYNC DB CALL IN ASYNC
```

**Analysis:** This works when called from `_list_sales_qs()` because `prefetch_related("payments")` caches the relation in memory, so the `.all()` call doesn't hit the database. However, it **crashes** when called from:

- `create_sale()` — sale created via `acreate()`, no prefetch cache
- `collect_payment()` — sale fetched via `aget()`, no prefetch cache
- `close_sale_with_due()` — sale fetched via `aget()`, no prefetch cache

**Impact:** Creating a sale, collecting a payment, or closing a sale with due will throw `SynchronousOnlyOperation` at the serialization step, returning a 500 error to the client.

**Fix:**
```python
# Option A: Async iteration
payments = [p async for p in sale.payments.all()]

# Option B: Add prefetch_related to all aget() calls
sale = await SaleRecord.objects.prefetch_related("payments").aget(id=sale_id)
```

---

### BUG-2: `_generate_id` Doesn't Filter by Prefix — Potential ID Collision

**File:** `inventory/api.py`, lines 119-139  
**Severity:** 🔴 Critical — Can generate duplicate primary keys

```python
async def _generate_id(self, prefix: str) -> str:
    if prefix == "prod":
        last = await Product.objects.all().aaggregate(_max=Max("id"))["_max"]
    elif prefix == "rstk":
        last = await RestockRecord.objects.all().aaggregate(_max=Max("id"))["_max"]
```

This aggregates the max ID across **all** records regardless of prefix. If the max ID is `"sale-99"`, parsing `"sale-99".split("-")[-1]` gives `99`, and the next Product ID would be `"prod-100"` — but `"prod-100"` may already exist if there are 100+ products.

**Contrast with** `sales/api.py:227` which correctly uses:
```python
last = await SaleRecord.objects.filter(id__startswith=prefix).aaggregate(...)
```

**Fix:** Add `.filter(id__startswith=prefix)` to both Product and RestockRecord queries.

---

### BUG-3: No Stock Validation on Sale — Negative Inventory Possible

**File:** `sales/api.py`, lines 122-123  
**Severity:** 🔴 Critical — Data integrity violation

```python
product.stock = F("stock") - payload.quantity
await product.asave()
```

There is no check that `product.stock >= payload.quantity`. Selling 50 units when only 10 are in stock will result in `stock = -40`. While the frontend validates stock availability client-side, there is **no server-side validation**, making this exploitable via direct API calls.

**Fix:**
```python
await product.arefresh_from_db()
if product.stock < payload.quantity:
    raise HttpError(400, f"Insufficient stock: only {product.stock} available, {payload.quantity} requested")
```

---

### BUG-4: `close_sale_with_due` Marks Sale as "Fully Paid" — Semantic Error

**File:** `sales/api.py`, line 103  
**Severity:** 🔴 Critical — Corrupts financial reporting

```python
sale.is_closed_with_due = True
sale.collection_status = SaleRecord.STATUS_FULLY_PAID  # ← Wrong!
```

Writing off bad debt as "Fully Paid" is semantically incorrect. A sale where the customer didn't pay the full amount is not "Fully Paid" — it's "Written Off". This causes:

- Dashboard `credit_collected` to be inflated (written-off amounts appear as collected)
- `credit_pending` to be understated
- Financial reports to misrepresent actual collection rates
- The frontend correctly checks `isClosedWithDue` in most places, but the `collectionStatus` being "Fully Paid" creates ambiguity

**Fix:** Add a `STATUS_WRITTEN_OFF = "Written Off"` choice to the model, or at minimum update the reports summary query to exclude `is_closed_with_due=True` sales from "Fully Paid" counts.

---

### BUG-5: `@transaction.atomic` Decorator on Async Methods — May Not Roll Back

**Files:** `inventory/api.py` (lines 61, 79), `sales/api.py` (lines 43, 49, 70, 95)  
**Severity:** 🔴 Critical — Transaction integrity at risk

```python
@route.post("add", response=ProductOut)
@transaction.atomic  # ← sync decorator on async method
async def add_product(self, payload: AddProductIn):
```

Django's `transaction.atomic` as a decorator does not properly manage async database connections. If an exception occurs inside the async method, the transaction may not roll back correctly, leaving the database in an inconsistent state.

**Fix:** Replace with context manager inside the method body:
```python
async def add_product(self, payload: AddProductIn):
    async with transaction.atomic():
        product = await Product.objects.acreate(...)
        return product
```

---

## 5. Moderate Issues (🟡 Should Fix)

### ISSUE-6: `_generate_id` Race Condition Under Concurrent Requests

All `_generate_id` methods read the max ID then write a new one without any locking. Two concurrent requests can generate the same ID, causing a primary key violation on one.

**Fix:** Use `select_for_update()` on the latest record, or catch `IntegrityError` and retry with an incremented counter.

---

### ISSUE-7: Seed Data Creates Stock/Sale Inconsistency

The seed data hardcodes product stock values without accounting for sales that reduce stock. After seeding, the inventory numbers don't match the expected formula: `current_stock = initial_stock + restocked - sold`.

**Fix:** Either calculate stock dynamically after all restocks and sales are created, or start all products at `stock=0` and let restock records drive the initial stock.

---

### ISSUE-8: Reports DSR Performance — N+1 Query Problem

**File:** `reports/api.py`, lines 79-100

```python
async for dsr in DSR.objects.all():
    sales_agg = await SaleRecord.objects.filter(dsr=dsr).aaggregate(...)
```

This runs one aggregation query per DSR. With 50 DSRs, this becomes 50 database queries on every summary request.

**Fix:** Use a single annotated queryset:
```python
from django.db.models import Case, When, Value, Sum, Count

dsr_performance = DSR.objects.annotate(
    total_sales=Sum("sales__total_amount", default=Decimal("0")),
    collected=Sum("sales__amount_paid", default=Decimal("0")),
    count=Count("sales"),
).order_by("-total_sales")
```

---

### ISSUE-9: `collect_payment` Performs Two Separate Database Writes

**File:** `sales/api.py`, lines 84-91

```python
sale.amount_paid = F("amount_paid") + payload.amount
await sale.asave()          # Write 1
await sale.arefresh_from_db()
sale.collection_status = self._calc_collection_status(...)
await sale.asave()          # Write 2
```

Two separate writes are unnecessary. The second write could also cause a race condition if another payment arrives between the two saves.

**Fix:** Refresh once, compute status, and save with `update_fields`:
```python
sale.amount_paid = F("amount_paid") + payload.amount
await sale.asave(update_fields=["amount_paid", "updated_at"])
await sale.arefresh_from_db()
sale.collection_status = self._calc_collection_status(
    float(sale.total_amount), float(sale.amount_paid)
)
await sale.asave(update_fields=["collection_status", "updated_at"])
```

---

### ISSUE-10: Collections.vue Emits Without Awaiting — Premature Success Messages

**File:** `Collections.vue`, lines 82 and 151

```javascript
emit('collectPayment', selectedSale.value.id, amt, receivedBy.value);
formSuccess.value = `Payment of ${formatCurrency.value(amt)} recorded!`;
```

Vue's `emit()` is synchronous and cannot be awaited. The success message appears immediately, but the parent's async API call may still be in progress or may fail. The user sees "Payment recorded!" before the server confirms it.

**Fix:** Refactor to pass the async handler as a prop, or have the component call the API service directly and emit a refresh event afterward.

---

### ISSUE-11: `fetchFullDetails()` Has Silent Error Handling

**File:** `App.vue`, lines 164-166

```javascript
} catch (err) {
  console.error(err);
  // No errorBanner set — user gets no feedback
}
```

Unlike `loadDatabase()` which sets `errorBanner`, `fetchFullDetails()` silently swallows errors. When the user clicks "Sync Database" and it fails, they get no visual feedback.

**Fix:** Add `errorBanner.value = 'Sync failed. Please try again.';` in the catch block.

---

## 6. Minor Issues (🟢 Nice to Fix)

### ISSUE-12: Duplicate `SummaryData` Interface (3 Copies)

`SummaryData` is defined in three places:
1. `reports.service.ts` — Source of truth (canonical)
2. `Overview.vue` — Local duplicate with `lowStockItems` typed as `Product[]` instead of the specific subset type
3. `Reports.vue` — Same local duplicate

Both component copies incorrectly type `lowStockItems` as `Product[]` when the API returns objects with only 5 fields `{id, name, stock, minStockAlert, category}` — not full Product objects with 10 fields. Both copies also miss the `totalProductsCount` field.

**Fix:** Import `SummaryData` from `reports.service.ts` instead of defining it locally.

---

### ISSUE-13: `summary` Typed as `any` in App.vue

```typescript
const summary = ref<any>(null);  // Should be ref<SummaryData | null>(null)
```

This loses type safety for the entire data pipeline flowing through Overview and Reports components.

---

### ISSUE-14: Restock Payload Includes Phantom Fields

The `Inventory.vue` restock emit sends `sellingPrice` and `location` fields that are not in `RestockPayload` and are ignored by the backend. These appear to be leftovers from an older design where restocking could update the product's selling price and location.

**Fix:** Remove `sellingPrice` and `location` from the restock emit payload in `Inventory.vue`.

---

### ISSUE-15: `customer_phone` Default Inconsistency Across Schemas

- `CreateSaleIn`: `customer_phone: Optional[str] = None`
- `BulkSaleRowIn`: `customer_phone: str = ""`

Same logical field, different defaults. This can cause `null` vs `""` inconsistencies in the database.

---

### ISSUE-16: `due_date` Typed as `Optional[str]` Instead of `Optional[date]`

**File:** `sales/schemas.py`, line 86

```python
due_date: Optional[str] = None  # Should be Optional[date]
```

Using `str` bypasses Pydantic's date validation. Invalid date strings silently become `None`.

---

### ISSUE-17: Inventory.vue `editProduct` Bypasses Centralized Handler

Unlike `addProduct` and `restockProduct` which emit events to App.vue (centralized pattern), `editProduct` calls `inventoryService.editProduct()` directly from the component. This creates an architectural inconsistency.

---

### ISSUE-18: Orphaned Schema `DSRModelOut`

**File:** `dsr/schemas.py` — Defined but never used in any endpoint.

---

### ISSUE-19: No Pagination on Any List Endpoint

All list endpoints return the complete table. With thousands of records, this becomes a performance bottleneck.

---

### ISSUE-20: No 404 Handling for `aget()` Calls

Multiple endpoints use `aget()` without catching `DoesNotExist`, resulting in 500 errors instead of proper 404 responses.

---

## 7. Security Audit (🔴 Production Blockers)

| # | Issue | Severity | File | Status |
|---|-------|----------|------|--------|
| SEC-1 | Hardcoded `SECRET_KEY` in settings | 🔴 Critical | `settings.py:28` | Must fix before deploy |
| SEC-2 | `DEBUG = True` enabled | 🔴 Critical | `settings.py:31` | Must fix before deploy |
| SEC-3 | `ALLOWED_HOSTS = ['*']` | 🟡 High | `settings.py:33` | Must fix before deploy |
| SEC-4 | `CORS_ALLOW_ALL_ORIGINS = True` | 🟡 High | `settings.py:94` | Must restrict in production |
| SEC-5 | No authentication on any endpoint | 🔴 Critical | All controllers | Anyone can access/modify data |
| SEC-6 | `ninja_jwt` installed but unused | 🟡 Medium | `settings.py:54` | Auth framework exists but not wired |

**Notes:**
- SEC-5 is partially mitigated if the system runs on a private network, but should still be addressed
- `ninja_jwt` is already in `INSTALLED_APPS` — wiring it up would require minimal effort
- The `SILENCED_SYSTEM_CHECKS = ["security.W019"]` line suppresses Django's security warning about `ALLOWED_HOSTS = ['*']`

---

## 8. Data Model Relationship Diagram

```
DealerConfig (standalone config)
    └── username (PK)

Product (inventory)
    ├── id (PK, string: "prod-N")
    └──< RestockRecord (CASCADE)
    └──< SaleRecord (PROTECT)

RestockRecord (inventory)
    ├── id (PK, string: "rstk-N")
    ├── product → Product (FK, CASCADE)
    └── supplier_name (denormalized string, no FK)

SaleRecord (sales)
    ├── id (PK, string: "sale-N")
    ├── product → Product (FK, PROTECT)
    ├── dsr → DSR (FK, SET_NULL, nullable)
    ├── is_closed_with_due (write-off flag)
    └──< CreditPayment (CASCADE)

CreditPayment (sales)
    ├── id (PK, string: "pay-N")
    └── sale → SaleRecord (FK, CASCADE)

DSR (dsr)
    ├── id (PK, string: "dsr-N")
    └── parent_dsr → DSR (self-ref FK, SET_NULL)

Supplier (supplier)
    ├── id (PK, string: "sup-N")
    └── (no FK relationships — referenced by name string only)
```

---

## 9. Frontend Component ↔ API Data Flow

### 9.1 App.vue Data Loading

| State Variable | API Source | Components Receiving |
|---------------|-----------|---------------------|
| `products` | `inventoryService.getAllProducts()` | Inventory, Sales, Reports |
| `sales` | `salesService.getAllSales()` | Overview, Sales, Collections, Reports |
| `dsrs` | `dsrService.getAllDsrs()` | Inventory, Sales, Reports |
| `suppliers` | `supplierService.getAllSuppliers()` | Inventory |
| `restocksList` | `inventoryService.getAllRestocks()` | Inventory |
| `summary` | `reportsService.getSummary()` | Overview, Reports |
| `dealers` | `dealerService.getAllDealers()` | App (settings modal) |

### 9.2 Key Transformation Pipeline Verification

**Request Path (Frontend → Backend):**
1. Vue component emits with camelCase fields
2. `apiClient.post()` applies `transformKeysToSnakeCase()` to request body
3. Django Ninja receives snake_case, Pydantic `populate_by_name=True` accepts both formats
4. Fields stored in Django models as snake_case

**Response Path (Backend → Frontend):**
1. Django Ninja serializes with `alias_generator=to_camel` → JSON keys are camelCase
2. `apiClient` applies `transformKeysToCamelCase()` to response — no-op on already-camelCase keys
3. Vue components receive camelCase objects matching TypeScript interfaces

**Verdict:** The double-transformation (backend alias + frontend transform) is redundant but safe. The regex `_([a-z])` in `snakeToCamel` won't match camelCase keys, making it a no-op.

---

## 10. Prioritized Remediation Plan

### Phase 1: Critical Fixes (Before Any Production Use)

| Priority | Bug ID | Estimated Effort | Description |
|----------|--------|-----------------|-------------|
| P0 | BUG-1 | 30 min | Fix sync ORM call in `_serialize_sale` — use async iteration or `prefetch_related` |
| P0 | BUG-2 | 15 min | Add `filter(id__startswith=prefix)` to inventory `_generate_id` |
| P0 | BUG-3 | 15 min | Add server-side stock validation before sale creation |
| P0 | BUG-4 | 30 min | Add "Written Off" status for `close_sale_with_due` + update reports queries |
| P0 | BUG-5 | 20 min | Replace `@transaction.atomic` decorator with `async with transaction.atomic():` |
| P0 | SEC-1-3 | 15 min | Move SECRET_KEY to env, set DEBUG=False, restrict ALLOWED_HOSTS |

### Phase 2: High Priority (Within 1 Week)

| Priority | Bug ID | Estimated Effort | Description |
|----------|--------|-----------------|-------------|
| P1 | ISSUE-6 | 30 min | Add locking/retry to `_generate_id` |
| P1 | ISSUE-10 | 1 hr | Fix Collections.vue async emit pattern |
| P1 | ISSUE-11 | 10 min | Add error feedback to `fetchFullDetails()` |
| P1 | SEC-5 | 4 hr | Wire up JWT authentication on all endpoints |
| P1 | SEC-4 | 10 min | Restrict CORS origins for production |

### Phase 3: Medium Priority (Within 2 Weeks)

| Priority | Bug ID | Estimated Effort | Description |
|----------|--------|-----------------|-------------|
| P2 | ISSUE-7 | 1 hr | Fix seed data stock/sale consistency |
| P2 | ISSUE-8 | 1 hr | Refactor DSR performance to single annotated queryset |
| P2 | ISSUE-9 | 30 min | Consolidate `collect_payment` to single DB write |
| P2 | ISSUE-12 | 30 min | Eliminate duplicate `SummaryData` interfaces |
| P2 | ISSUE-13 | 10 min | Type `summary` as `SummaryData \| null` in App.vue |
| P2 | ISSUE-14 | 10 min | Remove phantom restock payload fields |

### Phase 4: Low Priority (Backlog)

| Priority | Bug ID | Description |
|----------|--------|-------------|
| P3 | ISSUE-15 | Normalize `customer_phone` defaults across schemas |
| P3 | ISSUE-16 | Type `due_date` as `Optional[date]` in Pydantic schemas |
| P3 | ISSUE-17 | Centralize `editProduct` through App.vue handler |
| P3 | ISSUE-18 | Remove orphaned `DSRModelOut` schema |
| P3 | ISSUE-19 | Add pagination to list endpoints |
| P3 | ISSUE-20 | Add proper 404 handling for `aget()` calls |
| P3 | Missing CRUD | Add Supplier CRUD, DSR update, single-record GET |

---

## 11. Test Scenarios for Manual Verification

### 11.1 Sale Creation Flow
1. Open Sales page → Click "New Sale" → Fill form → Submit
2. **Expected:** Sale created, stock decreased, success message shown
3. **Bug Check:** If BUG-1 is present, creating a sale via API will crash at `_serialize_sale`

### 11.2 Payment Collection Flow
1. Open Collections page → Click "Collect" on a pending invoice → Enter amount → Submit
2. **Expected:** Payment recorded, status updated, success message
3. **Bug Check:** If BUG-1 is present, `collect_payment` endpoint will crash
4. **Bug Check:** If ISSUE-10 is present, success message appears before server confirms

### 11.3 Negative Stock Test
1. Find a product with stock=5
2. Create a sale for 10 units via API (bypassing frontend validation)
3. **Expected (current):** Sale succeeds, stock becomes -5
4. **Expected (after fix):** Sale rejected with 400 error

### 11.4 Write-Off Test
1. Open Collections → Click "Write Off" on a pending credit sale
2. **Expected (current):** Status becomes "Fully Paid", `is_closed_with_due=True`
3. **Expected (after fix):** Status becomes "Written Off"

### 11.5 ID Generation Collision Test
1. Create 100+ products via API
2. Create sales (generating "sale-N" IDs)
3. Create more products — check if new product ID collides with existing ones
4. **Bug Check:** If BUG-2 is present, product IDs may collide after sales reach higher numbers

---

## 12. File Index (Files Audited)

### Backend
- `dealercore/settings.py` — Django configuration
- `dealercore/api.py` — Root API router
- `inventory/models.py` — Product, RestockRecord models
- `inventory/api.py` — Inventory controller
- `inventory/schemas.py` — Inventory Pydantic schemas
- `sales/models.py` — SaleRecord, CreditPayment models
- `sales/api.py` — Sales controller
- `sales/schemas.py` — Sales Pydantic schemas
- `dsr/models.py` — DSR model
- `dsr/api.py` — DSR controller
- `dsr/schemas.py` — DSR Pydantic schemas
- `supplier/models.py` — Supplier model
- `supplier/api.py` — Supplier controller
- `dealer/models.py` — DealerConfig model
- `dealer/api.py` — Dealer controller
- `reports/api.py` — Reports controller
- `reports/schemas.py` — Reports Pydantic schemas
- `dealer/management/commands/seed_data.py` — Seed data command

### Frontend
- `src/types.ts` — TypeScript type definitions
- `src/services/apiClient.ts` — HTTP client with key transforms
- `src/services/api/index.ts` — Barrel export
- `src/services/api/inventory.service.ts` — Inventory API service
- `src/services/api/sales.service.ts` — Sales API service
- `src/services/api/dsr.service.ts` — DSR API service
- `src/services/api/supplier.service.ts` — Supplier API service
- `src/services/api/dealer.service.ts` — Dealer API service
- `src/services/api/reports.service.ts` — Reports API service
- `src/App.vue` — Main application shell
- `src/components/Overview.vue` — Dashboard page
- `src/components/Inventory.vue` — Inventory management
- `src/components/Sales.vue` — Sales entry
- `src/components/Collections.vue` — Payment collections
- `src/components/Reports.vue` — Financial reports
- `src/components/charts/BaseChart.vue` — Chart.js component
- `src/components/charts/ChartCard.vue` — Chart card wrapper

---

## 13. Conclusion

The DEALERCORE v3.0 system demonstrates solid architectural decisions: centralized API services, consistent key transformation, proper type alignment, and clean component composition. The frontend-backend contract is fully synchronized with zero orphaned endpoints or type mismatches.

However, the system has **5 critical bugs** that affect core functionality (sale creation, payment collection, ID generation, stock validation, and transaction integrity) and **6 security concerns** that block production deployment. These issues are straightforward to fix — the estimated total remediation effort for Phase 1 (critical fixes) is approximately **2 hours**.

The most impactful single fix would be **BUG-1** (sync ORM call in async context), as it currently prevents the sale creation, payment collection, and write-off flows from working correctly through the API when payments are not pre-fetched.
