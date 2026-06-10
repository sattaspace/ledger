<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Database, Search, Play, RefreshCw, AlertCircle, DatabaseZap } from 'lucide-vue-next';

const selectedTable = ref<string>('expenses');
const searchWord = ref<string>('');
const tablesData = ref<Record<string, any[]>>({});
const sqlQuery = ref<string>('SELECT * FROM expenses LIMIT 10;');
const sqlResults = ref<{ columns: string[]; rows: any[] } | null>(null);
const sqlError = ref<string | null>(null);
const loading = ref<boolean>(true);
const queryTimeMs = ref<number | null>(null);

const availableTables = ['users', 'groups', 'group_members', 'expenses', 'saving_goals', 'deposits'];

const fetchDump = async () => {
  loading.value = true;
  try {
    const res = await fetch('/api/db/dump-tables');
    if (!res.ok) throw new Error(await res.text());
    tablesData.value = await res.json();
  } catch (err: any) {
    console.error("Failed to load db dump:", err);
  } finally {
    loading.value = false;
  }
};

const executeSQL = async () => {
  if (!sqlQuery.value.trim()) return;
  sqlError.value = null;
  sqlResults.value = null;
  const start = performance.now();
  try {
    const res = await fetch('/api/db/execute-sql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sql: sqlQuery.value })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Query execution failed.");
    }
    sqlResults.value = data;
    queryTimeMs.value = Math.round(performance.now() - start);
  } catch (err: any) {
    sqlError.value = err.message || "SQL Error";
  }
};

const setSqlTemplate = (tableName: string) => {
  sqlQuery.value = `SELECT * FROM ${tableName} LIMIT 10;`;
  executeSQL();
};

onMounted(() => {
  fetchDump();
  executeSQL();
});
</script>

<template>
  <div class="space-y-8 font-sans">
    
    <!-- Header Hero Banner -->
    <div class="relative bg-zinc-900 text-white rounded-3xl p-8 overflow-hidden shadow-xl border border-zinc-800">
      <div class="absolute inset-0 bg-gradient-to-r from-teal-500/20 to-emerald-500/10 pointer-events-none" />
      <div class="absolute right-0 bottom-0 translate-x-12 translate-y-12 opacity-10 blur-xl">
        <DatabaseZap class="w-96 h-96 text-teal-400" />
      </div>

      <div class="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div class="flex items-center gap-3 mb-2">
            <span class="px-3 py-1 bg-teal-500/20 text-teal-300 font-mono text-xs font-semibold rounded-full border border-teal-500/30">
              Active Environment
            </span>
            <div class="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              SQLite3 Live Connection
            </div>
          </div>
          <h1 class="text-3xl font-extrabold tracking-tight font-display mb-1.5">
            Database Entry Inspector
          </h1>
          <p class="text-zinc-400 max-w-xl text-sm leading-relaxed">
            Verify real-time SQL execution and data persistence directly inside the sandboxed <code>data.db</code>. Perform live searches or write custom queries.
          </p>
        </div>

        <div class="flex items-center gap-3 shrink-0">
          <button 
            @click="fetchDump" 
            class="flex items-center gap-2 px-5 py-3 bg-zinc-800 hover:bg-zinc-700 active:scale-95 text-white font-bold text-sm rounded-xl transition-all border border-zinc-700 cursor-pointer"
          >
            <RefreshCw class="w-4 h-4" :class="{ 'animate-spin': loading }" />
            Sync DB State
          </button>
        </div>
      </div>
    </div>

    <!-- Live Table Viewer and SQL Runner Bento Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      
      <!-- Left side: Table browser -->
      <div class="lg:col-span-2 space-y-8">
        <div class="bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-3xl shadow-sm overflow-hidden flex flex-col">
          
          <!-- Table controls -->
          <div class="p-6 border-b border-zinc-200 dark:border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <Database class="w-5 h-5 text-teal-500" />
              <select 
                v-model="selectedTable"
                class="bg-zinc-50 dark:bg-white/5 border border-zinc-200 dark:border-white/10 rounded-xl px-3 py-2 text-sm font-bold text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-teal-500/40 cursor-pointer"
              >
                <option v-for="t in availableTables" :key="t" :value="t">
                  Table: {{ t }}
                </option>
              </select>
            </div>

            <!-- Search -->
            <div class="relative max-w-xs w-full">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              <input 
                v-model="searchWord"
                type="text"
                placeholder="Search raw rows..."
                class="w-full pl-9 pr-3 py-2 bg-zinc-50 dark:bg-white/5 border border-zinc-200 dark:border-white/10 rounded-xl text-xs text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-teal-500/40 focus:bg-white dark:focus:bg-zinc-900"
              />
            </div>
          </div>

          <!-- Table Container -->
          <div class="flex-1 overflow-x-auto min-h-[400px] max-h-[550px] custom-scrollbar">
            <div v-if="loading" class="flex flex-col items-center justify-center p-20 text-center">
              <div class="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin mb-4" />
              <p class="text-zinc-500 dark:text-zinc-400 text-sm">Mapping tables...</p>
            </div>
            
            <div v-else-if="!tablesData[selectedTable] || tablesData[selectedTable].length === 0" class="flex flex-col items-center justify-center p-20 text-center">
              <div class="w-12 h-12 bg-zinc-100 dark:bg-white/5 rounded-2xl flex items-center justify-center mb-4 text-zinc-400">
                <AlertCircle class="w-6 h-6" />
              </div>
              <p class="text-zinc-500 dark:text-zinc-400 font-bold mb-1">Table Empty</p>
              <p class="text-zinc-400 text-xs">No records exist in table <code>{{ selectedTable }}</code> yet.</p>
            </div>

            <!-- Standard Data Grid -->
            <table v-else class="w-full text-left border-collapse text-xs">
              <thead>
                <tr class="bg-zinc-50 dark:bg-white/5 border-b border-zinc-200 dark:border-white/5 text-zinc-400 font-bold uppercase tracking-wider font-mono">
                  <th v-for="key in Object.keys(tablesData[selectedTable][0])" :key="key" class="p-4 whitespace-nowrap">
                    {{ key }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-zinc-200 dark:divide-white/5">
                <tr 
                  v-for="(row, idx) in tablesData[selectedTable].filter(r => JSON.stringify(r).toLowerCase().includes(searchWord.toLowerCase()))" 
                  :key="idx"
                  class="hover:bg-zinc-55/70 dark:hover:bg-white/[0.01] transition-colors"
                >
                  <td v-for="(val, key) in row" :key="key" class="p-4 whitespace-nowrap font-mono max-w-sm truncate text-zinc-700 dark:text-zinc-300">
                    <span v-if="val === null || val === undefined" class="text-zinc-400 italic font-sans">NULL</span>
                    <span v-else-if="typeof val === 'object'" class="text-teal-600 dark:text-teal-400" :title="JSON.stringify(val)">
                      {{ JSON.stringify(val) }}
                    </span>
                    <span v-else>{{ val }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Footer summary -->
          <div class="bg-zinc-50 dark:bg-white/5 border-t border-zinc-200 dark:border-white/5 p-4 flex justify-between items-center text-xs text-zinc-500">
            <span>Showing table row structures instantly to frontend</span>
            <span>Total rows: {{ tablesData[selectedTable]?.length || 0 }}</span>
          </div>

        </div>
      </div>

      <!-- Right side: Custom Live SQL Playground -->
      <div class="space-y-8">
        <div class="bg-zinc-950 text-zinc-100 rounded-3xl p-6 border border-zinc-800 shadow-xl flex flex-col justify-between min-h-[480px]">
          <div>
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-teal-400" />
                <h3 class="font-bold text-sm tracking-wide text-white uppercase font-display">SQL Console Playground</h3>
              </div>
              <span class="text-[10px] bg-zinc-800 text-zinc-400 py-1 px-2.5 rounded-full border border-zinc-700 font-mono uppercase">Read Only</span>
            </div>

            <p class="text-zinc-400 text-xs leading-relaxed mb-4">
              Test queries manually! Select active objects directly from table references.
            </p>

            <div class="flex flex-wrap gap-2 mb-4">
              <span class="text-zinc-500 text-[10px] font-bold py-1">Quick Tables:</span>
              <button 
                v-for="t in availableTables" 
                :key="t"
                @click="setSqlTemplate(t)"
                class="px-2 py-0.5 bg-zinc-900 border border-zinc-800 hover:border-teal-500 rounded-md text-[10px] text-zinc-300 transition-colors font-mono cursor-pointer"
              >
                {{ t }}
              </button>
            </div>

            <!-- SQL Textarea Box -->
            <div class="relative bg-zinc-900 border border-zinc-800 rounded-xl p-3 focus-within:ring-2 focus-within:ring-teal-500/40 mb-4 font-mono">
              <textarea 
                v-model="sqlQuery"
                rows="4"
                placeholder="SELECT * FROM expenses LIMIT 10;"
                class="w-full bg-transparent border-0 outline-none resize-none text-xs text-teal-400 focus:ring-0 leading-relaxed font-mono"
              />
            </div>

            <button 
              @click="executeSQL"
              class="w-full flex items-center justify-center gap-2 py-3 bg-teal-500 hover:bg-teal-600 active:scale-95 text-zinc-950 font-bold text-xs rounded-xl shadow-lg shadow-teal-500/10 cursor-pointer transition-all"
            >
              <Play class="w-3.5 h-3.5 fill-current" />
              Execute SELECT Query
            </button>
          </div>

          <!-- Error Feedback -->
          <div v-if="sqlError" class="mt-4 p-3.5 bg-red-950/40 border border-red-900/30 rounded-xl text-xs text-red-400 flex items-start gap-2.5">
            <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
            <span class="font-mono">{{ sqlError }}</span>
          </div>

          <!-- SQL Results Output -->
          <div v-if="sqlResults" class="mt-4 p-4 bg-zinc-900/60 rounded-xl border border-zinc-800 max-h-[220px] overflow-y-auto custom-scrollbar font-mono">
            <div class="flex items-center justify-between text-[10px] text-zinc-500 border-b border-zinc-800 pb-2 mb-2">
              <span>Rows fetched: {{ sqlResults.rows.length }}</span>
              <span>Time: {{ queryTimeMs }}ms</span>
            </div>

            <div v-if="sqlResults.rows.length === 0" class="text-center text-xs text-zinc-500 p-4 italic">
              Empty set returned.
            </div>

            <div v-else class="overflow-x-auto">
              <table class="w-full text-left text-[10px] text-zinc-300 border-collapse">
                <thead>
                  <tr class="text-zinc-500 font-bold uppercase tracking-wider text-[9px] border-b border-zinc-800 pb-1">
                    <th v-for="col in sqlResults.columns" :key="col" class="pr-3 pb-1 font-mono">{{ col }}</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-zinc-800/50">
                  <tr v-for="(row, i) in sqlResults.rows" :key="i" class="hover:bg-zinc-800/10">
                    <td v-for="col in sqlResults.columns" :key="col" class="pr-3 py-1.5 font-mono truncate max-w-[150px]">
                      <span v-if="row[col] === null || row[col] === undefined" class="text-zinc-600 italic">null</span>
                      <span v-else-if="typeof row[col] === 'object'">{{ JSON.stringify(row[col]) }}</span>
                      <span v-else>{{ row[col] }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          
        </div>
      </div>

    </div>

  </div>
</template>
