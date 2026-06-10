import { Timestamp } from 'firebase/firestore';

export type GroupType = 'personal' | 'household' | 'trip' | 'other' | 'business' | 'freelance' | 'investment' | 'employment';
export type SplitType = 'equal' | 'percentage' | 'exact';
export type MemberRole = 'admin' | 'member';
export type BudgetType = 'weekly' | 'monthly' | 'total';

export interface UserProfile {
  uid: string;
  displayName: string | null;
  email: string | null;
  photoURL: string | null;
  createdAt: Timestamp;
  defaultCurrency?: string;
}

export interface Group {
  id: string;
  name: string;
  description?: string;
  createdBy: string;
  createdAt: Timestamp;
  type: GroupType;
  memberIds: string[];
  maxBudget?: number;
  budgetType?: BudgetType;
  currencyCode?: string; // Group's target currency or the owner's default currency
}

export interface GroupMember {
  uid: string;
  role: MemberRole;
  joinedAt: Timestamp;
  displayName?: string;
  email?: string;
}

export interface Expense {
  id: string;
  amount: number; // Converted amount in the default currency (for calculations and charts)
  description: string;
  category: string;
  paidBy: string; // userId
  date: Timestamp;
  createdAt: Timestamp;
  splitType: SplitType;
  currencyCode?: string;       // Original currency used for entry
  originalAmount?: number;     // Original input amount
  exchangeRateUsed?: number;   // Rate used for conversion: Converted = originalAmount * exchangeRateUsed
}

export const CATEGORIES = [
  'Food',
  'Rent',
  'Utilities',
  'Transport',
  'Entertainment',
  'Shopping',
  'Health',
  'Travel',
  'Other'
];

export interface SavingGoal {
  id: string;
  name: string;
  targetAmount: number;
  currencyCode: string;
  category: string;
  createdAt: Timestamp;
  createdBy: string;
}

export interface Deposit {
  id: string;
  amount: number; // Converted amount in goals' currency or default currency
  originalAmount: number; // Original input amount
  currencyCode: string; // Original currency used for deposit
  exchangeRateUsed?: number;
  depositedBy: string; // userId
  date: Timestamp;
  createdAt: Timestamp;
  note?: string;
}

export const SAVING_GOAL_CATEGORIES = [
  'Vacation & Travel',
  'Home & Property',
  'Vehicle & Transport',
  'Emergency Fund',
  'Gadget & Appliance',
  'Education',
  'Investment',
  'Other'
];

export interface IncomeTarget {
  id: string;
  name: string;
  targetAmount: number;
  currencyCode: string;
  category: string;
  createdAt: Timestamp;
  createdBy: string;
}

export interface IncomeRecord {
  id: string;
  amount: number; // Converted amount in targets' currency or default currency
  originalAmount: number; // Original input amount
  currencyCode: string; // Original currency used
  exchangeRateUsed?: number;
  receivedBy: string; // userId
  date: Timestamp;
  createdAt: Timestamp;
  note?: string;
  sourceType?: string; // e.g. Freelance, Bank Transfer, Cash, Check, etc.
}

export const INCOME_CATEGORIES = [
  'Salary & Wages',
  'Freelance & Consulting',
  'Investments & Dividends',
  'Rental Income',
  'Sales & E-Commerce',
  'Gifts & Grants',
  'Side Hustle',
  'Other'
];

export interface FinancialAccount {
  id: string;
  groupId: string;
  name: string;
  type: 'checking' | 'savings' | 'credit_card' | 'debit_card';
  bankName?: string;
  cardNumber?: string;
  balance: number;
  creditLimit?: number;
  color?: string;
  createdAt: Timestamp;
  createdBy: string;
}

export interface AccountTransaction {
  id: string;
  groupId: string;
  accountId: string;
  amount: number;
  description: string;
  category: string;
  date: Timestamp;
  createdAt: Timestamp;
  note?: string;
  transferToAccountId?: string;
  type: 'expense' | 'deposit' | 'transfer' | 'payment';
}

export const ACCOUNT_TRANSACTION_CATEGORIES = [
  'Dining Out',
  'Groceries',
  'Fuel & Transit',
  'Shopping',
  'Entertainment',
  'Utilities & Bills',
  'Salary & Deposit',
  'Card Payment',
  'Transfer',
  'Other'
];

export interface Loan {
  id: string;
  groupId: string;
  type: 'given' | 'taken'; // given = Lent by me, taken = Borrowed by me
  personName: string;
  amount: number;
  interestRate?: number;
  currencyCode: string;
  date: any; // Timestamp
  dueDate?: any; // Timestamp
  status: 'active' | 'settled';
  description?: string;
  createdAt: any; // Timestamp
  createdBy: string;
  isMortgage?: boolean;
  collateralName?: string;
  collateralValue?: number;
  downPayment?: number;
  amortizationYears?: number;
}

export interface LoanPayment {
  id: string;
  groupId: string;
  loanId: string;
  amount: number;
  date: any; // Timestamp
  note?: string;
  linkedAccountId?: string;
  linkedTransactionId?: string;
  createdAt: any; // Timestamp
}

export interface Mortgage {
  id: string;
  groupId: string;
  type: 'given' | 'taken'; // given = Lien/Mortgage we gave/lent, taken = Mortgage we took/borrowed
  personName: string; // mortgagor / mortgagee / financier name
  amount: number; // original principal loan level
  interestRate?: number;
  currencyCode: string;
  date: any; // Timestamp
  dueDate?: any; // Timestamp
  status: 'active' | 'settled';
  description?: string;
  createdAt: any; // Timestamp
  createdBy: string;
  collateralName: string; // property title
  collateralValue: number; // estimated asset value
  downPayment?: number; // up front payment
  amortizationYears?: number; // term of repayment
  mutuallySettled?: boolean;
  settledAt?: any;
}

export interface MortgagePayment {
  id: string;
  groupId: string;
  mortgageId: string;
  amount: number;
  date: any; // Timestamp
  note?: string;
  linkedAccountId?: string;
  linkedTransactionId?: string;
  createdAt: any; // Timestamp
}

export interface Rent {
  id: string;
  groupId: string;
  type: 'given' | 'taken'; // given = we lease out (tenant pays us rent), taken = we lease (we pay landlord rent)
  propertyName: string; // property/room/office address or unit
  tenantOrLandlord: string; // Name of tenant (if given) or landlord (if taken)
  amount: number; // rent amount per period
  frequency: 'monthly' | 'weekly' | 'yearly' | 'other';
  currencyCode: string;
  startDate: any; // Timestamp
  endDate?: any; // Timestamp optional lease end
  depositAmount?: number; // security deposit
  status: 'active' | 'settled'; // active lease or settled/terminated lease
  description?: string;
  createdAt: any; // Timestamp
  createdBy: string;
}

export interface RentPayment {
  id: string;
  groupId: string;
  rentId: string;
  amount: number;
  date: any; // Timestamp
  note?: string;
  linkedAccountId?: string;
  linkedTransactionId?: string;
  createdAt: any; // Timestamp
}
export interface VaultDocument {
  id: string;
  groupId: string;
  name: string;
  fileSize: number;
  fileType: string;
  description?: string;
  linkedService?: 'accounts' | 'loans_debts' | 'mortgages' | 'rent' | 'budget' | 'savings' | null;
  linkedEntityId?: string | null;
  fileData?: string; // base64 representation of file
  createdAt: any; // Timestamp
  createdBy: string;
}

