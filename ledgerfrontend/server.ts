import express from 'express';
import path from 'path';
import fs from 'fs';
import { GoogleGenAI } from '@google/genai';

const app = express();
app.use(express.json());

// === JSON DATABASE SETUP (db.json) ===
const DB_FILE = path.resolve('db.json');

// Interface definition for DB tables
interface JSONDatabase {
  users: any[];
  groups: any[];
  group_members: any[];
  expenses: any[];
  saving_goals: any[];
  deposits: any[];
  income_targets: any[];
  inflows: any[];
  loans_debts: any[];
  loan_payments: any[];
  mortgages: any[];
  mortgage_payments: any[];
  user_settings: any[];
  financial_accounts: any[];
  account_transactions: any[];
  rents: any[];
  rent_payments: any[];
  documents: any[];
}

let dbData: JSONDatabase = createEmptyDBStructure();

// Helper to load db
function loadDB() {
  try {
    if (fs.existsSync(DB_FILE)) {
      const raw = fs.readFileSync(DB_FILE, 'utf-8');
      dbData = JSON.parse(raw);
      // Ensure all tables exist in loaded file
      const empty = createEmptyDBStructure();
      for (const key of Object.keys(empty) as (keyof JSONDatabase)[]) {
        if (!dbData[key]) {
          dbData[key] = [];
        }
      }
      console.log("Successfully loaded database from db.json");
    } else {
      console.log("No db.json found. Creating beautiful demo seed data...");
      seedInitialData();
    }
  } catch (e) {
    console.error("Failed to load db.json, fallback to empty/seeded database:", e);
    seedInitialData();
  }
}

// Helper to write db
function saveDB() {
  try {
    fs.writeFileSync(DB_FILE, JSON.stringify(dbData, null, 2), 'utf-8');
  } catch (e) {
    console.error("Failed to save db.json to file", e);
  }
}

function createEmptyDBStructure(): JSONDatabase {
  return {
    users: [],
    groups: [],
    group_members: [],
    expenses: [],
    saving_goals: [],
    deposits: [],
    income_targets: [],
    inflows: [],
    loans_debts: [],
    loan_payments: [],
    mortgages: [],
    mortgage_payments: [],
    user_settings: [],
    financial_accounts: [],
    account_transactions: [],
    rents: [],
    rent_payments: [],
    documents: []
  };
}

function seedInitialData() {
  dbData = createEmptyDBStructure();
  
  const sampleUserId = "snt82gjjo5QrMdbyiEakOZW6JD33";
  const sampleGroupId = "local-group-1";
  const sampleSavingsGroupId = "local-group-savings";
  const sampleGoalId1 = "goal-trip";
  const sampleGoalId2 = "goal-emergency";

  const nowVal = { _isTimestamp: true, seconds: Math.floor(Date.now() / 1000), nanoseconds: 0 };
  const dayAgoVal = { _isTimestamp: true, seconds: Math.floor(Date.now() / 1000) - 86400, nanoseconds: 0 };
  const twoDaysAgoVal = { _isTimestamp: true, seconds: Math.floor(Date.now() / 1000) - 172800, nanoseconds: 0 };

  dbData.users.push({
    uid: sampleUserId,
    displayName: "Kabita Gorain",
    email: "kabitagorain6@gmail.com",
    photoURL: "https://avatar.iran.liara.run/public/60",
    defaultCurrency: "USD",
    createdAt: nowVal
  });

  dbData.groups.push({
    id: sampleGroupId,
    name: "Primary Household Budget",
    description: "Track shared household expenditures, groceries, and bills.",
    createdBy: sampleUserId,
    createdAt: nowVal,
    type: "household",
    memberIds: [sampleUserId],
    maxBudget: 1500,
    budgetType: "monthly",
    currencyCode: "USD",
    service: "budget"
  });

  dbData.group_members.push({
    groupId: sampleGroupId,
    uid: sampleUserId,
    role: "admin",
    displayName: "Kabita Gorain",
    email: "kabitagorain6@gmail.com",
    joinedAt: nowVal
  });

  dbData.groups.push({
    id: sampleSavingsGroupId,
    name: "Dream Vacation & Emergency Fund",
    description: "Shared savings campaigns for vacations, holidays, and safety cushions.",
    createdBy: sampleUserId,
    createdAt: nowVal,
    type: "household",
    memberIds: [sampleUserId],
    maxBudget: 5000,
    budgetType: "total",
    currencyCode: "USD",
    service: "savings"
  });

  dbData.group_members.push({
    groupId: sampleSavingsGroupId,
    uid: sampleUserId,
    role: "admin",
    displayName: "Kabita Gorain",
    email: "kabitagorain6@gmail.com",
    joinedAt: nowVal
  });

  dbData.saving_goals.push({
    id: sampleGoalId1,
    groupId: sampleSavingsGroupId,
    name: "Summer Hawaii Family Cruise",
    targetAmount: 3200,
    currencyCode: "USD",
    category: "Vacation & Travel",
    createdAt: dayAgoVal,
    createdBy: sampleUserId
  });

  dbData.saving_goals.push({
    id: sampleGoalId2,
    groupId: sampleSavingsGroupId,
    name: "Winter Emergency Reserve",
    targetAmount: 1000,
    currencyCode: "USD",
    category: "Emergency Fund",
    createdAt: twoDaysAgoVal,
    createdBy: sampleUserId
  });

  dbData.deposits.push({
    id: "dep-1",
    groupId: sampleSavingsGroupId,
    goalId: sampleGoalId1,
    amount: 500,
    originalAmount: 500,
    currencyCode: "USD",
    exchangeRateUsed: 1.0,
    depositedBy: sampleUserId,
    date: nowVal,
    createdAt: nowVal,
    note: "Starting fund commitment"
  });

  dbData.deposits.push({
    id: "dep-2",
    groupId: sampleSavingsGroupId,
    goalId: sampleGoalId1,
    amount: 250,
    originalAmount: 250,
    currencyCode: "USD",
    exchangeRateUsed: 1.0,
    depositedBy: sampleUserId,
    date: nowVal,
    createdAt: nowVal,
    note: "Cash gift contribution"
  });

  dbData.expenses.push({
    id: "exp-1",
    groupId: sampleGroupId,
    amount: 145,
    description: "Weekly Groceries and Supplies",
    category: "Groceries",
    paidBy: sampleUserId,
    date: nowVal,
    createdAt: nowVal,
    splitType: "equal",
    currencyCode: "USD",
    originalAmount: 145,
    exchangeRateUsed: 1.0
  });

  dbData.expenses.push({
    id: "exp-2",
    groupId: sampleGroupId,
    amount: 60,
    description: "Cinema and snacks",
    category: "Entertainment",
    paidBy: sampleUserId,
    date: nowVal,
    createdAt: nowVal,
    splitType: "equal",
    currencyCode: "USD",
    originalAmount: 60,
    exchangeRateUsed: 1.0
  });

  saveDB();
}

// Initial DB load
loadDB();

// === Path Parser Helper ===
interface ParsedPath {
  table: string;
  isCollection: boolean;
  docId?: string;
  filterParams?: Record<string, any>;
}

function parsePath(pathStr: string): ParsedPath | null {
  const cleanPath = pathStr.replace(/^\/+|\/+$/g, '');
  const parts = cleanPath.split('/');

  if (parts.length === 0 || !parts[0]) return null;

  // 1. users
  if (parts[0] === 'users') {
    if (parts.length === 1) return { table: 'users', isCollection: true };
    if (parts.length === 2) return { table: 'users', isCollection: false, docId: parts[1], filterParams: { uid: parts[1] } };
    if (parts.length === 3 && parts[2] === 'settings') {
      return { table: 'user_settings', isCollection: true, filterParams: { userId: parts[1] } };
    }
    if (parts.length === 4 && parts[2] === 'settings') {
      return { table: 'user_settings', isCollection: false, docId: `${parts[1]}_${parts[3]}`, filterParams: { userId: parts[1], settingId: parts[3] } };
    }
  }

  // 2. groups
  if (parts[0] === 'groups') {
    if (parts.length === 1) return { table: 'groups', isCollection: true };
    if (parts.length === 2) return { table: 'groups', isCollection: false, docId: parts[1], filterParams: { id: parts[1] } };

    // 3. groups/:id/members
    if (parts[2] === 'members') {
      if (parts.length === 3) return { table: 'group_members', isCollection: true, filterParams: { groupId: parts[1] } };
      if (parts.length === 4) return { table: 'group_members', isCollection: false, docId: parts[3], filterParams: { groupId: parts[1], uid: parts[3] } };
    }

    // 4. groups/:id/expenses
    if (parts[2] === 'expenses') {
      if (parts.length === 3) return { table: 'expenses', isCollection: true, filterParams: { groupId: parts[1] } };
      if (parts.length === 4) return { table: 'expenses', isCollection: false, docId: parts[3], filterParams: { id: parts[3] } };
    }

    // 5. groups/:id/saving_goals
    if (parts[2] === 'saving_goals') {
      if (parts.length === 3) return { table: 'saving_goals', isCollection: true, filterParams: { groupId: parts[1] } };
      if (parts.length === 4) return { table: 'saving_goals', isCollection: false, docId: parts[3], filterParams: { id: parts[3] } };

      // 6. groups/:id/saving_goals/:goalId/deposits
      if (parts[4] === 'deposits') {
        if (parts.length === 5) return { table: 'deposits', isCollection: true, filterParams: { groupId: parts[1], goalId: parts[3] } };
        if (parts.length === 6) return { table: 'deposits', isCollection: false, docId: parts[5], filterParams: { id: parts[5] } };
      }
    }

    // 7. groups/:id/income_targets
    if (parts[2] === 'income_targets') {
      if (parts.length === 3) return { table: 'income_targets', isCollection: true, filterParams: { groupId: parts[1] } };
      if (parts.length === 4) return { table: 'income_targets', isCollection: false, docId: parts[3], filterParams: { id: parts[3] } };

      // 8. groups/:id/income_targets/:targetId/inflows
      if (parts[4] === 'inflows') {
        if (parts.length === 5) return { table: 'inflows', isCollection: true, filterParams: { groupId: parts[1], targetId: parts[3] } };
        if (parts.length === 6) return { table: 'inflows', isCollection: false, docId: parts[5], filterParams: { id: parts[5] } };
      }
    }

    // 9. groups/:id/financial_accounts
    if (parts[2] === 'financial_accounts') {
      if (parts.length === 3) return { table: 'financial_accounts', isCollection: true, filterParams: { groupId: parts[1] } };
      if (parts.length === 4) return { table: 'financial_accounts', isCollection: false, docId: parts[3], filterParams: { id: parts[3] } };

      // 10. groups/:id/financial_accounts/:accountId/account_transactions
      if (parts[4] === 'account_transactions') {
        if (parts.length === 5) return { table: 'account_transactions', isCollection: true, filterParams: { groupId: parts[1], accountId: parts[3] } };
        if (parts.length === 6) return { table: 'account_transactions', isCollection: false, docId: parts[5], filterParams: { id: parts[5] } };
      }
    }

    // 11. groups/:id/account_transactions (direct query under group)
    if (parts[2] === 'account_transactions') {
      if (parts.length === 3) return { table: 'account_transactions', isCollection: true, filterParams: { groupId: parts[1] } };
      if (parts.length === 4) return { table: 'account_transactions', isCollection: false, docId: parts[3], filterParams: { id: parts[3] } };
    }

    // 12. groups/:id/loans_debts (direct subcollection query under group)
    if (parts[2] === 'loans_debts') {
      if (parts.length === 3) return { table: 'loans_debts', isCollection: true, filterParams: { groupId: parts[1] } };
      if (parts.length === 4) return { table: 'loans_debts', isCollection: false, docId: parts[3], filterParams: { id: parts[3] } };

      // 13. groups/:id/loans_debts/:loanId/loan_payments
      if (parts[4] === 'loan_payments') {
        if (parts.length === 5) return { table: 'loan_payments', isCollection: true, filterParams: { groupId: parts[1], loanId: parts[3] } };
        if (parts.length === 6) return { table: 'loan_payments', isCollection: false, docId: parts[5], filterParams: { id: parts[5] } };
      }
    }

    // 14. groups/:id/mortgages (direct subcollection query under group)
    if (parts[2] === 'mortgages') {
      if (parts.length === 3) return { table: 'mortgages', isCollection: true, filterParams: { groupId: parts[1] } };
      if (parts.length === 4) return { table: 'mortgages', isCollection: false, docId: parts[3], filterParams: { id: parts[3] } };

      // 15. groups/:id/mortgages/:mortgageId/mortgage_payments
      if (parts[4] === 'mortgage_payments') {
        if (parts.length === 5) return { table: 'mortgage_payments', isCollection: true, filterParams: { groupId: parts[1], mortgageId: parts[3] } };
        if (parts.length === 6) return { table: 'mortgage_payments', isCollection: false, docId: parts[5], filterParams: { id: parts[5] } };
      }
    }

    // 16. groups/:id/rents (direct subcollection query under group)
    if (parts[2] === 'rents') {
      if (parts.length === 3) return { table: 'rents', isCollection: true, filterParams: { groupId: parts[1] } };
      if (parts.length === 4) return { table: 'rents', isCollection: false, docId: parts[3], filterParams: { id: parts[3] } };

      // 17. groups/:id/rents/:rentId/rent_payments
      if (parts[4] === 'rent_payments') {
        if (parts.length === 5) return { table: 'rent_payments', isCollection: true, filterParams: { groupId: parts[1], rentId: parts[3] } };
        if (parts.length === 6) return { table: 'rent_payments', isCollection: false, docId: parts[5], filterParams: { id: parts[5] } };
      }
    }

    // 18. groups/:id/documents (direct subcollection query under group)
    if (parts[2] === 'documents') {
      if (parts.length === 3) return { table: 'documents', isCollection: true, filterParams: { groupId: parts[1] } };
      if (parts.length === 4) return { table: 'documents', isCollection: false, docId: parts[3], filterParams: { id: parts[3] } };
    }
  }

  // 19. standalone documents collection
  if (parts[0] === 'documents') {
    if (parts.length === 1) return { table: 'documents', isCollection: true };
    if (parts.length === 2) return { table: 'documents', isCollection: false, docId: parts[1], filterParams: { id: parts[1] } };
  }

  return null;
}

// === Database Operations ===
function fetchRows(table: string, filterParams?: Record<string, any>): any[] {
  const records = dbData[table as keyof JSONDatabase] || [];
  const deepCopy = JSON.parse(JSON.stringify(records));
  
  if (!filterParams || Object.keys(filterParams).length === 0) {
    return deepCopy;
  }
  
  return deepCopy.filter((row: any) => {
    for (const key of Object.keys(filterParams)) {
      if (row[key] !== filterParams[key]) {
        return false;
      }
    }
    return true;
  });
}

function saveRow(table: string, id: string, data: any, filterParams?: Record<string, any>, merge = false) {
  const records = dbData[table as keyof JSONDatabase];
  if (!records) return;

  const pk = (table === 'users') ? 'uid' : 'id';
  const existingIdx = records.findIndex((row: any) => row[pk] === id);
  const finalData = { ...filterParams, ...data };
  
  if (table === 'users') {
    finalData.uid = id;
  } else {
    finalData.id = id;
  }

  if (existingIdx !== -1) {
    const existing = records[existingIdx];
    records[existingIdx] = merge ? { ...existing, ...finalData } : finalData;
  } else {
    records.push(finalData);
  }

  saveDB();
}

function deleteRow(table: string, id: string) {
  const records = dbData[table as keyof JSONDatabase] as any[];
  if (!records) return;

  const pk = (table === 'users') ? 'uid' : 'id';
  const filtered = records.filter(row => row[pk] !== id);
  dbData[table as keyof JSONDatabase] = filtered as any;
  saveDB();
}

// === Self Healing Routine ===
function selfHealingBalances() {
  try {
    console.log("Self-healing account balances against JSON database...");
    const accounts = dbData.groups.filter(g => g.service === 'accounts');
    for (const acc of accounts) {
      const txs = dbData.account_transactions.filter(tx => tx.groupId === acc.id);
      if (txs.length > 0) {
        let sum = 0;
        for (const tx of txs) {
          sum += (parseFloat(tx.amount) || 0);
        }
        let calculatedBalance = sum;
        if (acc.accountType === 'credit_card') {
          calculatedBalance = -sum;
        }
        acc.balance = calculatedBalance;
        console.log(`[Self-Healing] Balance of account "${acc.name}" synchronized to ${calculatedBalance}`);
      }
    }
    saveDB();
  } catch (error) {
    console.error("Error during auto-healing account balances:", error);
  }
}

// Run healing on startup
selfHealingBalances();

// === Express API Router Endpoints ===

// 1. Live db querying
app.post('/api/db/query', (req, res) => {
  try {
    const { path: pathStr, constraints = [] } = req.body;
    const parsed = parsePath(pathStr);
    if (!parsed) {
      return res.status(400).json({ error: `Invalid query path: ${pathStr}` });
    }

    let records = fetchRows(parsed.table, parsed.filterParams);

    // Filter constraints
    const whereConstraints = constraints.filter((c: any) => c && c.type === 'where');
    for (const wc of whereConstraints) {
      const { field, op, value } = wc;
      records = records.filter(row => {
        const itemVal = row[field];
        if (op === 'array-contains') {
          return Array.isArray(itemVal) && itemVal.includes(value);
        }
        if (op === '==') {
          return itemVal === value;
        }
        return true;
      });
    }

    // Sorting constraints
    const orderByConstraint = constraints.find((c: any) => c && c.type === 'orderBy');
    if (orderByConstraint) {
      const { field, direction } = orderByConstraint;
      records.sort((a, b) => {
        let valA = a[field];
        let valB = b[field];

        if (valA && typeof valA.seconds === 'number') valA = valA.seconds;
        if (valB && typeof valB.seconds === 'number') valB = valB.seconds;

        if (valA === valB) return 0;
        if (valA === undefined || valA === null) return 1;
        if (valB === undefined || valB === null) return -1;

        const cmp = valA < valB ? -1 : 1;
        return direction === 'desc' ? -cmp : cmp;
      });
    }

    return res.json({ docs: records });
  } catch (err: any) {
    console.error("Query error:", err);
    return res.status(500).json({ error: err.message });
  }
});

// 2. Fetch single document
app.get('/api/db/get', (req, res) => {
  try {
    const pathStr = req.query.path as string;
    const parsed = parsePath(pathStr);
    if (!parsed || parsed.isCollection) {
      return res.status(400).json({ error: `Invalid document path: ${pathStr}` });
    }

    const pk = (parsed.table === 'users') ? 'uid' : 'id';
    const records = dbData[parsed.table as keyof JSONDatabase] || [];
    const row = records.find((r: any) => r[pk] === parsed.docId);
    
    if (!row) {
      return res.json({ exists: false, data: null });
    }

    return res.json({ exists: true, data: JSON.parse(JSON.stringify(row)) });
  } catch (err: any) {
    console.error("Get error:", err);
    return res.status(500).json({ error: err.message });
  }
});

// 3. Set or update document
app.post('/api/db/set', (req, res) => {
  try {
    const { path: pathStr, data, options } = req.body;
    const parsed = parsePath(pathStr);
    if (!parsed || parsed.isCollection) {
      return res.status(400).json({ error: `Invalid document path: ${pathStr}` });
    }

    const merge = !!options?.merge;
    saveRow(parsed.table, parsed.docId!, data, parsed.filterParams, merge);
    
    // Auto-heal account balances if creating/updating transactions
    if (parsed.table === 'account_transactions') {
      selfHealingBalances();
    }

    return res.json({ success: true });
  } catch (err: any) {
    console.error("Set error:", err);
    return res.status(500).json({ error: err.message });
  }
});

// 4. Create new document
app.post('/api/db/add', (req, res) => {
  try {
    const { path: pathStr, data } = req.body;
    const parsed = parsePath(pathStr);
    if (!parsed || !parsed.isCollection) {
      return res.status(400).json({ error: `Invalid collection path: ${pathStr}` });
    }

    const newId = data.id || Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 14);
    saveRow(parsed.table, newId, data, parsed.filterParams, false);

    // Auto-heal account balances if creating/updating transactions
    if (parsed.table === 'account_transactions') {
      selfHealingBalances();
    }

    return res.json({ id: newId });
  } catch (err: any) {
    console.error("Add error:", err);
    return res.status(500).json({ error: err.message });
  }
});

// 5. Delete document
app.post('/api/db/delete', (req, res) => {
  try {
    const { path: pathStr } = req.body;
    const parsed = parsePath(pathStr);
    if (!parsed || parsed.isCollection) {
      return res.status(400).json({ error: `Invalid document path: ${pathStr}` });
    }

    deleteRow(parsed.table, parsed.docId!);

    // Auto-heal account balances if creating/updating transactions
    if (parsed.table === 'account_transactions') {
      selfHealingBalances();
    }

    return res.json({ success: true });
  } catch (err: any) {
    console.error("Delete error:", err);
    return res.status(500).json({ error: err.message });
  }
});

// === REST API Explorer / Inspector Endpoints ===

// 6. DB Inspector tables dump
app.get('/api/db/dump-tables', (req, res) => {
  try {
    return res.json(dbData);
  } catch (err: any) {
    console.error("Dump error:", err);
    return res.status(500).json({ error: err.message });
  }
});

// 7. DB Inspector custom queries fallback (Simulated SQL)
app.post('/api/db/execute-sql', (req, res) => {
  try {
    const { sql } = req.body;
    if (!sql || typeof sql !== 'string') {
      return res.status(400).json({ error: "No query statement provided." });
    }

    const match = sql.match(/select\s+\*\s+from\s+(\w+)/i);
    if (match) {
      const tableName = match[1].toLowerCase();
      const records = dbData[tableName as keyof JSONDatabase] || [];
      const limitMatch = sql.match(/limit\s+(\d+)/i);
      const limit = limitMatch ? parseInt(limitMatch[1], 10) : 100;
      const rows = records.slice(0, limit);
      return res.json({
        columns: rows.length > 0 ? Object.keys(rows[0]) : [],
        rows: rows
      });
    }

    return res.status(400).json({ error: "Only read-only SELECT database query statements are supported in this JSON explorer" });
  } catch (err: any) {
    return res.status(400).json({ error: err.message || "Query statement compilation error." });
  }
});

// === Gemini 2.5 Flash Advisory Integrations ===
app.post('/api/analyze', async (req, res) => {
  try {
    const { groupName, groupType, budgetType, maxBudget, totalSpent, expenseSummary } = req.body;

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return res.json({ text: "API Key Error: GEMINI_API_KEY is not defined on the server side. Please ensure the user secret is set in the panel." });
    }

    const ai = new GoogleGenAI({ apiKey });

    const prompt = `
      Analyze the following spending data for a group budget named "${groupName}".
      Group Type: ${groupType}
      Budget Type: ${budgetType}
      Max Budget: ${maxBudget || 'No limit'}
      Total Spent in Current Period: ${totalSpent}
      
      Expenses:
      ${JSON.stringify(expenseSummary, null, 2)}
      
      Please provide:
      1. A summary of spending habits.
      2. Identification of any unusual or high spending categories.
      3. Practical suggestions for saving or better budget management.
      4. A brief outlook based on the current budget limit.
      
      Keep the tone helpful, professional, and encouraging. Use markdown for formatting.
    `;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [{ parts: [{ text: prompt }] }]
    });

    return res.json({ text: response.text || "Could not generate analysis." });
  } catch (error: any) {
    console.error("API error during Gemini call inside Express:", error);
    return res.json({ text: `AI analysis error: ${error.message || String(error)}` });
  }
});

app.post('/api/analyze-savings', async (req, res) => {
  try {
    const { groupName, groupType, totalTarget, totalSaved, goalsSummary } = req.body;

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return res.json({ text: "API Key Error: GEMINI_API_KEY is not defined on the server side. Please ensure the user secret is set in the panel." });
    }

    const ai = new GoogleGenAI({ apiKey });

    const prompt = `
      Analyze the following savings goals data for a group named "${groupName}".
      Group Type: ${groupType}
      Combined Savings Target: ${totalTarget}
      Combined Savings Reached: ${totalSaved}
      
      Active Saving Goals:
      ${JSON.stringify(goalsSummary, null, 2)}
      
      Please provide:
      1. An analysis of the savings progress and trajectory.
      2. Tailored, strategic recommendations based on the categories of their active goals (e.g., Vacation/Travel, Emergency Fund, Education, Investment, etc.).
      3. Actionable advice and custom encouragement to motivate additional or more continuous deposits.
      4. Recommendations on how to prioritize these active targets most effectively.
      
      Keep the tone highly professional, motivating, supportive, and practical. Use markdown for styling elements (headers, bolding text, bullet lists).
    `;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [{ parts: [{ text: prompt }] }]
    });

    return res.json({ text: response.text || "Could not generate analysis." });
  } catch (error: any) {
    console.error("API error during Gemini call inside Express:", error);
    return res.json({ text: `AI savings analysis error: ${error.message || String(error)}` });
  }
});

app.post('/api/analyze-income', async (req, res) => {
  try {
    const { groupName, groupType, totalTarget, totalEarned, targetsSummary } = req.body;

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return res.json({ text: "API Key Error: GEMINI_API_KEY is not defined on the server side. Please ensure the user secret is set in the panel." });
    }

    const ai = new GoogleGenAI({ apiKey });

    const prompt = `
      Analyze the following target and income inflows data for a tracking group named "${groupName}".
      Group Type: ${groupType}
      Combined Income Inflow Target: ${totalTarget}
      Combined Income Earned/Recorded: ${totalEarned}
      
      Active Income Targets/Streams:
      ${JSON.stringify(targetsSummary, null, 2)}
      
      Please provide:
      1. An analysis of the income flows, velocity, stability, and trajectory.
      2. Tailored, strategic recommendations based on the categories of their active income targets (e.g., Salary & Wages, Freelance/Consulting, Investments/Dividends, Rental Income, sales, Side Hustle, etc.).
      3. Actionable advice on expanding active or passive income streams, improving pricing/rates, or identifying seasonal gaps.
      4. Creative recommendations on how to optimize their workflow/projects to maximize profit.
      
      Keep the tone highly professional, motivating, supportive, and practical. Use markdown for styling elements (headers, bolding text, bullet lists).
    `;

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: [{ parts: [{ text: prompt }] }]
    });

    return res.json({ text: response.text || "Could not generate analysis." });
  } catch (error: any) {
    console.error("API error during Gemini call inside Express:", error);
    return res.json({ text: `AI income analysis error: ${error.message || String(error)}` });
  }
});

// === Static Asset Hosting ===
const PORT = 3000;
const buildDir = path.resolve('dist');

app.use(express.static(buildDir));

// Fallback path router for SPA (Client-Side Rendering)
app.get('*', (req, res, next) => {
  if (req.path.startsWith('/api')) {
    return next();
  }
  return res.sendFile(path.join(buildDir, 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`JSON-backed Server running smoothly on http://0.0.0.0:${PORT}`);
});
