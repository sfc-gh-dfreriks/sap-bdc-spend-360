import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { currencySymbol } from './currency';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Money in the active reporting currency (name kept for existing call sites). */
export function formatDollar(value: number | null): string {
  const sym = currencySymbol();
  if (value == null) return `${sym}0`;
  const v = Math.abs(value);
  if (v >= 1e9) return `${sym}${(value / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${sym}${(value / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${sym}${(value / 1e3).toFixed(0)}K`;
  return `${sym}${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

export function formatPct(value: number | null): string {
  if (value == null) return '0%';
  return value.toFixed(1) + '%';
}

export function formatNumber(value: number | null): string {
  if (value == null) return '0';
  return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
}
