<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { 
  FileText, 
  UserPlus, 
  TrendingUp, 
  Sparkles, 
  CheckCircle,
  Truck, 
  Coins, 
  User, 
  AlertTriangle,
  BrainCircuit,
  Phone,
  BarChart2,
  Lock,
  ChevronDown,
  ChevronUp,
  Search,
  Calendar,
  X,
  Plus,
  Printer,
  Download,
  Edit,
  Trash2,
  Users,
  Mail
} from 'lucide-vue-next';
import type { DSR, Product, SaleRecord } from '../types';
import { BaseChart, ChartCard } from './charts';
import type { ChartData, ChartOptions } from 'chart.js';
import type { SummaryData } from '../services/api/reports.service';
import AddRepModal from './AddRepModal.vue';
import InvitationList from './InvitationList.vue';
import { useAccess } from '../composables/useAccess';

const { hasAccess } = useAccess();
// DSRs in portal mode can only see the Invitations panel if they have the
// manage_dsrs permission. Dealers always have it (set in handleDsrEnterPortal
// for DSRs, and dealers bypass via the navItems filter in App.vue).
const canManageDsrs = hasAccess('manage_dsrs');



const props = withDefaults(defineProps<{
  summary: SummaryData | null;
  dsrs: DSR[];
  sales: SaleRecord[];
  products: Product[];
  aiResponse?: string;
  isAiLoading?: boolean;
  formatCurrency?: (amt: number) => string;
  onEditDsr?: (dsrId: string, data: any) => Promise<any>;
  onDeleteDsr?: (dsrId: string) => Promise<void>;
}>(), {
  aiResponse: '',
  isAiLoading: false,
});

const emit = defineEmits<{
  (e: 'askGemini'): void;
  (e: 'refreshData'): void;
}>();

// Add Rep modal state (unified invite + direct)
const showAddRepModal = ref(false);

// DSR Edit/Delete state
const showEditDsrForm = ref(false);
const editingDsr = ref<DSR | null>(null);
const editDsrName = ref('');
const editDsrPhone = ref('');
const editDsrRole = ref<'DSR' | 'Order Collector'>('DSR');
const editDsrParentId = ref('');
const editDsrError = ref('');
const editDsrSuccess = ref('');
const editDsrSubmitting = ref(false);
const deleteConfirmDsr = ref<DSR | null>(null);

// Invitation list toggle
const showInvitationList = ref(false);

// Window helpers for template access
const printPage = () => window.print();

const printData = ref<{
  type: 'EXECUTIVE' | 'DSR_STATEMENT' | 'VEHICLE_TRIP' | 'CUSTOMER_DUE';
  period: string;
  payload: any;
} | null>(null);

const selectedPeriod = ref<'ALL' | 'TODAY' | 'WEEK' | 'MONTH' | 'QUARTER' | 'YEAR'>('ALL');
const expandedVehicle = ref<string | null>(null);
const expandedRep = ref<string | null>(null);
const vehicleQuery = ref('');
const repSearchQuery = ref('');

const repPage = ref(1);
const vehiclePage = ref(1);
const repRecordPage = ref(1);
const vRecordPage = ref(1);

const repsPerPage = 5;
const vehiclesPerPage = 6;
const subSalesPerPage = 5;

// Reset inner sub-pagination counters on collapse/expand triggers
watch(expandedRep, () => { repRecordPage.value = 1; });
watch(expandedVehicle, () => { vRecordPage.value = 1; });

// Reset outer pages when queries / period indices shift
watch([repSearchQuery, selectedPeriod], () => { repPage.value = 1; });
watch([vehicleQuery, selectedPeriod], () => { vehiclePage.value = 1; });

const formatCurrency = computed(() => {
  return props.formatCurrency || ((amt: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amt);
  });
});

const isWithinPeriod = (dateStr: string, periodStr: string) => {
  if (periodStr === 'ALL') return true;
  const d = new Date(dateStr);
  const now = new Date();
  
  const year = now.getFullYear();
  const month = now.getMonth();
  const day = now.getDate();
  
  if (periodStr === 'TODAY') {
    return d.getFullYear() === year && d.getMonth() === month && d.getDate() === day;
  }
  if (periodStr === 'WEEK') {
    const diffTime = Math.abs(now.getTime() - d.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays <= 7;
  }
  if (periodStr === 'MONTH') {
    return d.getFullYear() === year && d.getMonth() === month;
  }
  if (periodStr === 'QUARTER') {
    const curQuarter = Math.floor(month / 3);
    const dQuarter = Math.floor(d.getMonth() / 3);
    return d.getFullYear() === year && curQuarter === dQuarter;
  }
  if (periodStr === 'YEAR') {
    return d.getFullYear() === year;
  }
  return true;
};

// Period-filtered sales records
const periodFilteredSales = computed(() => {
  // Exclude voided sales from ALL period calculations
  return (props.sales || []).filter(s => !s.isVoided && isWithinPeriod(s.date, selectedPeriod.value));
});

// Period totals sum
const periodTotals = computed(() => {
  let revenueSum = 0;
  let cogsSum = 0;
  let creditPendingAmt = 0;
  let writtenOffAmt = 0;
  
  periodFilteredSales.value.forEach(sale => {
    if (sale.isClosedWithDue) {
      // Written-off: report only the UNCOLLECTED portion (not full total)
      // to avoid double-counting partial payments already collected
      writtenOffAmt += Math.max(0, (sale.totalAmount || 0) - (sale.amountPaid || 0));
      return; // Skip adding to revenue
    }
    
    // Use netAmount (after returns) for revenue
    const netAmt = sale.netAmount || (sale.totalAmount - (sale.returnTotalAmount || 0));
    revenueSum += netAmt;
    
    const prod = (props.products || []).find(p => p.id === sale.productId);
    const costPerUnit = prod ? prod.unitPrice : 0;
    cogsSum += (costPerUnit * sale.quantity);

    if (sale.paymentType === 'Credit' && !sale.isClosedWithDue) {
      const due = sale.balanceDue || (netAmt - sale.amountPaid);
      creditPendingAmt += Math.max(0, due);
    }
  });
  
  return {
    revenue: revenueSum,
    cogs: cogsSum,
    grossProfit: revenueSum - cogsSum,
    pending: creditPendingAmt,
    writtenOff: writtenOffAmt
  };
});

// Calculate representative stats dynamically
const periodDsrPerformance = computed(() => {
  return (props.dsrs || []).map(dsr => {
    const dsrSales = periodFilteredSales.value.filter(s => 
      s.dsrId === dsr.id || (s.dsrName && s.dsrName.toLowerCase().trim() === dsr.name.toLowerCase().trim())
    );
    const salesTotal = dsrSales.reduce((acc, curr) => {
      if (curr.isClosedWithDue) return acc;
      const netAmt = curr.netAmount || (curr.totalAmount - (curr.returnTotalAmount || 0));
      return acc + netAmt;
    }, 0);
    const collected = dsrSales.reduce((acc, curr) => acc + (curr.isClosedWithDue ? 0 : (curr.amountPaid || 0)), 0);
    const pending = dsrSales.reduce((acc, curr) => {
      if (curr.isClosedWithDue || curr.paymentType !== 'Credit') return acc;
      const netAmt = curr.netAmount || (curr.totalAmount - (curr.returnTotalAmount || 0));
      const dueAmt = curr.balanceDue || (netAmt - curr.amountPaid);
      return acc + Math.max(0, dueAmt);
    }, 0);
    return {
      id: dsr.id,
      name: dsr.name,
      role: dsr.role || 'DSR',
      parentDsrId: dsr.parentDsrId,
      parentDsrName: dsr.parentDsrName,
      totalSales: salesTotal,
      collected,
      pending,
      count: dsrSales.length,
    };
  });
});

const filteredDsrPerformance = computed(() => {
  const query = repSearchQuery.value.toLowerCase().trim();
  return periodDsrPerformance.value.filter(rep => 
    rep.name.toLowerCase().includes(query)
  );
});

const currentRepsList = computed(() => {
  const start = (repPage.value - 1) * repsPerPage;
  return filteredDsrPerformance.value.slice(start, start + repsPerPage);
});

const totalRepPages = computed(() => Math.ceil(filteredDsrPerformance.value.length / repsPerPage));

// Calculate logistics vehicles performance dynamically
const vehiclePerformance = computed(() => {
  const vehicles: { [vehicleNumber: string]: {
    vehicleNumber: string;
    totalSales: number;
    collected: number;
    pending: number;
    writtenOff: number;
    count: number;
    reps: string[];
    records: SaleRecord[];
  } } = {};

  periodFilteredSales.value.forEach(s => {
    if (s.isVehicle && s.vehicleNumber) {
      const vNum = s.vehicleNumber.toUpperCase().trim();
      if (!vehicles[vNum]) {
        vehicles[vNum] = {
          vehicleNumber: vNum,
          totalSales: 0,
          collected: 0,
          pending: 0,
          writtenOff: 0,
          count: 0,
          reps: [],
          records: []
        };
      }

      const v = vehicles[vNum];
      const netAmt = s.netAmount || (s.totalAmount - (s.returnTotalAmount || 0));
      const dueAmt = s.balanceDue || (netAmt - s.amountPaid);
      
      if (s.isClosedWithDue) {
        // Written-off: only count uncollected portion, don't inflate totals
        v.writtenOff += Math.max(0, dueAmt);
        v.collected += s.amountPaid || 0;
      } else {
        v.totalSales += netAmt;
        v.collected += s.amountPaid || 0;
        if (dueAmt > 0) {
          v.pending += dueAmt;
        }
      }
      v.count += 1;

      if (s.dsrName && !v.reps.includes(s.dsrName)) {
        v.reps.push(s.dsrName);
      }

      v.records.push(s);
    }
  });

  return Object.values(vehicles);
});

const filteredVehicles = computed(() => {
  const query = vehicleQuery.value.toLowerCase().trim();
  return vehiclePerformance.value.filter(v => {
    return v.vehicleNumber.toLowerCase().includes(query) || v.reps.some(r => r.toLowerCase().includes(query));
  });
});

const currentVehiclesList = computed(() => {
  const start = (vehiclePage.value - 1) * vehiclesPerPage;
  return filteredVehicles.value.slice(start, start + vehiclesPerPage);
});

const totalVehiclePages = computed(() => Math.ceil(filteredVehicles.value.length / vehiclesPerPage));

// ─── Customer-wise Due Report ──────────────────────────────────────────
const customerQuery = ref('');
const customerPage = ref(1);
const customersPerPage = 8;
const expandedCustomer = ref<string | null>(null);
const custRecordPage = ref(1);

watch(customerQuery, () => { customerPage.value = 1; });
watch(expandedCustomer, () => { custRecordPage.value = 1; });

const customerDueData = computed(() => {
  const customers: { [key: string]: {
    name: string;
    phone: string;
    totalBilled: number;
    totalPaid: number;
    pending: number;
    writtenOff: number;
    invoiceCount: number;
    records: SaleRecord[];
  } } = {};

  periodFilteredSales.value.forEach(s => {
    const key = s.customerName.toLowerCase().trim();
    if (!key) return;
    if (!customers[key]) {
      customers[key] = {
        name: s.customerName,
        phone: s.customerPhone || '',
        totalBilled: 0,
        totalPaid: 0,
        pending: 0,
        writtenOff: 0,
        invoiceCount: 0,
        records: [],
      };
    }
    const c = customers[key];
    const netAmt = s.netAmount || (s.totalAmount - (s.returnTotalAmount || 0));
    const dueAmt = s.balanceDue || (netAmt - s.amountPaid);
    
    c.totalBilled += netAmt;
    c.totalPaid += s.amountPaid || 0;
    c.invoiceCount += 1;
    if (s.customerPhone && !c.phone) c.phone = s.customerPhone;

    if (s.isClosedWithDue) {
      c.writtenOff += Math.max(0, dueAmt);
    } else {
      if (dueAmt > 0) {
        c.pending += dueAmt;
      }
    }

    c.records.push(s);
  });

  // Sort by pending descending (biggest dues first)
  return Object.values(customers).sort((a, b) => b.pending - a.pending);
});

const filteredCustomers = computed(() => {
  const q = customerQuery.value.toLowerCase().trim();
  if (!q) return customerDueData.value;
  return customerDueData.value.filter(c =>
    c.name.toLowerCase().includes(q) || c.phone.toLowerCase().includes(q)
  );
});

const currentCustomersList = computed(() => {
  const start = (customerPage.value - 1) * customersPerPage;
  return filteredCustomers.value.slice(start, start + customersPerPage);
});

const totalCustomerPages = computed(() => Math.ceil(filteredCustomers.value.length / customersPerPage));

// ─── DSR Edit/Delete Handlers ──────────────────────────────────────────
const handleStartEditDsr = (dsr: DSR) => {
  editingDsr.value = dsr;
  editDsrName.value = dsr.name;
  editDsrPhone.value = dsr.phone || '';
  editDsrRole.value = dsr.role || 'DSR';
  editDsrParentId.value = dsr.parentDsrId || '';
  showEditDsrForm.value = true;
  editDsrError.value = '';
  editDsrSuccess.value = '';
};

const handleEditDsrSubmit = async () => {
  editDsrError.value = '';
  editDsrSuccess.value = '';
  if (!editingDsr.value) return;
  if (!editDsrName.value) {
    editDsrError.value = 'Name is required!';
    return;
  }
  editDsrSubmitting.value = true;
  try {
    await props.onEditDsr!(editingDsr.value.id, {
      name: editDsrName.value,
      phone: editDsrPhone.value,
      role: editDsrRole.value,
      parentDsrId: editDsrRole.value === 'Order Collector' ? editDsrParentId.value : null,
    });
    showEditDsrForm.value = false;
    editingDsr.value = null;
    emit('refreshData');
  } catch (err: any) {
    editDsrError.value = err.message || 'Error updating representative.';
  } finally {
    editDsrSubmitting.value = false;
  }
};

const handleDeleteDsr = (dsr: DSR) => {
  deleteConfirmDsr.value = dsr;
};

const handleConfirmDeleteDsr = async () => {
  if (!deleteConfirmDsr.value) return;
  try {
    await props.onDeleteDsr!(deleteConfirmDsr.value.id);
    deleteConfirmDsr.value = null;
    emit('refreshData');
  } catch (err: any) {
    editDsrError.value = err.message || 'Error deleting representative.';
    deleteConfirmDsr.value = null;
  }
};

// CSV Export Utilities
const handleExportCSV = () => {
  if (!printData.value) return;
  let headers: string[] = [];
  let rows: any[] = [];
  let filename = `dms_report_${printData.value.type.toLowerCase()}_${selectedPeriod.value.toLowerCase()}.csv`;

  // Dealer header info for CSV
  const dealerInfo = props.summary?.dealer || null;

  if (printData.value.type === 'EXECUTIVE') {
    // Add dealer header rows at the top
    if (dealerInfo) {
      rows.push(['Business Name', dealerInfo.businessName || '']);
      rows.push(['Address', dealerInfo.address || '']);
      rows.push(['Phone', dealerInfo.phoneNumber || '']);
      rows.push(['GST Number', dealerInfo.gstNumber || '']);
      rows.push(['Email', dealerInfo.email || '']);
      rows.push([]);
    }
    headers = ['Metric/Item', 'Detail/Value', 'Summary Info'];
    rows.push(['Enterprise Name', dealerInfo?.businessName || props.summary?.dealer?.businessName || 'Dealer Enterprise', 'Authorized FMCG Wholesale']);
    rows.push(['Account Period', selectedPeriod.value, 'Date selection scope']);
    rows.push(['Period Revenue', formatCurrency.value(periodTotals.value.revenue), `${periodFilteredSales.value.length} bills total`]);
    rows.push(['Cost of Goods Sold', formatCurrency.value(periodTotals.value.cogs), 'FMCG unit prices sum']);
    rows.push(['Gross Profit Margin', formatCurrency.value(periodTotals.value.grossProfit), 'Spread before logistics']);
    rows.push(['Outstanding Credits', formatCurrency.value(periodTotals.value.pending), 'Active ledger dues']);
    rows.push([]);
    rows.push(['REPRESENTATIVES LEDGER SUMMARY']);
    rows.push(['Representative Name', 'Role', 'Total Sales Volume', 'Outstanding Pending']);
    filteredDsrPerformance.value.forEach(rep => {
      rows.push([rep.name, rep.role || 'DSR', formatCurrency.value(rep.totalSales), formatCurrency.value(rep.pending)]);
    });
  } else if (printData.value.type === 'DSR_STATEMENT') {
    const rep = printData.value.payload.rep;
    const rSales = printData.value.payload.sales;
    filename = `dms_dsr_statement_${rep.name.replace(/\s+/g, '_').toLowerCase()}.csv`;
    headers = ['Date', 'Invoice ID/Reference', 'Customer Store', 'Product Item', 'Qty', 'Selling Price', 'Invoiced Value', 'Collected Paid', 'Balance Out'];
    rSales.forEach((s: any) => {
      const balance = s.isClosedWithDue ? 0 : Math.max(0, s.totalAmount - s.amountPaid);
      rows.push([
        new Date(s.date).toLocaleDateString(),
        s.id || '--',
        s.customerName,
        s.productName,
        s.quantity,
        s.sellingPrice,
        s.totalAmount,
        s.amountPaid,
        s.isClosedWithDue ? 'WRITTEN_OFF' : balance
      ]);
    });
  } else if (printData.value.type === 'VEHICLE_TRIP') {
    const v = printData.value.payload.vehicle;
    filename = `dms_vehicle_trip_${v.vehicleNumber.toLowerCase()}.csv`;
    headers = ['Trip Date', 'Outlet Store', 'Contact Phone', 'Loaded Product Name', 'Quantity Dispatched', 'Invoiced Value', 'Paid On Route', 'Pending Deficit'];
    v.records.forEach((r: any) => {
      const balance = r.isClosedWithDue ? 0 : Math.max(0, r.totalAmount - r.amountPaid);
      rows.push([
        new Date(r.date).toLocaleDateString(),
        r.customerName,
        r.customerPhone || 'N/A',
        r.productName,
        r.quantity,
        r.totalAmount,
        r.amountPaid,
        r.isClosedWithDue ? 'WRITTEN_OFF' : balance
      ]);
    });
  } else if (printData.value.type === 'CUSTOMER_DUE') {
    filename = `dms_customer_due_statement_${selectedPeriod.value.toLowerCase()}.csv`;
    headers = ['Customer Name', 'Phone', 'Total Billed', 'Total Paid', 'Pending Due', 'Written Off', 'Invoice Count'];
    printData.value.payload.customers.forEach((c: any) => {
      rows.push([c.name, c.phone || 'N/A', c.totalBilled, c.totalPaid, c.pending, c.writtenOff || 0, c.invoiceCount]);
    });
  }

  const csvContent = [
    headers.join(','),
    ...rows.map(e => e.map((val: any) => {
      const str = String(val === undefined ? '' : val).replace(/"/g, '""');
      return str.includes(',') || str.includes('\n') ? `"${str}"` : str;
    }).join(','))
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// ========== CHART COMPUTED PROPERTIES ==========

// Financial Comparison Bar Chart Data
const financialComparisonData = computed(() => ({
  labels: ['Financial Breakdown'],
  datasets: [
    {
      label: 'Revenue',
      data: [periodTotals.value.revenue],
      backgroundColor: 'rgba(16, 185, 129, 0.75)',
      borderColor: 'rgb(16, 185, 129)',
      borderWidth: 2,
      borderRadius: 6,
    },
    {
      label: 'Cost of Goods',
      data: [periodTotals.value.cogs],
      backgroundColor: 'rgba(100, 116, 139, 0.75)',
      borderColor: 'rgb(100, 116, 139)',
      borderWidth: 2,
      borderRadius: 6,
    },
    {
      label: 'Gross Profit',
      data: [periodTotals.value.grossProfit],
      backgroundColor: 'rgba(20, 184, 166, 0.75)',
      borderColor: 'rgb(20, 184, 166)',
      borderWidth: 2,
      borderRadius: 6,
    },
    {
      label: 'Credit Pending',
      data: [periodTotals.value.pending],
      backgroundColor: 'rgba(244, 63, 94, 0.75)',
      borderColor: 'rgb(244, 63, 94)',
      borderWidth: 2,
      borderRadius: 6,
    },
    {
      label: 'Written Off',
      data: [periodTotals.value.writtenOff],
      backgroundColor: 'rgba(245, 158, 11, 0.75)',
      borderColor: 'rgb(245, 158, 11)',
      borderWidth: 2,
      borderRadius: 6,
    },
  ]
}));

const financialComparisonOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: {
        usePointStyle: true,
        pointStyle: 'rectRounded',
        padding: 16,
        font: { family: 'Inter', size: 11 },
      }
    },
    tooltip: {
      callbacks: {
        label: (ctx: any) => {
          return `${ctx.dataset.label}: ${formatCurrency.value(ctx.raw as number)}`;
        }
      }
    }
  },
  scales: {
    x: { grid: { display: false } },
    y: { 
      grid: { color: '#EAE4DC' },
      ticks: { 
        callback: (value: any) => {
          const val = value as number;
          if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
          if (val >= 1000) return `₹${(val / 1000).toFixed(1)}K`;
          return `₹${val}`;
        }
      }
    }
  }
}));

// DSR Performance Horizontal Bar Chart Data
const dsrBarData = computed(() => {
  const topReps = filteredDsrPerformance.value.slice(0, 8);
  return {
    labels: topReps.map(r => r.name),
    datasets: [
      {
        label: 'Collected',
        data: topReps.map(r => r.collected),
        backgroundColor: 'rgba(16, 185, 129, 0.75)',
        borderColor: 'rgb(16, 185, 129)',
        borderWidth: 1,
        borderRadius: 4,
      },
      {
        label: 'Pending',
        data: topReps.map(r => r.pending),
        backgroundColor: 'rgba(244, 63, 94, 0.75)',
        borderColor: 'rgb(244, 63, 94)',
        borderWidth: 1,
        borderRadius: 4,
      },
    ]
  };
});

const dsrBarOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y' as const,
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: {
        usePointStyle: true,
        pointStyle: 'rectRounded',
        padding: 16,
        font: { family: 'Inter', size: 11 },
      }
    },
    tooltip: {
      callbacks: {
        label: (ctx: any) => {
          return `${ctx.dataset.label}: ${formatCurrency.value(ctx.raw as number)}`;
        }
      }
    }
  },
  scales: {
    x: {
      grid: { color: '#EAE4DC' },
      ticks: {
        callback: (value: any) => {
          const val = value as number;
          if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
          if (val >= 1000) return `₹${(val / 1000).toFixed(1)}K`;
          return `₹${val}`;
        }
      }
    },
    y: {
      grid: { display: false },
      ticks: {
        font: { family: 'Inter', size: 11 },
      }
    }
  }
}));

// Payment Type Doughnut Chart Data
const paymentPieData = computed(() => {
  const cashCount = periodFilteredSales.value.filter(s => s.paymentType === 'Cash').length;
  const creditCount = periodFilteredSales.value.filter(s => s.paymentType === 'Credit').length;
  return {
    labels: ['Cash Sales', 'Credit Sales'],
    datasets: [{
      data: [cashCount, creditCount],
      backgroundColor: ['rgba(16, 185, 129, 0.8)', 'rgba(244, 63, 94, 0.8)'],
      borderColor: ['rgb(16, 185, 129)', 'rgb(244, 63, 94)'],
      borderWidth: 2,
      hoverOffset: 8,
    }]
  };
});

const paymentPieOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: {
        usePointStyle: true,
        pointStyle: 'circle',
        padding: 16,
        font: { family: 'Inter', size: 11 },
      }
    },
    tooltip: {
      callbacks: {
        label: (ctx: any) => {
          const total = (ctx.dataset.data as number[]).reduce((a: number, b: number) => a + b, 0);
          const pct = total > 0 ? ((ctx.raw as number) / total * 100).toFixed(1) : '0';
          return `${ctx.label}: ${ctx.raw} invoices (${pct}%)`;
        }
      }
    }
  }
}));

// Revenue Trend Line Chart (daily for selected period)
const revenueTrendData = computed(() => {
  const salesInPeriod = periodFilteredSales.value;
  
  // Group by date
  const dateMap: Record<string, number> = {};
  salesInPeriod.forEach(s => {
    const dateKey = new Date(s.date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
    dateMap[dateKey] = (dateMap[dateKey] || 0) + (s.totalAmount || 0);
  });
  
  // If no data or too few points, create last-7-days fallback
  if (Object.keys(dateMap).length < 2) {
    const labels: string[] = [];
    const values: number[] = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
      labels.push(key);
      values.push(dateMap[key] || 0);
    }
    return {
      labels,
      datasets: [{
        label: 'Revenue',
        data: values,
        borderColor: 'rgb(139, 92, 246)',
        backgroundColor: 'rgba(139, 92, 246, 0.08)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: 'rgb(139, 92, 246)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
      }]
    };
  }
  
  const labels = Object.keys(dateMap);
  const values = Object.values(dateMap);
  
  return {
    labels,
    datasets: [{
      label: 'Revenue',
      data: values,
      borderColor: 'rgb(139, 92, 246)',
      backgroundColor: 'rgba(139, 92, 246, 0.08)',
      fill: true,
      tension: 0.4,
      pointBackgroundColor: 'rgb(139, 92, 246)',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      pointRadius: 3,
      pointHoverRadius: 5,
    }]
  };
});

const revenueTrendOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx: any) => `Revenue: ${formatCurrency.value(ctx.raw as number)}`
      }
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#64748B', font: { family: 'Inter', size: 10 } }
    },
    y: {
      grid: { color: '#F1F5F9' },
      ticks: {
        color: '#94A3B8',
        font: { family: 'JetBrains Mono', size: 10 },
        callback: (value: any) => {
          const val = value as number;
          if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
          if (val >= 1000) return `₹${(val / 1000).toFixed(1)}K`;
          return `₹${val}`;
        }
      }
    }
  }
}));
</script>

<template>
  <div class="dashboard-layout font-sans text-left animate-fadeIn">

    <!-- ═══════════════════════════════════════════════════════════
         MIDDLE COLUMN — Operational Content
         ═══════════════════════════════════════════════════════════ -->
    <div class="dashboard-middle">

      <!-- HEADER -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 class="text-xl md:text-2xl font-bold text-slate-800 flex items-center gap-2">
            <BarChart2 class="h-6 w-6 text-violet-600" />
            Financial Reports
          </h2>
          <p class="text-sm text-slate-500 mt-1">Accounting metrics, rep performance, and AI insights</p>
        </div>

        <div class="flex flex-wrap gap-2">
          <!-- Unified Add Rep Button (only shown if user can manage DSRs) -->
          <button 
            v-if="canManageDsrs"
            id="btn-add-rep"
            @click="showAddRepModal = true"
            class="py-2.5 px-4 bg-gradient-to-r from-violet-600 to-purple-600 text-white rounded-lg flex items-center gap-2 hover:from-violet-700 hover:to-purple-700 transition cursor-pointer font-semibold text-sm shadow-sm"
          >
            <UserPlus class="h-4 w-4" />
            <span>Add Rep</span>
          </button>

          <!-- Toggle Invitation List (only shown if user can manage DSRs) -->
          <button 
            v-if="canManageDsrs && !showInvitationList"
            @click="showInvitationList = true"
            class="py-2.5 px-4 bg-white text-slate-600 border border-slate-200 rounded-lg flex items-center gap-2 hover:bg-slate-50 transition cursor-pointer font-semibold text-sm shadow-sm"
            title="View pending invitations"
          >
            <Mail class="h-4 w-4 text-slate-500" />
            <span>Invitations</span>
          </button>
          <button 
            v-else-if="canManageDsrs && showInvitationList"
            @click="showInvitationList = false"
            class="py-2.5 px-4 bg-violet-100 text-violet-700 border border-violet-200 rounded-lg flex items-center gap-2 hover:bg-violet-50 transition cursor-pointer font-semibold text-sm"
          >
            <X class="h-4 w-4" />
            <span>Hide</span>
          </button>

          <button 
            id="btn-print-executive-report"
            @click="printData = {
              type: 'EXECUTIVE',
              period: selectedPeriod,
              payload: {
                totals: periodTotals,
                reps: filteredDsrPerformance,
                vehicles: vehiclePerformance,
                customers: customerDueData,
                lowStock: products.filter(p => p.stock <= (p.minStockAlert || 10))
              }
            }"
            class="py-2.5 px-4 bg-violet-600 hover:bg-violet-700 text-white rounded-lg flex items-center gap-2 transition cursor-pointer font-semibold text-sm shadow-sm"
          >
            <Printer class="h-4 w-4" />
            <span>Print Statement</span>
          </button>
        </div>
      </div>

      <!-- PERIOD SELECTOR (Pill Buttons) -->
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <span class="text-sm font-semibold text-slate-600 flex items-center gap-2">
          <Calendar class="h-5 w-5 text-violet-600" />
          Time Period
        </span>
        <div class="inline-flex bg-slate-100 p-1 rounded-lg gap-0.5">
          <button
            v-for="period in (['ALL', 'TODAY', 'WEEK', 'MONTH', 'QUARTER', 'YEAR'] as const)"
            :key="period"
            :id="`period-filter-${period}`"
            @click="selectedPeriod = period"
            :class="['px-4 py-2 text-sm font-semibold rounded-md cursor-pointer transition',
              selectedPeriod === period
                ? 'bg-white text-slate-900 shadow-sm font-bold'
                : 'text-slate-500 hover:text-slate-700'
            ]"
          >
            {{ period === 'ALL' ? 'All Time' : period }}
          </button>
        </div>
      </div>

      <!-- Edit DSR Form -->
      <div v-if="showEditDsrForm && editingDsr" class="bg-white p-6 rounded-xl border border-blue-200 shadow-sm space-y-5 animate-fadeIn text-left">
        <div class="flex justify-between items-center pb-3 border-b border-slate-100">
          <h3 class="font-bold text-slate-800 text-base flex items-center gap-2">
            <Edit class="h-5 w-5 text-blue-600" />
            <span>Edit: {{ editingDsr.name }}</span>
          </h3>
          <button type="button" @click="showEditDsrForm = false; editingDsr = null" class="text-slate-400 hover:text-slate-600 cursor-pointer p-1 rounded-lg hover:bg-slate-100 transition">
            <X class="h-5 w-5" />
          </button>
        </div>
        <form @submit.prevent="handleEditDsrSubmit" class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 block">Name *</label>
            <input type="text" v-model="editDsrName" class="w-full text-sm py-3 px-4 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-slate-800" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 block">Phone</label>
            <input type="text" v-model="editDsrPhone" class="w-full text-sm py-3 px-4 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 block">Role</label>
            <div class="flex rounded-lg border border-slate-200 p-0.5 bg-slate-100">
              <button type="button" @click="editDsrRole = 'DSR'" :class="['flex-1 text-sm font-semibold rounded-md cursor-pointer py-2.5 transition text-center', editDsrRole === 'DSR' ? 'bg-white text-slate-800 shadow-sm font-bold' : 'text-slate-500 hover:text-slate-700']">DSR Rep</button>
              <button type="button" @click="editDsrRole = 'Order Collector'" :class="['flex-1 text-sm font-semibold rounded-md cursor-pointer py-2.5 transition text-center', editDsrRole === 'Order Collector' ? 'bg-white text-slate-800 shadow-sm font-bold' : 'text-slate-500 hover:text-slate-700']">Collector</button>
            </div>
          </div>
          <div v-if="editDsrRole === 'Order Collector'" class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 block">Supervisor DSR</label>
            <select v-model="editDsrParentId" class="w-full text-sm py-3 px-4 border border-slate-200 rounded-lg bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">-- None --</option>
              <option v-for="d in dsrs.filter(d => !d.role || d.role === 'DSR')" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </div>
          <div class="md:col-span-3 flex items-center gap-3 pt-2">
            <p v-if="editDsrError" class="text-sm text-rose-600 font-semibold flex items-center gap-1"><AlertTriangle class="h-4 w-4" /> {{ editDsrError }}</p>
            <p v-if="editDsrSuccess" class="text-sm text-emerald-600 font-semibold flex items-center gap-1"><CheckCircle class="h-4 w-4" /> {{ editDsrSuccess }}</p>
            <div class="ml-auto flex gap-2">
              <button type="button" @click="showEditDsrForm = false; editingDsr = null" class="py-2.5 px-4 border border-slate-300 rounded-lg text-sm cursor-pointer hover:bg-slate-50 font-semibold">Cancel</button>
              <button type="submit" :disabled="editDsrSubmitting" class="py-2.5 px-5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold cursor-pointer disabled:opacity-40 shadow-sm transition">
                {{ editDsrSubmitting ? 'Saving...' : 'Save Changes' }}
              </button>
            </div>
          </div>
        </form>
      </div>

      <!-- Delete DSR Confirmation -->
      <div v-if="deleteConfirmDsr" class="bg-rose-50 p-5 rounded-xl border border-rose-200 space-y-4 animate-fadeIn text-left">
        <div class="flex items-start gap-3">
          <AlertTriangle class="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <h4 class="font-bold text-slate-800 text-sm">Delete Representative</h4>
            <p class="text-sm text-slate-600 mt-1">Remove <strong class="text-rose-600">{{ deleteConfirmDsr.name }}</strong>? Their existing sales records will be preserved (DSR field set to blank).</p>
          </div>
        </div>
        <div class="flex justify-end gap-2">
          <button @click="deleteConfirmDsr = null" class="px-4 py-2 text-sm border border-slate-200 rounded-lg hover:bg-slate-50 font-semibold cursor-pointer transition">Cancel</button>
          <button @click="handleConfirmDeleteDsr" class="px-4 py-2 text-sm bg-rose-600 text-white rounded-lg font-semibold cursor-pointer hover:bg-rose-700 transition flex items-center gap-1.5">
            <Trash2 class="h-4 w-4" /> Delete
          </button>
        </div>
      </div>

      <!-- ========== METRIC CARDS (Gradient Accents) ========== -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-left">
        <!-- Revenue -->
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2 relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-400 to-emerald-600"></div>
          <span class="text-xs uppercase text-slate-400 font-semibold tracking-wide">Revenue</span>
          <h3 class="text-2xl font-bold text-emerald-700 font-mono">{{ formatCurrency(periodTotals.revenue) }}</h3>
          <p class="text-xs text-slate-400">{{ periodFilteredSales.length }} invoices this period</p>
        </div>

        <!-- COGS -->
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2 relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-slate-400 to-slate-600"></div>
          <span class="text-xs uppercase text-slate-400 font-semibold tracking-wide">Cost of Goods</span>
          <h3 class="text-2xl font-bold text-slate-700 font-mono">{{ formatCurrency(periodTotals.cogs) }}</h3>
          <p class="text-xs text-slate-400">Purchase & stocking cost</p>
        </div>

        <!-- Profit -->
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2 relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-1" :class="periodTotals.grossProfit >= 0 ? 'bg-gradient-to-r from-teal-400 to-teal-600' : 'bg-gradient-to-r from-rose-400 to-rose-600'"></div>
          <span class="text-xs uppercase text-slate-400 font-semibold tracking-wide">Gross Profit</span>
          <h3 :class="['text-2xl font-bold font-mono', periodTotals.grossProfit >= 0 ? 'text-teal-700' : 'text-rose-600']">
            {{ formatCurrency(periodTotals.grossProfit) }}
          </h3>
          <p class="text-xs text-slate-400">Before operating expenses</p>
        </div>

        <!-- Pending -->
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2 relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-rose-400 to-rose-600"></div>
          <span class="text-xs uppercase text-rose-500 font-semibold tracking-wide">Credit Pending</span>
          <h3 class="text-2xl font-bold text-rose-600 font-mono">{{ formatCurrency(periodTotals.pending) }}</h3>
          <p class="text-xs text-rose-500">Awaiting collection</p>
        </div>

        <!-- Written Off Summary -->
        <div v-if="periodTotals.writtenOff > 0" class="bg-gradient-to-br from-amber-50 to-amber-100 p-5 rounded-xl border border-amber-200 shadow-sm relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-400 to-amber-600"></div>
          <div class="space-y-1">
            <span class="text-xs uppercase text-amber-600 font-semibold tracking-wide">Uncollected Bad Debt</span>
            <h3 class="text-2xl font-bold text-amber-700 font-mono">{{ formatCurrency(periodTotals.writtenOff) }}</h3>
            <p class="text-xs text-amber-600">
              {{ periodFilteredSales.filter(s => s.isClosedWithDue).length }} invoices written off
            </p>
            <p class="text-xs text-slate-500 mt-2">
              View details in "Bad Debt" tab
            </p>
          </div>
        </div>
      </div>

      <!-- ========== DSR REPRESENTATIVE TABLE ========== -->
      <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5 font-sans text-left">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <h3 class="font-bold text-slate-800 text-sm uppercase tracking-wider flex items-center gap-2">
              <User class="h-5 w-5 text-violet-600" />
              DSR-wise Due
            </h3>
            <p class="text-sm text-slate-400 mt-1">Outstanding balances grouped by sales representative</p>
          </div>
          <div class="relative w-full max-w-xs text-left">
            <Search class="absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search reps..." 
              v-model="repSearchQuery"
              class="w-full text-sm pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 text-slate-800"
            />
          </div>
        </div>

        <div class="overflow-x-auto border border-slate-200 rounded-xl shadow-sm">
          <table class="w-full text-left font-sans text-sm">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-slate-400 uppercase text-xs font-bold tracking-wider">
                <th class="py-3 px-4">Representative</th>
                <th class="py-3 px-4 font-mono text-xs">Phone</th>
                <th class="py-3 px-4">Total Sales</th>
                <th class="py-3 px-4 text-emerald-700 font-bold">Collected</th>
                <th class="py-3 px-4 text-rose-600 font-bold">Pending</th>
                <th class="py-3 px-4 text-center">Invoices</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <template v-for="(rep, idx) in currentRepsList" :key="idx">
                <tr 
                  @click="expandedRep = expandedRep === (rep.id || rep.name) ? null : (rep.id || rep.name)"
                  :class="['hover:bg-slate-50 transition cursor-pointer font-medium', expandedRep === (rep.id || rep.name) ? 'bg-violet-50/30' : '']"
                >
                  <td class="py-3.5 px-4">
                    <div>
                      <p class="font-bold text-slate-800 text-sm leading-none">{{ rep.name }}</p>
                      <div class="text-xs text-slate-400 mt-1.5 flex flex-wrap gap-1.5 items-center">
                        <span v-if="rep.role === 'DSR'" class="text-violet-700 bg-violet-50 px-2 py-0.5 rounded-md font-semibold text-[10px] uppercase">DSR</span>
                        <span v-else class="text-cyan-700 bg-cyan-50 px-2 py-0.5 rounded-md font-semibold text-[10px] uppercase">Collector</span>
                        <span v-if="rep.role === 'Order Collector'" class="text-slate-400 text-xs">under {{ rep.parentDsrName || 'Dealer' }}</span>
                      </div>
                    </div>
                  </td>
                  <td class="py-3.5 px-4 font-mono text-sm text-slate-500">{{ dsrs.find(d => d.id === rep.id || d.name === rep.name)?.phone || '--' }}</td>
                  <td class="py-3.5 px-4 font-bold text-slate-800 font-mono">{{ formatCurrency(rep.totalSales) }}</td>
                  <td class="py-3.5 px-4 text-emerald-600 font-bold font-mono">{{ formatCurrency(rep.collected) }}</td>
                <td :class="['py-3.5 px-4 font-bold font-mono', rep.pending > 0 ? 'text-rose-600' : 'text-slate-400']">
                  <span class="block leading-none">{{ formatCurrency(rep.pending) }}</span>
                  <span v-if="rep.pending > 0" class="text-[10px] text-rose-400 uppercase tracking-wider mt-1 block font-semibold">Collect</span>
                </td>
                <td class="py-3.5 px-4 text-center">
                  <div class="flex items-center justify-center gap-1">
                    <button type="button" class="bg-violet-50 hover:bg-violet-100 border border-violet-100 text-violet-700 px-3 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1 cursor-pointer transition">
                      <span>{{ rep.count }} bills</span>
                      <ChevronUp v-if="expandedRep === (rep.id || rep.name)" class="h-3 w-3 shrink-0" />
                      <ChevronDown v-else class="h-3 w-3 shrink-0" />
                    </button>
                    <button 
                      type="button" 
                      @click="handleStartEditDsr(dsrs.find(d => d.id === rep.id || d.name === rep.name)!)"
                      class="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition cursor-pointer"
                      title="Edit representative"
                    >
                      <Edit class="h-3.5 w-3.5" />
                    </button>
                    <button 
                      type="button" 
                      @click="handleDeleteDsr(dsrs.find(d => d.id === rep.id || d.name === rep.name)!)"
                      class="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition cursor-pointer"
                      title="Delete representative"
                    >
                      <Trash2 class="h-3.5 w-3.5" />
                    </button>
                  </div>
                </td>
              </tr>

              <!-- Expanded Invoices -->
              <tr v-if="expandedRep === (rep.id || rep.name)">
                <td colSpan="6" class="bg-slate-50/80 p-4 border-t border-b border-slate-200">
                  <div class="space-y-4 animate-fadeIn font-sans text-left">
                    <div class="flex items-center justify-between border-b border-slate-200 pb-3">
                      <span class="font-bold text-slate-700 text-sm">
                        Invoices for <strong class="text-violet-700">{{ rep.name }}</strong>
                      </span>
                      <div class="flex items-center gap-2">
                        <button
                          type="button"
                          @click="printData = { type: 'DSR_STATEMENT', period: selectedPeriod, payload: { rep: rep, sales: periodFilteredSales.filter(s => s.dsrId === rep.id || (s.dsrName && s.dsrName.toLowerCase().trim() === rep.name.toLowerCase().trim())) } }"
                          class="px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-600 border border-slate-300 rounded-lg font-semibold text-xs flex items-center gap-1.5 cursor-pointer transition shadow-sm"
                        >
                          <Printer class="h-3.5 w-3.5 text-violet-600" />
                          Print Statement
                        </button>
                      </div>
                    </div>

                    <div v-if="repSales = periodFilteredSales.filter(s => s.dsrId === rep.id || (s.dsrName && s.dsrName.toLowerCase().trim() === rep.name.toLowerCase().trim())), repSales.length > 0" class="space-y-3">
                      <div class="overflow-x-auto border border-slate-200 rounded-xl shadow-sm">
                        <table class="w-full text-left text-sm bg-white">
                          <thead>
                            <tr class="bg-slate-50 border-b border-slate-200 text-slate-400 uppercase text-xs font-bold tracking-wider">
                              <th class="py-3 px-3">Date</th>
                              <th class="py-3 px-3">Customer</th>
                              <th class="py-3 px-3">Product</th>
                              <th class="py-3 px-3 text-center">Invoice</th>
                              <th class="py-3 px-3 text-center text-emerald-700">Paid</th>
                              <th class="py-3 px-3 text-center text-rose-600">Balance</th>
                              <th class="py-3 px-3 text-center">Type</th>
                              <th class="py-3 px-3 text-center">Status</th>
                            </tr>
                          </thead>
                          <tbody class="divide-y divide-slate-100 text-sm font-medium text-slate-600">
                            <tr v-for="sale in repSales.slice((repRecordPage - 1) * subSalesPerPage, repRecordPage * subSalesPerPage)" :key="sale.id" class="hover:bg-slate-50 transition align-middle">
                              <td class="py-3 px-3 text-xs text-slate-400 font-mono">{{ new Date(sale.date).toLocaleDateString() }}</td>
                              <td class="py-3 px-3 font-bold text-slate-800 leading-tight">
                                {{ sale.customerName }}
                                <span v-if="sale.isVehicle && sale.vehicleNumber" class="ml-1 px-1.5 bg-slate-800 text-white rounded font-mono text-[10px] uppercase">{{ sale.vehicleNumber }}</span>
                              </td>
                              <td>
                                <p class="font-semibold text-slate-700 leading-none">{{ sale.productName }}</p>
                                <p class="text-xs text-slate-400 font-mono mt-0.5">Qty: {{ sale.quantity }} @ {{ formatCurrency(sale.sellingPrice) }}</p>
                              </td>
                              <td class="py-3 px-2 text-center font-bold font-mono">{{ formatCurrency(sale.totalAmount) }}</td>
                              <td class="py-3 px-2 text-center font-bold font-mono text-emerald-600">{{ formatCurrency(sale.amountPaid) }}</td>
                              <td class="py-3 px-2 text-center font-bold font-mono">
                                <span v-if="sale.isClosedWithDue" class="text-amber-600 bg-amber-50 px-2 py-0.5 rounded text-xs font-semibold">Written Off</span>
                                <span v-else-if="sale.totalAmount - sale.amountPaid > 0" class="text-rose-600">{{ formatCurrency(sale.totalAmount - sale.amountPaid) }}</span>
                                <span v-else class="text-emerald-600">₹0</span>
                              </td>
                              <td class="py-3 px-3 text-center font-medium text-slate-400 text-xs">{{ sale.paymentType }}</td>
                              <td class="py-3 px-3 text-center">
                                <span v-if="sale.isClosedWithDue" class="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Written Off</span>
                                <span v-else-if="sale.totalAmount - sale.amountPaid === 0" class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Paid</span>
                                <span v-else class="bg-rose-100 text-rose-800 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Pending</span>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>

                      <!-- Sub Pagination -->
                      <div v-if="totalRepSalesPages = Math.ceil(repSales.length / subSalesPerPage), totalRepSalesPages > 1" class="flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-2 shadow-sm font-sans">
                        <span class="text-sm text-slate-500">
                          Page <span class="font-bold">{{ repRecordPage }}</span> of <span class="font-bold">{{ totalRepSalesPages }}</span>
                        </span>
                        <div class="flex gap-1">
                          <button type="button" :disabled="repRecordPage === 1" @click="repRecordPage = Math.max(repRecordPage - 1, 1)" class="px-3 py-1 text-sm border border-slate-300 rounded-lg bg-slate-50 hover:bg-slate-100 disabled:opacity-40 cursor-pointer">Prev</button>
                          <button type="button" :disabled="repRecordPage === totalRepSalesPages" @click="repRecordPage = Math.min(repRecordPage + 1, totalRepSalesPages)" class="px-3 py-1 text-sm border border-slate-300 rounded-lg bg-slate-50 hover:bg-slate-100 disabled:opacity-40 cursor-pointer">Next</button>
                        </div>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            </template>

            <tr v-if="filteredDsrPerformance.length === 0">
              <td colSpan="6" class="text-center py-10 text-slate-400 italic font-semibold">No representatives found</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Outer Pagination -->
      <div v-if="totalRepPages > 1" class="pt-3 flex items-center justify-between">
        <span class="text-sm text-slate-500">
          Showing <span class="font-semibold">{{ (repPage - 1) * repsPerPage + 1 }}</span> – <span class="font-semibold">{{ Math.min(repPage * repsPerPage, filteredDsrPerformance.length) }}</span> of <span class="font-semibold">{{ filteredDsrPerformance.length }}</span>
        </span>
        <div class="flex gap-1">
          <button type="button" :disabled="repPage === 1" @click="repPage = Math.max(repPage - 1, 1)" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer transition">Prev</button>
          <button v-for="no in totalRepPages" :key="no" type="button" @click="repPage = no" :class="['px-3 py-1.5 text-sm border rounded-lg cursor-pointer font-semibold transition', repPage === no ? 'bg-violet-600 border-violet-600 text-white' : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-100']">{{ no }}</button>
          <button type="button" :disabled="repPage === totalRepPages" @click="repPage = Math.min(repPage + 1, totalRepPages)" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer transition">Next</button>
        </div>
      </div>
    </div>

    <!-- ========== VEHICLE REPORTS (Card Grid) ========== -->
    <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5 font-sans text-left">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <h3 class="font-bold text-slate-800 text-sm uppercase tracking-wider flex items-center gap-2">
            <Truck class="h-5 w-5 text-blue-600" />
            Vehicle-wise Due
          </h3>
          <p class="text-sm text-slate-400 mt-1">Outstanding balances grouped by vehicle plate</p>
        </div>

        <div class="relative w-full max-w-xs text-left">
          <Search class="absolute left-3 top-3 h-4 w-4 text-slate-400" />
          <input type="text" placeholder="Search vehicles or reps..." v-model="vehicleQuery" class="w-full text-sm pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      <!-- Vehicle Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div 
          v-for="v in currentVehiclesList" 
          :key="v.vehicleNumber"
          :class="['border rounded-xl p-5 transition flex flex-col text-left',
            expandedVehicle === v.vehicleNumber 
              ? 'border-blue-400 bg-blue-50/20 shadow-md ring-1 ring-blue-400/20' 
              : 'border-slate-200 hover:border-slate-300 hover:shadow-md'
          ]"
        >
          <div class="space-y-3">
            <div class="flex justify-between items-start">
              <div>
                <span class="bg-slate-800 text-white font-mono font-bold text-sm tracking-wider px-3 py-1.5 rounded-lg shadow-sm uppercase leading-none">
                  {{ v.vehicleNumber }}
                </span>
                <p class="text-xs text-slate-400 mt-2 font-medium">
                  Reps: {{ v.reps.join(', ') || 'Direct' }}
                </p>
              </div>
              <span class="text-xs bg-slate-100 px-2.5 py-1 rounded-full text-slate-500 font-semibold">
                {{ v.count }} stops
              </span>
            </div>

            <div class="grid grid-cols-2 gap-3 pt-3 border-t border-slate-100 font-sans text-left">
              <div>
                <p class="text-xs text-slate-400 font-semibold uppercase">Dispatched</p>
                <p class="text-sm font-bold text-slate-800 font-mono mt-0.5">{{ formatCurrency(v.totalSales) }}</p>
              </div>
              <div>
                <p class="text-xs text-emerald-600 font-semibold uppercase">Collected</p>
                <p class="text-sm font-bold text-emerald-600 font-mono mt-0.5">{{ formatCurrency(v.collected) }}</p>
              </div>
              <div>
                <p class="text-xs text-rose-500 font-semibold uppercase">Pending</p>
                <p class="text-sm font-bold text-rose-600 font-mono mt-0.5">{{ formatCurrency(v.pending) }}</p>
              </div>
              <div>
                <p class="text-xs text-slate-400 font-semibold uppercase">Written Off</p>
                <p class="text-sm font-semibold text-slate-500 font-mono mt-0.5">{{ formatCurrency(v.writtenOff) }}</p>
              </div>
            </div>
          </div>

          <button
            type="button"
            @click="expandedVehicle = expandedVehicle === v.vehicleNumber ? null : v.vehicleNumber"
            class="w-full text-center mt-4 py-2 bg-white hover:bg-slate-100 border border-slate-200 rounded-lg text-sm font-semibold text-slate-600 cursor-pointer transition shadow-sm flex items-center justify-center gap-2"
          >
            <component :is="expandedVehicle === v.vehicleNumber ? ChevronUp : ChevronDown" class="h-4 w-4" />
            {{ expandedVehicle === v.vehicleNumber ? 'Hide Details' : 'View Details' }}
          </button>
        </div>

        <div v-if="currentVehiclesList.length === 0" class="col-span-full text-center py-10 border border-dashed border-slate-200 rounded-xl text-slate-400 text-sm font-semibold">
          No vehicles matching your filter
        </div>
      </div>

      <!-- Vehicle Pagination -->
      <div v-if="totalVehiclePages > 1" class="pt-3 flex items-center justify-between">
        <span class="text-sm text-slate-500">
          Showing <span class="font-semibold">{{ (vehiclePage - 1) * vehiclesPerPage + 1 }}</span> – <span class="font-semibold">{{ Math.min(vehiclePage * vehiclesPerPage, filteredVehicles.length) }}</span> of <span class="font-semibold">{{ filteredVehicles.length }}</span>
        </span>
        <div class="flex gap-1">
          <button type="button" :disabled="vehiclePage === 1" @click="vehiclePage = Math.max(vehiclePage - 1, 1)" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer transition">Prev</button>
          <button v-for="no in totalVehiclePages" :key="no" type="button" @click="vehiclePage = no" :class="['px-3 py-1.5 text-sm border rounded-lg cursor-pointer font-semibold transition', vehiclePage === no ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-100']">{{ no }}</button>
          <button type="button" :disabled="vehiclePage === totalVehiclePages" @click="vehiclePage = Math.min(vehiclePage + 1, totalVehiclePages)" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer transition">Next</button>
        </div>
      </div>

      <!-- Expanded Vehicle Details -->
      <div v-if="expandedVehicle" class="bg-slate-50 p-5 rounded-xl border border-slate-200 space-y-4 animate-fadeIn text-left">
        <div class="flex justify-between items-center border-b border-slate-200 pb-3">
          <h4 class="font-bold text-slate-800 text-sm flex items-center gap-2">
            <Truck class="h-4 w-4 text-blue-600" />
            Delivery Stops for <span class="font-mono text-blue-700 uppercase">{{ expandedVehicle }}</span>
          </h4>
          <div class="flex items-center gap-3">
            <button
              type="button"
              @click="printData = { type: 'VEHICLE_TRIP', period: selectedPeriod, payload: { vehicle: vehiclePerformance.find(v => v.vehicleNumber === expandedVehicle) } }"
              class="px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-600 border border-slate-300 rounded-lg font-semibold text-xs flex items-center gap-1.5 cursor-pointer transition shadow-sm"
            >
              <Printer class="h-3.5 w-3.5 text-blue-600" />
              Print Trip Sheet
            </button>
            <button @click="expandedVehicle = null" class="text-slate-400 hover:text-rose-600 font-semibold text-sm cursor-pointer flex items-center gap-1">
              <span>Close</span>
              <X class="h-4 w-4 shrink-0" />
            </button>
          </div>
        </div>

        <div v-if="currVehicleRecords = (vehiclePerformance.find(v => v.vehicleNumber === expandedVehicle)?.records || []), currVehicleRecords.length > 0" class="overflow-x-auto border border-slate-200 rounded-xl shadow-sm bg-white">
          <table class="w-full text-left text-sm">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-slate-400 uppercase text-xs font-bold tracking-wider">
                <th class="py-3 px-3">Date</th>
                <th class="py-3 px-3">Customer</th>
                <th class="py-3 px-3">Product</th>
                <th class="py-3 px-3 text-center">Invoice</th>
                <th class="py-3 px-3 text-center">Paid</th>
                <th class="py-3 px-3 text-center text-rose-600">Balance</th>
                <th class="py-3 px-3 text-center">Rep</th>
                <th class="py-3 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-sm font-medium text-slate-600">
              <tr v-for="r in currVehicleRecords.slice((vRecordPage - 1) * subSalesPerPage, vRecordPage * subSalesPerPage)" :key="r.id" class="hover:bg-slate-50 transition align-top">
                <td class="py-3 px-3 text-xs text-slate-400 font-mono">{{ new Date(r.date).toLocaleDateString() }}</td>
                <td class="py-3 px-3">
                  <p class="font-bold text-slate-800 leading-tight">{{ r.customerName }}</p>
                  <p class="text-xs text-slate-400 mt-0.5">{{ r.customerPhone || 'N/A' }}</p>
                </td>
                <td class="py-3 px-3">
                  <p class="font-semibold text-slate-700 leading-none">{{ r.productName }}</p>
                  <p class="text-xs text-slate-400 font-mono mt-0.5">Qty: {{ r.quantity }} @ {{ formatCurrency(r.sellingPrice) }}</p>
                </td>
                <td class="py-3 px-3 text-center font-bold font-mono">{{ formatCurrency(r.totalAmount) }}</td>
                <td class="py-3 px-3 text-center font-bold font-mono text-emerald-600">{{ formatCurrency(r.amountPaid) }}</td>
                <td class="py-3 px-3 text-center font-bold font-mono">
                  <span v-if="r.isClosedWithDue" class="text-amber-600 bg-amber-50 px-2 py-0.5 rounded text-xs font-semibold">Written Off</span>
                  <span v-else-if="r.totalAmount - r.amountPaid > 0" class="text-rose-600">{{ formatCurrency(r.totalAmount - r.amountPaid) }}</span>
                  <span v-else class="text-emerald-600">₹0</span>
                </td>
                <td class="py-3 px-3 text-slate-500 text-center">{{ r.dsrName || 'Counter' }}</td>
                <td class="py-3 px-3 text-center">
                  <span v-if="r.isClosedWithDue" class="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Written Off</span>
                  <span v-else-if="r.totalAmount - r.amountPaid === 0" class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Paid</span>
                  <span v-else-if="r.paymentType === 'Credit'" class="bg-rose-100 text-rose-800 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Credit</span>
                  <span v-else class="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Cash</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Inner Pagination -->
        <div v-if="totalVRecordPages = Math.ceil(currVehicleRecords.length / subSalesPerPage), totalVRecordPages > 1" class="flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-2 shadow-sm font-sans">
          <span class="text-sm text-slate-500">Page <span class="font-bold">{{ vRecordPage }}</span> of <span class="font-bold">{{ totalVRecordPages }}</span></span>
          <div class="flex gap-1">
            <button type="button" :disabled="vRecordPage === 1" @click="vRecordPage = Math.max(vRecordPage - 1, 1)" class="px-3 py-1 text-sm border border-slate-300 rounded-lg bg-slate-50 hover:bg-slate-100 disabled:opacity-40 cursor-pointer font-semibold">Prev</button>
            <button type="button" :disabled="vRecordPage === totalVRecordPages" @click="vRecordPage = Math.min(vRecordPage + 1, totalVRecordPages)" class="px-3 py-1 text-sm border border-slate-300 rounded-lg bg-slate-50 hover:bg-slate-100 disabled:opacity-40 cursor-pointer font-semibold">Next</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== CUSTOMER-WISE DUE REPORT ========== -->
    <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5 font-sans text-left">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div>
          <h3 class="font-bold text-slate-800 text-sm uppercase tracking-wider flex items-center gap-2">
            <Users class="h-5 w-5 text-rose-600" />
            Customer-wise Due
          </h3>
          <p class="text-sm text-slate-400 mt-1">Outstanding balances grouped by customer ({{ filteredCustomers.length }} customers)</p>
        </div>
        <div class="flex items-center gap-3">
          <div class="relative w-full max-w-xs text-left">
            <Search class="absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search customers..." 
              v-model="customerQuery"
              class="w-full text-sm pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500 text-slate-800"
            />
          </div>
          <button 
            type="button"
            @click="printData = { type: 'CUSTOMER_DUE', period: selectedPeriod, payload: { customers: customerDueData } }"
            class="shrink-0 px-3 py-2.5 bg-white hover:bg-slate-100 text-slate-600 border border-slate-300 rounded-lg font-semibold text-xs flex items-center gap-1.5 cursor-pointer transition shadow-sm"
          >
            <Printer class="h-3.5 w-3.5 text-rose-600" />
            Print Statement
          </button>
        </div>
      </div>

      <div class="overflow-x-auto border border-slate-200 rounded-xl shadow-sm">
        <table class="w-full text-left font-sans text-sm">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-slate-400 uppercase text-xs font-bold tracking-wider">
              <th class="py-3 px-4">Customer</th>
              <th class="py-3 px-4 font-mono text-xs">Phone</th>
              <th class="py-3 px-4">Total Billed</th>
              <th class="py-3 px-4 text-emerald-700 font-bold">Paid</th>
              <th class="py-3 px-4 text-rose-600 font-bold">Pending Due</th>
              <th class="py-3 px-4 text-amber-600">Written Off</th>
              <th class="py-3 px-4 text-center">Invoices</th>
              <th class="py-3 px-4 text-center">Details</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <template v-for="c in currentCustomersList" :key="c.name">
              <tr class="hover:bg-slate-50 transition">
                <td class="py-3 px-4">
                  <p class="font-bold text-slate-800">{{ c.name }}</p>
                </td>
                <td class="py-3 px-4 font-mono text-xs text-slate-500">{{ c.phone || 'N/A' }}</td>
                <td class="py-3 px-4 font-bold font-mono text-slate-700">{{ formatCurrency(c.totalBilled) }}</td>
                <td class="py-3 px-4 font-bold font-mono text-emerald-600">{{ formatCurrency(c.totalPaid) }}</td>
                <td class="py-3 px-4">
                  <span v-if="c.pending > 0" class="font-bold font-mono text-rose-600">{{ formatCurrency(c.pending) }}</span>
                  <span v-else class="text-emerald-600 font-semibold text-xs">Clear</span>
                </td>
                <td class="py-3 px-4 font-mono text-xs" :class="c.writtenOff > 0 ? 'text-amber-600 font-semibold' : 'text-slate-400'">
                  {{ c.writtenOff > 0 ? formatCurrency(c.writtenOff) : '—' }}
                </td>
                <td class="py-3 px-4 text-center">
                  <span class="bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full text-xs font-bold">{{ c.invoiceCount }}</span>
                </td>
                <td class="py-3 px-4 text-center">
                  <button 
                    type="button"
                    @click="expandedCustomer = expandedCustomer === c.name ? null : c.name"
                    class="text-xs font-semibold cursor-pointer px-2 py-1 rounded-lg transition"
                    :class="expandedCustomer === c.name ? 'bg-rose-100 text-rose-700' : 'bg-slate-50 text-slate-500 hover:bg-slate-100'"
                  >
                    <component :is="expandedCustomer === c.name ? ChevronUp : ChevronDown" class="h-3.5 w-3.5 inline" />
                  </button>
                </td>
              </tr>
            </template>
            <tr v-if="currentCustomersList.length === 0">
              <td colspan="8" class="py-10 text-center text-slate-400 font-semibold text-sm">No customers with outstanding dues in this period</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Customer Pagination -->
      <div v-if="totalCustomerPages > 1" class="pt-3 flex items-center justify-between">
        <span class="text-sm text-slate-500">
          Showing <span class="font-semibold">{{ (customerPage - 1) * customersPerPage + 1 }}</span> – <span class="font-semibold">{{ Math.min(customerPage * customersPerPage, filteredCustomers.length) }}</span> of <span class="font-semibold">{{ filteredCustomers.length }}</span>
        </span>
        <div class="flex gap-1">
          <button type="button" :disabled="customerPage === 1" @click="customerPage = Math.max(customerPage - 1, 1)" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer transition">Prev</button>
          <button v-for="no in totalCustomerPages" :key="no" type="button" @click="customerPage = no" :class="['px-3 py-1.5 text-sm border rounded-lg cursor-pointer font-semibold transition', customerPage === no ? 'bg-rose-600 border-rose-600 text-white' : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-100']">{{ no }}</button>
          <button type="button" :disabled="customerPage === totalCustomerPages" @click="customerPage = Math.min(customerPage + 1, totalCustomerPages)" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer transition">Next</button>
        </div>
      </div>

      <!-- Expanded Customer Invoice Details -->
      <div v-if="expandedCustomer" class="bg-slate-50 p-5 rounded-xl border border-slate-200 space-y-4 animate-fadeIn text-left">
        <div class="flex justify-between items-center border-b border-slate-200 pb-3">
          <h4 class="font-bold text-slate-800 text-sm flex items-center gap-2">
            <Users class="h-4 w-4 text-rose-600" />
            Invoices for <span class="text-rose-700">{{ expandedCustomer }}</span>
          </h4>
          <button @click="expandedCustomer = null" class="text-slate-400 hover:text-rose-600 font-semibold text-sm cursor-pointer flex items-center gap-1">
            <span>Close</span>
            <X class="h-4 w-4 shrink-0" />
          </button>
        </div>

        <div v-if="custRec = (customerDueData.find(c => c.name === expandedCustomer)?.records || []), custRec.length > 0" class="overflow-x-auto border border-slate-200 rounded-xl shadow-sm bg-white">
          <table class="w-full text-left text-sm">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-slate-400 uppercase text-xs font-bold tracking-wider">
                <th class="py-3 px-3">Date</th>
                <th class="py-3 px-3">Product</th>
                <th class="py-3 px-3 text-center">Qty</th>
                <th class="py-3 px-3 text-center">Invoice</th>
                <th class="py-3 px-3 text-center">Paid</th>
                <th class="py-3 px-3 text-center text-rose-600">Balance</th>
                <th class="py-3 px-3 text-center">Rep</th>
                <th class="py-3 px-3 text-center">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-sm font-medium text-slate-600">
              <tr v-for="r in custRec.slice((custRecordPage - 1) * subSalesPerPage, custRecordPage * subSalesPerPage)" :key="r.id" class="hover:bg-slate-50 transition align-top">
                <td class="py-3 px-3 text-xs text-slate-400 font-mono">{{ new Date(r.date).toLocaleDateString() }}</td>
                <td class="py-3 px-3">
                  <p class="font-semibold text-slate-700 leading-none">{{ r.productName }}</p>
                  <p v-if="r.isVehicle && r.vehicleNumber" class="text-xs text-blue-500 mt-0.5 font-mono">{{ r.vehicleNumber }}</p>
                </td>
                <td class="py-3 px-3 text-center">{{ r.quantity }}</td>
                <td class="py-3 px-3 text-center font-bold font-mono">{{ formatCurrency(r.totalAmount) }}</td>
                <td class="py-3 px-3 text-center font-bold font-mono text-emerald-600">{{ formatCurrency(r.amountPaid) }}</td>
                <td class="py-3 px-3 text-center font-bold font-mono">
                  <span v-if="r.isClosedWithDue" class="text-amber-600 bg-amber-50 px-2 py-0.5 rounded text-xs font-semibold">Written Off</span>
                  <span v-else-if="r.totalAmount - r.amountPaid > 0" class="text-rose-600">{{ formatCurrency(r.totalAmount - r.amountPaid) }}</span>
                  <span v-else class="text-emerald-600">Clear</span>
                </td>
                <td class="py-3 px-3 text-slate-500 text-center">{{ r.dsrName || 'Counter' }}</td>
                <td class="py-3 px-3 text-center">
                  <span v-if="r.isClosedWithDue" class="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Written Off</span>
                  <span v-else-if="r.totalAmount - r.amountPaid === 0" class="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Paid</span>
                  <span v-else-if="r.paymentType === 'Credit'" class="bg-rose-100 text-rose-800 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Credit</span>
                  <span v-else class="bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase">Cash</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Inner Pagination for customer records -->
        <div v-if="totalCustRecPages = Math.ceil((customerDueData.find(c => c.name === expandedCustomer)?.records || []).length / subSalesPerPage), totalCustRecPages > 1" class="flex items-center justify-between bg-white border border-slate-200 rounded-xl px-4 py-2 shadow-sm font-sans">
          <span class="text-sm text-slate-500">Page <span class="font-bold">{{ custRecordPage }}</span> of <span class="font-bold">{{ totalCustRecPages }}</span></span>
          <div class="flex gap-1">
            <button type="button" :disabled="custRecordPage === 1" @click="custRecordPage = Math.max(custRecordPage - 1, 1)" class="px-3 py-1 text-sm border border-slate-300 rounded-lg bg-slate-50 hover:bg-slate-100 disabled:opacity-40 cursor-pointer font-semibold">Prev</button>
            <button type="button" :disabled="custRecordPage === totalCustRecPages" @click="custRecordPage = Math.min(custRecordPage + 1, totalCustRecPages)" class="px-3 py-1 text-sm border border-slate-300 rounded-lg bg-slate-50 hover:bg-slate-100 disabled:opacity-40 cursor-pointer font-semibold">Next</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== LOW STOCK ALERTS ========== -->
    <div v-if="products.filter(p => p.stock <= (p.minStockAlert || 10)).length > 0" class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4 text-left font-sans">
      <div class="flex items-center gap-2 border-b border-slate-100 pb-3">
        <AlertTriangle class="h-5 w-5 text-amber-500 animate-pulse" />
        <span class="text-slate-800 font-bold text-sm uppercase tracking-wide">Low Stock Alerts</span>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        <div 
          v-for="p in products.filter(p => p.stock <= (p.minStockAlert || 10))" 
          :key="p.id"
          class="p-4 border border-dashed border-amber-300 bg-amber-50/20 hover:bg-amber-50/40 rounded-xl transition"
        >
          <p class="font-bold text-slate-800 text-sm truncate">{{ p.name }}</p>
          <div class="flex items-center justify-between text-sm text-slate-500 mt-2 font-sans">
            <span>Stock: <strong class="text-rose-600">{{ p.stock }}</strong></span>
            <span>Min: {{ p.minStockAlert || 10 }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== AI ASSISTANT (Chat-like Interface) ========== -->
    <div class="bg-gradient-to-br from-slate-900 to-slate-800 text-slate-100 p-6 rounded-xl border border-slate-700 shadow-sm space-y-5 text-left">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-700">
        <div class="flex items-center gap-3 text-left">
          <div class="bg-violet-600 text-white p-2.5 rounded-xl shadow-md">
            <BrainCircuit class="h-6 w-6" />
          </div>
          <div>
            <h3 class="font-semibold text-base text-white flex items-center gap-2">
              <Sparkles class="h-4 w-4 text-amber-400" />
              AI Financial Assistant
            </h3>
            <p class="text-xs text-slate-400 font-sans mt-0.5">Automated analysis & actionable recommendations</p>
          </div>
        </div>

        <button 
          id="rep-btn-run-ai"
          @click="emit('askGemini')"
          :disabled="isAiLoading"
          class="bg-violet-600 hover:bg-violet-500 text-white font-semibold text-sm px-5 py-2.5 rounded-lg font-bold shadow-md flex items-center justify-center gap-2 transition disabled:opacity-50 cursor-pointer"
        >
          <svg v-if="isAiLoading" class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <Sparkles v-else class="h-4 w-4" />
          <span>{{ isAiLoading ? 'Analyzing...' : 'Generate Analysis' }}</span>
        </button>
      </div>

      <!-- Chat Response Area -->
      <div class="bg-slate-950/80 p-5 rounded-xl border border-slate-700/50 relative min-h-[120px]">
        <div v-if="isAiLoading" class="flex flex-col items-center justify-center py-8 space-y-3 text-center">
          <div class="animate-bounce bg-violet-600 text-white p-2.5 rounded-xl shadow-sm">
            <Sparkles class="h-5 w-5 text-white" />
          </div>
          <p class="text-sm text-slate-400 font-sans">AI is analyzing your financial data...</p>
        </div>

        <div v-else-if="aiResponse" class="space-y-3 text-slate-200 text-sm leading-relaxed select-text">
          <div v-for="(line, idx) in aiResponse.split('\n')" :key="idx">
            <h4 v-if="line.startsWith('###') || (line.startsWith('**') && line.endsWith('**') && line.length < 50)" class="font-bold text-white text-sm md:text-base mt-5 mb-2 border-b border-slate-700 pb-2 flex items-center gap-2">
              <Sparkles class="h-4 w-4 text-amber-400 shrink-0" />
              <span>{{ line.replace(/[#*]/g, '').trim() }}</span>
            </h4>
            <div v-else-if="line.startsWith('**') || line.startsWith('* **')" class="ml-4 my-1.5 text-left font-sans flex gap-2">
              <span class="text-violet-400 shrink-0">•</span>
              <span><strong class="text-violet-300">{{ line.replace(/^\*\s+\*\*/, '').replace(/^\*\*/, '').split('**')[0] }}</strong>{{ line.replace(/^\*\s+\*\*/, '').replace(/^\*\*/, '').split('**').slice(1).join('') }}</span>
            </div>
            <div v-else-if="line.trim().startsWith('*') || line.trim().startsWith('-')" class="ml-4 my-1.5 text-left font-sans flex gap-2">
              <span class="text-slate-500 shrink-0">•</span>
              <span>{{ line.trim().substring(1).trim() }}</span>
            </div>
            <div v-else-if="line.trim().length === 0" class="h-2" />
            <p v-else class="text-slate-300 text-sm font-sans leading-relaxed text-left font-medium">{{ line }}</p>
          </div>
        </div>

        <div v-else class="flex flex-col items-center justify-center py-10 text-center text-slate-500 space-y-2 select-none font-sans">
          <Sparkles class="h-8 w-8 text-slate-600 animate-pulse" />
          <p class="font-bold text-slate-400 text-sm">No analysis generated yet</p>
          <p class="text-xs text-slate-500 font-sans max-w-xs leading-relaxed">Click "Generate Analysis" to let AI review your finances and suggest actions</p>
        </div>
      </div>
    </div>

    <!-- ========== PRINT PREVIEW OVERLAY ========== -->
    <div v-if="printData" class="fixed inset-0 bg-white z-[999] overflow-y-auto p-4 sm:p-8 font-sans text-slate-900 leading-normal text-left select-text print-ready-overlay">
      <component :is="'style'">{`
        @media print {
          body * { visibility: hidden !important; }
          .print-ready-overlay, .print-ready-overlay * { visibility: visible !important; }
          .print-ready-overlay { position: absolute !important; left: 0 !important; top: 0 !important; width: 100% !important; height: auto !important; background: white !important; color: black !important; padding: 0 !important; margin: 0 !important; }
          .no-print { display: none !important; height: 0 !important; visibility: hidden !important; }
          .paper-sheet { border: none !important; box-shadow: none !important; margin: 0 !important; padding: 0 !important; max-width: 100% !important; }
        }
      `}</component>

      <div class="max-w-4xl mx-auto mb-6 flex flex-col sm:flex-row gap-3 justify-between items-center bg-slate-100 p-4 border border-slate-200 rounded-xl no-print">
        <div class="space-y-0.5 text-left font-sans">
          <span class="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            <Printer class="h-4 w-4 text-violet-600" />
            Print Preview
          </span>
          <p class="text-xs text-slate-500 mt-1 font-sans">Ready for print or CSV export</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button @click="printPage" class="py-2 px-4 bg-violet-600 hover:bg-violet-700 text-white text-sm font-bold rounded-lg flex items-center gap-2 cursor-pointer shadow-sm transition">
            <Printer class="h-4 w-4" />
            Print
          </button>
          <button @click="handleExportCSV" class="py-2 px-4 bg-slate-800 hover:bg-slate-900 text-white text-sm font-bold rounded-lg flex items-center gap-2 cursor-pointer shadow-sm transition">
            <Download class="h-4 w-4 text-slate-200" />
            Export CSV
          </button>
          <button @click="printData = null" class="py-2 px-4 bg-slate-200 hover:bg-slate-300 text-slate-700 text-sm font-bold border border-slate-300 rounded-lg cursor-pointer transition">
            Exit
          </button>
        </div>
      </div>

      <!-- Printable Sheet -->
      <div class="max-w-4xl mx-auto border border-slate-300 bg-white p-6 sm:p-10 shadow-xl rounded-xl font-sans text-slate-900 paper-sheet text-left">
        <!-- Letterhead — Dynamic from dealer configuration -->
        <div class="border-b-2 border-slate-900 pb-5 text-left space-y-2 font-sans">
          <div class="flex flex-col sm:flex-row justify-between items-start gap-4">
            <div>
              <h1 class="text-xl sm:text-2xl font-bold text-slate-900 uppercase tracking-widest leading-none">{{ summary?.dealer?.businessName || 'DEALERCORE ENTERPRISE' }}</h1>
              <p class="text-xs font-bold text-slate-500 font-sans tracking-widest uppercase mt-1">AUTHORIZED WHOLESALE FMCG DISTRIBUTOR & LOGISTICS PARTNER</p>
              <p class="text-xs text-slate-500 font-sans mt-0.5 leading-relaxed">
                {{ summary?.dealer?.address || 'Business Address' }}
                <template v-if="summary?.dealer?.phoneNumber"> | Tel: {{ summary.dealer.phoneNumber }}</template>
                <template v-if="summary?.dealer?.gstNumber"> | GSTIN: {{ summary.dealer.gstNumber }}</template>
              </p>
            </div>
            <div class="text-left sm:text-right text-xs text-slate-500 space-y-0.5">
              <p class="font-bold text-slate-900 font-mono tracking-wide leading-none">DOCKET ID: DMS-{{ Math.floor(100000 + Math.random() * 900000) }}</p>
              <p>Processed On: {{ new Date().toLocaleDateString() }}</p>
              <p>Period: {{ printData.period }}</p>
            </div>
          </div>
        </div>

        <!-- Executive Report -->
        <div v-if="printData.type === 'EXECUTIVE'" class="mt-6 space-y-6 animate-fadeIn font-sans text-left">
          <div class="bg-slate-50 p-3 border border-slate-200 rounded-lg flex justify-between items-center text-left">
            <span class="text-sm font-bold text-slate-800 uppercase tracking-wider">Executive Summary</span>
            <span class="text-xs font-bold text-slate-600 bg-slate-200 px-3 py-1 rounded-md font-mono uppercase">Period: {{ printData.period }}</span>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-left">
            <div class="p-3 border border-slate-200 rounded-lg"><span class="text-xs uppercase font-bold text-slate-400">Revenue</span><p class="text-sm font-bold text-slate-900 font-mono mt-0.5">{{ formatCurrency(printData.payload.totals.revenue) }}</p></div>
            <div class="p-3 border border-slate-200 rounded-lg"><span class="text-xs uppercase font-bold text-slate-400">Cost</span><p class="text-sm font-bold text-slate-800 font-mono mt-0.5">{{ formatCurrency(printData.payload.totals.cogs) }}</p></div>
            <div class="p-3 border border-slate-200 rounded-lg"><span class="text-xs uppercase font-bold text-slate-400">Gross Margin</span><p class="text-sm font-bold text-emerald-800 font-mono mt-0.5">{{ formatCurrency(printData.payload.totals.grossProfit) }}</p></div>
            <div class="p-3 border border-slate-200 bg-rose-50/10 rounded-lg"><span class="text-xs uppercase font-bold text-rose-600">Pending Credit</span><p class="text-sm font-bold text-rose-600 font-mono mt-0.5">{{ formatCurrency(printData.payload.totals.pending) }}</p></div>
          </div>

          <div class="space-y-2 text-left">
            <h3 class="text-xs font-bold uppercase text-slate-800 tracking-wider">Rep Ledger</h3>
            <table class="w-full text-left text-sm border border-slate-300 rounded-lg overflow-hidden">
              <thead><tr class="bg-slate-100 border-b border-slate-300 font-mono font-bold text-xs uppercase text-slate-500"><th class="py-2 px-3">Name</th><th class="py-2 px-3 text-center">Role</th><th class="py-2 px-3 text-right">Sales</th><th class="py-2 px-3 text-right">Collected</th><th class="py-2 px-3 text-right text-rose-700">Pending</th><th class="py-2 px-3 text-center">Bills</th></tr></thead>
              <tbody class="divide-y divide-slate-100 font-medium">
                <tr v-for="(rep, rIdx) in printData.payload.reps" :key="rIdx"><td class="py-2 px-3 font-semibold text-slate-800">{{ rep.name }}</td><td class="py-2 px-3 text-center text-slate-500 font-mono text-xs">{{ rep.role || 'DSR' }}</td><td class="py-2 px-3 text-right font-mono">{{ formatCurrency(rep.totalSales) }}</td><td class="py-2 px-3 text-right font-mono text-emerald-700">{{ formatCurrency(rep.collected) }}</td><td :class="['py-2 px-3 text-right font-mono font-bold', rep.pending > 0 ? 'text-rose-600' : 'text-slate-400']">{{ formatCurrency(rep.pending) }}</td><td class="py-2 px-3 text-center font-mono">{{ rep.count }}</td></tr>
              </tbody>
            </table>
          </div>

          <div class="space-y-2 text-left">
            <h3 class="text-xs font-bold uppercase text-slate-800 tracking-wider">Vehicle Fleet</h3>
            <table class="w-full text-left text-sm border border-slate-300 rounded-lg overflow-hidden">
              <thead><tr class="bg-slate-100 border-b border-slate-300 font-mono font-bold text-xs uppercase text-slate-500"><th class="py-2 px-3">Plate</th><th class="py-2 px-3">Reps</th><th class="py-2 px-3 text-center">Stops</th><th class="py-2 px-3 text-right">Load Value</th><th class="py-2 px-3 text-right">Recovered</th><th class="py-2 px-3 text-right text-rose-700">Outstanding</th></tr></thead>
              <tbody class="divide-y divide-slate-100 font-medium">
                <tr v-for="vNode in printData.payload.vehicles" :key="vNode.vehicleNumber"><td class="py-2 px-3 font-mono font-bold">{{ vNode.vehicleNumber }}</td><td class="py-2 px-3 text-xs text-slate-500">{{ vNode.reps.join(', ') || 'Direct' }}</td><td class="py-2 px-3 text-center font-mono">{{ vNode.count }}</td><td class="py-2 px-3 text-right font-mono">{{ formatCurrency(vNode.totalSales) }}</td><td class="py-2 px-3 text-right font-mono text-emerald-700">{{ formatCurrency(vNode.collected) }}</td><td class="py-2 px-3 text-right font-mono font-bold text-rose-600">{{ formatCurrency(vNode.pending) }}</td></tr>
              </tbody>
            </table>
          </div>

          <div v-if="printData.payload.lowStock.length > 0" class="space-y-2 text-left">
            <h3 class="text-xs font-bold uppercase text-rose-600 tracking-wider">Low Stock Alerts</h3>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-2">
              <div v-for="lowProd in printData.payload.lowStock" :key="lowProd.id" class="p-2 border border-dashed border-rose-300 rounded-lg bg-rose-50/5 font-sans">
                <p class="font-bold text-slate-900 text-sm truncate leading-none">{{ lowProd.name }}</p>
                <div class="flex justify-between items-center text-xs text-slate-500 mt-2 font-sans"><span>Stock: <strong class="text-rose-600">{{ lowProd.stock }}</strong></span><span>Min: {{ lowProd.minStockAlert || 10 }}</span></div>
              </div>
            </div>
          </div>

          <!-- Customer-wise Due in Executive Report -->
          <div v-if="printData.payload.customers && printData.payload.customers.length > 0" class="space-y-2 text-left">
            <h3 class="text-xs font-bold uppercase text-slate-800 tracking-wider">Customer-wise Outstanding</h3>
            <table class="w-full text-left text-sm border border-slate-300 rounded-lg overflow-hidden">
              <thead><tr class="bg-slate-100 border-b border-slate-300 font-mono font-bold text-xs uppercase text-slate-500"><th class="py-2 px-3">Customer</th><th class="py-2 px-3 font-mono text-xs">Phone</th><th class="py-2 px-3 text-right">Billed</th><th class="py-2 px-3 text-right text-emerald-700">Paid</th><th class="py-2 px-3 text-right text-rose-700">Pending</th><th class="py-2 px-3 text-center">Invoices</th></tr></thead>
              <tbody class="divide-y divide-slate-100 font-medium">
                <tr v-for="cust in printData.payload.customers" :key="cust.name"><td class="py-2 px-3 font-semibold text-slate-800">{{ cust.name }}</td><td class="py-2 px-3 font-mono text-xs text-slate-500">{{ cust.phone || 'N/A' }}</td><td class="py-2 px-3 text-right font-mono">{{ formatCurrency(cust.totalBilled) }}</td><td class="py-2 px-3 text-right font-mono text-emerald-700">{{ formatCurrency(cust.totalPaid) }}</td><td :class="['py-2 px-3 text-right font-mono font-bold', cust.pending > 0 ? 'text-rose-600' : 'text-slate-400']">{{ formatCurrency(cust.pending) }}</td><td class="py-2 px-3 text-center font-mono">{{ cust.invoiceCount }}</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- DSR Statement -->
        <div v-if="printData.type === 'DSR_STATEMENT'" class="mt-6 space-y-6 animate-fadeIn text-left font-sans">
          <div class="border border-slate-200 rounded-lg p-4 bg-slate-50 grid grid-cols-1 md:grid-cols-3 gap-4 text-left">
            <div><span class="text-xs uppercase font-bold text-slate-400">Representative</span><h4 class="text-sm font-bold text-slate-900 mt-0.5">{{ printData.payload.rep.name }}</h4><p class="text-xs text-slate-500 mt-1 font-mono">{{ printData.payload.rep.phone || '--' }}</p></div>
            <div><span class="text-xs uppercase font-bold text-slate-400">Position</span><h4 class="text-sm font-bold text-slate-800 mt-0.5">{{ printData.payload.rep.role || 'DSR' }}</h4><p v-if="printData.payload.rep.role === 'Order Collector'" class="text-xs text-slate-500 mt-1">Supervisor: {{ printData.payload.rep.parentDsrName || 'Dealer' }}</p></div>
            <div><span class="text-xs uppercase font-bold text-rose-600 block">Pending Collection</span><h4 class="text-base font-bold text-rose-600 font-mono mt-0.5">{{ formatCurrency(printData.payload.rep.pending) }}</h4><p class="text-xs text-slate-400">of {{ formatCurrency(printData.payload.rep.totalSales) }} dispatched</p></div>
          </div>
          <div class="space-y-2 text-left">
            <h3 class="text-xs font-bold uppercase text-slate-800 tracking-wider">Client Invoices</h3>
            <table class="w-full text-left text-sm border border-slate-300 rounded-lg overflow-hidden">
              <thead><tr class="bg-slate-100 border-b border-slate-300 font-mono font-bold text-xs uppercase text-slate-500"><th class="py-2.5 px-3">Date</th><th class="py-2.5 px-3">Customer</th><th class="py-2.5 px-3">Product</th><th class="py-2.5 px-2 text-right">Invoice</th><th class="py-2.5 px-2 text-right">Paid</th><th class="py-2.5 px-2 text-right text-rose-700">Outstanding</th><th class="py-2.5 px-3 text-center">Signature</th></tr></thead>
              <tbody class="divide-y divide-slate-100 font-semibold">
                <tr v-for="sale in printData.payload.sales" :key="sale.id" class="align-top hover:bg-slate-50">
                  <td class="py-2.5 px-3 text-xs font-mono text-slate-400">{{ new Date(sale.date).toLocaleDateString() }}</td>
                  <td class="py-2.5 px-3"><p class="font-bold text-slate-800 leading-tight">{{ sale.customerName }}</p><p v-if="sale.customerPhone" class="text-xs text-slate-400 font-mono mt-0.5">{{ sale.customerPhone }}</p></td>
                  <td class="py-2.5 px-3"><p class="font-medium text-slate-700">{{ sale.productName }}</p><p class="text-xs text-slate-400 font-mono mt-0.5">Qty: {{ sale.quantity }} @ {{ formatCurrency(sale.sellingPrice) }}</p></td>
                  <td class="py-2.5 px-2 text-right font-mono">{{ formatCurrency(sale.totalAmount) }}</td>
                  <td class="py-2.5 px-2 text-right font-mono text-emerald-700">{{ formatCurrency(sale.amountPaid) }}</td>
                  <td class="py-2.5 px-2 text-right font-mono font-bold text-rose-600">{{ sale.isClosedWithDue ? 'WRITTEN_OFF' : formatCurrency(sale.totalAmount - sale.amountPaid) }}</td>
                  <td class="py-2.5 px-3 border-l border-slate-200"><div class="w-[100px] h-7 border border-dashed border-slate-300 rounded bg-slate-50/50" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Vehicle Trip Sheet -->
        <div v-if="printData.type === 'VEHICLE_TRIP'" class="mt-6 space-y-6 animate-fadeIn font-sans text-left">
          <div class="border border-slate-200 rounded-lg p-4 bg-slate-50 grid grid-cols-1 md:grid-cols-3 gap-4 text-left">
            <div><span class="text-xs uppercase font-bold text-slate-400 font-sans block">Vehicle</span><h4 class="text-sm font-bold text-slate-900 mt-0.5 font-mono uppercase">{{ printData.payload.vehicle.vehicleNumber }}</h4><p class="text-xs text-slate-500 mt-1 uppercase font-semibold tracking-wider">Route Trip Dispatch</p></div>
            <div><span class="text-xs uppercase font-bold text-slate-400 font-sans block">Assigned Reps</span><h4 class="text-sm font-bold text-slate-800 mt-0.5">{{ printData.payload.vehicle.reps.join(', ') || 'Direct' }}</h4><p class="text-xs text-slate-500 mt-1">{{ printData.payload.vehicle.count }} stops</p></div>
            <div><span class="text-xs uppercase font-bold text-slate-400 font-sans block">Load Value</span><h4 class="text-sm font-bold text-slate-900 mt-0.5 font-mono">{{ formatCurrency(printData.payload.vehicle.totalSales) }}</h4><p class="text-xs text-emerald-700 mt-1 font-bold">Recovered: {{ formatCurrency(printData.payload.vehicle.collected) }}</p></div>
          </div>
          <div class="space-y-2 text-left">
            <h3 class="text-xs font-bold uppercase text-slate-800 tracking-wider">Route Delivery Stops</h3>
            <table class="w-full text-left text-sm border border-slate-300 rounded-lg overflow-hidden">
              <thead><tr class="bg-slate-100 border-b border-slate-300 font-mono font-bold text-xs uppercase text-slate-500"><th class="py-2.5 px-2 text-center">#</th><th class="py-2.5 px-3">Outlet</th><th class="py-2.5 px-3">Product</th><th class="py-2.5 px-2.5 text-center">Invoice</th><th class="py-2.5 px-2.5 text-center">Paid</th><th class="py-2.5 px-2.5 text-center text-rose-600">Balance</th><th class="py-2.5 px-3 text-center">Cash Collected</th><th class="py-2.5 px-3 text-center">Stamp</th></tr></thead>
              <tbody class="divide-y divide-slate-100 font-semibold">
                <tr v-for="(rec, rIdx) in printData.payload.vehicle.records" :key="rec.id" class="align-top hover:bg-slate-50">
                  <td class="py-3 px-2 text-center font-mono text-slate-400">{{ Number(rIdx) + 1 }}</td>
                  <td class="py-3 px-3"><p class="font-bold text-slate-800 leading-tight">{{ rec.customerName }}</p><p v-if="rec.customerPhone" class="text-xs text-slate-400 font-mono mt-0.5">{{ rec.customerPhone }}</p></td>
                  <td class="py-3 px-3"><p class="font-semibold text-slate-700">{{ rec.productName }}</p><p class="text-xs text-slate-400 font-mono">Qty: {{ rec.quantity }} @ {{ formatCurrency(rec.sellingPrice) }}</p></td>
                  <td class="py-3 px-2.5 text-center font-mono">{{ formatCurrency(rec.totalAmount) }}</td>
                  <td class="py-3 px-2.5 text-center font-mono text-emerald-700">{{ formatCurrency(rec.amountPaid) }}</td>
                  <td class="py-3 px-2.5 text-center font-mono font-bold text-rose-600">{{ rec.isClosedWithDue ? 'WRITTEN_OFF' : formatCurrency(rec.totalAmount - rec.amountPaid) }}</td>
                  <td class="py-3 px-3 border-l border-r border-slate-200"><div class="w-[95px] h-7 border border-dashed border-slate-300 rounded bg-slate-50/20 flex items-center justify-center text-slate-300 font-mono">₹</div></td>
                  <td class="py-3 px-3"><div class="w-[85px] h-7 border border-dashed border-slate-300 rounded" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Customer-wise Due Statement -->
        <div v-if="printData.type === 'CUSTOMER_DUE'" class="mt-6 space-y-6 animate-fadeIn font-sans text-left">
          <div class="bg-slate-50 p-3 border border-slate-200 rounded-lg flex justify-between items-center text-left">
            <span class="text-sm font-bold text-slate-800 uppercase tracking-wider">Customer-wise Outstanding Statement</span>
            <span class="text-xs font-bold text-slate-600 bg-slate-200 px-3 py-1 rounded-md font-mono uppercase">Period: {{ printData.period }}</span>
          </div>

          <div v-for="cust in printData.payload.customers" :key="cust.name" class="space-y-3 text-left border border-slate-200 rounded-lg p-4">
            <div class="flex justify-between items-start border-b border-slate-100 pb-2">
              <div>
                <h4 class="font-bold text-slate-900 text-sm">{{ cust.name }}</h4>
                <p class="text-xs text-slate-400 font-mono">{{ cust.phone || 'N/A' }}</p>
              </div>
              <div class="text-right">
                <span class="text-xs text-slate-400 uppercase font-bold">Pending</span>
                <p class="text-sm font-bold text-rose-600 font-mono">{{ formatCurrency(cust.pending) }}</p>
              </div>
            </div>
            <table class="w-full text-left text-xs border border-slate-200 rounded overflow-hidden">
              <thead><tr class="bg-slate-50 border-b border-slate-200 font-mono font-bold text-[10px] uppercase text-slate-500"><th class="py-2 px-2">Date</th><th class="py-2 px-2">Product</th><th class="py-2 px-2 text-center">Billed</th><th class="py-2 px-2 text-center">Paid</th><th class="py-2 px-2 text-center text-rose-700">Balance</th><th class="py-2 px-2 text-center">Status</th></tr></thead>
              <tbody class="divide-y divide-slate-100 font-medium">
                <tr v-for="r in cust.records" :key="r.id">
                  <td class="py-1.5 px-2 font-mono text-slate-400">{{ new Date(r.date).toLocaleDateString() }}</td>
                  <td class="py-1.5 px-2">{{ r.productName }} (x{{ r.quantity }})</td>
                  <td class="py-1.5 px-2 text-center font-mono">{{ formatCurrency(r.totalAmount) }}</td>
                  <td class="py-1.5 px-2 text-center font-mono text-emerald-700">{{ formatCurrency(r.amountPaid) }}</td>
                  <td class="py-1.5 px-2 text-center font-mono font-bold text-rose-600">{{ r.isClosedWithDue ? 'WRITTEN_OFF' : formatCurrency(r.totalAmount - r.amountPaid) }}</td>
                  <td class="py-1.5 px-2 text-center"><span v-if="r.isClosedWithDue" class="text-amber-600">Written Off</span><span v-else-if="r.totalAmount - r.amountPaid > 0" class="text-rose-600">Pending</span><span v-else class="text-emerald-600">Paid</span></td>
                </tr>
              </tbody>
            </table>
            <div class="flex justify-between text-xs text-slate-400">
              <span>Total Billed: {{ formatCurrency(cust.totalBilled) }}</span>
              <span>Paid: {{ formatCurrency(cust.totalPaid) }}</span>
              <span v-if="cust.writtenOff > 0" class="text-amber-600">Written Off: {{ formatCurrency(cust.writtenOff) }}</span>
            </div>
          </div>

          <div v-if="printData.payload.customers.length === 0" class="text-center py-8 text-slate-400 text-sm font-semibold">
            No customers with outstanding dues in this period
          </div>
        </div>

        <!-- Footer Signatures — Dynamic dealer info -->
        <div class="mt-8 pt-8 border-t border-slate-300 grid grid-cols-2 md:grid-cols-3 gap-6 text-xs text-slate-600 font-sans text-left">
          <div class="space-y-4"><p class="font-bold text-slate-800 block">DSR Signature:</p><div class="h-10 border-b border-dashed border-slate-300 w-full" /><p class="text-xs text-slate-400 font-mono">Representative Sign</p></div>
          <div class="space-y-4"><p class="font-bold text-slate-800 block">Verification:</p><div class="h-10 border-b border-dashed border-slate-300 w-full" /><p class="text-xs text-slate-400 font-mono">Supervisor Signoff</p></div>
          <div class="space-y-4 col-span-2 md:col-span-1"><p class="font-bold text-slate-800 block">For {{ summary?.dealer?.businessName || 'the Enterprise' }}:</p><div class="h-10 border-b border-dashed border-slate-300 w-full" /><p class="text-xs text-slate-400 font-bold tracking-wider uppercase font-mono">Authorized Signatory</p></div>
        </div>

        <div class="mt-10 border-t border-slate-200 pt-4 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-400 font-mono text-center sm:text-left gap-2 leading-none">
          <span>This document is an automated DMS generation and is verified by regional management.</span>
          <span>Hash: {{ Math.random().toString(36).substr(2, 9).toUpperCase() }}</span>
        </div>
      </div>
    </div>
    </div><!-- end dashboard-middle -->

    <!-- ═══════════════════════════════════════════════════════════
         RIGHT COLUMN — Charts Sidebar
         ═══════════════════════════════════════════════════════════ -->
    <aside class="dashboard-charts">
      <!-- Financial Comparison Bar -->
      <ChartCard title="Financial Comparison" subtitle="Revenue, cost, profit & pending">
        <div style="height: 220px">
          <BaseChart chartType="bar" :chartData="financialComparisonData" :chartOptions="financialComparisonOptions" />
        </div>
      </ChartCard>
      
      <!-- Revenue Trend Line -->
      <ChartCard title="Revenue Trend" subtitle="Daily revenue over period">
        <div style="height: 200px">
          <BaseChart chartType="line" :chartData="revenueTrendData" :chartOptions="revenueTrendOptions" />
        </div>
      </ChartCard>
      
      <!-- Payment Doughnut -->
      <ChartCard title="Payment Mix" subtitle="Cash vs Credit">
        <div style="height: 200px">
          <BaseChart chartType="doughnut" :chartData="paymentPieData" :chartOptions="paymentPieOptions" />
        </div>
      </ChartCard>

      <!-- DSR Performance Horizontal Bar -->
      <ChartCard title="Rep Performance" subtitle="Collected vs Pending">
        <div style="height: 200px">
          <BaseChart chartType="bar" :chartData="dsrBarData" :chartOptions="dsrBarOptions" />
        </div>
      </ChartCard>
    </aside>

    <!-- ========== ADD REP MODAL ========== -->
    <AddRepModal
      :is-open="showAddRepModal"
      :dsrs="dsrs"
      @close="showAddRepModal = false"
      @added="emit('refreshData')"
    />

    <!-- ========== INVITATION LIST (Toggle) ========== -->
    <div v-if="showInvitationList && canManageDsrs" class="mt-4">
      <InvitationList @refresh="emit('refreshData')" />
    </div>
  </div>
</template>

<style scoped>
/* 3-column dashboard layout */
.dashboard-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100%;
}

@media (min-width: 1280px) {
  .dashboard-layout {
    flex-direction: row;
    gap: 24px;
  }
}

.dashboard-middle {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dashboard-charts {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex-shrink: 0;
}

@media (min-width: 1280px) {
  .dashboard-charts {
    width: 380px;
    min-width: 380px;
    max-height: calc(100vh - var(--dc-header-h, 88px) - var(--dc-footer-h, 36px) - 48px);
    overflow-y: auto;
    position: sticky;
    top: 24px;
    align-self: flex-start;
  }

  .dashboard-charts::-webkit-scrollbar {
    width: 4px;
  }
  .dashboard-charts::-webkit-scrollbar-track {
    background: transparent;
  }
  .dashboard-charts::-webkit-scrollbar-thumb {
    background: #e2e8f0;
    border-radius: 999px;
  }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fadeIn {
  animation: fadeIn 0.5s ease-out;
}
</style>
