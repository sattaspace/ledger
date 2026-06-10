export interface Brand {
  id: string;
  name: string;
}

export interface Category {
  id: string;
  name: string;
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  brand: string;
  category: string;
  stock: number;
  minStockAlert: number;
  unitPrice: number; // Cost Price
  sellingPrice: number;
  location: string;
}

export interface RestockRecord {
  id: string;
  productId: string;
  productName: string;
  quantity: number;
  supplierName: string;
  costPrice: number;
  totalCost: number;
  date: string;
  receivedBy: string;
}

export interface CreditPayment {
  id: string;
  amount: number;
  date: string;
  receivedBy: string;
}

export interface SaleReturn {
  id: string;
  saleId: string;
  productName: string;
  quantity: number;
  returnAmount: number;
  reason: string;
  processedBy: string;
  date: string;
}

export interface SaleRecord {
  id: string;
  productId: string;
  productName: string;
  quantity: number;
  customerName: string;
  customerPhone: string;
  isVehicle: boolean;
  vehicleNumber?: string;
  dsrId?: string;
  dsrName?: string;
  originalDsrId?: string;
  originalDsrName?: string;
  sellingPrice: number;
  totalAmount: number;
  returnTotalAmount: number;
  netAmount: number;
  balanceDue: number;
  paymentType: "Cash" | "Credit";
  amountPaid: number;
  collectionStatus:
    | "Fully Paid"
    | "Pending"
    | "Partial"
    | "Written Off"
    | "Voided";
  dueDate?: string;
  date: string;
  payments: CreditPayment[];
  isClosedWithDue?: boolean;
  isVoided?: boolean;
  returns?: SaleReturn[];
}

export interface DSR {
  id: string;
  name: string;
  phone: string;
  activeSalesCount: number;
  role?: "DSR" | "Order Collector";
  parentDsrId?: string;
  parentDsrName?: string;
}

export interface Supplier {
  id: string;
  name: string;
  phone: string;
  category: string;
}

export interface DealerConfig {
  username: string; // unique identifier
  fullName: string;
  role: string;
  businessName: string;
  address: string;
  phoneNumber: string;
  email: string;
  gstNumber: string;
  googleMapUrl: string;
  communicationNumber: string;
  defaultCurrency: string; // e.g. "INR", "USD", "EUR", "GBP", "AED"
  defaultLocale: string; // e.g. "en-IN", "en-US", "de-DE", "en-GB", "ar-AE"
}

export interface DatabaseSchema {
  products: Product[];
  restocks: RestockRecord[];
  sales: SaleRecord[];
  dsrs: DSR[];
  suppliers: Supplier[];
  dealers?: DealerConfig[];
  brands?: Brand[];
  categories?: Category[];
}

// ─── Due Report Types ──────────────────────────────────────

export interface CustomerDueSale {
  saleId: string;
  productName: string;
  quantity: number;
  totalAmount: number;
  returnTotalAmount: number;
  netAmount: number;
  amountPaid: number;
  balanceDue: number;
  collectionStatus: string;
  dueDate?: string;
  date: string;
  dsrName: string;
  originalDsrName: string;
}

export interface CustomerDueRow {
  customerName: string;
  customerPhone: string;
  totalSales: number;
  totalPaid: number;
  totalReturns: number;
  totalDue: number;
  saleCount: number;
  sales: CustomerDueSale[];
}

export interface VehicleDueSale {
  saleId: string;
  customerName: string;
  productName: string;
  quantity: number;
  totalAmount: number;
  returnTotalAmount: number;
  netAmount: number;
  amountPaid: number;
  balanceDue: number;
  collectionStatus: string;
  dueDate?: string;
  date: string;
  dsrName: string;
  originalDsrName: string;
}

export interface VehicleDueRow {
  vehicleNumber: string;
  totalSales: number;
  totalPaid: number;
  totalReturns: number;
  totalDue: number;
  saleCount: number;
  sales: VehicleDueSale[];
}

export interface DsrDueSale {
  saleId: string;
  customerName: string;
  productName: string;
  quantity: number;
  totalAmount: number;
  returnTotalAmount: number;
  netAmount: number;
  amountPaid: number;
  balanceDue: number;
  collectionStatus: string;
  dueDate?: string;
  date: string;
  originalDsrName: string;
}

export interface DsrDueRow {
  dsrId?: string;
  dsrName: string;
  role: string;
  totalSales: number;
  totalPaid: number;
  totalReturns: number;
  totalDue: number;
  saleCount: number;
  sales: DsrDueSale[];
}

export interface DueReport {
  dealer?: {
    businessName: string;
    address: string;
    phoneNumber: string;
    email: string;
    gstNumber: string;
    defaultCurrency: string;
  };
  generatedAt: string;
  reportType: "customer" | "vehicle" | "dsr";
  totalOutstanding: number;
  rows: CustomerDueRow[] | VehicleDueRow[] | DsrDueRow[];
}
