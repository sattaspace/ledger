import { ref } from 'vue';
import { doc, getDoc, setDoc } from 'firebase/firestore';
import { db } from '../firebase';

export const DEFAULT_EXPENSE_CATEGORIES = [
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

export const DEFAULT_SAVING_CATEGORIES = [
  'Vacation & Travel',
  'Home & Property',
  'Vehicle & Transport',
  'Emergency Fund',
  'Gadget & Appliance',
  'Education',
  'Investment',
  'Other'
];

export const DEFAULT_INCOME_CATEGORIES = [
  'Salary & Wages',
  'Freelance & Consulting',
  'Investments & Dividends',
  'Rental Income',
  'Sales & E-Commerce',
  'Gifts & Grants',
  'Side Hustle',
  'Other'
];

export const expenseCategories = ref<string[]>([...DEFAULT_EXPENSE_CATEGORIES]);
export const savingCategories = ref<string[]>([...DEFAULT_SAVING_CATEGORIES]);
export const incomeCategories = ref<string[]>([...DEFAULT_INCOME_CATEGORIES]);

export async function fetchCustomCategories(userId: string) {
  if (!userId) return;
  try {
    const userDocRef = doc(db, 'users', userId, 'settings', 'categories');
    const userDoc = await getDoc(userDocRef);
    if (userDoc.exists()) {
      const data = userDoc.data();
      if (data.expenseCategories && Array.isArray(data.expenseCategories)) {
        expenseCategories.value = data.expenseCategories;
      } else {
        expenseCategories.value = [...DEFAULT_EXPENSE_CATEGORIES];
      }
      if (data.savingCategories && Array.isArray(data.savingCategories)) {
        savingCategories.value = data.savingCategories;
      } else {
        savingCategories.value = [...DEFAULT_SAVING_CATEGORIES];
      }
      if (data.incomeCategories && Array.isArray(data.incomeCategories)) {
        incomeCategories.value = data.incomeCategories;
      } else {
        incomeCategories.value = [...DEFAULT_INCOME_CATEGORIES];
      }
    } else {
      // Lazy init central document
      await setDoc(userDocRef, {
        expenseCategories: DEFAULT_EXPENSE_CATEGORIES,
        savingCategories: DEFAULT_SAVING_CATEGORIES,
        incomeCategories: DEFAULT_INCOME_CATEGORIES
      });
      expenseCategories.value = [...DEFAULT_EXPENSE_CATEGORIES];
      savingCategories.value = [...DEFAULT_SAVING_CATEGORIES];
      incomeCategories.value = [...DEFAULT_INCOME_CATEGORIES];
    }
  } catch (error) {
    console.error('Error fetching custom categories:', error);
  }
}

export async function saveCustomCategories(userId: string, newExpenses: string[], newSavings: string[], newIncomes?: string[]) {
  if (!userId) return;
  try {
    const userDocRef = doc(db, 'users', userId, 'settings', 'categories');
    const payload: any = {
      expenseCategories: newExpenses,
      savingCategories: newSavings
    };
    if (newIncomes) {
      payload.incomeCategories = newIncomes;
    }
    await setDoc(userDocRef, payload, { merge: true });
    expenseCategories.value = newExpenses;
    savingCategories.value = newSavings;
    if (newIncomes) {
      incomeCategories.value = newIncomes;
    }
  } catch (error) {
    console.error('Error saving custom categories:', error);
  }
}

