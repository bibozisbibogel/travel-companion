/**
 * Currency formatting utilities
 * Story 3.4 - Task 3: Currency Formatting and Display
 */

/**
 * Currency symbol mapping for common currencies
 */
export const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
  CNY: '¥',
  AUD: 'A$',
  CAD: 'C$',
  CHF: 'CHF',
  INR: '₹',
  MXN: 'Mex$',
  BRL: 'R$',
};

/**
 * Locale mapping for currency formatting
 */
export const CURRENCY_LOCALES: Record<string, string> = {
  USD: 'en-US',
  EUR: 'de-DE',
  GBP: 'en-GB',
  JPY: 'ja-JP',
  CNY: 'zh-CN',
  AUD: 'en-AU',
  CAD: 'en-CA',
  CHF: 'de-CH',
  INR: 'en-IN',
  MXN: 'es-MX',
  BRL: 'pt-BR',
};

/**
 * Decimal precision for different currencies
 * Most currencies use 2 decimals, but some (like JPY) use 0
 */
export const CURRENCY_DECIMALS: Record<string, number> = {
  USD: 2,
  EUR: 2,
  GBP: 2,
  JPY: 0,
  CNY: 2,
  AUD: 2,
  CAD: 2,
  CHF: 2,
  INR: 2,
  MXN: 2,
  BRL: 2,
};

/**
 * Format currency amount with proper symbols, separators, and precision
 * @param amount - The amount to format (string or number)
 * @param currency - ISO currency code (e.g., 'USD', 'EUR')
 * @param options - Optional formatting options
 */
export function formatCurrency(
  amount: string | number,
  currency: string = 'EUR',
  options?: {
    showSymbol?: boolean;
    decimals?: number;
    locale?: string;
  }
): string {
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;

  if (isNaN(numAmount)) {
    return `${CURRENCY_SYMBOLS[currency] || currency} 0.00`;
  }

  const locale = options?.locale || CURRENCY_LOCALES[currency] || 'en-US';
  const decimals = options?.decimals ?? CURRENCY_DECIMALS[currency] ?? 2;
  const showSymbol = options?.showSymbol !== false;

  return new Intl.NumberFormat(locale, {
    style: showSymbol ? 'currency' : 'decimal',
    currency: currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(numAmount);
}

/**
 * Format currency with compact notation for large amounts
 * Example: 1500 -> $1.5K, 1000000 -> $1M
 */
export function formatCurrencyCompact(
  amount: string | number,
  currency: string = 'EUR'
): string {
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;

  if (isNaN(numAmount)) {
    return `${CURRENCY_SYMBOLS[currency] || currency} 0`;
  }

  const locale = CURRENCY_LOCALES[currency] || 'en-US';

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency,
    notation: 'compact',
    compactDisplay: 'short',
  }).format(numAmount);
}

/**
 * Parse formatted currency string back to number
 */
export function parseCurrency(formattedAmount: string): number {
  // Remove currency symbols, spaces, and commas
  const cleaned = formattedAmount.replace(/[^\d.-]/g, '');
  return parseFloat(cleaned);
}

/**
 * Convert amount from one currency to another
 * Note: This is a placeholder. In production, use real-time exchange rates from backend
 */
export function convertCurrency(
  amount: number,
  fromCurrency: string,
  toCurrency: string,
  exchangeRates?: Record<string, number>
): number {
  // If currencies are the same, no conversion needed
  if (fromCurrency === toCurrency) {
    return amount;
  }

  // If exchange rates provided, use them
  if (exchangeRates) {
    const rate = exchangeRates[`${fromCurrency}_${toCurrency}`];
    if (rate) {
      return amount * rate;
    }
  }

  // Placeholder: Return original amount if no exchange rate available
  console.warn(
    `Exchange rate not available for ${fromCurrency} to ${toCurrency}`
  );
  return amount;
}

/**
 * Get currency symbol for a given currency code
 */
export function getCurrencySymbol(currency: string): string {
  return CURRENCY_SYMBOLS[currency] || currency;
}

/**
 * Format percentage with consistent precision
 */
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`;
}

/**
 * Calculate percentage of amount relative to total
 */
export function calculatePercentage(amount: number, total: number): number {
  if (total === 0) return 0;
  return (amount / total) * 100;
}

/**
 * Validate currency code
 */
export function isValidCurrency(currency: string): boolean {
  return currency in CURRENCY_SYMBOLS;
}

/**
 * Get locale for currency formatting
 */
export function getCurrencyLocale(currency: string): string {
  return CURRENCY_LOCALES[currency] || 'en-US';
}
