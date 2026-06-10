import { ref } from 'vue';
import { db } from '../firebase';
import { 
  collection, 
  doc, 
  addDoc, 
  setDoc,
  updateDoc, 
  deleteDoc, 
  onSnapshot, 
  query, 
  orderBy, 
  serverTimestamp,
  getDoc,
  getDocs
} from 'firebase/firestore';
import { 
  type Group, 
  type Expense, 
  type SavingGoal, 
  type Deposit, 
  type GroupMember,
  type IncomeTarget,
  type IncomeRecord,
  type FinancialAccount,
  type AccountTransaction,
  type Loan,
  type LoanPayment,
  type Mortgage,
  type MortgagePayment,
  type Rent,
  type RentPayment,
  type VaultDocument
} from '../types';

/**
 * ============================================================================
 * CENTRALIZED DATA & API COMMUNICATION SERVICE
 * ============================================================================
 * This service acts as the central hub for database operations.
 * If the application is migrated to standard REST endpoints, Firebase backend, or Cloud SQL, 
 * this is the single file that needs to be updated.
 */

// === 1. GLOBAL GROUPS SERVICE ===
export function subscribeAllGroups(callback: (groups: Group[]) => void) {
  const colRef = collection(db, 'groups');
  return onSnapshot(colRef, (snap) => {
    const list = snap.docs.map(doc => ({ id: doc.id, ...doc.data() } as Group));
    callback(list);
  });
}

export function subscribeGroupDetail(groupId: string, callback: (g: Group) => void) {
  const docRef = doc(db, 'groups', groupId);
  return onSnapshot(docRef, (snap) => {
    if (snap.exists()) {
      callback({ id: snap.id, ...snap.data() } as Group);
    }
  });
}

export async function createGroup(groupData: any) {
  return await addDoc(collection(db, 'groups'), {
    ...groupData,
    createdAt: serverTimestamp()
  });
}

export async function updateGroupSettings(groupId: string, data: Partial<Group>) {
  const docRef = doc(db, 'groups', groupId);
  return await updateDoc(docRef, data);
}

export async function deleteGroup(groupId: string) {
  const docRef = doc(db, 'groups', groupId);
  return await deleteDoc(docRef);
}

// === 2. MEMBERS MANAGEMENT ===
export function subscribeGroupMembers(groupId: string, callback: (members: GroupMember[]) => void) {
  const colRef = collection(db, 'groups', groupId, 'members');
  return onSnapshot(colRef, (snap) => {
    const list = snap.docs.map(d => ({ uid: d.id, ...d.data() } as GroupMember));
    callback(list);
  });
}

// === 3. BUDGET & EXPENSES CRUD ===
export function subscribeGroupExpenses(groupId: string, callback: (expenses: Expense[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'expenses'), orderBy('date', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as Expense));
    callback(list);
  });
}

export async function createExpense(groupId: string, expense: Omit<Expense, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'expenses'), {
    ...expense,
    createdAt: serverTimestamp()
  });
}

export async function updateExpense(groupId: string, expenseId: string, expense: Partial<Expense>) {
  const docRef = doc(db, 'groups', groupId, 'expenses', expenseId);
  return await updateDoc(docRef, expense);
}

export async function deleteExpense(groupId: string, expenseId: string) {
  const docRef = doc(db, 'groups', groupId, 'expenses', expenseId);
  return await deleteDoc(docRef);
}

// === 4. SAVINGS GOALS & DEPOSITS ===
export function subscribeGroupGoals(groupId: string, callback: (goals: SavingGoal[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'saving_goals'), orderBy('createdAt', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as SavingGoal));
    callback(list);
  });
}

export async function createGoal(groupId: string, goal: Omit<SavingGoal, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'saving_goals'), {
    ...goal,
    createdAt: serverTimestamp()
  });
}

export async function updateGoal(groupId: string, goalId: string, goal: Partial<SavingGoal>) {
  const docRef = doc(db, 'groups', groupId, 'saving_goals', goalId);
  return await updateDoc(docRef, goal);
}

export async function deleteGoal(groupId: string, goalId: string) {
  const docRef = doc(db, 'groups', groupId, 'saving_goals', goalId);
  return await deleteDoc(docRef);
}

export function subscribeGoalDeposits(groupId: string, goalId: string, callback: (deposits: Deposit[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'saving_goals', goalId, 'deposits'), orderBy('date', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as Deposit));
    callback(list);
  });
}

export async function createDeposit(groupId: string, goalId: string, deposit: Omit<Deposit, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'saving_goals', goalId, 'deposits'), {
    ...deposit,
    createdAt: serverTimestamp()
  });
}

export async function deleteDeposit(groupId: string, goalId: string, depositId: string) {
  const docRef = doc(db, 'groups', groupId, 'saving_goals', goalId, 'deposits', depositId);
  return await deleteDoc(docRef);
}

// === 5. INCOME TARGETS & INFLOWS ===
export function subscribeIncomeTargets(groupId: string, callback: (targets: IncomeTarget[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'income_targets'), orderBy('createdAt', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as IncomeTarget));
    callback(list);
  });
}

export async function createIncomeTarget(groupId: string, target: Omit<IncomeTarget, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'income_targets'), {
    ...target,
    createdAt: serverTimestamp()
  });
}

export async function updateIncomeTarget(groupId: string, targetId: string, data: Partial<IncomeTarget>) {
  const docRef = doc(db, 'groups', groupId, 'income_targets', targetId);
  return await updateDoc(docRef, data);
}

export async function deleteIncomeTarget(groupId: string, targetId: string) {
  const docRef = doc(db, 'groups', groupId, 'income_targets', targetId);
  return await deleteDoc(docRef);
}

export function subscribeIncomeInflows(groupId: string, targetId: string, callback: (inflows: IncomeRecord[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'income_targets', targetId, 'inflows'), orderBy('date', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as IncomeRecord));
    callback(list);
  });
}

export async function createIncomeInflow(groupId: string, targetId: string, inflow: Omit<IncomeRecord, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'income_targets', targetId, 'inflows'), {
    ...inflow,
    createdAt: serverTimestamp()
  });
}

export async function deleteIncomeInflow(groupId: string, targetId: string, inflowId: string) {
  const docRef = doc(db, 'groups', groupId, 'income_targets', targetId, 'inflows', inflowId);
  return await deleteDoc(docRef);
}

// === 6. FINANCIAL ACCOUNTS & TRANSACTIONS ===
export function subscribeFinancialAccounts(groupId: string, callback: (accounts: FinancialAccount[]) => void) {
  // Financial accounts are managed as sub-ledgers.
  // We can query sub-ledgers from groups that have service === 'accounts' OR we listen to 'financial_accounts' subcollection inside groups.
  // In our app structure, financial cards are stored under the main groups collection as ledgers of type 'accounts'.
  const colRef = collection(db, 'groups');
  return onSnapshot(colRef, (snap) => {
    const list = snap.docs
      .map(doc => ({ id: doc.id, ...doc.data() } as any))
      .filter(g => g.service === 'accounts');
    callback(list);
  });
}

export function subscribeAccountTransactions(accountId: string, callback: (txs: AccountTransaction[]) => void) {
  const colRef = query(collection(db, 'groups', accountId, 'account_transactions'), orderBy('date', 'desc'));
  return onSnapshot(colRef, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as AccountTransaction));
    callback(list);
  });
}

export async function createAccountTransaction(accountId: string, tx: Omit<AccountTransaction, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', accountId, 'account_transactions'), {
    ...tx,
    createdAt: serverTimestamp()
  });
}

export async function deleteAccountTransaction(accountId: string, txId: string) {
  const docRef = doc(db, 'groups', accountId, 'account_transactions', txId);
  return await deleteDoc(docRef);
}

// === 7. LOANS & DEBTS ===
export function subscribeLoans(groupId: string, callback: (loans: Loan[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'loans_debts'), orderBy('createdAt', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as Loan));
    callback(list);
  });
}

export async function createLoan(groupId: string, loan: Omit<Loan, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'loans_debts'), {
    ...loan,
    createdAt: serverTimestamp()
  });
}

export async function updateLoan(groupId: string, loanId: string, data: Partial<Loan>) {
  const docRef = doc(db, 'groups', groupId, 'loans_debts', loanId);
  return await updateDoc(docRef, data);
}

export async function deleteLoan(groupId: string, loanId: string) {
  const docRef = doc(db, 'groups', groupId, 'loans_debts', loanId);
  return await deleteDoc(docRef);
}

export function subscribeLoanPayments(groupId: string, loanId: string, callback: (payments: LoanPayment[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'loans_debts', loanId, 'loan_payments'), orderBy('date', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as LoanPayment));
    callback(list);
  });
}

export async function createLoanPayment(groupId: string, loanId: string, payment: Omit<LoanPayment, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'loans_debts', loanId, 'loan_payments'), {
    ...payment,
    createdAt: serverTimestamp()
  });
}

export async function deleteLoanPayment(groupId: string, loanId: string, paymentId: string) {
  const docRef = doc(db, 'groups', groupId, 'loans_debts', loanId, 'loan_payments', paymentId);
  return await deleteDoc(docRef);
}

// === 8. MORTGAGES ===
export function subscribeMortgages(groupId: string, callback: (mortgages: Mortgage[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'mortgages'), orderBy('createdAt', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as Mortgage));
    callback(list);
  });
}

export async function createMortgage(groupId: string, mortgage: Omit<Mortgage, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'mortgages'), {
    ...mortgage,
    createdAt: serverTimestamp()
  });
}

export async function updateMortgage(groupId: string, mortgageId: string, data: Partial<Mortgage>) {
  const docRef = doc(db, 'groups', groupId, 'mortgages', mortgageId);
  return await updateDoc(docRef, data);
}

export async function deleteMortgage(groupId: string, mortgageId: string) {
  const docRef = doc(db, 'groups', groupId, 'mortgages', mortgageId);
  return await deleteDoc(docRef);
}

export function subscribeMortgagePayments(groupId: string, mortgageId: string, callback: (payments: MortgagePayment[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'mortgages', mortgageId, 'mortgage_payments'), orderBy('date', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as MortgagePayment));
    callback(list);
  });
}

export async function createMortgagePayment(groupId: string, mortgageId: string, payment: Omit<MortgagePayment, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'mortgages', mortgageId, 'mortgage_payments'), {
    ...payment,
    createdAt: serverTimestamp()
  });
}

export async function deleteMortgagePayment(groupId: string, mortgageId: string, paymentId: string) {
  const docRef = doc(db, 'groups', groupId, 'mortgages', mortgageId, 'mortgage_payments', paymentId);
  return await deleteDoc(docRef);
}

// === 9. RENT MANAGEMENT ===
export function subscribeRents(groupId: string, callback: (rents: Rent[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'rents'), orderBy('createdAt', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as Rent));
    callback(list);
  });
}

export async function createRent(groupId: string, rent: Omit<Rent, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'rents'), {
    ...rent,
    createdAt: serverTimestamp()
  });
}

export async function updateRent(groupId: string, rentId: string, data: Partial<Rent>) {
  const docRef = doc(db, 'groups', groupId, 'rents', rentId);
  return await updateDoc(docRef, data);
}

export async function deleteRent(groupId: string, rentId: string) {
  const docRef = doc(db, 'groups', groupId, 'rents', rentId);
  return await deleteDoc(docRef);
}

export function subscribeRentPayments(groupId: string, rentId: string, callback: (payments: RentPayment[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'rents', rentId, 'rent_payments'), orderBy('date', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as RentPayment));
    callback(list);
  });
}

export async function createRentPayment(groupId: string, rentId: string, payment: Omit<RentPayment, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'rents', rentId, 'rent_payments'), {
    ...payment,
    createdAt: serverTimestamp()
  });
}

export async function deleteRentPayment(groupId: string, rentId: string, paymentId: string) {
  const docRef = doc(db, 'groups', groupId, 'rents', rentId, 'rent_payments', paymentId);
  return await deleteDoc(docRef);
}

// === 10. DOCUMENT CABINETS (DOCUMENT VAULT) ===
export function subscribeVaultDocuments(groupId: string, callback: (docs: VaultDocument[]) => void) {
  const q = query(collection(db, 'groups', groupId, 'documents'), orderBy('createdAt', 'desc'));
  return onSnapshot(q, (snap) => {
    const list = snap.docs.map(d => ({ id: d.id, ...d.data() } as VaultDocument));
    callback(list);
  });
}

export async function createVaultDocument(groupId: string, document: Omit<VaultDocument, 'id' | 'createdAt'>) {
  return await addDoc(collection(db, 'groups', groupId, 'documents'), {
    ...document,
    createdAt: serverTimestamp()
  });
}

export async function deleteVaultDocument(groupId: string, docId: string) {
  const docRef = doc(db, 'groups', groupId, 'documents', docId);
  return await deleteDoc(docRef);
}


/**
 * ============================================================================
 * REAL-WORLD UTILITY CALCULATOR ENGINES (FOR BUSINESS FORECASTS)
 * ============================================================================
 */

export interface AmortizationPeriod {
  periodIndex: number;
  paymentAmount: number;
  interestPaid: number;
  principalPaid: number;
  remainingPrincipal: number;
}

/**
 * Calculates a complete amortization split over a given loan interest rate and term
 */
export function calculateAmortizationSchedule(
  principal: number, 
  annualRatePct: number, 
  years: number
): {
  monthlyPayment: number;
  totalInterestPaid: number;
  totalCostOfLoan: number;
  schedule: AmortizationPeriod[];
} {
  const monthlyRate = (annualRatePct / 100) / 12;
  const totalMonths = years * 12;
  
  let monthlyPayment = 0;
  if (monthlyRate === 0) {
    monthlyPayment = principal / totalMonths;
  } else {
    monthlyPayment = principal * 
      (monthlyRate * Math.pow(1 + monthlyRate, totalMonths)) / 
      (Math.pow(1 + monthlyRate, totalMonths) - 1);
  }

  const schedule: AmortizationPeriod[] = [];
  let remainingPrincipal = principal;
  let totalInterestPaid = 0;

  for (let i = 1; i <= totalMonths; i++) {
    const interestPaid = remainingPrincipal * monthlyRate;
    const principalPaid = monthlyPayment - interestPaid;
    remainingPrincipal = Math.max(remainingPrincipal - principalPaid, 0);
    totalInterestPaid += interestPaid;

    schedule.push({
      periodIndex: i,
      paymentAmount: parseFloat(monthlyPayment.toFixed(2)),
      interestPaid: parseFloat(interestPaid.toFixed(2)),
      principalPaid: parseFloat(principalPaid.toFixed(2)),
      remainingPrincipal: parseFloat(remainingPrincipal.toFixed(2))
    });

    if (remainingPrincipal <= 0) break;
  }

  return {
    monthlyPayment: parseFloat(monthlyPayment.toFixed(2)),
    totalInterestPaid: parseFloat(totalInterestPaid.toFixed(2)),
    totalCostOfLoan: parseFloat((principal + totalInterestPaid).toFixed(2)),
    schedule
  };
}

/**
 * Forecasts upcoming rent schedules based on rent agreement parameters
 */
export function generateRentForecast(
  amount: number,
  frequency: 'weekly' | 'monthly' | 'yearly' | 'other',
  startDateStr: string,
  endDateStr?: string,
  forecastLimit: number = 12
): { date: string; amount: number }[] {
  const list: { date: string; amount: number }[] = [];
  const start = new Date(startDateStr);
  const end = endDateStr ? new Date(endDateStr) : null;
  
  let current = new Date(start);
  for (let i = 0; i < forecastLimit; i++) {
    if (end && current > end) break;
    
    list.push({
      date: current.toISOString().split('T')[0],
      amount
    });

    if (frequency === 'weekly') {
      current.setDate(current.getDate() + 7);
    } else if (frequency === 'monthly') {
      current.setMonth(current.getMonth() + 1);
    } else if (frequency === 'yearly') {
      current.setFullYear(current.getFullYear() + 1);
    } else {
      current.setMonth(current.getMonth() + 1); // fallback monthly
    }
  }

  return list;
}

/**
 * Forecasts when a savings goal milestone will be completed based on progress and deposit trend
 */
export function forecastSavingsCompletion(
  target: number,
  current: number,
  monthlySavingsEstimation: number
): {
  monthsToGoal: number;
  estimatedDate: string | null;
  feasibilityPercent: number;
} {
  const remaining = target - current;
  if (remaining <= 0) {
    return { monthsToGoal: 0, estimatedDate: 'Goal Achieved!', feasibilityPercent: 100 };
  }
  
  if (monthlySavingsEstimation <= 0) {
    return { monthsToGoal: Infinity, estimatedDate: 'Requires Deposit Plan', feasibilityPercent: 0 };
  }

  const months = Math.ceil(remaining / monthlySavingsEstimation);
  const dateObj = new Date();
  dateObj.setMonth(dateObj.getMonth() + months);

  let feasibility = Math.round((monthlySavingsEstimation / (remaining / 12 || 1)) * 100);
  feasibility = Math.min(Math.max(feasibility, 5), 100); // bounds

  return {
    monthsToGoal: months,
    estimatedDate: dateObj.toLocaleDateString(undefined, { year: 'numeric', month: 'short' }),
    feasibilityPercent: feasibility
  };
}
