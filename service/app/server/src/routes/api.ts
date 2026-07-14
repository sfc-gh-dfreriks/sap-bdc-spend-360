import { Router, type Request, type Response } from "express";
import { runQuery } from "../services/snowflake.js";
import { callCortexAnalyst } from "../services/analyst.js";

const router = Router();
const DT = "APP_DATA.DT_SPEND_360";
const SR = "APP_DATA.DT_SUPPLIER_RISK";
const CH = "APP_DATA.DT_CATEGORY_HIERARCHY";
const SVOP = "APP_DATA.DT_SAVINGS_OPPORTUNITY";
const INV = "APP_DATA.DT_INVOICE_SPEND";

function parseList(raw: unknown): string[] {
  if (typeof raw !== "string" || raw.trim() === "") return [];
  return raw.split(",").map((v) => v.trim()).filter(Boolean);
}
function filters(req: Request): { where: string; binds: string[] } {
  const cats = parseList(req.query.categories);
  const comps = parseList(req.query.companies);
  const parts: string[] = []; const binds: string[] = [];
  if (cats.length) { parts.push(`CATEGORY IN (${cats.map(() => "?").join(",")})`); binds.push(...cats); }
  if (comps.length) { parts.push(`COMPANY IN (${comps.map(() => "?").join(",")})`); binds.push(...comps); }
  return { where: parts.length ? `WHERE ${parts.join(" AND ")}` : "", binds };
}

router.get("/api/filters", async (_req, res) => {
  try {
    const [cats, comps] = await Promise.all([
      runQuery(`SELECT DISTINCT CATEGORY AS v FROM ${DT} ORDER BY 1`),
      runQuery(`SELECT DISTINCT COMPANY AS v FROM ${DT} ORDER BY 1`),
    ]);
    res.json({ categories: cats.map((r) => r.v), companies: comps.map((r) => r.v) });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

router.get("/api/overview", async (req, res) => {
  try {
    const { where, binds } = filters(req);
    const [kpis, byCat, byCompany, trend, topSuppliers] = await Promise.all([
      runQuery(
        `SELECT SUM(SPEND) AS total_spend, COUNT(*) AS po_lines, COUNT(DISTINCT SUPPLIER) AS suppliers,
                COUNT(DISTINCT CATEGORY) AS categories,
                ROUND(100*SUM(CASE WHEN IS_ON_CONTRACT THEN SPEND ELSE 0 END)/NULLIF(SUM(SPEND),0),1) AS contract_pct,
                ROUND(AVG(SPEND)) AS avg_po_value
           FROM ${DT} ${where}`, binds),
      runQuery(`SELECT CATEGORY AS name, SUM(SPEND) AS spend FROM ${DT} ${where} GROUP BY 1 ORDER BY 2 DESC`, binds),
      runQuery(`SELECT COMPANY AS name, SUM(SPEND) AS spend FROM ${DT} ${where} GROUP BY 1 ORDER BY 2 DESC`, binds),
      runQuery(`SELECT PO_MONTH AS month, SUM(SPEND) AS spend FROM ${DT} ${where} GROUP BY 1 ORDER BY 1`, binds),
      runQuery(`SELECT SUPPLIER AS name, SUM(SPEND) AS spend FROM ${DT} ${where} GROUP BY 1 ORDER BY 2 DESC LIMIT 10`, binds),
    ]);
    res.json({ kpis: kpis[0] ?? {}, byCat, byCompany, trend, topSuppliers });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

router.get("/api/categories", async (req, res) => {
  try {
    const { where, binds } = filters(req);
    const [byCat, contractByCat, trendByCat] = await Promise.all([
      runQuery(`SELECT CATEGORY AS name, SUM(SPEND) AS spend, COUNT(*) AS lines, ROUND(AVG(NET_PRICE),2) AS avg_price FROM ${DT} ${where} GROUP BY 1 ORDER BY 2 DESC`, binds),
      runQuery(`SELECT CATEGORY AS name,
                  ROUND(100*SUM(CASE WHEN IS_ON_CONTRACT THEN SPEND ELSE 0 END)/NULLIF(SUM(SPEND),0),1) AS contract_pct
                FROM ${DT} ${where} GROUP BY 1 ORDER BY 2 DESC`, binds),
      runQuery(`SELECT PO_MONTH AS month, CATEGORY AS name, SUM(SPEND) AS spend FROM ${DT} ${where} GROUP BY 1,2 ORDER BY 1`, binds),
    ]);
    res.json({ byCat, contractByCat, trendByCat });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

router.get("/api/suppliers", async (req, res) => {
  try {
    const { where, binds } = filters(req);
    const [top, concentration, byCompany] = await Promise.all([
      runQuery(`SELECT SUPPLIER AS name, SUM(SPEND) AS spend, COUNT(*) AS lines,
                  COUNT(DISTINCT CATEGORY) AS categories,
                  ROUND(100*SUM(CASE WHEN IS_ON_CONTRACT THEN SPEND ELSE 0 END)/NULLIF(SUM(SPEND),0),1) AS contract_pct
                FROM ${DT} ${where} GROUP BY 1 ORDER BY 2 DESC LIMIT 20`, binds),
      runQuery(`WITH s AS (SELECT SUPPLIER, SUM(SPEND) AS spend FROM ${DT} ${where} GROUP BY 1),
                 t AS (SELECT SUM(spend) AS total FROM s)
                SELECT
                  ROUND(100*SUM(CASE WHEN rnk<=10 THEN spend ELSE 0 END)/NULLIF(MAX(total),0),1) AS top10_pct,
                  ROUND(100*SUM(CASE WHEN rnk<=50 THEN spend ELSE 0 END)/NULLIF(MAX(total),0),1) AS top50_pct,
                  COUNT(*) AS supplier_count
                FROM (SELECT spend, ROW_NUMBER() OVER (ORDER BY spend DESC) AS rnk FROM s), t`, binds),
      runQuery(`SELECT COMPANY AS name, COUNT(DISTINCT SUPPLIER) AS suppliers FROM ${DT} ${where} GROUP BY 1 ORDER BY 2 DESC`, binds),
    ]);
    res.json({ top, concentration: concentration[0] ?? {}, byCompany });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

router.get("/api/contracts", async (req, res) => {
  try {
    const { where, binds } = filters(req);
    const [split, byCompany, offContractByCat] = await Promise.all([
      runQuery(`SELECT IFF(IS_ON_CONTRACT,'On Contract','Off Contract') AS name, SUM(SPEND) AS spend FROM ${DT} ${where} GROUP BY 1`, binds),
      runQuery(`SELECT COMPANY AS name,
                  ROUND(100*SUM(CASE WHEN IS_ON_CONTRACT THEN SPEND ELSE 0 END)/NULLIF(SUM(SPEND),0),1) AS contract_pct
                FROM ${DT} ${where} GROUP BY 1 ORDER BY 2 DESC`, binds),
      runQuery(`SELECT CATEGORY AS name, SUM(CASE WHEN NOT IS_ON_CONTRACT THEN SPEND ELSE 0 END) AS off_contract_spend
                FROM ${DT} ${where} GROUP BY 1 ORDER BY 2 DESC`, binds),
    ]);
    res.json({ split, byCompany, offContractByCat });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

router.get("/api/purchase-orders", async (req, res) => {
  try {
    const { where, binds } = filters(req);
    const rows = await runQuery(
      `SELECT PO_ID, SUPPLIER, CATEGORY, COMPANY, PO_DATE, ORDER_QUANTITY, NET_PRICE, SPEND,
              IFF(IS_ON_CONTRACT,'Yes','No') AS on_contract, BUYER
         FROM ${DT} ${where} ORDER BY SPEND DESC LIMIT 200`, binds);
    res.json({ rows });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

router.get("/api/lineage", async (_req, res) => {
  try {
    const c = (await runQuery(
      `SELECT
         (SELECT COUNT(*) FROM SAP_BDC_DEMO_PURCHASE_ORDER.BDCCONNECT.PURCHASEORDERITEM) AS l0_po,
         (SELECT COUNT(*) FROM SAP_BDC_DEMO_SUPPLIER.BDCCONNECT.SUPPLIER) AS l0_supplier,
         (SELECT COUNT(*) FROM APP_DATA.DT_SPEND_360) AS dt_spend`))[0] as any;
    res.json({
      app: "SAP BDC Spend 360",
      database: "SAP_SPEND_360",
      sourceSystems: ["SAP S/4HANA — Sourcing & Procurement", "SAP Ariba"],
      summary:
        "Procurement data flows from SAP S/4HANA Sourcing & Procurement (and SAP Ariba) into Snowflake as SAP BDC " +
        "zero-copy data products (L0), organized into passthrough views (L1), curated into a gold spend fact and " +
        "unified semantic view (L2), and served to this app and the SAP Spend Analyst Cortex Agent — no ETL, no data movement.",
      products: [
        { sapSystem: "S/4HANA — Sourcing & Procurement", dataProduct: "Purchase Order", l0Object: "SAP_BDC_DEMO_PURCHASE_ORDER.BDCCONNECT.PURCHASEORDERITEM", l1Object: "SAP_BDC_L1.PURCHASE_ORDER_ITEM", rows: c.l0_po },
        { sapSystem: "S/4HANA — Business Partner", dataProduct: "Supplier", l0Object: "SAP_BDC_DEMO_SUPPLIER.BDCCONNECT.SUPPLIER", l1Object: "SAP_BDC_L1.SUPPLIER", rows: c.l0_supplier },
        { sapSystem: "S/4HANA / Ariba — Contracts", dataProduct: "Purchase Contract", l0Object: "SAP_BDC_DEMO_PURCHASE_CONTRACT (contract linkage)", l1Object: "via PURCHASECONTRACT on spend fact", rows: null },
      ],
      layers: [
        { name: "SAP Source Systems", tone: "sap", objects: ["SAP S/4HANA Procurement", "SAP Ariba"] },
        { name: "L0 — Bronze (BDC Zero-Copy)", tone: "bronze", objects: ["SAP_BDC_DEMO_PURCHASE_ORDER", "SAP_BDC_DEMO_SUPPLIER", "SAP_BDC_DEMO_PURCHASE_CONTRACT"] },
        { name: "L1 — Silver (Passthrough Views)", tone: "silver", objects: ["SAP_BDC_L1.PURCHASE_ORDER_ITEM", "SAP_BDC_L1.SUPPLIER"] },
        { name: "L2 — Gold (Dynamic Table + Semantic View)", tone: "gold", objects: ["ANALYTICS.DT_SPEND_360", "SEMANTIC.SAP_SPEND_360_ANALYTICS"] },
        { name: "AI + Application", tone: "ai", objects: ["AGENTS.SAP_SPEND_ANALYST (Cortex Agent)", "SAP BDC Spend 360 (React)"] },
      ],
    });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

router.post("/api/analyst", async (req, res) => {
  try {
    const { messages } = req.body;
    if (!Array.isArray(messages)) return res.status(400).json({ error: "messages array is required" });
    res.json(await callCortexAnalyst(messages));
  } catch (err) { console.error("POST /api/analyst error:", err); res.status(500).json({ error: String(err) }); }
});

router.post("/api/analyst/run-sql", async (req, res) => {
  try {
    const { sql } = req.body;
    if (!sql || typeof sql !== "string") return res.status(400).json({ error: "sql string is required" });
    const t = sql.trim().toUpperCase();
    if (!t.startsWith("SELECT") && !t.startsWith("WITH")) return res.status(400).json({ error: "Only SELECT/WITH allowed" });
    const rows = await runQuery(sql);
    res.json({ rows, columns: rows.length > 0 ? Object.keys(rows[0]) : [] });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

// ---------------------------------------------------------------------------
// Spend Intelligence: supplier risk, sustainability/diversity, savings
// ---------------------------------------------------------------------------
router.get("/api/supplier-risk", async (_req, res) => {
  try {
    const [kpis, byTier, topRisk, byRegion, scatter] = await Promise.all([
      runQuery(`SELECT COUNT(*) AS supplier_count, ROUND(AVG(RISK_SCORE),1) AS avg_risk,
                  SUM(CASE WHEN RISK_SCORE>=70 THEN 1 ELSE 0 END) AS high_risk_suppliers,
                  SUM(CASE WHEN IS_SINGLE_SOURCE THEN ANNUAL_SPEND ELSE 0 END) AS single_source_spend
                FROM ${SR}`),
      runQuery(`SELECT TIER AS name, COUNT(*) AS suppliers, SUM(ANNUAL_SPEND) AS spend, ROUND(AVG(RISK_SCORE),1) AS avg_risk
                FROM ${SR} GROUP BY 1 ORDER BY 3 DESC`),
      runQuery(`SELECT SUPPLIER_NAME AS name, RISK_SCORE, FINANCIAL_RISK, GEO_RISK, COMPLIANCE_RISK,
                  ANNUAL_SPEND, COUNTRY, IS_SINGLE_SOURCE FROM ${SR} ORDER BY RISK_SCORE DESC LIMIT 15`),
      runQuery(`SELECT REGION AS name, ROUND(AVG(RISK_SCORE),1) AS avg_risk, SUM(ANNUAL_SPEND) AS spend, COUNT(*) AS suppliers
                FROM ${SR} GROUP BY 1 ORDER BY 3 DESC`),
      runQuery(`SELECT SUPPLIER_NAME AS name, RISK_SCORE, ANNUAL_SPEND AS spend, TIER FROM ${SR}
                WHERE ANNUAL_SPEND > 0 ORDER BY ANNUAL_SPEND DESC LIMIT 120`),
    ]);
    res.json({ kpis: kpis[0] ?? {}, byTier, topRisk, byRegion, scatter });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

router.get("/api/sustainability", async (_req, res) => {
  try {
    const [kpis, byRegion, diverseByClass, esgBuckets, topEsg] = await Promise.all([
      runQuery(`SELECT ROUND(AVG(ESG_SCORE),1) AS avg_esg,
                  SUM(CASE WHEN IS_SUSTAINABLE THEN 1 ELSE 0 END) AS sustainable_suppliers,
                  SUM(CASE WHEN IS_SUSTAINABLE THEN ANNUAL_SPEND ELSE 0 END) AS sustainable_spend,
                  SUM(CASE WHEN IS_DIVERSE THEN 1 ELSE 0 END) AS diverse_suppliers,
                  SUM(CASE WHEN IS_DIVERSE THEN ANNUAL_SPEND ELSE 0 END) AS diverse_spend
                FROM ${SR}`),
      runQuery(`SELECT REGION AS name, ROUND(AVG(ENV_SCORE),1) AS env, ROUND(AVG(SOCIAL_SCORE),1) AS social,
                  ROUND(AVG(GOV_SCORE),1) AS gov FROM ${SR} GROUP BY 1 ORDER BY 1`),
      runQuery(`SELECT DIVERSITY_CLASS AS name, COUNT(*) AS suppliers, SUM(ANNUAL_SPEND) AS spend
                FROM ${SR} WHERE DIVERSITY_CLASS IS NOT NULL GROUP BY 1 ORDER BY 3 DESC`),
      runQuery(`SELECT CASE WHEN ESG_SCORE>=80 THEN '80-100 (Leaders)' WHEN ESG_SCORE>=60 THEN '60-79'
                  WHEN ESG_SCORE>=40 THEN '40-59' ELSE '<40 (Laggards)' END AS name,
                  COUNT(*) AS suppliers FROM ${SR} GROUP BY 1 ORDER BY 1 DESC`),
      runQuery(`SELECT SUPPLIER_NAME AS name, ESG_SCORE, ENV_SCORE, SOCIAL_SCORE, GOV_SCORE, ANNUAL_SPEND
                FROM ${SR} ORDER BY ESG_SCORE DESC LIMIT 15`),
    ]);
    res.json({ kpis: kpis[0] ?? {}, byRegion, diverseByClass, esgBuckets, topEsg });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

router.get("/api/savings", async (_req, res) => {
  try {
    const [kpis, byType, byStatus, byCategory, pipeline] = await Promise.all([
      runQuery(`SELECT SUM(ESTIMATED_SAVINGS) AS total_identified,
                  SUM(CASE WHEN STATUS='Realized' THEN ESTIMATED_SAVINGS ELSE 0 END) AS realized,
                  SUM(CASE WHEN STATUS='In-progress' THEN ESTIMATED_SAVINGS ELSE 0 END) AS in_progress,
                  COUNT(*) AS opportunities FROM ${SVOP}`),
      runQuery(`SELECT OPP_TYPE AS name, SUM(ESTIMATED_SAVINGS) AS savings, COUNT(*) AS opportunities
                FROM ${SVOP} GROUP BY 1 ORDER BY 2 DESC`),
      runQuery(`SELECT STATUS AS name, SUM(ESTIMATED_SAVINGS) AS savings FROM ${SVOP} GROUP BY 1 ORDER BY 2 DESC`),
      runQuery(`SELECT CATEGORY AS name, SUM(ESTIMATED_SAVINGS) AS savings FROM ${SVOP} GROUP BY 1 ORDER BY 2 DESC LIMIT 12`),
      runQuery(`SELECT OPP_ID, CATEGORY, OPP_TYPE, ESTIMATED_SAVINGS, SAVINGS_PCT, STATUS, OWNER, TARGET_DATE
                FROM ${SVOP} ORDER BY ESTIMATED_SAVINGS DESC LIMIT 25`),
    ]);
    res.json({ kpis: kpis[0] ?? {}, byType, byStatus, byCategory, pipeline });
  } catch (err) { res.status(500).json({ error: String(err) }); }
});

export default router;
