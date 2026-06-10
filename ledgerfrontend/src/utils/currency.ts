export interface CurrencyInfo {
  code: string;
  symbol: string;
  name: string;
  rateToUsd: number;
}

export const CURRENCIES: CurrencyInfo[] = [
  { code: 'USD', symbol: '$', name: 'US Dollar', rateToUsd: 1.0 },
  { code: 'EUR', symbol: '€', name: 'Euro', rateToUsd: 1.08 },
  { code: 'GBP', symbol: '£', name: 'British Pound', rateToUsd: 1.27 },
  { code: 'INR', symbol: '₹', name: 'Indian Rupee', rateToUsd: 0.012 },
  { code: 'JPY', symbol: '¥', name: 'Japanese Yen', rateToUsd: 0.0064 },
  { code: 'AUD', symbol: 'A$', name: 'Australian Dollar', rateToUsd: 0.66 },
  { code: 'CAD', symbol: 'C$', name: 'Canadian Dollar', rateToUsd: 0.73 },
  { code: 'CNY', symbol: '¥', name: 'Chinese Yuan', rateToUsd: 0.14 },
  { code: 'CHF', symbol: 'CHF', name: 'Swiss Franc', rateToUsd: 1.10 }
];

export const getCurrencySymbol = (code: string): string => {
  const currency = CURRENCIES.find(c => c.code === code);
  return currency ? currency.symbol : '$';
};

export const convertCurrency = (
  amount: number,
  fromCode: string,
  toCode: string
): number => {
  const fromCurrency = CURRENCIES.find(c => c.code === fromCode);
  const toCurrency = CURRENCIES.find(c => c.code === toCode);
  
  if (!fromCurrency || !toCurrency) return amount;
  
  // Convert from original currency to USD base
  const amountInUsd = amount * fromCurrency.rateToUsd;
  // Convert from USD base to target currency
  const convertedAmount = amountInUsd / toCurrency.rateToUsd;
  
  return parseFloat(convertedAmount.toFixed(4));
};
