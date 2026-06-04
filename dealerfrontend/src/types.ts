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
  sellingPrice: number;
  totalAmount: number;
  paymentType: 'Cash' | 'Credit';
  amountPaid: number;
  collectionStatus: 'Fully Paid' | 'Pending' | 'Partial';
  dueDate?: string;
  date: string;
  payments: CreditPayment[];
  isClosedWithDue?: boolean;
}

export interface DSR {
  id: string;
  name: string;
  phone: string;
  activeSalesCount: number;
  role?: 'DSR' | 'Order Collector';
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
}
