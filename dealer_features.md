# DEALERCORE v3.0 — Feature & Module Overview

DEALERCORE is a comprehensive Dealer & Supply Chain Management System designed to handle inventory, sales, payment collections, supplier management, representative routing, and financial reporting.

---

## 1. System Architecture & Tech Stack

- **Backend (`dealerbackend`):**
  - **Framework:** Python 3 + Django 5.2 (Async setup with Daphne).
  - **API Engine:** `django-ninja-extra` (Class-Based API controllers, ModelSchemas).
  - **Database:** SQLite (`dealer_db.sqlite3`).
  - **Key features:** Safe concurrent stock updates (using database-level `select_for_update()` row locks within custom async transaction manager `aatomic()`), atomic API endpoints, and clean separation between business logic and serialization.

- **Frontend (`dealerfrontend`):**
  - **Framework:** Astro 6.4 (Server-rendered mode) + Vue 3.5 (interactive UI pages).
  - **Styles:** TailwindCSS v4.
  - **Key features:** Centralized HTTP service client (`apiClient`) with automatic request case conversion (camelCase ↔ snake_case), premium glassmorphic modal design, real-time toast notifications, and interactive metrics charts (Chart.js / vue-chartjs).

---

## 2. Core Functional Modules

### 2.1 Dealer & Profile Configuration (`dealer`)
Allows managing settings, currency preferences, and localized context for the dealer or franchise owner.
- **Natural Primary Key:** Lookups are performed by `username` (natural key, e.g. `sanjay`).
- **Global Settings:** Profile fields include business name, registered GST number, address, phone number, communication number, email, and Google Maps location URL.
- **Localization:** Supports currency configuration (INR, USD, EUR, etc.) and locale preferences (e.g. `en-IN` for formatting).
- **Settings Switcher:** The UI allows switching between different dealer profiles dynamically, storing the active selection in `localStorage`.

### 2.2 Inventory & Stock Management (`inventory`)
Tracks materials, assets, and catalog items, automatically synchronizing with restocks and sales returns.
- **Product Registry:** SKU validation, category categorization, and brand autocomplete. Tracks current stock, minimum stock alert limits, unit cost (COGS), and retail selling price.
- **Restocking Ledger:** Tracks incoming stock shipments with details on quantity, supplier name, cost price per unit, total purchase value, date received, and processing manager. Restocking automatically increases the product's physical stock count.
- **Alert System:** Visual dashboard banners and red badges highlight items whose stock levels have dipped below their defined `min_stock_alert` threshold.

### 2.3 Sales, Dispatch, & Returns (`sales`)
Manages sales operations (cash/credit invoices, vehicle dispatches, items return, and void requests).
- **Cash Sales:** Immediate payment, automatically setting the collection status to `Fully Paid`.
- **Credit Sales:** Tracks deferred payments with due dates. System computes:
  - `net_amount` = `total_amount - return_total_amount` (actual customer obligation).
  - `balance_due` = `net_amount - amount_paid`.
- **Bulk Dispatch Roster:** Allows loggers to input a vehicle number, assign a route collector (DSR), and add multiple line rows for product, quantity, customer, payment terms, and initial payment in a single database transaction.
- **Product Returns:** Increments inventory stock, proportionally calculates return value, registers a `SaleReturn` audit record, and updates the sale's `return_total_amount`. Recalculates collection status against the reduced `net_amount`.
- **Voiding Transactions (Void Protection):** Completely reverses sales, restoring inventory stock. If money has changed hands (`amount_paid > 0` or payments exist), voiding is blocked unless `force=True` is provided, preventing accidental financial audit trail deletions.
- **Audit Trails:** Divides assignment into:
  - `original_dsr` (Immutable seller who made the sale - used for commission/performance).
  - `dsr` (Mutable collector current-assigned for payment collection).

### 2.4 Collections & Ledger Management (`sales` / `dsr`)
Tracks active credit invoice collections and routes payment collections.
- **Payment Collections:** Records credit payments (`CreditPayment`) with amount, date, and receiver. Decreases outstanding dues, updates invoice status (`Pending` ↔ `Partial` ↔ `Fully Paid`).
- **Bad Debt Write-Offs (`close-with-due`):** Closes the invoice, flag `is_closed_with_due=True`, sets status to `Written Off`. Excludes this sale from active credit dashboards, outstanding collections, DSR performance metrics, and customer outstanding totals. Tracks written-off amount separately for transparency.

### 2.5 DSR & Order Collector Hierarchy (`dsr`)
Manages the field representatives and order collectors.
- **Hierarchy Support:** Supports self-referential relations where Order Collectors (OCs) report to a parent Daily Sales Representative (DSR).
- **Workload Tracker:** Dynamically computes `active_sales_count` (excludes voided/written-off/paid invoices) to show collection workloads.

### 2.6 Financial Reporting & AI Reconciliation (`reports`)
Aggregates dealer performance data and outputs print-ready statements.
- **Overview Dashboard Summary:** Computes active revenue, COGS (total cost of restocks), gross profit, collected credit, outstanding credit, bad debt losses, low stock counts, product sales lists, and DSR totals.
- **Printable Statements:**
  - **Customer-wise Due:** Groups outstanding receivables by customer name.
  - **Vehicle-wise Due:** Groups outstanding credit sales by vehicle license plates.
  - **DSR-wise Due:** Groups active outstanding balances by the current collector (DSR).
- **AI Reconciliation:** Generates a summarized financial context report detailing pending credit invoices, written-off statistics, and unrecovered debt for LLM integration.

### 2.7 Supplier Management (`supplier`)
- Provides CRUD operations (name, phone, category) for restocking references.
