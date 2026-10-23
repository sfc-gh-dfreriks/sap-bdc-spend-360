// Data access layer. Two modes:
//   - Live (default): fetch from the Express server at /api/*
//   - Static (VITE_STATIC=1): read pre-baked JSON snapshots from <base>/data/*
//     and route the Cortex agent to VITE_AGENT_URL (a serverless function).
const STATIC = import.meta.env.VITE_STATIC === '1';
const AGENT_BASE = (import.meta.env.VITE_AGENT_URL ?? '').replace(/\/$/, '');
const DATA_BASE = `${import.meta.env.BASE_URL}data`;
const BASE = '/api';
import { getCurrency } from './currency';

function buildParams(categories: string[], companies: string[]): string {
  const params = new URLSearchParams();
  if (categories.length) params.set('categories', categories.join(','));
  if (companies.length) params.set('companies', companies.join(','));
  params.set('currency', getCurrency());
  return params.toString();
}

/** Canonical snapshot key — MUST match makeKey() in scripts/export-static.mjs.
 *  Categories are baked only as "all" or a single value, so multi-category
 *  selections normalize to "all categories" (company filtering stays exact). */
function filterKey(categories: string[], companies: string[]): string {
  const cat = categories.length === 1 ? categories[0] : '';
  return `${cat}||${[...companies].sort().join(',')}`;
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

async function liveGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return camelizeKeys(await res.json()) as T;
}

const fileCache = new Map<string, Promise<any>>();
function loadStaticFile(file: string): Promise<any> {
  let p = fileCache.get(file);
  if (!p) {
    p = fetch(`${DATA_BASE}/${file}.json`).then((res) => {
      if (!res.ok) throw new Error(`Static data error: ${res.status} ${file}`);
      return res.json();
    });
    fileCache.set(file, p);
  }
  return p;
}

// Money-bearing snapshots are baked once per currency under data/<CCY>/.
const ccyFile = (name: string) => `${getCurrency()}/${name}`;

async function getKeyed<T>(name: string, c: string[], co: string[]): Promise<T> {
  if (STATIC) {
    const map = await loadStaticFile(ccyFile(name));
    return camelizeKeys(map[filterKey(c, co)] ?? {}) as T;
  }
  return liveGet<T>(`/${name}?${buildParams(c, co)}`);
}
async function getSingle<T>(name: string, perCurrency = true): Promise<T> {
  if (STATIC) return camelizeKeys(await loadStaticFile(perCurrency ? ccyFile(name) : name)) as T;
  return liveGet<T>(`/${name}${perCurrency ? `?currency=${getCurrency()}` : ''}`);
}

export function fetchFilters(): Promise<{ categories: string[]; companies: string[] }> {
  if (STATIC) return loadStaticFile('filters');
  return liveGet('/filters');
}

export const fetchOverview = (c: string[], co: string[]) => getKeyed<any>('overview', c, co);
export const fetchCategories = (c: string[], co: string[]) => getKeyed<any>('categories', c, co);
export const fetchSuppliers = (c: string[], co: string[]) => getKeyed<any>('suppliers', c, co);
export const fetchContracts = (c: string[], co: string[]) => getKeyed<any>('contracts', c, co);
export const fetchPurchaseOrders = (c: string[], co: string[]) => getKeyed<any>('purchase-orders', c, co);
export const fetchLineage = () => getSingle<any>('lineage', false);
export const fetchSupplierRisk = () => getSingle<any>('supplier-risk');
export const fetchSustainability = () => getSingle<any>('sustainability');
export const fetchSavings = () => getSingle<any>('savings');

export async function fetchAnalyst(messages: { role: string; content: string }[]) {
  const base = STATIC ? AGENT_BASE : BASE;
  const res = await fetch(`${base}/analyst`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function runAnalystSql(sql: string) {
  const base = STATIC ? AGENT_BASE : BASE;
  const res = await fetch(`${base}/analyst/run-sql`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sql }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── Ask Cortex ──────────────────────────────────────────────────────────────
// Live: POST starts a background job, then poll until done.
// Static: answers for each topic's default question are baked at export time
// (data/ask_cortex.json, keyed by askKey); free-text questions are routed to the
// agent endpoint when one is configured, else a graceful message.
export interface AskCortexRequest {
  topic: string;
  args?: Record<string, string>;
  question?: string;
}

/** MUST match askKey() in scripts/export-static.mjs. */
export function askKey(r: AskCortexRequest): string {
  const a = Object.entries(r.args ?? {}).sort().map(([k, v]) => `${k}=${v}`).join('&');
  return a ? `${r.topic}?${a}` : r.topic;
}

export async function askCortex(r: AskCortexRequest, signal?: AbortSignal): Promise<string> {
  const req = { ...r, args: { currency: getCurrency(), ...(r.args ?? {}) } };
  if (STATIC) {
    const baked = ((await loadStaticFile('ask_cortex').catch(() => ({}))) ?? {}) as Record<string, string>;
    if (!req.question && baked[askKey(req)]) return baked[askKey(req)];
    if (AGENT_BASE && req.question) {
      const res = await fetch(`${AGENT_BASE}/ask-cortex`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req), signal,
      });
      if (res.ok) return (await res.json()).answer;
    }
    return baked[askKey(req)] ??
      '_Live Cortex analysis is not available in this static build. Run the app against Snowflake to ask your own question._';
  }
  const start = await fetch(`${BASE}/ask-cortex`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req), signal,
  });
  if (!start.ok) throw new Error(`Ask Cortex: ${start.status}`);
  const { id } = await start.json();
  for (let i = 0; i < 90; i++) {
    await new Promise((res) => setTimeout(res, 2000));
    if (signal?.aborted) throw new Error('cancelled');
    const j = await liveGet<any>(`/ask-cortex/${id}`);
    if (j.status === 'done') return j.answer;
    if (j.status === 'error') throw new Error(j.error);
  }
  throw new Error('Ask Cortex timed out');
}
