# Ledger — User Feature List

> Based on the Ledger Database Plan (21 models)  
> Organized by module and implementation phase

---

## Phase 1 — Core (Accounts & Transactions)

### Account Management
- **Create accounts** — Checking, Savings, Credit Card, Cash, Digital Wallet, Brokerage, Crypto
- **Group by institution** — Chase Checking + Chase Savings under "Chase Bank"
- **Multi-currency accounts** — USD checking, EUR savings, BDT cash — each account has its own currency
- **Account dashboard** — See all accounts with current balances at a glance
- **Available credit** — Credit cards show credit limit, used amount, and available credit
- **Credit card billing cycle** — Statement closing day & payment due day tracking
- **Interest rate tracking** — APR stored per account for credit cards and loans
- **Account colors & icons** — Customize each account's appearance
- **Manual sort order** — Drag-and-drop account ordering
- **Deactivate accounts** — Hide closed accounts without losing transaction history
- **Soft delete** — Accidentally deleted accounts can be recovered

### Institution Management
- **Add institutions** — Banks, credit unions, brokerages, crypto exchanges, digital wallets
- **Institution types** — Categorize as Bank, Credit Union, Brokerage, Crypto Exchange, Digital Wallet, Other
- **Quick links** — Store website and customer service phone number
- **Institution colors & icons** — Visual identification

### Transaction Management
- **Add transactions** — Income, Expense, Transfer, Refund — with explicit type selection
- **Multi-currency transactions** — Buy something in EUR on a USD account? System auto-converts and stores both amounts
- **Historical exchange rate capture** — Rate is frozen at transaction time, so your reports stay accurate even if rates change later
- **Current value display** — See what a foreign-currency transaction is worth today using latest rates
- **Payee tracking** — Record who you paid or who paid you ("Amazon", "Salary from Acme Corp")
- **Reference numbers** — Check numbers, bank transaction IDs for reconciliation
- **Transaction status** — Pending → Cleared → Void lifecycle
- **Search & filter** — By date range, account, category, payee, amount, status, tags
- **Bulk operations** — Categorize, tag, or status-change multiple transactions at once
- **Recurring transaction detection** — Auto-flag recurring payments

### Split Transactions
- **Split a single transaction** across multiple categories — e.g., a $100 Walmart purchase split into $60 Groceries + $30 Electronics + $10 Household
- **Validation** — System ensures split amounts don't exceed the original transaction total

### Internal Transfers
- **Transfer between accounts** — Pay credit card from checking? Two linked transactions showing the flow
- **Transfer pair linking** — The outflow and inflow are automatically linked as a pair
- **Excluded from reports** — Transfers don't count as income or expense in spending reports

### Category Management
- **Hierarchical categories** — Food → Groceries, Food → Dining Out
- **Income vs Expense** — Categories clearly marked as income or expense
- **Custom icons & colors** — Each category gets a distinct visual identity (essential for charts)
- **Sort order** — Arrange categories in your preferred order
- **Unique per level** — No duplicate category names at the same hierarchy level

---

## Phase 2 — Bills & Budgets

### Recurring Bills & Subscriptions
- **Add bills** — Netflix, Rent, Electricity, Insurance, Domain renewals, any recurring payment
- **Flexible recurrence** — Weekly, Bi-weekly, Monthly, Quarterly, Yearly, or One-time
- **Fixed vs variable amount** — Netflix is always $15.99; Electricity varies each month
- **Auto-advancing due dates** — System automatically calculates the next due date after each payment
- **Bill status lifecycle** — Active → Paused → Cancelled (pause a subscription without losing history)
- **Auto-generate transactions** — On due date, system creates a transaction automatically (Celery task)
- **Default account & category** — Bills remember which account pays them and which category to use
- **Bill payment history** — See every payment made for each bill with actual amounts (for variable bills)
- **Bill calendar view** — See all upcoming bills on a calendar
- **Pause & resume** — Temporarily pause a bill when you cancel a subscription but might resubscribe

### Bill Reminders
- **Custom reminders** — Get notified N days before a bill is due (default: 5 days)
- **Toggle per bill** — Enable/disable reminders individually

### Budget Management
- **Set budgets by category** — "I want to spend max $500 on Food this month"
- **Budget periods** — Weekly, Monthly, or Yearly budgets
- **Real-time tracking** — See how much you've spent vs. budget limit with percentage indicator
- **Budget remaining** — Instantly see how much you have left to spend
- **Progress visualization** — Color-coded progress bars (green → yellow → red as you approach limit)
- **Rollover budgets** — Optionally carry unspent amounts to the next period
- **Multi-currency budgets** — Budget in your base currency

### Tags
- **Create flat labels** — Unlike categories (one per transaction), tags are many-per-transaction
- **Cross-cutting filtering** — "Show me all #vacation2026 expenses across all categories"
- **Tag-based reports** — Spending breakdown by tag
- **Custom colors** — Each tag gets a distinct color
- **Examples** — #vacation2026, #tax-deductible, #business, #reimbursable, #shared-expense

---

## Phase 3 — Cards & Debt

### Card Management
- **Add cards to accounts** — Multiple cards per account (joint cards, debit + ATM on same checking)
- **Card types** — Debit or Credit
- **Card identification** — Name + last four digits for quick recognition
- **Expiry tracking** — Know when cards expire
- **Annual fee tracking** — Record annual fee amount and when it's charged
- **Card colors** — Match the physical card color for visual recognition
- **Transaction attribution** — Optionally tag which card was used for a transaction

### Debt & Loan Tracking
- **Track money borrowed** — Bank loans, mortgages, student loans, auto loans, personal loans, informal loans from family
- **Track money lent** — Personal loans you gave to others, mortgages you hold
- **Debt nature separation** — Clear distinction between "I owe someone" vs "Someone owes me"
- **Debt types** — Mortgage, Personal, Student, Auto, Business, Informal (friends/family)
- **Counterparty tracking** — Who is the lender or borrower
- **Institution linking** — Link bank loans to the Institution record
- **Payment schedule** — Monthly payment amount and payment day
- **Balance tracking** — Principal amount, remaining balance, progress percentage
- **Full payment history** — Every payment recorded with date, total amount, principal portion, interest portion, and extra payment
- **Amortization visibility** — See how much went to interest vs principal over time
- **Interest cost tracking** — Total interest paid on each debt
- **Auto-link to transactions** — Each debt payment can be linked to the corresponding transaction
- **Notes** — Store loan terms, verbal agreements, reference numbers

---

## Phase 4 — Investments

### Investment Portfolio
- **Investment accounts** — Dedicated account type for brokerage, crypto, and investment platforms
- **Portfolio dashboard** — Total portfolio value, total cost basis, total unrealized gain/loss
- **Gain/loss percentage** — See overall portfolio performance at a glance
- **Last sync timestamp** — Know how fresh your market data is

### Holdings (Individual Positions)
- **Track individual positions** — 10 shares AAPL, 0.5 BTC, $5,000 VTI
- **Asset types** — Stock, ETF, Cryptocurrency, Bond, Mutual Fund, Other
- **Cost basis tracking** — Total amount invested per position
- **Average purchase price** — Auto-calculated from cost basis / quantity
- **Current market price** — Updated via API integration
- **Current value** — Quantity × current price, auto-calculated
- **Unrealized gain/loss** — Per position, both dollar amount and percentage
- **Purchase date** — When the position was opened
- **Multi-currency** — Holdings in different currencies (US stocks in USD, Indian stocks in INR)

---

## Phase 5 — Goals, Insurance, Invoices, Vault

### Savings Goals
- **Create savings goals** — "Emergency Fund: $10,000", "Vacation: $3,000", "New Car: $25,000"
- **Progress tracking** — Percentage complete, remaining amount, visual progress bar
- **Deadline tracking** — Days remaining until goal deadline
- **Auto-completion** — Goal marked complete when target is reached
- **Link to account** — See which account holds the savings
- **Custom icons & colors** — Visual distinction between goals
- **Multi-currency** — Goals in different currencies

### Insurance Policy Tracking
- **Policy management** — Health, Auto, Home/Renters, Life, Travel, Business, Other
- **Premium tracking** — Amount, frequency (monthly/quarterly/yearly), next renewal date
- **Coverage details** — Coverage amount, deductible, detailed coverage notes
- **Provider tracking** — Insurance company name with optional Institution link
- **Policy numbers** — Quick reference for claims
- **Renewal reminders** — Get notified 30 days (configurable) before policy renewal
- **Document linking** — Attach policy documents from the Document Vault

### Freelancer Invoices
- **Create invoices** — Professional invoices with itemized line items
- **Invoice lifecycle** — Draft → Sent → Viewed → Partially Paid → Paid → Overdue → Cancelled
- **Client management** — Client name and email stored per invoice
- **Line items** — Description, quantity, unit price, total per line
- **Tax calculation** — Subtotal + tax = total amount
- **Partial payments** — Track amount paid vs. amount due
- **Overdue detection** — Auto-flag invoices past due date
- **Auto-create income transaction** — When invoice is paid, automatically create an income transaction
- **Payment terms** — Store terms like "Net 30", "Due on Receipt"
- **Invoice numbering** — Auto or manual invoice numbers with uniqueness enforcement
- **Multi-currency** — Invoice clients in their preferred currency

### Document Vault
- **Upload documents** — PDFs, images, spreadsheets, CSVs
- **Auto file type detection** — System recognizes PDF, PNG, JPG, Excel, CSV
- **File size tracking** — Know how much storage each document uses
- **Link to any entity** — Attach to Account, Transaction, InsurancePolicy, DebtFacility, etc.
- **Expiry tracking** — Documents like IDs and insurance policies have expiration dates
- **Expiry reminders** — Get notified before attached documents expire
- **Organized storage** — Files stored in year/month folders for easy management

---

## Cross-Cutting Features

### Multi-Currency (All Modules)
- **38 currencies supported** — Via base backend single source of truth
- **Automatic conversion** — Enter amount in any currency, system converts to your base currency
- **Historical rate capture** — Exchange rate frozen at transaction creation time
- **Current value display** — See what past foreign-currency transactions are worth today
- **Proper formatting** — Zero-decimal currencies (JPY, KRW) displayed without decimals; 2-decimal currencies shown correctly
- **Currency symbols** — Proper symbols (¥, €, £, ৳, ₹, ₩) from centralized metadata
- **Every monetary model has a currency field** — Accounts, Transactions, Debts, Bills, Budgets, Holdings, Goals, Insurance, Invoices

### Data Integrity
- **Soft deletes everywhere** — Nothing is permanently deleted; recoverable from admin
- **Active/inactive toggle** — Deactivate accounts, categories, goals without losing history
- **Denormalized balances** — Dashboard loads fast (balances pre-calculated)
- **Balance recalculation** — One-click recalculation from transaction history

### Search & Reporting
- **Transaction search** — By payee, category, tag, date range, amount range, account, status
- **Category spending reports** — How much did I spend on each category this month?
- **Income vs Expense** — Monthly, quarterly, yearly comparison
- **Budget vs Actual** — Are you staying within budget?
- **Net worth tracking** — Total assets minus total liabilities
- **Debt progress** — How much have you paid off?
- **Investment performance** — Unrealized gains/losses across portfolio
- **Tag-based reports** — "How much did #vacation2026 cost in total?"
- **Multi-currency reports** — All amounts converted to base currency for aggregation

### Notifications & Reminders
- **Bill due reminders** — N days before bill is due
- **Insurance renewal reminders** — N days before policy renewal
- **Document expiry reminders** — N days before attached documents expire
- **Credit card due date reminders** — Based on Account.due_day
- **Annual fee reminders** — Based on Card.annual_fee_date
- **Savings goal deadline reminders** — Approaching goal deadlines

### Dashboard Widgets
- **Account balances overview** — All accounts with current balances
- **Net worth summary** — Assets - Liabilities = Net Worth
- **Monthly spending breakdown** — Pie chart by category
- **Budget status** — Which budgets are on track, which are over?
- **Upcoming bills** — Next 7 days of due bills
- **Recent transactions** — Last 10 transactions across all accounts
- **Debt progress** — Progress bars for each debt
- **Savings goal progress** — Visual progress for each goal
- **Investment portfolio snapshot** — Total value, daily change, top holdings

---

## Feature Summary by Phase

| Phase | Module | User Features |
|---|---|---|
| **1** | Core | 6 account types, multi-currency transactions, split transactions, internal transfers, hierarchical categories, payee tracking |
| **2** | Bills & Budgets | Recurring bill management, auto-transaction generation, variable-amount bills, bill calendar, budget tracking, rollover budgets, tags |
| **3** | Cards & Debt | Card management, annual fee tracking, debt/loan tracking (both sides), amortization, payment history, interest tracking |
| **4** | Investments | Portfolio dashboard, per-position tracking, unrealized gains/losses, market data sync, multi-asset types |
| **5** | Extended | Savings goals, insurance tracking, freelancer invoicing, document vault, expiry reminders |

**Total: 80+ user-facing features across 5 implementation phases.**
