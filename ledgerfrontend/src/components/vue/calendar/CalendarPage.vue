<script setup lang="ts">
/**
 * CalendarPage — financial calendar with bills, insurance renewals,
 * debt payments, and goal deadlines.
 *
 * Uses a month view grid with event dots and a side panel showing
 * events for the selected day.
 */

import { ref, computed, onMounted } from "vue";
import { ledgerApi } from "@/lib/ledgerApi";
import { useToast } from "@/composables/useToast";
import { getUserTimezone } from "@/lib/timezone";
import { formatCurrency, getBaseCurrency } from "@/lib/currency";

// ─── Types ──────────────────────────────────────────────────────────────────

interface CalendarEvent {
  id: string;
  type: "bill" | "insurance" | "debt" | "goal";
  title: string;
  date: string;
  amount?: number;
  currency?: string;
  link: string;
  color: string;
}

// ─── State ──────────────────────────────────────────────────────────────────

const loading = ref(true);
const currentMonth = ref(new Date().getMonth());
const currentYear = ref(new Date().getFullYear());
const selectedDate = ref<string | null>(null);
const events = ref<CalendarEvent[]>([]);
const toast = useToast();

// ─── Computed ───────────────────────────────────────────────────────────────

const monthName = computed(() => {
  return new Date(currentYear.value, currentMonth.value).toLocaleDateString(undefined, {
    month: "long",
    year: "numeric",
  });
});

const calendarDays = computed(() => {
  const year = currentYear.value;
  const month = currentMonth.value;
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();

  const days: { date: number; month: "prev" | "current" | "next"; fullDate: string }[] = [];

  // Previous month padding
  for (let i = firstDay - 1; i >= 0; i--) {
    const date = daysInPrevMonth - i;
    const m = month === 0 ? 11 : month - 1;
    const y = month === 0 ? year - 1 : year;
    days.push({
      date,
      month: "prev",
      fullDate: `${y}-${String(m + 1).padStart(2, "0")}-${String(date).padStart(2, "0")}`,
    });
  }

  // Current month
  for (let i = 1; i <= daysInMonth; i++) {
    days.push({
      date: i,
      month: "current",
      fullDate: `${year}-${String(month + 1).padStart(2, "0")}-${String(i).padStart(2, "0")}`,
    });
  }

  // Next month padding (fill to 42 cells = 6 rows)
  const remaining = 42 - days.length;
  for (let i = 1; i <= remaining; i++) {
    const m = month === 11 ? 0 : month + 1;
    const y = month === 11 ? year + 1 : year;
    days.push({
      date: i,
      month: "next",
      fullDate: `${y}-${String(m + 1).padStart(2, "0")}-${String(i).padStart(2, "0")}`,
    });
  }

  return days;
});

const eventsByDate = computed(() => {
  const map: Record<string, CalendarEvent[]> = {};
  for (const event of events.value) {
    const dateKey = event.date.split("T")[0]; // Handle ISO dates
    if (!map[dateKey]) map[dateKey] = [];
    map[dateKey].push(event);
  }
  return map;
});

const selectedEvents = computed(() => {
  if (!selectedDate.value) return [];
  return eventsByDate.value[selectedDate.value] || [];
});

const today = computed(() => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
});

// ─── Helpers ────────────────────────────────────────────────────────────────

function getTypeColor(type: CalendarEvent["type"]): string {
  switch (type) {
    case "bill": return "bg-amber-500";
    case "insurance": return "bg-green-500";
    case "debt": return "bg-red-500";
    case "goal": return "bg-cyan-500";
  }
}

function getTypeBgColor(type: CalendarEvent["type"]): string {
  switch (type) {
    case "bill": return "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800";
    case "insurance": return "bg-green-50 border-green-200 dark:bg-green-950/30 dark:border-green-800";
    case "debt": return "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800";
    case "goal": return "bg-cyan-50 border-cyan-200 dark:bg-cyan-950/30 dark:border-cyan-800";
  }
}

function getTypeLabel(type: CalendarEvent["type"]): string {
  switch (type) {
    case "bill": return "Bill Due";
    case "insurance": return "Insurance Renewal";
    case "debt": return "Debt Payment";
    case "goal": return "Goal Deadline";
  }
}

function selectDate(fullDate: string): void {
  selectedDate.value = fullDate;
}

function prevMonth(): void {
  if (currentMonth.value === 0) {
    currentMonth.value = 11;
    currentYear.value--;
  } else {
    currentMonth.value--;
  }
  selectedDate.value = null;
}

function nextMonth(): void {
  if (currentMonth.value === 11) {
    currentMonth.value = 0;
    currentYear.value++;
  } else {
    currentMonth.value++;
  }
  selectedDate.value = null;
}

function goToday(): void {
  const d = new Date();
  currentMonth.value = d.getMonth();
  currentYear.value = d.getFullYear();
  selectedDate.value = today.value;
}

// ─── Data Fetching ──────────────────────────────────────────────────────────

async function fetchCalendarEvents(): Promise<void> {
  loading.value = true;
  events.value = [];

  try {
    // Fetch bills
    try {
      const bills = await ledgerApi.bills.upcoming(90);
      for (const bill of bills) {
        events.value.push({
          id: `bill-${bill.id}`,
          type: "bill",
          title: bill.name,
          date: bill.next_due_date?.split("T")[0] || "",
          amount: bill.amount,
          currency: bill.currency,
          link: `/dashboard/bills/${bill.id}`,
          color: getTypeColor("bill"),
        });
      }
    } catch { /* skip */ }

    // Fetch insurance renewals
    try {
      const policies = await ledgerApi.insurance.renewals(90);
      for (const policy of policies) {
        if (policy.next_renewal_date) {
          events.value.push({
            id: `insurance-${policy.id}`,
            type: "insurance",
            title: `${policy.provider_name} (${policy.policy_type})`,
            date: policy.next_renewal_date?.split("T")[0] || "",
            amount: policy.premium_amount,
            currency: policy.currency,
            link: `/dashboard/insurance`,
            color: getTypeColor("insurance"),
          });
        }
      }
    } catch { /* skip */ }

    // Fetch savings goals with deadlines
    try {
      const goals = await ledgerApi.savingsGoals.dashboard();
      for (const goal of goals) {
        if (goal.deadline) {
          events.value.push({
            id: `goal-${goal.id}`,
            type: "goal",
            title: goal.name,
            date: goal.deadline?.split("T")[0] || "",
            amount: goal.target_amount,
            currency: goal.currency,
            link: `/dashboard/goals`,
            color: getTypeColor("goal"),
          });
        }
      }
    } catch { /* skip */ }

  } catch (err) {
    console.error("Failed to fetch calendar events:", err);
    toast.error("Failed to load calendar events");
  } finally {
    loading.value = false;
  }
}

// ─── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(() => {
  fetchCalendarEvents();
  selectedDate.value = today.value;
});
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-navy-900 dark:text-navy-100">Financial Calendar</h1>
        <p class="mt-1 text-sm text-slate-custom-600 dark:text-slate-custom-400">
          Bills, renewals, payments, and deadlines at a glance
        </p>
      </div>
      <div class="flex items-center gap-2">
        <!-- Legend -->
        <div class="hidden sm:flex items-center gap-3 text-xs text-slate-custom-600 dark:text-slate-custom-400 mr-4">
          <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-amber-500"></span> Bills</span>
          <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-green-500"></span> Insurance</span>
          <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-red-500"></span> Debt</span>
          <span class="flex items-center gap-1"><span class="h-2 w-2 rounded-full bg-cyan-500"></span> Goals</span>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <svg class="h-8 w-8 animate-spin text-cyan-500" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <div v-else class="grid gap-6 lg:grid-cols-[1fr_320px]">
      <!-- Calendar Grid -->
      <div class="rounded-xl border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900/80 p-4">
        <!-- Month Navigation -->
        <div class="mb-4 flex items-center justify-between">
          <button
            class="rounded-lg p-2 text-slate-custom-600 hover:bg-navy-100 dark:text-slate-custom-400 dark:hover:bg-navy-800 transition-colors"
            @click="prevMonth"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div class="flex items-center gap-3">
            <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100">{{ monthName }}</h2>
            <button
              class="rounded-lg border border-navy-200 px-2 py-1 text-xs font-medium text-slate-custom-600 hover:bg-navy-100 dark:border-navy-700 dark:text-slate-custom-400 dark:hover:bg-navy-800 transition-colors"
              @click="goToday"
            >
              Today
            </button>
          </div>
          <button
            class="rounded-lg p-2 text-slate-custom-600 hover:bg-navy-100 dark:text-slate-custom-400 dark:hover:bg-navy-800 transition-colors"
            @click="nextMonth"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        <!-- Day Headers -->
        <div class="grid grid-cols-7 gap-1 mb-1">
          <div v-for="day in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']" :key="day" class="py-2 text-center text-xs font-semibold text-slate-custom-600 dark:text-slate-custom-400">
            {{ day }}
          </div>
        </div>

        <!-- Day Cells -->
        <div class="grid grid-cols-7 gap-1">
          <button
            v-for="day in calendarDays"
            :key="day.fullDate"
            class="relative flex flex-col items-center rounded-lg p-1.5 min-h-[64px] text-sm transition-colors"
            :class="[
              day.month !== 'current' ? 'text-slate-custom-400 dark:text-slate-custom-600' : 'text-navy-900 dark:text-navy-100',
              selectedDate === day.fullDate ? 'bg-cyan-100 dark:bg-cyan-950 ring-2 ring-cyan-500' : 'hover:bg-navy-50 dark:hover:bg-navy-800/50',
              today === day.fullDate && selectedDate !== day.fullDate ? 'font-bold' : '',
            ]"
            @click="selectDate(day.fullDate)"
          >
            <span
              class="flex h-7 w-7 items-center justify-center rounded-full text-sm"
              :class="today === day.fullDate ? 'bg-cyan-600 text-white' : ''"
            >
              {{ day.date }}
            </span>
            <!-- Event dots -->
            <div v-if="eventsByDate[day.fullDate]" class="mt-0.5 flex flex-wrap gap-0.5 justify-center">
              <span
                v-for="(evt, idx) in eventsByDate[day.fullDate].slice(0, 4)"
                :key="idx"
                class="h-1.5 w-1.5 rounded-full"
                :class="evt.color"
              ></span>
              <span v-if="eventsByDate[day.fullDate].length > 4" class="text-[8px] text-slate-custom-500">+{{ eventsByDate[day.fullDate].length - 4 }}</span>
            </div>
          </button>
        </div>
      </div>

      <!-- Selected Day Events Panel -->
      <div class="rounded-xl border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900/80 p-4">
        <h3 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-3">
          {{ selectedDate ? new Date(selectedDate + "T00:00:00").toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" }) : "Select a date" }}
        </h3>

        <div v-if="!selectedDate" class="py-8 text-center">
          <p class="text-sm text-slate-custom-500 dark:text-slate-custom-500">Click a day to see events</p>
        </div>

        <div v-else-if="selectedEvents.length === 0" class="py-8 text-center">
          <div class="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-navy-100 dark:bg-navy-800">
            <svg class="h-5 w-5 text-slate-custom-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <p class="text-sm text-slate-custom-500 dark:text-slate-custom-500">No events on this day</p>
        </div>

        <div v-else class="space-y-2">
          <a
            v-for="event in selectedEvents"
            :key="event.id"
            :href="event.link"
            class="block rounded-lg border p-3 transition-all hover:shadow-sm"
            :class="getTypeBgColor(event.type)"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <p class="text-sm font-medium text-navy-900 dark:text-navy-100 truncate">{{ event.title }}</p>
                <p class="mt-0.5 text-xs text-slate-custom-600 dark:text-slate-custom-400">{{ getTypeLabel(event.type) }}</p>
              </div>
              <svg class="h-4 w-4 shrink-0 text-slate-custom-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </div>
            <p v-if="event.amount && event.currency" class="mt-1.5 text-sm font-semibold text-navy-900 dark:text-navy-100">
              {{ formatCurrency(event.amount, event.currency) }}
            </p>
          </a>
        </div>
      </div>
    </div>
  </div>
</template>
