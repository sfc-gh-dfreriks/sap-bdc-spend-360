const BASE = '/api';

function buildParams(categories: string[], companies: string[]): string {
  const params = new URLSearchParams();
  if (categories.length) params.set('categories', categories.join(','));
  if (companies.length) params.set('companies', companies.join(','));
  return params.toString();
}

function camelizeKey(key: string): string {
  return key.replace(/_([a-z0-9])/g, (_, c) => c.toUpperCase());
}
function camelizeKeys(obj: any): any {
  if (Array.isArray(obj)) return obj.map(camelizeKeys);
  if (obj !== null && typeof obj === 'object') {
    const out: any = {};
    for (const [k, v] of Object.entries(obj)) out[camelizeKey(k)] = camelizeKeys(v);
    return out;
  }
  return obj;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return camelizeKeys(await res.json()) as T;
}

export function fetchFilters(): Promise<{ categories: string[]; companies: string[] }> {
  return get('/filters');
}

const q = (c: string[], co: string[]) => buildParams(c, co);
export const fetchOverview = (c: string[], co: string[]) => get<any>(`/overview?${q(c, co)}`);
export const fetchCategories = (c: string[], co: string[]) => get<any>(`/categories?${q(c, co)}`);
export const fetchSuppliers = (c: string[], co: string[]) => get<any>(`/suppliers?${q(c, co)}`);
export const fetchContracts = (c: string[], co: string[]) => get<any>(`/contracts?${q(c, co)}`);
export const fetchPurchaseOrders = (c: string[], co: string[]) => get<any>(`/purchase-orders?${q(c, co)}`);
export const fetchLineage = () => get<any>(`/lineage`);
export const fetchSupplierRisk = () => get<any>(`/supplier-risk`);
export const fetchSustainability = () => get<any>(`/sustainability`);
export const fetchSavings = () => get<any>(`/savings`);

export async function fetchAnalyst(messages: { role: string; content: string }[]) {
  const res = await fetch(`${BASE}/analyst`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
