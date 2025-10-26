/**
 * Currency Utilities Tests
 * Story 3.4 - Task 4: Unit and Integration Tests
 */

import { describe, it, expect } from 'vitest';
import {
  formatCurrency,
  formatCurrencyCompact,
  parseCurrency,
  convertCurrency,
  getCurrencySymbol,
  formatPercentage,
  calculatePercentage,
  isValidCurrency,
  getCurrencyLocale,
} from '@/lib/currencyUtils';

describe('Currency Utilities', () => {
  describe('formatCurrency', () => {
    it('formats USD correctly with symbol', () => {
      expect(formatCurrency(1234.56, 'USD')).toMatch(/\$1,234\.56/);
    });

    it('formats EUR correctly with symbol', () => {
      const result = formatCurrency(1234.56, 'EUR');
      expect(result).toContain('€');
      expect(result).toMatch(/1[.,]234[.,]56/);
    });

    it('formats GBP correctly with symbol', () => {
      expect(formatCurrency(1234.56, 'GBP')).toMatch(/£1,234\.56/);
    });

    it('handles JPY with zero decimals', () => {
      const result = formatCurrency(1234, 'JPY');
      expect(result).toMatch(/[¥￥]1[.,]234/);
      expect(result).not.toMatch(/\.\d{2}/);
    });

    it('accepts string amounts', () => {
      expect(formatCurrency('1234.56', 'USD')).toMatch(/\$1,234\.56/);
    });

    it('handles number amounts', () => {
      expect(formatCurrency(1234.56, 'USD')).toMatch(/\$1,234\.56/);
    });

    it('handles invalid amounts gracefully', () => {
      const result = formatCurrency('invalid', 'USD');
      expect(result).toMatch(/\$.*0/);
    });

    it('uses EUR as default currency', () => {
      expect(formatCurrency(1000)).toMatch(/€/);
    });

    it('formats large amounts with thousand separators', () => {
      const result = formatCurrency(1234567.89, 'USD');
      expect(result).toMatch(/1,234,567\.89/);
    });

    it('handles zero amounts', () => {
      expect(formatCurrency(0, 'USD')).toMatch(/\$0\.00/);
    });

    it('handles negative amounts', () => {
      const result = formatCurrency(-500, 'USD');
      expect(result).toMatch(/-?\$500\.00/);
    });

    it('respects custom decimal places', () => {
      const result = formatCurrency(1234.5678, 'USD', { decimals: 3 });
      expect(result).toMatch(/1,234\.568/);
    });

    it('can hide currency symbol', () => {
      const result = formatCurrency(1234.56, 'USD', { showSymbol: false });
      expect(result).not.toMatch(/\$/);
      expect(result).toMatch(/1,234\.56/);
    });
  });

  describe('formatCurrencyCompact', () => {
    it('formats thousands with K notation', () => {
      const result = formatCurrencyCompact(1500, 'USD');
      expect(result).toMatch(/\$1\.5K/);
    });

    it('formats millions with M notation', () => {
      const result = formatCurrencyCompact(1500000, 'USD');
      expect(result).toMatch(/\$1\.5M/);
    });

    it('formats small amounts normally', () => {
      const result = formatCurrencyCompact(500, 'USD');
      expect(result).toMatch(/\$500/);
    });

    it('handles string amounts', () => {
      const result = formatCurrencyCompact('1500', 'USD');
      expect(result).toMatch(/\$1\.5K/);
    });

    it('handles invalid amounts gracefully', () => {
      const result = formatCurrencyCompact('invalid', 'USD');
      expect(result).toMatch(/\$/);
    });
  });

  describe('parseCurrency', () => {
    it('parses USD formatted string', () => {
      expect(parseCurrency('$1,234.56')).toBe(1234.56);
    });

    it('parses EUR formatted string', () => {
      expect(parseCurrency('€1,234.56')).toBe(1234.56);
    });

    it('parses negative amounts', () => {
      expect(parseCurrency('-$500.00')).toBe(-500);
    });

    it('handles strings without currency symbols', () => {
      expect(parseCurrency('1,234.56')).toBe(1234.56);
    });

    it('removes spaces', () => {
      expect(parseCurrency('$ 1,234.56')).toBe(1234.56);
    });
  });

  describe('convertCurrency', () => {
    it('returns same amount when currencies are identical', () => {
      expect(convertCurrency(100, 'USD', 'USD')).toBe(100);
    });

    it('converts using provided exchange rates', () => {
      const rates = { USD_EUR: 0.85 };
      expect(convertCurrency(100, 'USD', 'EUR', rates)).toBe(85);
    });

    it('returns original amount when no exchange rate available', () => {
      expect(convertCurrency(100, 'USD', 'EUR')).toBe(100);
    });

    it('handles multiple currency conversions', () => {
      const rates = {
        USD_EUR: 0.85,
        EUR_GBP: 0.88,
      };
      expect(convertCurrency(100, 'USD', 'EUR', rates)).toBe(85);
      expect(convertCurrency(100, 'EUR', 'GBP', rates)).toBe(88);
    });
  });

  describe('getCurrencySymbol', () => {
    it('returns correct symbol for USD', () => {
      expect(getCurrencySymbol('USD')).toBe('$');
    });

    it('returns correct symbol for EUR', () => {
      expect(getCurrencySymbol('EUR')).toBe('€');
    });

    it('returns correct symbol for GBP', () => {
      expect(getCurrencySymbol('GBP')).toBe('£');
    });

    it('returns correct symbol for JPY', () => {
      expect(getCurrencySymbol('JPY')).toBe('¥');
    });

    it('returns currency code for unknown currencies', () => {
      expect(getCurrencySymbol('XYZ')).toBe('XYZ');
    });
  });

  describe('formatPercentage', () => {
    it('formats percentage with default 1 decimal', () => {
      expect(formatPercentage(85.5)).toBe('85.5%');
    });

    it('formats percentage with custom decimals', () => {
      expect(formatPercentage(85.567, 2)).toBe('85.57%');
    });

    it('formats whole numbers', () => {
      expect(formatPercentage(100)).toBe('100.0%');
    });

    it('handles zero', () => {
      expect(formatPercentage(0)).toBe('0.0%');
    });

    it('formats with zero decimals', () => {
      expect(formatPercentage(85.5, 0)).toBe('86%');
    });
  });

  describe('calculatePercentage', () => {
    it('calculates percentage correctly', () => {
      expect(calculatePercentage(50, 100)).toBe(50);
    });

    it('calculates percentage with decimals', () => {
      expect(calculatePercentage(75, 200)).toBe(37.5);
    });

    it('handles zero total gracefully', () => {
      expect(calculatePercentage(50, 0)).toBe(0);
    });

    it('handles zero amount', () => {
      expect(calculatePercentage(0, 100)).toBe(0);
    });

    it('handles amounts larger than total', () => {
      expect(calculatePercentage(150, 100)).toBe(150);
    });

    it('calculates small percentages accurately', () => {
      const result = calculatePercentage(1, 1000);
      expect(result).toBeCloseTo(0.1, 2);
    });
  });

  describe('isValidCurrency', () => {
    it('returns true for supported currencies', () => {
      expect(isValidCurrency('USD')).toBe(true);
      expect(isValidCurrency('EUR')).toBe(true);
      expect(isValidCurrency('GBP')).toBe(true);
      expect(isValidCurrency('JPY')).toBe(true);
    });

    it('returns false for unsupported currencies', () => {
      expect(isValidCurrency('XYZ')).toBe(false);
      expect(isValidCurrency('INVALID')).toBe(false);
    });

    it('is case-sensitive', () => {
      expect(isValidCurrency('usd')).toBe(false);
      expect(isValidCurrency('USD')).toBe(true);
    });
  });

  describe('getCurrencyLocale', () => {
    it('returns correct locale for USD', () => {
      expect(getCurrencyLocale('USD')).toBe('en-US');
    });

    it('returns correct locale for EUR', () => {
      expect(getCurrencyLocale('EUR')).toBe('de-DE');
    });

    it('returns correct locale for GBP', () => {
      expect(getCurrencyLocale('GBP')).toBe('en-GB');
    });

    it('returns default locale for unknown currency', () => {
      expect(getCurrencyLocale('XYZ')).toBe('en-US');
    });
  });

  describe('Precision and Rounding', () => {
    it('handles floating point precision correctly', () => {
      const result = formatCurrency(0.1 + 0.2, 'USD');
      expect(result).toMatch(/\$0\.30/);
    });

    it('rounds correctly for display', () => {
      const result = formatCurrency(1.235, 'USD');
      expect(result).toMatch(/\$1\.2[34]/); // May round to .23 or .24 depending on locale
    });
  });

  describe('Integration', () => {
    it('formats, parses, and maintains value accuracy', () => {
      const original = 1234.56;
      const formatted = formatCurrency(original, 'USD');
      const parsed = parseCurrency(formatted);
      expect(parsed).toBe(original);
    });

    it('calculates and formats percentage correctly', () => {
      const percentage = calculatePercentage(450, 500);
      const formatted = formatPercentage(percentage);
      expect(formatted).toBe('90.0%');
    });
  });
});
