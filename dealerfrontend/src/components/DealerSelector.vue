/**
 * DealerSelector — UI component for selecting dealer context.
 *
 * Shows a dropdown for DSRs/Collectors who work for multiple dealers.
 * Auto-selects for single-dealer users (dropdown hidden in that case).
 *
 * The selected dealer is stored in localStorage and sent as X-Dealer-Username
 * header in API requests for proper multi-tenant data isolation.
 *
 * Usage:
 *   <DealerSelector @dealer-changed="handleDealerChanged" />
 */

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { ChevronDown, Building2, Check } from "lucide-vue-next";
import { useDealerContext } from "../composables/useDealerContext";
import { useAuth } from "../composables/useAuth";
import type { DealerConfig } from "../lib/types";

// ─── Props & Emits ────────────────────────────────────────────────────────────

const emit = defineEmits<{
  (e: "dealer-changed", dealer: DealerConfig): void;
}>();

// ─── Composables ───────────────────────────────────────────────────────────────

const {
  dealers,
  selectedDealer,
  loading,
  isMultiDealer,
  selectDealer,
  initDealerContext,
} = useDealerContext();

const { user, access } = useAuth();

// Check if user is a dealer (from auth response)
const isDealer = computed(() => {
  // Check is_dealer flag from access map
  return access.value?.is_dealer === true || access.value?.role === 'dealer';
});

// ─── Local State ──────────────────────────────────────────────────────────────

const isOpen = ref(false);
const dropdownRef = ref<HTMLElement | null>(null);

// ─── Computed ─────────────────────────────────────────────────────────────────

const displayText = computed(() => {
  if (!selectedDealer.value) return "Select Dealer";
  return selectedDealer.value.businessName || selectedDealer.value.fullName || "Unknown Dealer";
});

const displayInitials = computed(() => {
  if (!selectedDealer.value) return "??";
  const name = selectedDealer.value.businessName || selectedDealer.value.fullName || "?";
  return name
    .split(" ")
    .map((n) => n[0] || "?")
    .join("")
    .substring(0, 2)
    .toUpperCase();
});

// ─── Methods ──────────────────────────────────────────────────────────────────

function handleSelect(dealer: DealerConfig) {
  selectDealer(dealer);
  isOpen.value = false;
  emit("dealer-changed", dealer);
}

function toggleDropdown() {
  if (isMultiDealer.value) {
    isOpen.value = !isOpen.value;
  }
}

function handleClickOutside(event: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    isOpen.value = false;
  }
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async () => {
  // Pass user info and is_dealer flag to auto-select the correct dealer
  await initDealerContext(user.value, isDealer.value);
  
  // Close dropdown when clicking outside
  document.addEventListener("click", handleClickOutside);
});

// Cleanup
import { onUnmounted } from "vue";
onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
});
</script>

<template>
  <!-- Only show if user has multiple dealers -->
  <div v-if="isMultiDealer" class="dealer-selector" ref="dropdownRef">
    <button
      type="button"
      class="dealer-selector-trigger"
      :class="{ 'dealer-selector-trigger--open': isOpen }"
      @click="toggleDropdown"
      :disabled="loading"
    >
      <div class="dealer-avatar">
        {{ displayInitials }}
      </div>
      <span class="dealer-name">{{ displayText }}</span>
      <ChevronDown class="dealer-chevron" :class="{ 'dealer-chevron--rotated': isOpen }" />
    </button>

    <!-- Dropdown Menu -->
    <Transition name="dropdown">
      <div v-if="isOpen" class="dealer-dropdown">
        <div class="dealer-dropdown-header">
          <Building2 class="dealer-dropdown-header-icon" />
          <span>Select Dealer Context</span>
        </div>
        
        <div class="dealer-dropdown-list">
          <button
            v-for="dealer in dealers"
            :key="dealer.username"
            type="button"
            class="dealer-option"
            :class="{ 'dealer-option--selected': selectedDealer?.username === dealer.username }"
            @click="handleSelect(dealer)"
          >
            <div class="dealer-option-avatar">
              {{ (dealer.businessName || dealer.fullName || "?")
                .split(" ")
                .map((n) => n[0] || "?")
                .join("")
                .substring(0, 2)
                .toUpperCase() }}
            </div>
            <div class="dealer-option-info">
              <span class="dealer-option-name">
                {{ dealer.businessName || dealer.fullName || "Unknown Dealer" }}
              </span>
              <span v-if="dealer.businessName" class="dealer-option-sub">
                {{ dealer.fullName }}
              </span>
            </div>
            <Check
              v-if="selectedDealer?.username === dealer.username"
              class="dealer-option-check"
            />
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dealer-selector {
  position: relative;
  z-index: 100;
}

.dealer-selector-trigger {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  color: #fff;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dealer-selector-trigger:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.dealer-selector-trigger--open {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.25);
}

.dealer-selector-trigger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dealer-avatar {
  width: 1.75rem;
  height: 1.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f97316, #ea580c);
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #fff;
}

.dealer-name {
  flex: 1;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
}

.dealer-chevron {
  width: 1rem;
  height: 1rem;
  color: rgba(255, 255, 255, 0.5);
  transition: transform 0.2s ease;
}

.dealer-chevron--rotated {
  transform: rotate(180deg);
}

/* Dropdown */
.dealer-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  min-width: 240px;
  background: #1f1f1f;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.75rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.dealer-dropdown-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.dealer-dropdown-header-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.dealer-dropdown-list {
  padding: 0.25rem;
  max-height: 300px;
  overflow-y: auto;
}

.dealer-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.625rem 0.75rem;
  background: transparent;
  border: none;
  border-radius: 0.5rem;
  color: #fff;
  cursor: pointer;
  transition: all 0.15s ease;
}

.dealer-option:hover {
  background: rgba(255, 255, 255, 0.05);
}

.dealer-option--selected {
  background: rgba(249, 115, 22, 0.15);
}

.dealer-option-avatar {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #374151, #4b5563);
  border-radius: 0.375rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #fff;
}

.dealer-option--selected .dealer-option-avatar {
  background: linear-gradient(135deg, #f97316, #ea580c);
}

.dealer-option-info {
  flex: 1;
  text-align: left;
  min-width: 0;
}

.dealer-option-name {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dealer-option-sub {
  display: block;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dealer-option-check {
  width: 1.125rem;
  height: 1.125rem;
  color: #f97316;
  flex-shrink: 0;
}

/* Transitions */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem);
}
</style>
