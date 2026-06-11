# DEALERCORE v3.0 — Django Ninja Extra Backend Structure

## Overview

This backend is designed to serve the DEALERCORE v3.0 frontend (Astro + Vue 3).
It uses **django-ninja-extra** with class-based controllers, **ModelSchema** auto-generation,
and Pydantic schemas. Fully async with Django ORM.

---

## Project Structure

```
backend/
├── manage.py                          # Django management script
├── dealercore/                        # Project package
│   ├── __init__.py
│   ├── settings_reference.py          # Settings reference (merge into your settings.py)
│   ├── urls.py                        # Root URL config — mounts NinjaExtraAPI at /api/
│   └── api.py                         # NinjaExtraAPI + register_controllers()
│
├── inventory/                         # Products & Restocking
│   ├── __init__.py
│   ├── models.py                      # Product, RestockRecord
│   ├── schemas.py                     # ProductOut (ModelSchema), AddProductIn, EditProductIn, RestockIn/Out
│   └── api.py                         # InventoryController: 4 endpoints
│
├── sales/                             # Sales & Payments
│   ├── __init__.py
│   ├── models.py                      # SaleRecord, CreditPayment
│   ├── schemas.py                     # CreditPaymentOut (ModelSchema), SaleRecordOut, CreateSaleIn, BulkSaleIn
│   └── api.py                         # SalesController: 5 endpoints
│
├── dsr/                               # Daily Sales Representatives
│   ├── __init__.py
│   ├── models.py                      # DSR (self-referential FK)
│   ├── schemas.py                     # DSRModelOut (ModelSchema), DSROut, CreateDSRIn
│   └── api.py                         # DSRController: 2 endpoints
│
├── supplier/                          # Supplier Reference Table
│   ├── __init__.py
│   ├── models.py                      # Supplier
│   ├── schemas.py                     # SupplierOut (ModelSchema)
│   └── api.py                         # SupplierController: 1 endpoint
│
├── dealer/                            # Dealer Configuration
│   ├── __init__.py
│   ├── models.py                      # DealerConfig (username as natural PK)
│   ├── schemas.py                     # DealerConfigOut (ModelSchema), UpdateDealerIn
│   └── api.py                         # DealerController: 2 endpoints
│
└── reports/                           # Computed Reports (no DB models)
    ├── __init__.py
    ├── models.py                      # Empty — reports are computed via ORM aggregation
    ├── schemas.py                     # SummaryOut, AiReconciliationOut, LowStockItem, etc.
    └── api.py                         # 2 endpoints: summary, ai-reconciliation
```

---

## Models Summary

| App | Model | Primary Key | Key Fields | Relationships |
|-----|-------|-------------|------------|---------------|
| **inventory** | `Product` | `CharField` (id) | name, sku, brand, category, stock, unit_price, selling_price, location | ← RestockRecord, ← SaleRecord |
| **inventory** | `RestockRecord` | `CharField` (id) | product (FK), quantity, supplier_name, cost_price, total_cost, date, received_by | → Product |
| **sales** | `SaleRecord` | `CharField` (id) | product (FK), dsr (FK nullable), customer_name, quantity, payment_type, collection_status, amount_paid, total_amount, is_closed_with_due | → Product, → DSR |
| **sales** | `CreditPayment` | `CharField` (id) | sale (FK), amount, date, received_by | → SaleRecord |
| **dsr** | `DSR` | `CharField` (id) | name, phone, role, parent_dsr (self-ref FK) | → self (parent), ← SaleRecord |
| **supplier** | `Supplier` | `CharField` (id) | name, phone, category | — (referenced by name in RestockRecord) |
| **dealer** | `DealerConfig` | `CharField` (username) | full_name, role, default_currency, default_locale | — (username is natural PK) |
| **reports** | — | — | No models. All data is aggregated via ORM queries. | — |

---

## API Endpoints (16 Total)

### Inventory (4)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/inventory` | List all products |
| POST | `/api/inventory/add` | Add new product (stock=0) |
| POST | `/api/inventory/restock` | Restock a product |
| POST | `/api/inventory/{id}/edit` | Partial update product |

### Sales (5)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sales` | List all sales |
| POST | `/api/sales` | Create single sale |
| POST | `/api/sales/bulk` | Create multiple sales |
| POST | `/api/sales/{id}/collect` | Collect payment on credit sale |
| POST | `/api/sales/{id}/close-with-due` | Write off sale as bad debt |

### DSR (2)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dsrs` | List all DSRs with active_sales_count |
| POST | `/api/dsrs` | Create DSR / Order Collector |

### Supplier (1)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/suppliers` | List all suppliers |

### Dealer (2)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dealers` | List dealer configs |
| POST | `/api/dealers/update` | Update dealer settings |

### Reports (2)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/reports/summary` | Full dashboard summary |
| POST | `/api/reports/ai-reconciliation` | AI reconciliation text |

---

## Setup Instructions

```bash
# 1. Create project (if starting fresh)
django-admin startproject dealercore .
# Then move the app folders inside

# 2. Install dependencies
pip install django ninja-extra pydantic

# 3. Add apps to INSTALLED_APPS (see settings_reference.py)
#    Add "ninja_extra" to INSTALLED_APPS (auto-includes ninja)

# 4. Run migrations
python manage.py makemigrations inventory sales dsr supplier dealer
python manage.py migrate

# 5. Seed dummy data
python manage.py seed_data                # Safe: skips existing records
python manage.py seed_data --flush        # Wipe + reseed fresh
python manage.py seed_data --flush --verbose   # Verbose output

# 6. Run async server
daphne dealercore.asgi:application --port 8088
# or
uvicorn dealercore.asgi:application --host 0.0.0.0 --port 8088 --reload

# 7. Access API docs
# http://localhost:8088/api/docs
```

---

## Seed Data

Two management commands are provided for populating the database with dummy data that exactly mirrors the frontend mock layer.

### Commands

| Command | Description |
|---------|-------------|
| `python manage.py seed_data` | Insert dummy data (idempotent — skips existing records via `get_or_create`) |
| `python manage.py seed_data --flush` | Delete all records, then insert fresh dummy data |
| `python manage.py seed_data --flush --verbose` | Same + print every created record |
| `python manage.py flush_data` | Delete all DEALERCORE records (with confirmation prompt) |
| `python manage.py flush_data --confirm` | Delete all records (no prompt) |

### Seed Data Counts

| Table | Records | Details |
|-------|---------|---------|
| Suppliers | 4 | Michelin Distributors, Castrol India, Bosch Parts Direct, Exide Industries |
| Products | 5 | Tyres, engine oil, spark plugs, batteries, brake pads |
| Restocks | 2 | prod-1 ×20 units, prod-2 ×10 units |
| DSRs | 4 | 3 DSRs + 1 Order Collector (Michael Chang → Rajesh Kumar) |
| Dealers | 4 | sanjay, rajesh, priya (USD), vijay |
| Sales | 3 | 1 cash sale (fully paid), 1 partial credit (with payment), 1 pending credit |
| Credit Payments | 1 | pay-1 on sale-2 |

### Data Source

Seed data is an **exact replica** of the frontend TypeScript mock layer (`src/services/mock/*.ts`). Same IDs, same values, same relationships. This ensures the frontend works identically whether hitting mock mode or the real backend.

---

## Entity Relationship Diagram

```
DealerConfig ──────────────────────── (independent)

DSR ──────┐
  │       │ self-ref (parent_dsr → DSR)
  ▼       ▼
SaleRecord ────── product → Product
  │                dsr → DSR (nullable)
  │
  └── CreditPayment (FK: sale → SaleRecord)

Product ────── RestockRecord (FK: product → Product)

Supplier ───── referenced by name in RestockRecord (no FK)
```

---

## Key Design Decisions

1. **String IDs** — Frontend uses `prod-1`, `sale-2` format. Backend generates the same format via `_generate_id()` helpers. This ensures frontend compatibility without UUID parsing.

2. **Denormalized Fields** — `product_name`, `supplier_name`, `dsr_name`, `parent_dsr_name` are stored as copies to avoid joins on list endpoints. These are set during create operations.

3. **CreditPayment as Separate Model** — Frontend embeds `payments[]` in SaleRecord, but Django uses a proper FK relationship. The API schema serializes payments as a nested list via reverse relation.

4. **DSR.active_sales_count** — Computed via Django ORM `Count` annotation with filter, not stored. Avoids stale data issues.

5. **Reports have no models** — All summary data is computed on-the-fly via ORM aggregations. No materialized views or cache tables (add as needed for performance).

6. **No DELETE endpoints** — Frontend has zero delete operations. All 16 endpoints are GET or POST only.

7. **DealerConfig.username as PK** — Username is the natural primary key, not an auto-increment integer.

8. **Class-based controllers** — All API views use `@api_controller` + `@route` decorators from `django-ninja-extra`. Organizes related endpoints into cohesive classes with shared helper methods.

9. **ModelSchema auto-generation** — Output schemas for `Product`, `RestockRecord`, `CreditPayment`, `DSR`, `Supplier`, `DealerConfig` are auto-generated from Django models via `ninja_extra.ModelSchema`. Only custom input schemas and computed-output schemas are defined manually.

---

## Frontend Integration

The frontend `apiClient.ts` sends requests to `VITE_API_BASE_URL`. Set:

```env
VITE_API_BASE_URL=http://localhost:8088/api
```

The frontend service layer (`src/services/api/*.ts`) maps 1:1 to these backend endpoints.
No URL changes needed — the paths are already aligned.
