<script setup lang="ts">
/**
 * NotificationsPage — centralized notifications & reminders hub.
 *
 * Aggregates all reminder types from across the Ledger system:
 *   - Bill due reminders (N days before due)
 *   - Insurance renewal reminders (N days before renewal)
 *   - Document expiry reminders (N days before expiry)
 *   - Credit card due date reminders (based on Account.due_day)
 *   - Annual fee reminders (based on Card.annual_fee_date)
 *   - Savings goal deadline reminders (approaching deadlines)
 */

import { ref, computed, onMounted } from "vue";
import { ledgerApi } from "@/lib/ledgerApi";
import { useAuth } from "@/composables/useAuth";
import { useToast } from "@/composables/useToast";

// ─── Types ──────────────────────────────────────────────────────────────────

interface NotificationItem {
  id: string;
  type: "bill_due" | "insurance_renewal" | "document_expiry" | "card_due" | "annual_fee" | "goal_deadline";
  title: string;
  description: string;
  date: string;
  daysLeft: number;
  link: string;
  icon: string;
  priority: "urgent" | "warning" | "info";
}

// ─── State ──────────────────────────────────────────────────────────────────

const loading = ref(true);
const activeTab = ref<"all" | "urgent" | "bill_due" | "insurance_renewal" | "document_expiry" | "card_due" | "goal_deadline">("all");
const notifications = ref<NotificationItem[]>([]);

const { user } = useAuth();
const toast = useToast();

// ─── Computed ───────────────────────────────────────────────────────────────

const filteredNotifications = computed(() => {
  if (activeTab.value === "all") return notifications.value;
  if (activeTab.value === "urgent") return notifications.value.filter((n) => n.priority === "urgent");
  return notifications.value.filter((n) => n.type === activeTab.value);
});

const urgentCount = computed(() => notifications.value.filter((n) => n.priority === "urgent").length);
const warningCount = computed(() => notifications.value.filter((n) => n.priority === "warning").length);

// ─── Helpers ────────────────────────────────────────────────────────────────

function daysBetween(dateStr: string): number {
  const target = new Date(dateStr);
  const now = new Date();
  const diff = target.getTime() - now.getTime();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function getPriority(daysLeft: number): "urgent" | "warning" | "info" {
  if (daysLeft <= 3) return "urgent";
  if (daysLeft <= 7) return "warning";
  return "info";
}

function getPriorityColor(priority: "urgent" | "warning" | "info"): string {
  switch (priority) {
    case "urgent": return "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300 border-red-200 dark:border-red-800";
    case "warning": return "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300 border-amber-200 dark:border-amber-800";
    case "info": return "bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300 border-cyan-200 dark:border-cyan-800";
  }
}

function getPriorityBadge(priority: "urgent" | "warning" | "info"): string {
  switch (priority) {
    case "urgent": return "bg-red-500 text-white";
    case "warning": return "bg-amber-500 text-white";
    case "info": return "bg-cyan-500 text-white";
  }
}

function getTypeIcon(type: NotificationItem["type"]): string {
  switch (type) {
    case "bill_due": return "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01";
    case "insurance_renewal": return "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z";
    case "document_expiry": return "M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4";
    case "card_due": return "M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z";
    case "annual_fee": return "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z";
    case "goal_deadline": return "M13 10V3L4 14h7v7l9-11h-7z";
  }
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function formatDaysLeft(days: number): string {
  if (days < 0) return `${Math.abs(days)} days overdue`;
  if (days === 0) return "Due today";
  if (days === 1) return "1 day left";
  return `${days} days left`;
}

// ─── Data Fetching ──────────────────────────────────────────────────────────

async function fetchNotifications(): Promise<void> {
  loading.value = true;
  notifications.value = [];

  try {
    const items: NotificationItem[] = [];

    // Fetch upcoming bills (due in next 30 days)
    try {
      const bills = await ledgerApi.bills.upcoming(30);
      for (const bill of bills) {
        const daysLeft = daysBetween(bill.next_due_date);
        if (daysLeft <= 30) {
          items.push({
            id: `bill-${bill.id}`,
            type: "bill_due",
            title: bill.name,
            description: `${bill.amount} ${bill.currency || ""} — ${bill.recurrence}`,
            date: bill.next_due_date,
            daysLeft,
            link: `/dashboard/bills/${bill.id}`,
            icon: getTypeIcon("bill_due"),
            priority: getPriority(daysLeft),
          });
        }
      }
    } catch {
      // Bills not available — skip
    }

    // Fetch insurance renewals (due in next 60 days)
    try {
      const policies = await ledgerApi.insurance.renewals(60);
      for (const policy of policies) {
        if (policy.next_renewal_date) {
          const daysLeft = daysBetween(policy.next_renewal_date);
          if (daysLeft <= 60) {
            items.push({
              id: `insurance-${policy.id}`,
              type: "insurance_renewal",
              title: policy.provider_name,
              description: `${policy.policy_type} — Coverage: ${policy.coverage_amount} ${policy.currency || ""}`,
              date: policy.next_renewal_date,
              daysLeft,
              link: `/dashboard/insurance`,
              icon: getTypeIcon("insurance_renewal"),
              priority: getPriority(daysLeft),
            });
          }
        }
      }
    } catch {
      // Insurance not available — skip
    }

    // Fetch expiring documents (within 30 days)
    try {
      const docs = await ledgerApi.vault.expiring(30);
      for (const doc of docs) {
        if (doc.expiry_date) {
          const daysLeft = daysBetween(doc.expiry_date);
          items.push({
            id: `doc-${doc.id}`,
            type: "document_expiry",
            title: doc.name,
            description: `${doc.file_type} — ${doc.entity_type || "General"}`,
            date: doc.expiry_date,
            daysLeft,
            link: `/dashboard/vault/${doc.id}`,
            icon: getTypeIcon("document_expiry"),
            priority: getPriority(daysLeft),
          });
        }
      }
    } catch {
      // Vault not available — skip
    }

    // Fetch savings goals with approaching deadlines
    try {
      const goals = await ledgerApi.savingsGoals.dashboard();
      for (const goal of goals) {
        if (goal.deadline) {
          const daysLeft = daysBetween(goal.deadline);
          const progress = goal.current_amount / goal.target_amount;
          if (daysLeft <= 30 && progress < 1) {
            items.push({
              id: `goal-${goal.id}`,
              type: "goal_deadline",
              title: goal.name,
              description: `${Math.round(progress * 100)}% saved — ${goal.current_amount}/${goal.target_amount} ${goal.currency || ""}`,
              date: goal.deadline,
              daysLeft,
              link: `/dashboard/goals`,
              icon: getTypeIcon("goal_deadline"),
              priority: getPriority(daysLeft),
            });
          }
        }
      }
    } catch {
      // Goals not available — skip
    }

    // Fetch credit card due date alerts
    try {
      const accountsResp = await ledgerApi.accounts.list({ is_active: true, limit: 100 });
      const liabilityAccounts = accountsResp.items.filter(
        (acct) => acct.account_type === "LIABILITY" && acct.due_day
      );
      for (const acct of liabilityAccounts) {
        const now = new Date();
        let dueDate = new Date(now.getFullYear(), now.getMonth(), acct.due_day!);
        // If the due day has passed this month, use next month
        if (dueDate < now) {
          dueDate = new Date(now.getFullYear(), now.getMonth() + 1, acct.due_day!);
        }
        const dateStr = dueDate.toISOString().split("T")[0];
        const daysLeft = daysBetween(dateStr);
        if (daysLeft <= 30) {
          items.push({
            id: `card-due-${acct.id}`,
            type: "card_due",
            title: `${acct.name} — Payment Due`,
            description: `Credit card payment due on day ${acct.due_day}`,
            date: dateStr,
            daysLeft,
            link: `/dashboard/accounts/${acct.id}`,
            icon: getTypeIcon("card_due"),
            priority: getPriority(daysLeft),
          });
        }
      }
    } catch {
      // Accounts not available — skip
    }

    // Fetch annual fee alerts
    try {
      const cardsResp = await ledgerApi.cards.list({ limit: 100 });
      const cardsWithFees = cardsResp.items.filter(
        (card) => card.is_active && card.annual_fee_date && parseFloat(card.annual_fee || "0") > 0
      );
      for (const card of cardsWithFees) {
        const daysLeft = daysBetween(card.annual_fee_date!);
        if (daysLeft <= 60) {
          items.push({
            id: `annual-fee-${card.id}`,
            type: "annual_fee",
            title: `${card.card_name} (•••• ${card.last_four}) — Annual Fee`,
            description: `$${parseFloat(card.annual_fee || "0").toFixed(2)} annual fee coming up`,
            date: card.annual_fee_date!,
            daysLeft,
            link: `/dashboard/cards`,
            icon: getTypeIcon("annual_fee"),
            priority: getPriority(daysLeft),
          });
        }
      }
    } catch {
      // Cards not available — skip
    }

    // Sort by priority (urgent first), then by daysLeft
    const priorityOrder: Record<string, number> = { urgent: 0, warning: 1, info: 2 };
    items.sort((a, b) => {
      const pDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
      if (pDiff !== 0) return pDiff;
      return a.daysLeft - b.daysLeft;
    });

    notifications.value = items;
  } catch (err) {
    console.error("Failed to fetch notifications:", err);
    toast.error("Failed to load notifications");
  } finally {
    loading.value = false;
  }
}

// ─── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
  fetchNotifications();
});
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-navy-900 dark:text-navy-100">Notifications & Reminders</h1>
        <p class="mt-1 text-sm text-slate-custom-600 dark:text-slate-custom-400">
          Stay on top of upcoming bills, renewals, and deadlines
        </p>
      </div>
      <div class="flex items-center gap-3">
        <!-- Urgent badge -->
        <span
          v-if="urgentCount > 0"
          class="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700 dark:bg-red-950 dark:text-red-300"
        >
          <span class="h-1.5 w-1.5 rounded-full bg-red-500"></span>
          {{ urgentCount }} urgent
        </span>
        <!-- Warning badge -->
        <span
          v-if="warningCount > 0"
          class="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-950 dark:text-amber-300"
        >
          <span class="h-1.5 w-1.5 rounded-full bg-amber-500"></span>
          {{ warningCount }} upcoming
        </span>
      </div>
    </div>

    <!-- Filter Tabs -->
    <div class="mb-6 flex flex-wrap gap-2 border-b border-navy-200 dark:border-navy-700 pb-3">
      <button
        v-for="tab in [
          { key: 'all', label: 'All' },
          { key: 'urgent', label: 'Urgent' },
          { key: 'bill_due', label: 'Bills' },
          { key: 'insurance_renewal', label: 'Insurance' },
          { key: 'document_expiry', label: 'Documents' },
          { key: 'card_due', label: 'Cards' },
          { key: 'goal_deadline', label: 'Goals' },
        ]"
        :key="tab.key"
        class="rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
        :class="activeTab === tab.key
          ? 'bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300'
          : 'text-slate-custom-600 hover:bg-navy-100 dark:text-slate-custom-400 dark:hover:bg-navy-800'"
        @click="activeTab = tab.key as any"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-8 w-8 animate-spin text-cyan-500" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">Loading notifications...</p>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-else-if="filteredNotifications.length === 0"
      class="flex flex-col items-center justify-center py-16 text-center"
    >
      <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-cyan-100 dark:bg-cyan-950">
        <svg class="h-8 w-8 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-navy-900 dark:text-navy-100">All caught up!</h3>
      <p class="mt-1 text-sm text-slate-custom-600 dark:text-slate-custom-400">
        No notifications to show. You're on top of everything.
      </p>
    </div>

    <!-- Notification List -->
    <div v-else class="space-y-3">
      <a
        v-for="notification in filteredNotifications"
        :key="notification.id"
        :href="notification.link"
        class="group flex items-start gap-4 rounded-xl border p-4 transition-all hover:shadow-md"
        :class="getPriorityColor(notification.priority)"
      >
        <!-- Icon -->
        <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/60 dark:bg-navy-800/60">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" :d="notification.icon" />
          </svg>
        </div>

        <!-- Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-start justify-between gap-2">
            <h4 class="text-sm font-semibold text-navy-900 dark:text-navy-100 truncate">
              {{ notification.title }}
            </h4>
            <span
              class="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
              :class="getPriorityBadge(notification.priority)"
            >
              {{ notification.priority }}
            </span>
          </div>
          <p class="mt-0.5 text-xs text-slate-custom-700 dark:text-slate-custom-400 line-clamp-2">
            {{ notification.description }}
          </p>
          <div class="mt-2 flex items-center gap-3 text-xs">
            <span class="font-medium" :class="notification.daysLeft <= 3 ? 'text-red-600 dark:text-red-400' : 'text-slate-custom-600 dark:text-slate-custom-400'">
              {{ formatDaysLeft(notification.daysLeft) }}
            </span>
            <span class="text-slate-custom-500 dark:text-slate-custom-500">
              {{ formatDate(notification.date) }}
            </span>
          </div>
        </div>

        <!-- Arrow -->
        <svg class="h-5 w-5 shrink-0 text-slate-custom-400 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </a>
    </div>
  </div>
</template>
