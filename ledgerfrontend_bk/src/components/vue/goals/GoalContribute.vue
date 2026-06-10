<script setup lang="ts">
/**
 * GoalContribute — Contribute modal for a SavingsGoal.
 *
 * Features:
 *   - Shows goal name, current progress bar, current_amount / target_amount
 *   - Fields: amount (CurrencyInput, required), account_id (dropdown from
 *     accountStore — the account to contribute from), date (date, optional),
 *     notes (textarea, optional)
 *   - On success: show updated progress, if goal becomes is_completed
 *     show celebration message
 *   - Props: goalId (required), open (for modal visibility control)
 *   - Emits: contributed, cancel
 *   - Uses store.contribute() method
 *   - FormErrors display
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  FormErrors,
} from "@/components/vue";
import CurrencyInput from "@/components/vue/CurrencyInput.vue";
import { useDropdownLoader } from "@/composables";
import { useSavingsGoalStore } from "@/stores/savingsGoal";
import { useAccountStore } from "@/stores/account";
import type {
  SavingsGoalOut,
  SavingsContributionOut,
} from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "GoalContribute" });

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = defineProps<{
  /** The savings goal ID to contribute to. */
  goalId: number;
  /** Whether the modal is open (parent controls visibility). */
  open?: boolean;
}>();

const emit = defineEmits<{
  contributed: [result: SavingsContributionOut];
  cancel: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const goalStore = useSavingsGoalStore();
const accountStore = useAccountStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

onMounted(async () => {
  await dropdownLoader.loadDropdown("accounts", accountStore);
});

// ─── Dropdown Data ───────────────────────────────────────────────────────────

const accountDropdown = computed(() =>
  dropdownLoader.getDropdown<{ id: number; name: string }>("accounts"),
);

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(amount: string | number, currency = "USD"): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return "$0.00";
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(num);
}

function getProgressColor(percent: number): string {
  if (percent >= 100) return "bg-cyan-500";
  if (percent >= 75) return "bg-green-500";
  if (percent >= 50) return "bg-cyan-500";
  if (percent >= 25) return "bg-amber-500";
  return "bg-red-500";
}

// ─── Goal Data ───────────────────────────────────────────────────────────────

const goal = computed<SavingsGoalOut | null>(() => goalStore.current);
const goalLoaded = ref(false);

onMounted(async () => {
  if (props.goalId) {
    try {
      await goalStore.fetchOne(props.goalId);
      goalLoaded.value = true;
    } catch {
      goalLoaded.value = false;
    }
  }
});

// ─── Form State ──────────────────────────────────────────────────────────────

const form = ref({
  amount: "",
  account_id: "" as string | number,
  date: new Date().toISOString().split("T")[0],
  notes: "",
});

const loading = ref(false);
const error = ref<string | null>(null);
const fieldErrors = ref<Record<string, string[]>>({});

// ─── Success State ───────────────────────────────────────────────────────────

const contributionResult = ref<SavingsContributionOut | null>(null);
const showCelebration = ref(false);

// ─── Handlers ────────────────────────────────────────────────────────────────

function handleAmountUpdate(data: { amount: string }) {
  form.value.amount = data.amount;
}

async function handleSubmit() {
  if (!props.goalId) return;

  loading.value = true;
  error.value = null;
  fieldErrors.value = {};
  contributionResult.value = null;
  showCelebration.value = false;

  try {
    const payload = {
      amount: String(form.value.amount),
      account_id: Number(form.value.account_id),
      date: form.value.date || null,
      notes: form.value.notes || null,
    };

    const result = await goalStore.contribute(props.goalId, payload);

    if (result) {
      contributionResult.value = result;

      // Check if goal is now completed after refreshing
      const updatedGoal = goalStore.current;
      if (updatedGoal?.is_completed) {
        showCelebration.value = true;
      }

      // Emit after a brief delay if celebration, otherwise immediately
      if (!showCelebration.value) {
        emit("contributed", result);
      }
    }
  } catch (err: unknown) {
    if (typeof err === "object" && err !== null) {
      const obj = err as Record<string, unknown>;
      if (typeof obj.message === "string") error.value = obj.message;
      else if (typeof obj.detail === "string") error.value = obj.detail;
      else error.value = "Failed to contribute to goal";
    } else {
      error.value = "Failed to contribute to goal";
    }

    // Check for field errors from the store
    if (goalStore.fieldErrors && Object.keys(goalStore.fieldErrors).length > 0) {
      fieldErrors.value = goalStore.fieldErrors;
    }
  } finally {
    loading.value = false;
  }
}

function handleCancel() {
  emit("cancel");
}

function handleCelebrationContinue() {
  if (contributionResult.value) {
    emit("contributed", contributionResult.value);
  }
}

// ─── Computed ────────────────────────────────────────────────────────────────

const canSubmit = computed(() => {
  return form.value.amount && parseFloat(form.value.amount) > 0 && form.value.account_id;
});
</script>

<template>
  <div>
    <!-- Celebration State -->
    <div v-if="showCelebration" class="text-center py-6 space-y-4">
      <div class="text-5xl mb-2" aria-hidden="true">&#127881;&#10024;&#127881;</div>
      <h3 class="text-xl font-bold text-cyan-700 dark:text-cyan-300">
        Goal Achieved!
      </h3>
      <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">
        Congratulations! You've reached your savings goal
        <span class="font-semibold text-navy-900 dark:text-navy-100">{{ goal?.name }}</span>!
      </p>
      <div
        v-if="contributionResult"
        class="rounded-lg bg-cyan-50 dark:bg-cyan-950/30 border border-cyan-200 dark:border-cyan-800 p-4 text-sm"
      >
        <p class="text-cyan-700 dark:text-cyan-300">
          <strong>Contributed:</strong>
          {{ formatCurrency(contributionResult.new_amount) }}
          (was {{ formatCurrency(contributionResult.old_amount) }})
        </p>
      </div>
      <button
        type="button"
        class="btn-primary"
        @click="handleCelebrationContinue"
      >
        Continue
      </button>
    </div>

    <!-- Normal Contribute Form -->
    <template v-else>
      <!-- Goal Progress Display -->
      <div
        v-if="goal && goalLoaded"
        class="mb-5 p-4 rounded-lg bg-navy-50 dark:bg-navy-800/50 border border-navy-200 dark:border-navy-700"
      >
        <h4 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-2">
          <span v-if="goal.icon" class="mr-1">{{ goal.icon }}</span>
          {{ goal.name }}
        </h4>
        <div class="mb-2">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
              {{ formatCurrency(goal.current_amount, goal.currency || "USD") }}
              of
              {{ formatCurrency(goal.target_amount, goal.currency || "USD") }}
            </span>
            <span class="text-xs font-medium text-navy-900 dark:text-navy-100">
              {{ goal.progress_percent }}%
            </span>
          </div>
          <div class="h-2.5 rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden">
            <div
              :class="['h-full rounded-full transition-all duration-500', getProgressColor(goal.progress_percent)]"
              :style="{ width: `${Math.min(goal.progress_percent, 100)}%` }"
            />
          </div>
        </div>
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
          {{ formatCurrency(goal.remaining, goal.currency || "USD") }} remaining
        </p>
      </div>

      <!-- Loading Goal -->
      <div
        v-else-if="!goalLoaded"
        class="mb-5 p-4 rounded-lg bg-navy-50 dark:bg-navy-800/50 border border-navy-200 dark:border-navy-700 animate-pulse"
      >
        <div class="h-4 bg-navy-200 dark:bg-navy-700 rounded w-1/2 mb-3" />
        <div class="h-2.5 bg-navy-200 dark:bg-navy-700 rounded mb-2" />
        <div class="h-3 bg-navy-200 dark:bg-navy-700 rounded w-1/3" />
      </div>

      <!-- Contribution Form -->
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <!-- Form Errors -->
        <FormErrors :errors="error" :field-errors="fieldErrors" />

        <!-- Amount -->
        <div class="space-y-1.5">
          <label class="label-text">
            Contribution Amount <span class="text-debit">*</span>
          </label>
          <CurrencyInput
            :amount="String(form.amount)"
            :currency="goal?.currency ?? 'USD'"
            :show-currency-select="false"
            placeholder="0.00"
            @update="handleAmountUpdate"
          />
        </div>

        <!-- Account -->
        <div class="space-y-1.5">
          <label for="contribute-account" class="label-text">
            From Account <span class="text-debit">*</span>
          </label>
          <select
            id="contribute-account"
            v-model="form.account_id"
            class="input-field"
            required
          >
            <option value="" disabled>Select an account</option>
            <option
              v-for="acct in accountDropdown"
              :key="acct.id"
              :value="acct.id"
            >
              {{ acct.name }}
            </option>
          </select>
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
            The account this contribution will be deducted from
          </p>
        </div>

        <!-- Date -->
        <div class="space-y-1.5">
          <label for="contribute-date" class="label-text">Date</label>
          <input
            id="contribute-date"
            v-model="form.date"
            type="date"
            class="input-field"
          />
        </div>

        <!-- Notes -->
        <div class="space-y-1.5">
          <label for="contribute-notes" class="label-text">Notes</label>
          <textarea
            id="contribute-notes"
            v-model="form.notes"
            class="input-field min-h-[60px] resize-y"
            placeholder="Optional notes about this contribution..."
            rows="2"
          />
        </div>

        <!-- Footer Buttons -->
        <div class="flex items-center justify-end gap-3 pt-3 border-t border-navy-100 dark:border-navy-800">
          <button
            type="button"
            class="btn-secondary"
            :disabled="loading"
            @click="handleCancel"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn-primary"
            :disabled="loading || !canSubmit"
            @click="handleSubmit"
          >
            <svg
              v-if="loading"
              class="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Contribute
          </button>
        </div>
      </form>
    </template>
  </div>
</template>
