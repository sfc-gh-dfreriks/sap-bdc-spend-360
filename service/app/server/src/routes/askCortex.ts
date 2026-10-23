import crypto from "node:crypto";
import { Router, type Request, type Response } from "express";
import { runQuery } from "../services/snowflake.js";
import { CURRENCIES, spendIn, supplierRiskIn, savingsIn, type Ccy } from "./api.js";

// ================================================================ Ask Cortex
// Each topic is a set of SQL "facts" the model must treat as authoritative.
// Facts reuse the same currency-converted subqueries the pages use.
const router = Router();
const MODEL = process.env.CORTEX_MODEL ?? "claude-sonnet-4-5";
type Facts = (args: Record<string, string>, ccy: Ccy) => Promise<Record<string, unknown>>;
const T = (sql: string, binds: string[] = []) => runQuery(sql, binds);
const one = async (sql: string) => (await T(sql))[0] ?? {};

const spendKpis = (D: string) => one(
  `SELECT ROUND(SUM(SPEND)) total_spend, COUNT(*) po_lines, COUNT(DISTINCT SUPPLIER) suppliers, COUNT(DISTINCT CATEGORY) categories,
          ROUND(100*SUM(IFF(IS_ON_CONTRACT,SPEND,0))/NULLIF(SUM(SPEND),0),1) contract_pct, MIN(PO_DATE) first_po, MAX(PO_DATE) last_po FROM ${D}`);

const TOPICS: Record<string, { title: string; facts: Facts }> = {
  general: { title: "cross-functional spend, supplier risk, ESG, savings and contract compliance", facts: async (_a, c) => {
    const D = spendIn(c), R = supplierRiskIn(c), S = savingsIn(c);
    return {
      spend_kpis: await spendKpis(D),
      spend_by_category: await T(`SELECT CATEGORY, ROUND(SUM(SPEND)) spend, ROUND(100*SUM(IFF(IS_ON_CONTRACT,SPEND,0))/NULLIF(SUM(SPEND),0),1) contract_pct FROM ${D} GROUP BY 1 ORDER BY 2 DESC LIMIT 15`),
      spend_by_company: await T(`SELECT COMPANY, ROUND(SUM(SPEND)) spend FROM ${D} GROUP BY 1 ORDER BY 2 DESC`),
      top_suppliers: await T(`SELECT SUPPLIER, ROUND(SUM(SPEND)) spend FROM ${D} GROUP BY 1 ORDER BY 2 DESC LIMIT 10`),
      monthly_trend: await T(`SELECT PO_MONTH, ROUND(SUM(SPEND)) spend FROM ${D} GROUP BY 1 ORDER BY 1`),
      risk_kpis: await one(`SELECT COUNT(*) suppliers, ROUND(AVG(RISK_SCORE),1) avg_risk, COUNT_IF(RISK_SCORE>=70) high_risk, ROUND(SUM(IFF(IS_SINGLE_SOURCE,ANNUAL_SPEND,0))) single_source_spend, ROUND(AVG(ESG_SCORE),1) avg_esg, COUNT_IF(IS_DIVERSE) diverse_suppliers FROM ${R}`),
      top_risk_suppliers: await T(`SELECT SUPPLIER_NAME, RISK_SCORE, ROUND(ANNUAL_SPEND) spend, COUNTRY, IS_SINGLE_SOURCE FROM ${R} ORDER BY RISK_SCORE DESC LIMIT 5`),
      savings_by_status: await T(`SELECT STATUS, ROUND(SUM(ESTIMATED_SAVINGS)) savings, COUNT(*) opps FROM ${S} GROUP BY 1 ORDER BY 2 DESC`),
    };
  } },
  overview: { title: "spend overview", facts: async (_a, c) => {
    const D = spendIn(c);
    return {
      kpis: await spendKpis(D),
      by_category: await T(`SELECT CATEGORY, ROUND(SUM(SPEND)) spend FROM ${D} GROUP BY 1 ORDER BY 2 DESC`),
      by_company: await T(`SELECT COMPANY, ROUND(SUM(SPEND)) spend FROM ${D} GROUP BY 1 ORDER BY 2 DESC`),
      monthly_trend: await T(`SELECT PO_MONTH, ROUND(SUM(SPEND)) spend FROM ${D} GROUP BY 1 ORDER BY 1`),
      top_suppliers: await T(`SELECT SUPPLIER, ROUND(SUM(SPEND)) spend FROM ${D} GROUP BY 1 ORDER BY 2 DESC LIMIT 10`),
    };
  } },
  categories: { title: "spend by category", facts: async (_a, c) => {
    const D = spendIn(c);
    return {
      by_category: await T(`SELECT CATEGORY, ROUND(SUM(SPEND)) spend, COUNT(*) lines, COUNT(DISTINCT SUPPLIER) suppliers, ROUND(AVG(NET_PRICE),2) avg_price FROM ${D} GROUP BY 1 ORDER BY 2 DESC`),
      category_by_quarter: await T(`SELECT DATE_TRUNC('quarter', PO_DATE) quarter, CATEGORY, ROUND(SUM(SPEND)) spend FROM ${D} GROUP BY 1,2 ORDER BY 1,3 DESC`),
    };
  } },
  suppliers: { title: "supplier spend and concentration", facts: async (_a, c) => {
    const D = spendIn(c);
    return {
      top_suppliers: await T(`SELECT SUPPLIER, ROUND(SUM(SPEND)) spend, COUNT(*) lines, COUNT(DISTINCT CATEGORY) categories, ROUND(100*SUM(IFF(IS_ON_CONTRACT,SPEND,0))/NULLIF(SUM(SPEND),0),1) contract_pct FROM ${D} GROUP BY 1 ORDER BY 2 DESC LIMIT 20`),
      concentration: await one(`WITH s AS (SELECT SUPPLIER, SUM(SPEND) spend FROM ${D} GROUP BY 1)
        SELECT COUNT(*) supplier_count, ROUND(100*SUM(IFF(rnk<=10,spend,0))/SUM(spend),1) top10_pct, ROUND(100*SUM(IFF(rnk<=50,spend,0))/SUM(spend),1) top50_pct
        FROM (SELECT spend, ROW_NUMBER() OVER (ORDER BY spend DESC) rnk FROM s)`),
      suppliers_by_company: await T(`SELECT COMPANY, COUNT(DISTINCT SUPPLIER) suppliers FROM ${D} GROUP BY 1 ORDER BY 2 DESC`),
    };
  } },
  "supplier-risk": { title: "supplier risk (representative enrichment scores)", facts: async (_a, c) => {
    const R = supplierRiskIn(c);
    return {
      kpis: await one(`SELECT COUNT(*) suppliers, ROUND(AVG(RISK_SCORE),1) avg_risk, COUNT_IF(RISK_SCORE>=70) high_risk, ROUND(SUM(IFF(IS_SINGLE_SOURCE,ANNUAL_SPEND,0))) single_source_spend FROM ${R}`),
      by_tier: await T(`SELECT TIER, COUNT(*) suppliers, ROUND(SUM(ANNUAL_SPEND)) spend, ROUND(AVG(RISK_SCORE),1) avg_risk FROM ${R} GROUP BY 1 ORDER BY 3 DESC`),
      by_region: await T(`SELECT REGION, COUNT(*) suppliers, ROUND(SUM(ANNUAL_SPEND)) spend, ROUND(AVG(RISK_SCORE),1) avg_risk FROM ${R} GROUP BY 1 ORDER BY 3 DESC`),
      top_risk: await T(`SELECT SUPPLIER_NAME, RISK_SCORE, FINANCIAL_RISK, GEO_RISK, COMPLIANCE_RISK, ROUND(ANNUAL_SPEND) spend, COUNTRY, IS_SINGLE_SOURCE FROM ${R} ORDER BY RISK_SCORE DESC LIMIT 15`),
    };
  } },
  sustainability: { title: "supplier ESG and diversity (representative enrichment scores)", facts: async (_a, c) => {
    const R = supplierRiskIn(c);
    return {
      kpis: await one(`SELECT ROUND(AVG(ESG_SCORE),1) avg_esg, COUNT_IF(IS_SUSTAINABLE) sustainable_suppliers, ROUND(SUM(IFF(IS_SUSTAINABLE,ANNUAL_SPEND,0))) sustainable_spend, COUNT_IF(IS_DIVERSE) diverse_suppliers, ROUND(SUM(IFF(IS_DIVERSE,ANNUAL_SPEND,0))) diverse_spend, ROUND(SUM(ANNUAL_SPEND)) total_spend FROM ${R}`),
      esg_by_region: await T(`SELECT REGION, ROUND(AVG(ENV_SCORE),1) env, ROUND(AVG(SOCIAL_SCORE),1) social, ROUND(AVG(GOV_SCORE),1) gov FROM ${R} GROUP BY 1 ORDER BY 1`),
      diversity_classes: await T(`SELECT DIVERSITY_CLASS, COUNT(*) suppliers, ROUND(SUM(ANNUAL_SPEND)) spend FROM ${R} WHERE DIVERSITY_CLASS IS NOT NULL GROUP BY 1 ORDER BY 3 DESC`),
      esg_laggards_by_spend: await T(`SELECT SUPPLIER_NAME, ESG_SCORE, ROUND(ANNUAL_SPEND) spend FROM ${R} WHERE ESG_SCORE < 50 ORDER BY ANNUAL_SPEND DESC LIMIT 10`),
      esg_leaders: await T(`SELECT SUPPLIER_NAME, ESG_SCORE, ROUND(ANNUAL_SPEND) spend FROM ${R} ORDER BY ESG_SCORE DESC LIMIT 10`),
    };
  } },
  savings: { title: "savings opportunity pipeline (representative enrichment)", facts: async (_a, c) => {
    const S = savingsIn(c);
    return {
      kpis: await one(`SELECT ROUND(SUM(ESTIMATED_SAVINGS)) identified, ROUND(SUM(IFF(STATUS='Realized',ESTIMATED_SAVINGS,0))) realized, ROUND(SUM(IFF(STATUS='In-progress',ESTIMATED_SAVINGS,0))) in_progress, COUNT(*) opportunities FROM ${S}`),
      by_type: await T(`SELECT OPP_TYPE, ROUND(SUM(ESTIMATED_SAVINGS)) savings, COUNT(*) opps FROM ${S} GROUP BY 1 ORDER BY 2 DESC`),
      by_status: await T(`SELECT STATUS, ROUND(SUM(ESTIMATED_SAVINGS)) savings FROM ${S} GROUP BY 1 ORDER BY 2 DESC`),
      by_category: await T(`SELECT CATEGORY, ROUND(SUM(ESTIMATED_SAVINGS)) savings FROM ${S} GROUP BY 1 ORDER BY 2 DESC LIMIT 12`),
      top_opportunities: await T(`SELECT OPP_ID, CATEGORY, OPP_TYPE, ROUND(ESTIMATED_SAVINGS) savings, SAVINGS_PCT, STATUS, OWNER, TARGET_DATE FROM ${S} ORDER BY ESTIMATED_SAVINGS DESC LIMIT 15`),
    };
  } },
  contracts: { title: "contract compliance and off-contract (maverick) spend", facts: async (_a, c) => {
    const D = spendIn(c);
    return {
      split: await T(`SELECT IFF(IS_ON_CONTRACT,'On Contract','Off Contract') status, ROUND(SUM(SPEND)) spend, COUNT(*) lines FROM ${D} GROUP BY 1`),
      by_company: await T(`SELECT COMPANY, ROUND(100*SUM(IFF(IS_ON_CONTRACT,SPEND,0))/NULLIF(SUM(SPEND),0),1) contract_pct FROM ${D} GROUP BY 1 ORDER BY 2 DESC`),
      off_contract_by_category: await T(`SELECT CATEGORY, ROUND(SUM(IFF(NOT IS_ON_CONTRACT,SPEND,0))) off_contract_spend, ROUND(100*SUM(IFF(IS_ON_CONTRACT,SPEND,0))/NULLIF(SUM(SPEND),0),1) contract_pct FROM ${D} GROUP BY 1 ORDER BY 2 DESC`),
      top_off_contract_suppliers: await T(`SELECT SUPPLIER, ROUND(SUM(SPEND)) off_contract_spend FROM ${D} WHERE NOT IS_ON_CONTRACT GROUP BY 1 ORDER BY 2 DESC LIMIT 10`),
    };
  } },
  "purchase-orders": { title: "purchase order lines", facts: async (_a, c) => {
    const D = spendIn(c);
    return {
      largest_lines: await T(`SELECT PO_ID, SUPPLIER, CATEGORY, COMPANY, PO_DATE, ORDER_QUANTITY, ROUND(SPEND) spend, CURRENCY local_currency, IS_ON_CONTRACT, BUYER FROM ${D} ORDER BY SPEND DESC LIMIT 25`),
      by_buyer: await T(`SELECT BUYER, COUNT(*) lines, ROUND(SUM(SPEND)) spend, ROUND(100*SUM(IFF(IS_ON_CONTRACT,SPEND,0))/NULLIF(SUM(SPEND),0),1) contract_pct FROM ${D} GROUP BY 1 ORDER BY 3 DESC LIMIT 15`),
      by_local_currency: await T(`SELECT CURRENCY local_currency, COUNT(*) lines, ROUND(SUM(SPEND)) spend FROM ${D} GROUP BY 1 ORDER BY 3 DESC`),
    };
  } },
};

const SYSTEM = `Before answering, check that every number and characterisation in your summary (profit vs loss, up vs down, ages, counts, totals) matches the facts and any table you include; never state a figure the facts do not support.
You are Snowflake Cortex, an SAP procurement and spend analyst for a multi-company enterprise.
Data comes from SAP Business Data Cloud data products (S/4HANA purchase orders, suppliers, purchase contracts)
landed in Snowflake via zero-copy shares. PO spend, categories, buyers and contract linkage are real BDC data;
supplier risk, ESG/diversity scores, savings opportunities and the category taxonomy are REPRESENTATIVE
ENRICHMENT values (demo data). Monetary values are in the reporting currency given in Context, converted at
daily ECB reference rates.

Rules:
- The JSON facts below are authoritative. Cite specific suppliers, categories, companies, buyers, percentages
  and amounts from them. Never invent numbers.
- Lead with the direct answer in one or two sentences, then evidence (a small markdown table when comparing),
  then 2-4 concrete recommended procurement actions.
- When your answer relies on risk, ESG, diversity or savings figures, note briefly that they are representative enrichment data.
- If the facts do not contain what is needed, say so plainly.
- Keep it under 300 words.`;

interface Job { status: "running" | "done" | "error"; answer?: string; error?: string; started: number }
const jobs = new Map<string, Job>();

async function runAsk(topic: string, args: Record<string, string>, question: string): Promise<string> {
  const t = TOPICS[topic];
  const ccy = ((CURRENCIES as readonly string[]).includes((args.currency ?? "").toUpperCase()) ? args.currency.toUpperCase() : "USD") as Ccy;
  const facts = await t.facts(args, ccy);
  const q = question?.trim() || `Analyse this ${t.title}: what stands out, why, and what should we do?`;
  const prompt = `${SYSTEM}\n\nTopic: ${t.title}\nContext: ${JSON.stringify({ ...args, currency: ccy })}\n\nFACTS (JSON):\n${JSON.stringify(facts).slice(0, 60000)}\n\nQuestion: ${q}`;
  let rows;
  try {
    rows = await runQuery(`SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?) AS answer`, [MODEL, prompt]);
  } catch (e) {
    // Native App: Cortex may be unavailable in the consumer account (region/model availability,
    // CORTEX_ENABLED_CROSS_REGION, or account-level Cortex restrictions). Degrade gracefully.
    console.error("Ask Cortex unavailable:", String(e));
    return "_Ask Cortex is not available in this installation: the app could not call Snowflake Cortex (`" + MODEL +
      "`). An account admin can enable it by allowing Cortex LLM functions for this account (and cross-region inference if the model is not hosted in this region). All other pages are unaffected._";
  }
  const r = rows[0] as any;
  return String(r?.ANSWER ?? r?.answer ?? "No answer returned.");
}

router.get("/api/ask-cortex/topics", (_req, res) => {
  res.json(Object.fromEntries(Object.entries(TOPICS).map(([k, v]) => [k, v.title])));
});

router.post("/api/ask-cortex", (req: Request, res: Response) => {
  const { topic, args = {}, question = "" } = req.body ?? {};
  if (typeof topic !== "string" || !TOPICS[topic]) return res.status(400).json({ error: "unknown topic" });
  const clean: Record<string, string> = {};
  for (const [k, v] of Object.entries(args ?? {})) if (typeof v === "string" && v.length < 80) clean[k] = v;
  const id = crypto.randomUUID();
  jobs.set(id, { status: "running", started: Date.now() });
  runAsk(topic, clean, String(question).slice(0, 1000))
    .then((answer) => jobs.set(id, { status: "done", answer, started: Date.now() }))
    .catch((err) => jobs.set(id, { status: "error", error: String(err), started: Date.now() }));
  for (const [k, j] of jobs) if (Date.now() - j.started > 3_600_000) jobs.delete(k);
  res.json({ id });
});

router.get("/api/ask-cortex/:id", (req: Request, res: Response) => {
  const j = jobs.get(String(req.params.id));
  if (!j) return res.status(404).json({ error: "job not found" });
  res.json(j);
});

export default router;
