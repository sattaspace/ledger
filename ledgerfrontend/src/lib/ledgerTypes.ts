/**
 * TypeScript interfaces for the Ledger Backend API.
 *
 * These types mirror the Django Ninja schemas in ledgerbackend/api/schemas/.
 * Keep them in sync with the backend schema definitions.
 *
 * Naming convention:
 *   - *Out      → Full response (read)
 *   - *ListOut  → Lightweight response for list/dropdown
 *   - *Create   → Request body for POST
 *   - *Update   → Request body for PATCH (all optional)
 *   - *Filter   → Query parameters for list endpoints
 *   - *TreeOut  → Hierarchical tree response
 *
 * Backend DecimalField → string (JSON serializes Decimal as string)
 * Backend date/datetime → string (ISO 8601)
 */

// =============================================================================
// Common — Pagination, Responses, Filters
// =============================================================================

/** Pagination parameters for list endpoints. */
export interface PaginationIn {
  limit?: number;
  offset?: number;
}

/** Pagination metadata returned with list responses. */
export interface PaginationOut {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

/** Generic paginated list response. */
export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationOut;
}

/** Simple message response for delete/restore/activate/deactivate. */
export interface MessageOut {
  detail: string;
}

/** Standard error response. */
export interface ErrorResponse {
  detail: string;
}

/** Validation error with field-level details. */
export interface ValidationErrorOut {
  detail: string;
  errors?: Record<string, string[]>;
}

/** Response for bulk soft-delete operations. */
export interface BulkDeleteOut {
  deleted_count: number;
  detail: string;
}

/** Response for bulk restore operations. */
export interface BulkRestoreOut {
  restored_count: number;
  detail: string;
}

// =============================================================================
// Core — Institution
// =============================================================================

export type InstitutionType = "BANK" | "CREDIT_UNION" | "BROKERAGE" | "CRYPTO" | "WALLET" | "OTHER";

export interface InstitutionCreate {
  name: string;
  institution_type?: InstitutionType;
  website?: string | null;
  customer_service_phone?: string | null;
  icon?: string | null;
  color?: string | null;
  notes?: string | null;
}

export interface InstitutionUpdate {
  name?: string | null;
  institution_type?: InstitutionType | null;
  website?: string | null;
  customer_service_phone?: string | null;
  icon?: string | null;
  color?: string | null;
  notes?: string | null;
}

export interface InstitutionOut {
  id: number;
  user_id: number;
  name: string;
  institution_type: string;
  website: string;
  customer_service_phone: string;
  icon: string;
  color: string;
  notes: string;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface InstitutionListOut {
  id: number;
  name: string;
  institution_type: string;
  icon: string;
  color: string;
}

export interface InstitutionFilter extends PaginationIn {
  institution_type?: string | null;
  search?: string | null;
}

// =============================================================================
// Core — Account
// =============================================================================

export type AccountType = "ASSET" | "LIABILITY" | "INVESTMENT";

export interface AccountCreate {
  name: string;
  institution_id: number;
  account_type?: AccountType;
  currency?: string;
  current_balance?: string;
  credit_limit?: string | null;
  interest_rate?: string;
  statement_closing_day?: number | null;
  due_day?: number | null;
  icon?: string | null;
  color?: string | null;
  notes?: string | null;
  sort_order?: number;
}

export interface AccountUpdate {
  name?: string | null;
  institution_id?: number | null;
  account_type?: AccountType | null;
  currency?: string | null;
  current_balance?: string | null;
  credit_limit?: string | null;
  interest_rate?: string | null;
  statement_closing_day?: number | null;
  due_day?: number | null;
  icon?: string | null;
  color?: string | null;
  notes?: string | null;
  sort_order?: number | null;
}

export interface AccountOut {
  id: number;
  user_id: number;
  name: string;
  institution_id: number;
  account_type: string;
  currency: string;
  current_balance: string;
  credit_limit: string | null;
  interest_rate: string;
  statement_closing_day: number | null;
  due_day: number | null;
  icon: string;
  color: string;
  notes: string;
  sort_order: number;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  // Computed
  available_credit: string | null;
  currency_symbol: string;
}

export interface AccountListOut {
  id: number;
  name: string;
  institution_id: number;
  account_type: string;
  currency: string;
  current_balance: string;
  icon: string;
  color: string;
  is_active: boolean;
}

export interface AccountFilter extends PaginationIn {
  account_type?: string | null;
  institution_id?: number | null;
  currency?: string | null;
  is_active?: boolean | null;
  search?: string | null;
}

export interface BalanceRecalculateOut {
  account_id: number;
  old_balance: string;
  new_balance: string;
  detail: string;
}

// =============================================================================
// Core — Transaction
// =============================================================================

export type TransactionType = "INCOME" | "EXPENSE" | "TRANSFER" | "REFUND";
export type TransactionStatus = "PENDING" | "CLEARED" | "VOID";

export interface TransactionCreate {
  date: string;
  account_id: number;
  card_id?: number | null;
  transaction_type?: TransactionType;
  amount_original: string;
  currency_original?: string;
  amount_base?: string | null;
  exchange_rate?: string | null;
  category_id?: number | null;
  status?: TransactionStatus;
  payee?: string | null;
  description?: string | null;
  reference_number?: string | null;
  is_recurring?: boolean;
  bill_id?: number | null;
}

export interface TransactionUpdate {
  date?: string | null;
  account_id?: number | null;
  card_id?: number | null;
  transaction_type?: TransactionType | null;
  amount_original?: string | null;
  currency_original?: string | null;
  amount_base?: string | null;
  exchange_rate?: string | null;
  category_id?: number | null;
  status?: TransactionStatus | null;
  payee?: string | null;
  description?: string | null;
  reference_number?: string | null;
  is_recurring?: boolean | null;
  bill_id?: number | null;
}

export interface TransactionOut {
  id: number;
  user_id: number;
  date: string;
  account_id: number;
  card_id: number | null;
  transaction_type: string;
  amount_original: string;
  currency_original: string;
  amount_base: string;
  exchange_rate: string;
  category_id: number | null;
  status: string;
  payee: string;
  description: string;
  reference_number: string;
  transfer_pair_id: number | null;
  is_recurring: boolean;
  bill_id: number | null;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface TransactionListOut {
  id: number;
  date: string;
  account_id: number;
  transaction_type: string;
  amount_original: string;
  currency_original: string;
  amount_base: string;
  status: string;
  payee: string;
  category_id: number | null;
  is_recurring: boolean;
}

export interface TransactionFilter extends PaginationIn {
  account_id?: number | null;
  category_id?: number | null;
  transaction_type?: string | null;
  status?: string | null;
  card_id?: number | null;
  currency_original?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  amount_min?: string | null;
  amount_max?: string | null;
  search?: string | null;
  is_recurring?: boolean | null;
}

// =============================================================================
// Core — Transfer
// =============================================================================

export interface TransferCreate {
  date: string;
  from_account_id: number;
  to_account_id: number;
  amount: string;
  currency?: string;
  description?: string | null;
  status?: TransactionStatus;
}

export interface TransferOut {
  outflow_transaction_id: number;
  inflow_transaction_id: number;
  detail: string;
}

// =============================================================================
// Core — TransactionSplit
// =============================================================================

export interface TransactionSplitCreate {
  transaction_id: number;
  category_id?: number | null;
  amount: string;
  notes?: string | null;
}

export interface TransactionSplitUpdate {
  category_id?: number | null;
  amount?: string | null;
  notes?: string | null;
}

export interface TransactionSplitOut {
  id: number;
  user_id: number;
  transaction_id: number;
  category_id: number | null;
  amount: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

// =============================================================================
// Categories — Category
// =============================================================================

export interface CategoryCreate {
  name: string;
  icon?: string | null;
  color?: string | null;
  parent_id?: number | null;
  is_income?: boolean;
  sort_order?: number;
}

export interface CategoryUpdate {
  name?: string | null;
  icon?: string | null;
  color?: string | null;
  parent_id?: number | null;
  is_income?: boolean | null;
  sort_order?: number | null;
}

export interface CategoryOut {
  id: number;
  user_id: number;
  name: string;
  icon: string;
  color: string;
  parent_id: number | null;
  is_income: boolean;
  sort_order: number;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategoryListOut {
  id: number;
  name: string;
  parent_id: number | null;
  is_income: boolean;
  icon: string;
  color: string;
}

export interface CategoryTreeOut {
  id: number;
  name: string;
  icon: string;
  color: string;
  is_income: boolean;
  sort_order: number;
  subcategories: CategoryTreeOut[];
}

export interface CategoryFilter extends PaginationIn {
  is_income?: boolean | null;
  parent_id?: number | null;
  search?: string | null;
}

// =============================================================================
// Categories — Tag
// =============================================================================

export interface TagCreate {
  name: string;
  color?: string | null;
}

export interface TagUpdate {
  name?: string | null;
  color?: string | null;
}

export interface TagOut {
  id: number;
  user_id: number;
  name: string;
  color: string;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface TagListOut {
  id: number;
  name: string;
  color: string;
}

export interface TagFilter extends PaginationIn {
  search?: string | null;
}

// =============================================================================
// Categories — TransactionTag
// =============================================================================

export interface TransactionTagCreate {
  transaction_id: number;
  tag_id: number;
}

export interface TransactionTagOut {
  id: number;
  user_id: number;
  transaction_id: number;
  tag_id: number;
  created_at: string;
  updated_at: string;
}

export interface TransactionTagBulkCreate {
  transaction_id: number;
  tag_ids: number[];
}

export interface TransactionTagBulkOut {
  transaction_id: number;
  tag_ids: number[];
  detail: string;
}

// =============================================================================
// Cards — Card
// =============================================================================

export type CardType = "DEBIT" | "CREDIT";

export interface CardCreate {
  account_id: number;
  card_type: CardType;
  card_name: string;
  last_four: string;
  expiry_date?: string | null;
  annual_fee?: string;
  annual_fee_date?: string | null;
  color?: string | null;
  sort_order?: number;
}

export interface CardUpdate {
  account_id?: number | null;
  card_type?: CardType | null;
  card_name?: string | null;
  last_four?: string | null;
  expiry_date?: string | null;
  annual_fee?: string | null;
  annual_fee_date?: string | null;
  color?: string | null;
  sort_order?: number | null;
}

export interface CardOut {
  id: number;
  user_id: number;
  account_id: number;
  card_type: string;
  card_name: string;
  last_four: string;
  expiry_date: string | null;
  annual_fee: string;
  annual_fee_date: string | null;
  color: string;
  sort_order: number;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface CardListOut {
  id: number;
  account_id: number;
  card_type: string;
  card_name: string;
  last_four: string;
  color: string;
}

export interface CardFilter extends PaginationIn {
  account_id?: number | null;
  card_type?: string | null;
  search?: string | null;
}

// =============================================================================
// Bills — Bill
// =============================================================================

export type BillRecurrence =
  | "WEEKLY"
  | "BIWEEKLY"
  | "MONTHLY"
  | "QUARTERLY"
  | "YEARLY"
  | "ONE_TIME";
export type BillStatus = "ACTIVE" | "PAUSED" | "CANCELLED";

export interface BillCreate {
  payee: string;
  amount: string;
  currency?: string;
  is_amount_fixed?: boolean;
  recurrence?: BillRecurrence;
  start_date: string;
  end_date?: string | null;
  next_due_date: string;
  account_id?: number | null;
  category_id?: number | null;
  status?: BillStatus;
  remind_me?: boolean;
  days_before_reminder?: number;
  notes?: string | null;
}

export interface BillUpdate {
  payee?: string | null;
  amount?: string | null;
  currency?: string | null;
  is_amount_fixed?: boolean | null;
  recurrence?: BillRecurrence | null;
  start_date?: string | null;
  end_date?: string | null;
  next_due_date?: string | null;
  account_id?: number | null;
  category_id?: number | null;
  status?: BillStatus | null;
  remind_me?: boolean | null;
  days_before_reminder?: number | null;
  notes?: string | null;
}

export interface BillOut {
  id: number;
  user_id: number;
  payee: string;
  amount: string;
  currency: string;
  is_amount_fixed: boolean;
  recurrence: string;
  start_date: string;
  end_date: string | null;
  next_due_date: string;
  account_id: number | null;
  category_id: number | null;
  status: string;
  remind_me: boolean;
  days_before_reminder: number;
  notes: string;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface BillListOut {
  id: number;
  payee: string;
  amount: string;
  currency: string;
  recurrence: string;
  next_due_date: string;
  status: string;
  is_amount_fixed: boolean;
}

export interface BillFilter extends PaginationIn {
  status?: string | null;
  recurrence?: string | null;
  account_id?: number | null;
  category_id?: number | null;
  due_within_days?: number | null;
  search?: string | null;
}

export interface BillGenerateTransactionOut {
  transaction_id: number;
  bill_id: number;
  next_due_date: string;
  detail: string;
}

// =============================================================================
// Bills — BillPayment
// =============================================================================

export interface BillPaymentCreate {
  bill_id: number;
  payment_date: string;
  amount: string;
  transaction_id?: number | null;
  notes?: string | null;
}

export interface BillPaymentUpdate {
  payment_date?: string | null;
  amount?: string | null;
  transaction_id?: number | null;
  notes?: string | null;
}

export interface BillPaymentOut {
  id: number;
  user_id: number;
  bill_id: number;
  payment_date: string;
  amount: string;
  transaction_id: number | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface BillPaymentFilter extends PaginationIn {
  bill_id?: number | null;
  date_from?: string | null;
  date_to?: string | null;
}

// =============================================================================
// Debt — DebtFacility
// =============================================================================

export type DebtNature = "MONEY_BORROWED" | "MONEY_LENT";
export type DebtType = "MORTGAGE" | "PERSONAL" | "STUDENT" | "AUTO" | "BUSINESS" | "INFORMAL";

export interface DebtFacilityCreate {
  name: string;
  debt_nature: DebtNature;
  debt_type: DebtType;
  entity_name: string;
  institution_id?: number | null;
  principal_amount: string;
  remaining_balance: string;
  currency?: string;
  interest_rate?: string;
  start_date: string;
  end_date?: string | null;
  term_months?: number | null;
  monthly_payment?: string;
  payment_day?: number | null;
  account_id?: number | null;
  notes?: string | null;
}

export interface DebtFacilityUpdate {
  name?: string | null;
  debt_nature?: DebtNature | null;
  debt_type?: DebtType | null;
  entity_name?: string | null;
  institution_id?: number | null;
  principal_amount?: string | null;
  remaining_balance?: string | null;
  currency?: string | null;
  interest_rate?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  term_months?: number | null;
  monthly_payment?: string | null;
  payment_day?: number | null;
  account_id?: number | null;
  notes?: string | null;
}

export interface DebtFacilityOut {
  id: number;
  user_id: number;
  name: string;
  debt_nature: string;
  debt_type: string;
  entity_name: string;
  institution_id: number | null;
  principal_amount: string;
  remaining_balance: string;
  currency: string;
  interest_rate: string;
  start_date: string;
  end_date: string | null;
  term_months: number | null;
  monthly_payment: string;
  payment_day: number | null;
  account_id: number | null;
  notes: string;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  // Computed
  is_mine: boolean;
  progress_percent: number;
}

export interface DebtFacilityListOut {
  id: number;
  name: string;
  debt_nature: string;
  debt_type: string;
  entity_name: string;
  principal_amount: string;
  remaining_balance: string;
  currency: string;
  interest_rate: string;
  monthly_payment: string;
  progress_percent: number;
}

export interface DebtFacilityFilter extends PaginationIn {
  debt_nature?: string | null;
  debt_type?: string | null;
  institution_id?: number | null;
  is_active?: boolean | null;
  search?: string | null;
}

/** Debt summary response from GET /debts/summary. */
export interface DebtSummary {
  total_borrowed: string;
  total_lent: string;
  net_position: string;
}

// =============================================================================
// Debt — DebtPayment
// =============================================================================

export interface DebtPaymentCreate {
  debt_id: number;
  payment_date: string;
  amount: string;
  principal_portion?: string;
  interest_portion?: string;
  extra_payment?: string;
  transaction_id?: number | null;
  notes?: string | null;
}

export interface DebtPaymentUpdate {
  payment_date?: string | null;
  amount?: string | null;
  principal_portion?: string | null;
  interest_portion?: string | null;
  extra_payment?: string | null;
  transaction_id?: number | null;
  notes?: string | null;
}

export interface DebtPaymentOut {
  id: number;
  user_id: number;
  debt_id: number;
  payment_date: string;
  amount: string;
  principal_portion: string;
  interest_portion: string;
  extra_payment: string;
  transaction_id: number | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface DebtPaymentFilter extends PaginationIn {
  debt_id?: number | null;
  date_from?: string | null;
  date_to?: string | null;
}

// =============================================================================
// Budgets — Budget
// =============================================================================

export type BudgetPeriod = "WEEKLY" | "MONTHLY" | "YEARLY";

export interface BudgetCreate {
  category_id: number;
  amount: string;
  currency?: string;
  period?: BudgetPeriod;
  start_date: string;
  allow_rollover?: boolean;
}

export interface BudgetUpdate {
  category_id?: number | null;
  amount?: string | null;
  currency?: string | null;
  period?: BudgetPeriod | null;
  start_date?: string | null;
  allow_rollover?: boolean | null;
}

export interface BudgetOut {
  id: number;
  user_id: number;
  category_id: number;
  amount: string;
  currency: string;
  period: string;
  start_date: string;
  allow_rollover: boolean;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  // Computed
  spent_amount: string;
  remaining: string;
  percent_used: number;
}

export interface BudgetListOut {
  id: number;
  category_id: number;
  amount: string;
  currency: string;
  period: string;
  spent_amount: string;
  remaining: string;
  percent_used: number;
}

export interface BudgetFilter extends PaginationIn {
  category_id?: number | null;
  period?: string | null;
  currency?: string | null;
}

// =============================================================================
// Investments — InvestmentAccount
// =============================================================================

export interface InvestmentAccountCreate {
  account_id: number;
  portfolio_value?: string;
  cost_basis_total?: string;
  last_synced_at?: string | null;
}

export interface InvestmentAccountUpdate {
  portfolio_value?: string | null;
  cost_basis_total?: string | null;
  last_synced_at?: string | null;
}

export interface InvestmentAccountOut {
  id: number;
  user_id: number;
  account_id: number;
  portfolio_value: string;
  cost_basis_total: string;
  last_synced_at: string | null;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  // Computed
  unrealized_gain_loss: string;
  unrealized_gain_loss_percent: number;
}

export interface InvestmentAccountListOut {
  id: number;
  account_id: number;
  portfolio_value: string;
  cost_basis_total: string;
  unrealized_gain_loss: string;
  unrealized_gain_loss_percent: number;
}

/** Investment summary response from GET /investments/summary. */
export interface InvestmentSummary {
  total_portfolio_value: string;
  total_cost_basis: string;
  total_unrealized_gain_loss: string;
  total_gain_loss_percent: number;
  account_count: number;
}

// =============================================================================
// Investments — Holding
// =============================================================================

export type AssetType = "STOCK" | "ETF" | "CRYPTO" | "BOND" | "MUTUAL_FUND" | "OTHER";

export interface HoldingCreate {
  investment_account_id: number;
  symbol: string;
  asset_name: string;
  asset_type: AssetType;
  quantity: string;
  cost_basis: string;
  current_price?: string | null;
  current_value?: string | null;
  currency?: string;
  purchase_date?: string | null;
  last_price_update?: string | null;
}

export interface HoldingUpdate {
  symbol?: string | null;
  asset_name?: string | null;
  asset_type?: AssetType | null;
  quantity?: string | null;
  cost_basis?: string | null;
  current_price?: string | null;
  current_value?: string | null;
  currency?: string | null;
  purchase_date?: string | null;
  last_price_update?: string | null;
}

export interface HoldingOut {
  id: number;
  user_id: number;
  investment_account_id: number;
  symbol: string;
  asset_name: string;
  asset_type: string;
  quantity: string;
  cost_basis: string;
  current_price: string | null;
  current_value: string | null;
  currency: string;
  purchase_date: string | null;
  last_price_update: string | null;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  // Computed
  unrealized_gain_loss: string | null;
  average_purchase_price: string | null;
}

export interface HoldingListOut {
  id: number;
  investment_account_id: number;
  symbol: string;
  asset_name: string;
  asset_type: string;
  quantity: string;
  cost_basis: string;
  current_value: string | null;
  currency: string;
  unrealized_gain_loss: string | null;
}

export interface HoldingFilter extends PaginationIn {
  investment_account_id?: number | null;
  asset_type?: string | null;
  currency?: string | null;
  search?: string | null;
}

// =============================================================================
// Goals — SavingsGoal
// =============================================================================

export interface SavingsGoalCreate {
  name: string;
  target_amount: string;
  current_amount?: string;
  currency?: string;
  deadline?: string | null;
  account_id?: number | null;
  icon?: string | null;
  color?: string | null;
}

export interface SavingsGoalUpdate {
  name?: string | null;
  target_amount?: string | null;
  current_amount?: string | null;
  currency?: string | null;
  deadline?: string | null;
  account_id?: number | null;
  icon?: string | null;
  color?: string | null;
}

export interface SavingsGoalOut {
  id: number;
  user_id: number;
  name: string;
  target_amount: string;
  current_amount: string;
  currency: string;
  deadline: string | null;
  account_id: number | null;
  icon: string;
  color: string;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  // Computed
  progress_percent: number;
  remaining: string;
  is_completed: boolean;
  days_remaining: number | null;
}

export interface SavingsGoalListOut {
  id: number;
  name: string;
  target_amount: string;
  current_amount: string;
  currency: string;
  deadline: string | null;
  progress_percent: number;
  is_completed: boolean;
  days_remaining: number | null;
  icon: string;
  color: string;
}

export interface SavingsGoalFilter extends PaginationIn {
  is_completed?: boolean | null;
  currency?: string | null;
  account_id?: number | null;
}

export interface SavingsContribution {
  amount: string;
  account_id: number;
  date?: string | null;
  notes?: string | null;
}

export interface SavingsContributionOut {
  goal_id: number;
  old_amount: string;
  new_amount: string;
  transaction_id: number | null;
  detail: string;
}

// =============================================================================
// Insurance — InsurancePolicy
// =============================================================================

export type InsuranceType = "HEALTH" | "AUTO" | "HOME" | "LIFE" | "TRAVEL" | "BUSINESS" | "OTHER";
export type PremiumFrequency = "MONTHLY" | "QUARTERLY" | "YEARLY";

export interface InsurancePolicyCreate {
  policy_name: string;
  insurance_type?: InsuranceType;
  provider: string;
  institution_id?: number | null;
  policy_number?: string | null;
  premium_amount: string;
  currency?: string;
  premium_frequency?: PremiumFrequency;
  renewal_date: string;
  coverage_amount?: string | null;
  coverage_details?: string | null;
  deductible?: string | null;
  remind_renewal?: boolean;
  days_before_renewal_reminder?: number;
}

export interface InsurancePolicyUpdate {
  policy_name?: string | null;
  insurance_type?: InsuranceType | null;
  provider?: string | null;
  institution_id?: number | null;
  policy_number?: string | null;
  premium_amount?: string | null;
  currency?: string | null;
  premium_frequency?: PremiumFrequency | null;
  renewal_date?: string | null;
  coverage_amount?: string | null;
  coverage_details?: string | null;
  deductible?: string | null;
  remind_renewal?: boolean | null;
  days_before_renewal_reminder?: number | null;
}

export interface InsurancePolicyOut {
  id: number;
  user_id: number;
  policy_name: string;
  insurance_type: string;
  provider: string;
  institution_id: number | null;
  policy_number: string;
  premium_amount: string;
  currency: string;
  premium_frequency: string;
  renewal_date: string;
  coverage_amount: string | null;
  coverage_details: string;
  deductible: string | null;
  remind_renewal: boolean;
  days_before_renewal_reminder: number;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface InsurancePolicyListOut {
  id: number;
  policy_name: string;
  insurance_type: string;
  provider: string;
  premium_amount: string;
  currency: string;
  premium_frequency: string;
  renewal_date: string;
}

export interface InsurancePolicyFilter extends PaginationIn {
  insurance_type?: string | null;
  provider?: string | null;
  premium_frequency?: string | null;
  renewal_within_days?: number | null;
  search?: string | null;
}

// =============================================================================
// Invoices — Invoice
// =============================================================================

export type InvoiceStatus =
  | "DRAFT"
  | "SENT"
  | "VIEWED"
  | "PARTIAL"
  | "PAID"
  | "OVERDUE"
  | "CANCELLED";

export interface InvoiceCreate {
  invoice_number: string;
  client_name: string;
  client_email?: string | null;
  issue_date: string;
  due_date: string;
  subtotal?: string;
  tax_amount?: string;
  total_amount: string;
  amount_paid?: string;
  currency?: string;
  status?: InvoiceStatus;
  transaction_id?: number | null;
  notes?: string | null;
  terms?: string | null;
}

export interface InvoiceUpdate {
  invoice_number?: string | null;
  client_name?: string | null;
  client_email?: string | null;
  issue_date?: string | null;
  due_date?: string | null;
  paid_date?: string | null;
  subtotal?: string | null;
  tax_amount?: string | null;
  total_amount?: string | null;
  amount_paid?: string | null;
  currency?: string | null;
  status?: InvoiceStatus | null;
  transaction_id?: number | null;
  notes?: string | null;
  terms?: string | null;
}

export interface InvoiceOut {
  id: number;
  user_id: number;
  invoice_number: string;
  client_name: string;
  client_email: string;
  issue_date: string;
  due_date: string;
  paid_date: string | null;
  subtotal: string;
  tax_amount: string;
  total_amount: string;
  amount_paid: string;
  currency: string;
  status: string;
  transaction_id: number | null;
  notes: string;
  terms: string;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  // Computed
  amount_due: string;
  is_overdue: boolean;
}

export interface InvoiceListOut {
  id: number;
  invoice_number: string;
  client_name: string;
  issue_date: string;
  due_date: string;
  total_amount: string;
  amount_paid: string;
  amount_due: string;
  currency: string;
  status: string;
  is_overdue: boolean;
}

export interface InvoiceFilter extends PaginationIn {
  status?: string | null;
  client_name?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  is_overdue?: boolean | null;
  currency?: string | null;
  search?: string | null;
}

export interface InvoiceMarkPaid {
  paid_date: string;
  amount_paid?: string | null;
  transaction_id?: number | null;
}

// =============================================================================
// Invoices — InvoiceLineItem
// =============================================================================

export interface InvoiceLineItemCreate {
  invoice_id: number;
  description: string;
  quantity?: string;
  unit_price: string;
  total: string;
}

export interface InvoiceLineItemUpdate {
  description?: string | null;
  quantity?: string | null;
  unit_price?: string | null;
  total?: string | null;
}

export interface InvoiceLineItemOut {
  id: number;
  user_id: number;
  invoice_id: number;
  description: string;
  quantity: string;
  unit_price: string;
  total: string;
  created_at: string;
  updated_at: string;
}

// =============================================================================
// Vault — DocumentVault
// =============================================================================

export type VaultFileType = "PDF" | "PNG" | "JPG" | "XLSX" | "CSV" | "OTHER";

export interface DocumentVaultCreate {
  title: string;
  file_type?: VaultFileType | null;
  file_size?: number;
  expiry_date?: string | null;
  remind_before_expiry?: boolean;
  days_before_expiry_reminder?: number;
  content_type_id: number;
  object_id: number;
}

export interface DocumentVaultUpdate {
  title?: string | null;
  file_type?: VaultFileType | null;
  file_size?: number | null;
  expiry_date?: string | null;
  remind_before_expiry?: boolean | null;
  days_before_expiry_reminder?: number | null;
  content_type_id?: number | null;
  object_id?: number | null;
}

export interface DocumentVaultOut {
  id: number;
  user_id: number;
  title: string;
  file: string;
  file_type: string;
  file_size: number;
  expiry_date: string | null;
  remind_before_expiry: boolean;
  days_before_expiry_reminder: number;
  content_type_id: number;
  object_id: number;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentVaultListOut {
  id: number;
  title: string;
  file_type: string;
  file_size: number;
  expiry_date: string | null;
  content_type_id: number;
  object_id: number;
}

export interface DocumentVaultFilter extends PaginationIn {
  content_type_id?: number | null;
  object_id?: number | null;
  file_type?: string | null;
  expiring_within_days?: number | null;
  search?: string | null;
}

// =============================================================================
// Reusable Union / Helper Types
// =============================================================================

/** All entity types that support soft-delete (DELETE + restore). */
export type SoftDeletableEntity =
  | "institution"
  | "account"
  | "category"
  | "transaction"
  | "card"
  | "bill"
  | "debt"
  | "budget"
  | "investment"
  | "savings_goal"
  | "insurance"
  | "invoice"
  | "document";

/** All entity types that support activate/deactivate. */
export type ActivatableEntity =
  | "institution"
  | "account"
  | "category"
  | "card"
  | "debt"
  | "budget"
  | "savings_goal"
  | "insurance"
  | "document";

/** Monetary amount with currency — used for display components. */
export interface MoneyDisplay {
  amount: string;
  currency: string;
  formatted: string;
  symbol: string;
}

/** Generic dropdown option — returned by /dropdown endpoints. */
export interface DropdownOption {
  id: number;
  label: string;
  secondary?: string;
  icon?: string;
  color?: string;
}

/** Content type mapping for DocumentVault generic relations. */
export interface ContentTypeMap {
  [modelName: string]: number;
}
