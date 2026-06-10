<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { auth, db, signIn } from './firebase';
import { onAuthStateChanged, signInAnonymously } from 'firebase/auth';
import { 
  collection, 
  query, 
  onSnapshot, 
  doc, 
  setDoc, 
  serverTimestamp, 
  getDoc,
  getDocs,
  deleteDoc,
  where
} from 'firebase/firestore';
import { 
  Plus, 
  LayoutDashboard, 
  ChevronRight,
  Wallet,
  X,
  Menu,
  Sun,
  Moon,
  Coins,
  Settings,
  Target,
  Database,
  TrendingUp,
  CreditCard,
  Scale,
  Home,
  KeyRound,
  FolderLock
} from 'lucide-vue-next';
import { type Group } from './types';
import { CURRENCIES } from './utils/currency';

// Child components
import BudgetExpenses from './components/BudgetExpenses.vue';
import GroupView from './components/GroupView.vue';
import SavingGoalsHub from './components/SavingGoalsHub.vue';
import GroupSavingGoalsView from './components/GroupSavingGoalsView.vue';
import IncomeHub from './components/IncomeHub.vue';
import GroupIncomeView from './components/GroupIncomeView.vue';
import AccountsHub from './components/AccountsHub.vue';
import GroupAccountsView from './components/GroupAccountsView.vue';
import LoansHub from './components/LoansHub.vue';
import GroupLoansView from './components/GroupLoansView.vue';
import MortgagesHub from './components/MortgagesHub.vue';
import GroupMortgagesView from './components/GroupMortgagesView.vue';
import RentHub from './components/RentHub.vue';
import GroupRentView from './components/GroupRentView.vue';
import DocumentVaultHub from './components/DocumentVaultHub.vue';
import GroupDocumentVaultView from './components/GroupDocumentVaultView.vue';
import CreateGroupModal from './components/CreateGroupModal.vue';
import DBInspector from './components/DBInspector.vue';
import CategorySettingsModal from './components/CategorySettingsModal.vue';
import { fetchCustomCategories } from './utils/categories';

const user = ref<any>(null);
const loading = ref(true);
const groups = ref<Group[]>([]);
const lastError = ref<string | null>(null);
const selectedGroupId = ref<string | null>(null);
const activeService = ref<'budget' | 'savings' | 'income' | 'accounts' | 'loans_debts' | 'mortgages' | 'rent' | 'document_vault' | 'db-inspector'>('budget');
const isCreateModalOpen = ref(false);
const isCategorySettingsOpen = ref(false);
const dataDeletedPopup = ref(false);
const showWelcomePopup = ref(false);
const isSidebarOpen = ref(false);

const filteredGroups = computed(() => {
  if (activeService.value === 'db-inspector') return [];
  return groups.value.filter(g => {
    const gService = g.service || 'budget';
    return gService === activeService.value;
  });
});

const theme = ref<'light' | 'dark'>(() => {
  if (typeof window !== 'undefined') {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'dark';
  }
  return 'dark';
});

// Toggle Theme Handler
const toggleTheme = () => {
  theme.value = theme.value === 'dark' ? 'light' : 'dark';
};

watch(theme, (newTheme) => {
  const root = window.document.documentElement;
  if (newTheme === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
  localStorage.setItem('theme', newTheme);
}, { immediate: true });

// Subscriptions
let unsubscribeAuth: (() => void) | null = null;
let unsubscribeGroups: (() => void) | null = null;

const updateDefaultCurrency = async (newCurrency: string) => {
  if (!user.value?.uid) return;
  try {
    const userRef = doc(db, 'users', user.value.uid);
    await setDoc(userRef, { defaultCurrency: newCurrency }, { merge: true });
    user.value = {
      ...user.value,
      defaultCurrency: newCurrency
    };
  } catch (error) {
    console.error("Error setting default currency:", error);
  }
};

onMounted(async () => {
  // Global callback with trigger creation modal from Budget & Expenses service
  (window as any).openCreateGroupModal = () => {
    isCreateModalOpen.value = true;
  };

  // Attempt auto silent login
  try {
    if (!auth.currentUser) {
      await signInAnonymously(auth);
    }
  } catch (err: any) {
    if (err?.code === 'auth/admin-restricted-operation') {
      console.log("Anonymous sign-in is disabled in your Firebase console. Please click 'Continue with Google' to sign in.");
    } else {
      console.warn("Auto anonymous sign in skipped:", err?.message || err);
    }
  }

  unsubscribeAuth = onAuthStateChanged(auth, async (currentUser) => {
    if (currentUser) {
      // Check if user has seen welcome popup
      const hasSeenWelcome = localStorage.getItem(`hasSeenWelcome_${currentUser.uid}`);
      if (!hasSeenWelcome) {
        showWelcomePopup.value = true;
      }

      // Ensure user profile exists
      const userRef = doc(db, 'users', currentUser.uid);
      const userSnap = await getDoc(userRef);
      let pData: any = null;

      if (!userSnap.exists()) {
        try {
          pData = {
            uid: currentUser.uid,
            displayName: "Kabita Gorain",
            email: "kabitagorain6@gmail.com",
            photoURL: "https://avatar.iran.liara.run/public/60",
            defaultCurrency: 'USD',
            createdAt: serverTimestamp(),
          };
          await setDoc(userRef, pData);
        } catch (error) {
          console.error("Error creating user profile:", error);
        }
      } else {
        pData = userSnap.data();
        const createdAt = pData.createdAt?.toDate();
        if (createdAt && (Date.now() - createdAt.getTime() > 24 * 60 * 60 * 1000)) {
          try {
            console.log("Checking for demo data reset...");
            const groupsQuery = query(collection(db, 'groups'), where('memberIds', 'array-contains', currentUser.uid));
            const groupsSnap = await getDocs(groupsQuery);
            console.log(`Found ${groupsSnap.docs.length} groups for user ${currentUser.uid}`);
            for (const groupDoc of groupsSnap.docs) {
              if (groupDoc.data().createdBy === currentUser.uid) {
                console.log(`Deleting group ${groupDoc.id} due to demo reset`);
                await deleteDoc(doc(db, 'groups', groupDoc.id));
              }
            }
            // Reset their createdAt
            await setDoc(userRef, {
              ...pData,
              createdAt: serverTimestamp(),
            });
            // Show popup
            dataDeletedPopup.value = true;
          } catch (error) {
            console.error("Error resetting demo data:", error);
          }
        }
      }

      user.value = {
        uid: currentUser.uid,
        displayName: "Kabita Gorain",
        email: "kabitagorain6@gmail.com",
        photoURL: "https://avatar.iran.liara.run/public/60",
        defaultCurrency: pData?.defaultCurrency || 'USD'
      };

      // Fetch custom categories for the current user
      await fetchCustomCategories(currentUser.uid);

      // Setup groups realtime listener
      const groupsQuery = query(
        collection(db, 'groups'),
        where('memberIds', 'array-contains', currentUser.uid)
      );

      unsubscribeGroups = onSnapshot(groupsQuery, (snapshot) => {
        console.log(`Groups snapshot received: ${snapshot.docs.length} groups`);
        lastError.value = null;
        groups.value = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        } as Group));
      }, (error) => {
        console.error("Error fetching groups:", error);
        lastError.value = error.message;
      });
    } else {
      user.value = null;
      groups.value = [];
      if (unsubscribeGroups) {
        unsubscribeGroups();
        unsubscribeGroups = null;
      }
    }
    loading.value = false;
  });
});

onUnmounted(() => {
  delete (window as any).openCreateGroupModal;
  if (unsubscribeAuth) unsubscribeAuth();
  if (unsubscribeGroups) unsubscribeGroups();
});

// Guard selected groupId if the group is deleted
watch(groups, (newGroups) => {
  if (selectedGroupId.value && !newGroups.find(g => g.id === selectedGroupId.value)) {
    selectedGroupId.value = null;
  }
});

const selectGroup = (id: string | null) => {
  selectedGroupId.value = id;
  isSidebarOpen.value = false;
};

const handleWelcomeDone = () => {
  showWelcomePopup.value = false;
  if (user.value) {
    localStorage.setItem(`hasSeenWelcome_${user.value.uid}`, 'true');
  }
};
</script>

<template>
  <!-- Loading state -->
  <div v-if="loading" class="flex items-center justify-center min-h-screen bg-zinc-50 dark:bg-zinc-950 transition-colors duration-300">
    <div class="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
  </div>

  <!-- Sign In state -->
  <div v-else-if="!user" class="flex flex-col items-center justify-center min-h-screen bg-white dark:bg-zinc-950 p-4 text-center relative overflow-hidden transition-colors duration-300">
    <!-- Background Gradients -->
    <div class="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
      <div class="absolute -top-1/4 -left-1/4 w-[80%] h-[80%] bg-indigo-600/10 dark:bg-indigo-600/20 rounded-full blur-[120px]" />
      <div class="absolute -bottom-1/4 -right-1/4 w-[80%] h-[80%] bg-fuchsia-600/10 dark:bg-fuchsia-600/20 rounded-full blur-[120px]" />
    </div>

    <div class="max-w-md w-full bg-zinc-50/50 dark:bg-white/5 backdrop-blur-2xl p-8 sm:p-12 rounded-[48px] shadow-2xl border border-zinc-200 dark:border-white/10 relative z-10 transition-transform">
      <div class="w-20 h-20 sm:w-24 sm:h-24 bg-gradient-to-br from-indigo-500 to-fuchsia-500 rounded-[32px] flex items-center justify-center mx-auto mb-8 sm:mb-10 shadow-2xl shadow-indigo-500/20">
        <Wallet class="w-10 h-10 sm:w-12 sm:h-12 text-white" />
      </div>
      <h1 class="text-4xl sm:text-5xl font-bold tracking-tight mb-4 text-zinc-900 dark:text-white font-display">Budgeted</h1>
      <p class="text-zinc-500 dark:text-zinc-400 mb-8 sm:mb-12 leading-relaxed text-base sm:text-lg">The professional way to track expenses, split bills, and manage shared budgets.</p>
      <button
        @click="signIn"
        class="w-full py-4 sm:py-5 bg-zinc-900 dark:bg-white text-white dark:text-zinc-950 rounded-2xl font-bold hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-all active:scale-[0.98] flex items-center justify-center gap-4 shadow-xl shadow-zinc-900/10 dark:shadow-white/10 text-base sm:text-lg cursor-pointer outline-none focus:ring-4 focus:ring-indigo-500/40"
      >
        <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="" class="w-6 h-6 bg-white rounded-full p-0.5" />
        Continue with Google
      </button>
    </div>
  </div>

  <!-- Authenticated application layout -->
  <div v-else class="flex h-screen bg-[#faf8f5] dark:bg-[#090e12] font-sans selection:bg-teal-100 selection:text-teal-900 relative overflow-hidden transition-colors duration-300">
    
    <!-- Mobile Sidebar Overlay -->
    <transition name="fade">
      <div v-if="isSidebarOpen" @click="isSidebarOpen = false" class="fixed inset-0 bg-zinc-950/60 backdrop-blur-sm z-40 lg:hidden" />
    </transition>

    <!-- Sidebar component -->
    <aside :class="`
      fixed lg:static inset-y-0 left-0 w-72 bg-white dark:bg-[#0d151a] border-r border-zinc-200 dark:border-white/5 flex flex-col z-50 lg:z-10 transition-all duration-300 ease-in-out overflow-y-auto custom-scrollbar
      ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
    `">
      <div class="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none opacity-10 dark:opacity-20">
        <div class="absolute -top-24 -left-24 w-64 h-64 bg-teal-600 rounded-full blur-[100px]" />
        <div class="absolute top-1/2 -right-32 w-64 h-64 bg-emerald-600 rounded-full blur-[100px]" />
      </div>

      <div class="p-8 relative z-10 shrink-0">
        <div class="flex items-center justify-between mb-10">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-teal-500 to-emerald-500 rounded-xl flex items-center justify-center shadow-lg shadow-teal-500/20">
              <Wallet class="w-6 h-6 text-white" />
            </div>
            <span class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Budgeted</span>
          </div>
          <button @click="isSidebarOpen = false" class="lg:hidden p-2 text-zinc-500 hover:text-zinc-900 dark:hover:text-white cursor-pointer">
            <X class="w-6 h-6" />
          </button>
        </div>

        <div class="mb-3 px-4 shrink-0">
          <span class="text-[10px] font-bold uppercase tracking-[0.2em] text-[#005253] dark:text-teal-400 font-display">Finance Services</span>
        </div>
        <nav class="space-y-1.5 font-display text-sm">
          <button 
            @click="activeService = 'budget'; selectGroup(null)"
            :class="`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 cursor-pointer ${activeService === 'budget' && !selectedGroupId ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-xl shadow-[#005a5b]/10 dark:shadow-teal-500/10' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'}`"
          >
            <LayoutDashboard class="w-5 h-5 shrink-0" />
            <span class="font-bold">Budget & Expenses</span>
          </button>
          <button 
            @click="activeService = 'savings'; selectGroup(null)"
            :class="`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 cursor-pointer ${activeService === 'savings' && !selectedGroupId ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-xl shadow-[#005a5b]/10 dark:shadow-teal-500/10' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'}`"
          >
            <Target class="w-5 h-5 shrink-0" />
            <span class="font-bold">Saving Goals Hub</span>
          </button>
          <button 
            @click="activeService = 'income'; selectGroup(null)"
            :class="`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 cursor-pointer ${activeService === 'income' && !selectedGroupId ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-xl shadow-[#005a5b]/10 dark:shadow-teal-500/10' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'}`"
          >
            <TrendingUp class="w-5 h-5 shrink-0" />
            <span class="font-bold">Target & Income</span>
          </button>
          <button 
            @click="activeService = 'accounts'; selectGroup(null)"
            :class="`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 cursor-pointer ${activeService === 'accounts' && !selectedGroupId ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-xl shadow-[#005a5b]/10 dark:shadow-teal-500/10' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'}`"
          >
            <CreditCard class="w-5 h-5 shrink-0" />
            <span class="font-bold">Cards & Accounts</span>
          </button>
          <button 
            @click="activeService = 'loans_debts'; selectGroup(null)"
            :class="`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 cursor-pointer ${activeService === 'loans_debts' && !selectedGroupId ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-xl shadow-[#005a5b]/10 dark:shadow-teal-500/10' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'}`"
          >
            <Scale class="w-5 h-5 shrink-0" />
            <span class="font-bold">Loans & Debts</span>
          </button>
          <button 
            @click="activeService = 'mortgages'; selectGroup(null)"
            :class="`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 cursor-pointer ${activeService === 'mortgages' && !selectedGroupId ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-xl shadow-[#005a5b]/10 dark:shadow-teal-500/10' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'}`"
          >
            <Home class="w-5 h-5 shrink-0" />
            <span class="font-bold">Mortgages Ledger</span>
          </button>
          <button 
            @click="activeService = 'rent'; selectGroup(null)"
            :class="`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 cursor-pointer ${activeService === 'rent' && !selectedGroupId ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-xl shadow-[#005a5b]/10 dark:shadow-teal-500/10' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'}`"
          >
            <KeyRound class="w-5 h-5 shrink-0" />
            <span class="font-bold">Rent Management</span>
          </button>
          <button 
            @click="activeService = 'document_vault'; selectGroup(null)"
            :class="`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 cursor-pointer ${activeService === 'document_vault' && !selectedGroupId ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-xl shadow-[#005a5b]/10 dark:shadow-teal-500/10' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'}`"
          >
            <FolderLock class="w-5 h-5 shrink-0" />
            <span class="font-bold">Document Vault</span>
          </button>
          <button 
            @click="activeService = 'db-inspector'; selectGroup(null)"
            :class="`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 cursor-pointer ${activeService === 'db-inspector' && !selectedGroupId ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-xl shadow-[#005a5b]/10 dark:shadow-teal-500/10' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'}`"
          >
            <Database class="w-5 h-5 shrink-0" />
            <span class="font-bold">SQLite DB Console</span>
          </button>
        </nav>
      </div>

      <!-- Scrollable User Budgets list -->
      <div class="flex-1 overflow-y-auto px-4 py-2 relative z-10 custom-scrollbar min-h-[200px] overflow-x-hidden">
        <div class="flex items-center justify-between px-4 mb-4">
          <span class="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400 dark:text-zinc-500 truncate block max-w-[180px]">
            {{ activeService === 'savings' ? 'Saving Groups' : activeService === 'income' ? 'Income Groups' : activeService === 'accounts' ? 'Account Ledgers' : activeService === 'loans_debts' ? 'Loan Ledgers' : activeService === 'mortgages' ? 'Mortgages' : activeService === 'rent' ? 'Lease Ledgers' : activeService === 'document_vault' ? 'Cabinet Vaults' : 'Your Budgets' }}
          </span>
          <button @click="isCreateModalOpen = true" class="p-1.5 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-lg transition-colors text-zinc-400 dark:text-zinc-500 hover:text-zinc-900 dark:hover:text-white cursor-pointer">
            <Plus class="w-4 h-4" />
          </button>
        </div>

        <div class="space-y-1">
          <button
            v-for="group in filteredGroups"
            :key="group.id"
            @click="selectGroup(group.id)"
            :class="`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-300 group cursor-pointer gap-2 ${selectedGroupId === group.id ? 'bg-teal-600 text-white shadow-lg shadow-teal-600/20' : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'}`"
          >
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <div :class="`w-2 h-2 rounded-full transition-transform group-hover:scale-125 shrink-0 ${
                group.type === 'personal' ? 'bg-blue-400' :
                group.type === 'household' ? 'bg-emerald-400' :
                group.type === 'trip' ? 'bg-orange-400' :
                group.type === 'employment' ? 'bg-emerald-500' :
                group.type === 'freelance' ? 'bg-cyan-400' :
                group.type === 'business' ? 'bg-purple-400' :
                group.type === 'investment' ? 'bg-amber-400' :
                'bg-indigo-400'
              }`" />
              <span class="truncate text-sm font-semibold text-ellipsis overflow-hidden whitespace-nowrap block flex-1 text-left">{{ group.name }}</span>
            </div>
            <ChevronRight v-if="selectedGroupId === group.id" class="w-4 h-4 opacity-70 shrink-0" />
          </button>
          <div v-if="filteredGroups.length === 0" class="px-4 py-8 text-center">
            <p class="text-xs text-zinc-405 dark:text-zinc-600 italic">
              {{ activeService === 'savings' ? 'No savings groups yet' : activeService === 'income' ? 'No income groups yet' : activeService === 'accounts' ? 'No account groups yet' : activeService === 'loans_debts' ? 'No loan trackers yet' : activeService === 'mortgages' ? 'No assets track yet' : activeService === 'rent' ? 'No leases yet' : activeService === 'document_vault' ? 'No cabinets yet' : 'No budgets yet' }}
            </p>
          </div>
        </div>
      </div>

      <!-- Sidebar footer -->
      <div class="p-6 mt-auto relative z-10 shrink-0">
        <div class="p-4 bg-zinc-50 dark:bg-white/5 rounded-2xl border border-zinc-200 dark:border-white/10 mb-4 backdrop-blur-md">
          <div class="flex items-center gap-3">
            <img :src="user.photoURL || `https://ui-avatars.com/api/?name=${user.displayName}&background=random`" alt="" class="w-10 h-10 rounded-xl shadow-sm border border-zinc-200 dark:border-white/10" />
            <div class="flex-1 min-w-0">
              <p class="text-sm font-bold text-zinc-900 dark:text-white truncate">{{ user.displayName }}</p>
              <p class="text-[10px] text-zinc-500 truncate font-mono">{{ user.email }}</p>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <div class="flex-1 relative">
            <div class="absolute left-3.5 top-1/2 -translate-y-1/2 z-10">
              <Coins class="w-4 h-4 text-teal-600 dark:text-teal-400" />
            </div>
            <select 
              :value="user.defaultCurrency" 
              @change="e => updateDefaultCurrency((e.target as HTMLSelectElement).value)"
              class="w-full pl-10 pr-3 py-2.5 bg-zinc-50 dark:bg-white/5 border border-zinc-200 dark:border-white/10 rounded-xl text-zinc-700 dark:text-zinc-300 font-bold text-xs cursor-pointer focus:outline-none focus:ring-2 focus:ring-teal-500 appearance-none"
            >
              <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">
                {{ c.code }} ({{ c.symbol }})
              </option>
            </select>
          </div>
          <button @click="isCategorySettingsOpen = true" class="p-3 rounded-xl text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white transition-all duration-300 cursor-pointer" title="Category Settings">
            <Settings class="w-5 h-5 text-[#005a5b] dark:text-teal-400" />
          </button>
          <button @click="toggleTheme" class="p-3 rounded-xl text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white transition-all duration-300 cursor-pointer" :title="theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'">
            <Sun v-if="theme === 'dark'" class="w-5 h-5" />
            <Moon v-else class="w-5 h-5" />
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Content Panel -->
    <main class="flex-1 overflow-y-auto relative h-full">
      <!-- Mobile Header -->
      <div class="lg:hidden flex items-center justify-between p-4 bg-zinc-950 border-b border-white/5 sticky top-0 z-30">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 bg-gradient-to-br from-teal-500 to-emerald-500 rounded-lg flex items-center justify-center">
            <Wallet class="w-5 h-5 text-white" />
          </div>
          <span class="font-bold text-white font-display">Budgeted</span>
        </div>
        <button @click="isSidebarOpen = true" class="p-2 text-zinc-400 hover:text-white cursor-pointer">
          <Menu class="w-6 h-6" />
        </button>
      </div>

      <!-- Service View Selector -->
      <transition name="fade" mode="out-in">
        <div v-if="!selectedGroupId" :key="activeService" class="p-10 max-w-7xl mx-auto">
          <BudgetExpenses 
            v-if="activeService === 'budget'"
            :user="user" 
            :groups="filteredGroups" 
            @selectGroup="selectGroup"
          />
          <SavingGoalsHub
            v-else-if="activeService === 'savings'"
            :user="user" 
            :groups="filteredGroups" 
            @selectGroup="selectGroup"
          />
          <IncomeHub
            v-else-if="activeService === 'income'"
            :user="user" 
            :groups="filteredGroups" 
            @selectGroup="selectGroup"
          />
          <AccountsHub
            v-else-if="activeService === 'accounts'"
            :user="user" 
            :groups="filteredGroups" 
            @selectGroup="selectGroup"
          />
          <LoansHub
            v-else-if="activeService === 'loans_debts'"
            :user="user" 
            :groups="filteredGroups" 
            @selectGroup="selectGroup"
          />
          <MortgagesHub
            v-else-if="activeService === 'mortgages'"
            :user="user" 
            :groups="filteredGroups" 
            @selectGroup="selectGroup"
          />
          <RentHub
            v-else-if="activeService === 'rent'"
            :user="user" 
            :groups="filteredGroups" 
            @selectGroup="selectGroup"
          />
          <DocumentVaultHub
            v-else-if="activeService === 'document_vault'"
            :user="user" 
            :groups="filteredGroups" 
            @selectGroup="selectGroup"
          />
          <DBInspector
            v-else-if="activeService === 'db-inspector'"
          />
        </div>
        <div v-else :key="selectedGroupId + '-' + activeService" class="p-10 max-w-7xl mx-auto">
          <GroupView 
            v-if="activeService === 'budget'"
            :groupId="selectedGroupId" 
            :user="user" 
            @back="selectedGroupId = null"
          />
          <GroupSavingGoalsView
            v-else-if="activeService === 'savings'"
            :groupId="selectedGroupId" 
            :user="user" 
            @back="selectedGroupId = null"
          />
          <GroupIncomeView
            v-else-if="activeService === 'income'"
            :groupId="selectedGroupId" 
            :user="user" 
            @back="selectedGroupId = null"
          />
          <GroupAccountsView
            v-else-if="activeService === 'accounts'"
            :groupId="selectedGroupId" 
            :user="user" 
            @back="selectedGroupId = null"
          />
          <GroupLoansView
            v-else-if="activeService === 'loans_debts'"
            :groupId="selectedGroupId" 
            :user="user" 
            @back="selectedGroupId = null"
          />
          <GroupMortgagesView
            v-else-if="activeService === 'mortgages'"
            :groupId="selectedGroupId" 
            :user="user" 
            @back="selectedGroupId = null"
          />
          <GroupRentView
            v-else-if="activeService === 'rent'"
            :groupId="selectedGroupId" 
            :user="user" 
            @back="selectedGroupId = null"
          />
          <GroupDocumentVaultView
            v-else-if="activeService === 'document_vault'"
            :groupId="selectedGroupId" 
            :user="user" 
            @back="selectedGroupId = null"
          />
        </div>
      </transition>
    </main>

    <!-- Modals & Overlay Popups -->
    <CreateGroupModal 
      :isOpen="isCreateModalOpen" 
      @close="isCreateModalOpen = false" 
      :user="user"
      :active-service="activeService"
    />

    <CategorySettingsModal
      :isOpen="isCategorySettingsOpen"
      :userId="user?.uid"
      @close="isCategorySettingsOpen = false"
    />

    <!-- Demo Data Reset Popup -->
    <transition name="fade">
      <div v-if="dataDeletedPopup" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="dataDeletedPopup = false" class="absolute inset-0 bg-zinc-900/40 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-[40px] shadow-2xl p-10 text-center z-10">
          <div class="w-20 h-20 bg-orange-50 dark:bg-orange-500/10 rounded-3xl flex items-center justify-center mx-auto mb-8 text-orange-600 dark:text-orange-400 border border-orange-100 dark:border-orange-500/20">
            <Settings class="w-10 h-10 animate-spin-slow" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-4 font-display">Demo Data Reset</h3>
          <p class="text-zinc-500 dark:text-zinc-400 mb-10 leading-relaxed text-sm">
            Your data has been deleted because 24 hours have passed since you first signed in. 
            This is a demo application. If you want your data to persist, please click the <span class="font-bold text-zinc-900 dark:text-white">Remix</span> button to create your own version of the app!
          </p>
          <button @click="dataDeletedPopup = false" class="w-full py-4 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-2xl font-bold hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-all shadow-lg active:scale-95 cursor-pointer">
            Got it
          </button>
        </div>
      </div>
    </transition>

    <!-- Welcome Popup -->
    <transition name="fade">
      <div v-if="showWelcomePopup" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="handleWelcomeDone" class="absolute inset-0 bg-zinc-900/40 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-[40px] shadow-2xl p-10 text-center z-10 animate-in">
          <div class="w-20 h-20 bg-indigo-50 dark:bg-indigo-500/10 rounded-3xl flex items-center justify-center mx-auto mb-8 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-500/20">
            <LayoutDashboard class="w-10 h-10" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-4 font-display">Welcome to the Demo!</h3>
          <p class="text-zinc-500 dark:text-zinc-400 mb-10 leading-relaxed text-sm">
            This is a demo application. To keep the demo fresh, <span class="font-bold text-zinc-900 dark:text-white">all data is automatically deleted every 24 hours</span>.
            <br /><br />
            If you want to create your own permanent version, click the <span class="font-bold text-zinc-900 dark:text-white">Remix</span> button in the top right!
          </p>
          <button @click="handleWelcomeDone" class="w-full py-4 bg-indigo-600 text-white rounded-2xl font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-500/20 active:scale-95 cursor-pointer">
            Got it, let's go!
          </button>
        </div>
      </div>
    </transition>

  </div>
</template>

<style>
/* CSS Transitions for fade */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1), transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.2);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.4);
}
</style>
