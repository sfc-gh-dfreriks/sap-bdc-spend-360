import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDollar(value: number | null): string {
  if (value == null) return '$0';
  const v = Math.abs(value);
  if (v >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

export function formatPct(value: number | null): string {
  if (value == null) return '0%';
  return value.toFixed(1) + '%';
}

export function formatNumber(value: number | null): string {
  if (value == null) return '0';
  return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
}
