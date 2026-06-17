/**
 * useSettingsModal — global state for the dealer settings modal.
 *
 * Extracted from App.vue so the modal (rendered in AppFooter.vue) can be
 * opened from any page or component.
 */

import { ref } from "vue";
import { dealerService } from "../services/api";
import { useDealerContext } from "./useDealerContext";
import { useToasts } from "./useToasts";

const showSettingsModal = ref(false);

// Settings form fields
const settingsSelectedCurrency = ref("INR");
const settingsSelectedLocale = ref("en-IN");
const settingsBusinessName = ref("");
const settingsGstNumber = ref("");
const settingsPhoneNumber = ref("");
const settingsEmail = ref("");
const settingsCommunicationNumber = ref("");
const settingsGoogleMapUrl = ref("");
const settingsAddress = ref("");

const CURRENCY_LOCALES: Record<string, string> = {
  INR: "en-IN",
  USD: "en-US",
  EUR: "en-IE",
  GBP: "en-GB",
  AED: "en-AE",
  JPY: "ja-JP",
  CAD: "en-CA",
  AUD: "en-AU",
  SGD: "en-SG",
};

function syncFromDealer(dealer: {
  defaultCurrency?: string;
  defaultLocale?: string;
  businessName?: string;
  gstNumber?: string;
  phoneNumber?: string;
  email?: string;
  communicationNumber?: string;
  googleMapUrl?: string;
  address?: string;
} | null): void {
  if (!dealer) return;
  settingsSelectedCurrency.value = dealer.defaultCurrency || "INR";
  settingsSelectedLocale.value = dealer.defaultLocale || "en-IN";
  settingsBusinessName.value = dealer.businessName || "";
  settingsGstNumber.value = dealer.gstNumber || "";
  settingsPhoneNumber.value = dealer.phoneNumber || "";
  settingsEmail.value = dealer.email || "";
  settingsCommunicationNumber.value = dealer.communicationNumber || "";
  settingsGoogleMapUrl.value = dealer.googleMapUrl || "";
  settingsAddress.value = dealer.address || "";
}

export function useSettingsModal() {
  const { selectedDealer, dealers, selectDealer } = useDealerContext();
  const { triggerToast, triggerErrorToast } = useToasts();

  function openSettings(): void {
    syncFromDealer(selectedDealer.value);
    showSettingsModal.value = true;
  }

  function closeSettings(): void {
    showSettingsModal.value = false;
  }

  async function handleSelectDealer(dealer: any): Promise<void> {
    selectDealer(dealer);
    syncFromDealer(dealer);
    triggerToast(`Active profile switched to ${dealer.fullName}`);
  }

  async function handleUpdateDealerSettings(): Promise<void> {
    if (!selectedDealer.value?.username) return;
    try {
      await dealerService.updateDealerSettings({
        username: selectedDealer.value.username,
        defaultCurrency: settingsSelectedCurrency.value,
        defaultLocale: CURRENCY_LOCALES[settingsSelectedCurrency.value] || "en-US",
        businessName: settingsBusinessName.value,
        gstNumber: settingsGstNumber.value,
        phoneNumber: settingsPhoneNumber.value,
        email: settingsEmail.value,
        communicationNumber: settingsCommunicationNumber.value,
        googleMapUrl: settingsGoogleMapUrl.value,
        address: settingsAddress.value,
      });
      // Sync back into the dealer-context composable so future opens show updated values
      if (selectedDealer.value) {
        selectDealer({
          ...selectedDealer.value,
          defaultCurrency: settingsSelectedCurrency.value,
          defaultLocale: CURRENCY_LOCALES[settingsSelectedCurrency.value] || "en-US",
          businessName: settingsBusinessName.value,
          gstNumber: settingsGstNumber.value,
          phoneNumber: settingsPhoneNumber.value,
          email: settingsEmail.value,
          communicationNumber: settingsCommunicationNumber.value,
          googleMapUrl: settingsGoogleMapUrl.value,
          address: settingsAddress.value,
        });
      }
      triggerToast("Settings updated successfully!");
      showSettingsModal.value = false;
    } catch (err: any) {
      console.error(err);
      triggerErrorToast(err?.message || "Error updating settings");
    }
  }

  return {
    showSettingsModal,
    settingsSelectedCurrency,
    settingsSelectedLocale,
    settingsBusinessName,
    settingsGstNumber,
    settingsPhoneNumber,
    settingsEmail,
    settingsCommunicationNumber,
    settingsGoogleMapUrl,
    settingsAddress,
    CURRENCY_LOCALES,
    dealers,
    selectedDealer,
    openSettings,
    closeSettings,
    handleSelectDealer,
    handleUpdateDealerSettings,
    syncFromDealer,
  };
}
