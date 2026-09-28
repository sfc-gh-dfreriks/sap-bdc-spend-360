#!/usr/bin/env python3
"""Extract every figure the Spend 360 deliverables quote, with its provenance.

Nothing in the kit, deck, docs or video is transcribed by hand. Each figure is
pulled live from the account and stamped with the query that produced it, so a
document cannot drift from what the platform contains.

Mirrors tools/people_facts.py in sap-bdc-people-360. Spend 360 specifics:

  1. Only ONE of the five DT_* objects in ANALYTICS is a dynamic table
     (DT_SPEND_360). DT_SUPPLIER_RISK, DT_CATEGORY_HIERARCHY,
     DT_SAVINGS_OPPORTUNITY and DT_INVOICE_SPEND are base tables. The prefix is
     never used as evidence - SHOW DYNAMIC TABLES is.
  2. Those four enrichment tables carry REPRESENTATIVE demo values (risk, ESG,
     diversity, savings, non-PO invoices), per sql/01_l0_sources.md. Only the PO
     and supplier data come from SAP BDC data products. The kit must say so.
  3. The app reads DT_SPEND_360 for dashboards and the raw BDC shares on the
     lineage page. The agent reads the semantic view.

Writes /tmp/spend_facts.json (the handoff the docx and pptx builders read).

Usage:
    python3 tools/spend_facts.py              # extract and write
    python3 tools/spend_facts.py --print      # extract and show the table
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import tomllib

import snowflake.connector

CONN = "dfreriksdemo"
DB = "SAP_SPEND_360"
A = f"{DB}.ANALYTICS"
OUT = pathlib.Path("/tmp/spend_facts.json")
REPO = "https://github.com/sfc-gh-dfreriks/sap-bdc-spend-360"
PUBLIC_URL = "https://sfc-gh-dfreriks.github.io/spend-360-public/"
APP_LISTING = "ORGDATACLOUD$INTERNAL$SPEND_360_ORG"
NATIVE_APP = "SPEND_360_APP"

APP = pathlib.Path.home() / "Documents" / "SAP" / "SAP Skills" / "spend_360_react"
SIDEBAR = APP / "client" / "src" / "components" / "Sidebar.tsx"
API_ROUTES = APP / "server" / "src" / "routes" / "api.ts"
ANALYST_SVC = APP / "server" / "src" / "services" / "analyst.ts"
ANALYST_PAGE = APP / "client" / "src" / "pages" / "Analyst.tsx"
APP_DEV_URL = "http://localhost:3007"

REGION_CONNS = ["dfreriksdemo", "dfreriks_eu_demo", "dfreriks_apac_demo"]

# DT_SPEND_360.SPEND is in each PO's document currency (USD, EUR, JPY). Every PO
# line is converted at the ECB reference rate for its PO date, from
# ANALYTICS.FX_RATES_CALENDAR (tools/load_fx_rates.py) -- the same conversion the
# app applies, so the kit and the screen agree.
FX_SOURCE = "ECB reference rates (api.frankfurter.dev), rate on each PO date"


def conn_params(name: str) -> dict:
    path = pathlib.Path.home() / ".snowflake" / "connections.toml"
    cfg = tomllib.loads(path.read_text())
    if name not in cfg:
        sys.exit(f"connection {name!r} not in {path}")
    c = dict(cfg[name])
    if "private_key_path" in c:
        c["private_key_file"] = str(pathlib.Path(c.pop("private_key_path")).expanduser())
    c.pop("database", None)
    c.pop("schema", None)
    return c


class Facts:
    """Collects values together with the source that produced each one."""

    def __init__(self, cur):
        self.cur = cur
        self.data: dict = {}
        self.provenance: dict = {}

    def sql_one(self, key, sql, source):
        self.cur.execute(sql)
        row = self.cur.fetchone()
        val = row[0] if row and len(row) == 1 else (list(row) if row else None)
        self.data[key] = self._clean(val)
        self.provenance[key] = source
        return self.data[key]

    def sql_rows(self, key, sql, source):
        self.cur.execute(sql)
        cols = [d[0] for d in self.cur.description]
        self.data[key] = [{c: self._clean(v) for c, v in zip(cols, r)} for r in self.cur.fetchall()]
        self.provenance[key] = source
        return self.data[key]

    def put(self, key, value, source):
        self.data[key] = self._clean(value)
        self.provenance[key] = source
        return value

    @staticmethod
    def _clean(v):
        if isinstance(v, (dt.date, dt.datetime)):
            return v.isoformat()[:10]
        if isinstance(v, list):
            return [Facts._clean(x) for x in v]
        if isinstance(v, dict):
            return {k: Facts._clean(x) for k, x in v.items()}
        if hasattr(v, "normalize"):  # Decimal
            return float(v)
        return v


def show(cur, sql):
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def collect(cur) -> Facts:
    f = Facts(cur)
    IS = f"{DB}.INFORMATION_SCHEMA"

    # ---- platform shape -----------------------------------------------------
    f.sql_rows("analytics_objects", f"""
        SELECT TABLE_NAME, TABLE_TYPE, ROW_COUNT FROM {IS}.TABLES
        WHERE TABLE_SCHEMA='ANALYTICS' ORDER BY ROW_COUNT DESC NULLS LAST""",
        "INFORMATION_SCHEMA.TABLES, ANALYTICS")
    f.put("analytics_rows", sum(o["ROW_COUNT"] or 0 for o in f.data["analytics_objects"]),
          "sum of ROW_COUNT over ANALYTICS")
    f.sql_rows("l1_objects", f"""
        SELECT TABLE_NAME, TABLE_TYPE FROM {IS}.TABLES
        WHERE TABLE_SCHEMA='SAP_BDC_L1' ORDER BY 1""", "INFORMATION_SCHEMA.TABLES, SAP_BDC_L1")

    dtrows = show(cur, f"SHOW DYNAMIC TABLES IN DATABASE {DB}")
    f.put("dynamic_tables", sorted(r["name"] for r in dtrows), "SHOW DYNAMIC TABLES")
    f.put("dynamic_table_count", len(dtrows), "SHOW DYNAMIC TABLES")
    f.put("dynamic_table_detail",
          [{"name": r["name"], "target_lag": r["target_lag"], "refresh_mode": r["refresh_mode"],
            "data_timestamp": Facts._clean(r.get("data_timestamp"))} for r in dtrows],
          "SHOW DYNAMIC TABLES")
    f.put("dt_prefixed_not_dynamic",
          sorted({o["TABLE_NAME"] for o in f.data["analytics_objects"] if o["TABLE_NAME"].startswith("DT_")}
                 - {r["name"] for r in dtrows}),
          "ANALYTICS DT_* names minus SHOW DYNAMIC TABLES")
    f.put("enrichment_tables", f.data["dt_prefixed_not_dynamic"],
          "sql/01_l0_sources.md: representative demo values aligned to SAP Spend Intelligence")

    # ---- semantic view ------------------------------------------------------
    svs = [{"fqn": f"{DB}.{d['schema_name']}.{d['name']}"}
           for d in show(cur, f"SHOW SEMANTIC VIEWS IN DATABASE {DB}")]
    f.put("semantic_views", svs, "SHOW SEMANTIC VIEWS")
    detail = {}
    for sv in svs:
        cur.execute(f"DESCRIBE SEMANTIC VIEW {sv['fqn']}")
        c2 = [d[0] for d in cur.description]
        rows = cur.fetchall()
        ki, ni = c2.index("object_kind"), c2.index("object_name")
        pi = c2.index("parent_entity") if "parent_entity" in c2 else None

        def distinct(kind):
            return {(r[pi] if pi is not None else None, r[ni]) for r in rows if r[ki] == kind}

        detail[sv["fqn"]] = {
            "tables": len(distinct("TABLE")),
            "table_names": sorted({r[ni] for r in rows if r[ki] == "TABLE"}),
            "dimensions": len(distinct("DIMENSION")),
            "facts": len(distinct("FACT")),
            "metrics": len(distinct("METRIC")),
            "relationships": len(distinct("RELATIONSHIP")),
            "verified_queries": len({r[ni] for r in rows if r[ki] and "VERIFIED" in str(r[ki]).upper()}),
        }
    f.put("semantic_view_detail", detail, "DESCRIBE SEMANTIC VIEW")

    agents = show(cur, f"SHOW AGENTS IN DATABASE {DB}")
    f.put("agents", [f"{DB}.{a['schema_name']}.{a['name']}" for a in agents], "SHOW AGENTS")

    # ---- data window ----------------------------------------------------------
    f.sql_one("po_window", f"SELECT MIN(PO_DATE), MAX(PO_DATE) FROM {A}.DT_SPEND_360",
              "MIN/MAX(PO_DATE), DT_SPEND_360")

    # ---- currency normalisation -------------------------------------------
    CONV = (f"(SELECT s.*, s.SPEND * f.USD_PER_UNIT AS SPEND_USD FROM {A}.DT_SPEND_360 s "
            f"JOIN {A}.FX_RATES_CALENDAR f ON f.RATE_DATE = s.PO_DATE AND f.CURRENCY = s.CURRENCY)")
    USD = "SPEND_USD"
    f.put("fx_source", FX_SOURCE, "tools/load_fx_rates.py")
    f.sql_rows("fx_ranges", f"""
        SELECT CURRENCY, ROUND(MIN(1 / USD_PER_UNIT), 4) AS MIN_PER_USD, ROUND(MAX(1 / USD_PER_UNIT), 4) AS MAX_PER_USD
        FROM {A}.FX_RATES_CALENDAR WHERE CURRENCY <> 'USD'
          AND RATE_DATE BETWEEN (SELECT MIN(PO_DATE) FROM {A}.DT_SPEND_360) AND (SELECT MAX(PO_DATE) FROM {A}.DT_SPEND_360)
        GROUP BY 1 ORDER BY 1""", "FX_RATES_CALENDAR over the PO window")
    f.sql_rows("spend_by_company_native", f"""
        SELECT COMPANY, CURRENCY, COUNT(*) AS PO_LINES, ROUND(SUM(SPEND)) AS SPEND_NATIVE,
               ROUND(SUM({USD})) AS SPEND_USD
        FROM {CONV} GROUP BY 1, 2 ORDER BY 5 DESC""",
        "GROUP BY COMPANY, CURRENCY, DT_SPEND_360 (native and USD-equivalent)")
    f.sql_one("raw_mixed_currency_sum", f"SELECT ROUND(SUM(SPEND)) FROM {CONV}",
              "SUM(SPEND) across currencies WITHOUT conversion - what the app shows today")
    f.sql_one("total_spend_usd", f"SELECT ROUND(SUM({USD})) FROM {CONV}",
              "SUM(SPEND x fixed FX), DT_SPEND_360")
    f.sql_one("on_contract_pct_usd", f"""
        SELECT ROUND(100 * SUM(IFF(IS_ON_CONTRACT, {USD}, 0)) / NULLIF(SUM({USD}), 0), 1)
        FROM {CONV}""", "on-contract / total, USD-equivalent, DT_SPEND_360")
    f.sql_one("off_contract_spend_usd", f"SELECT ROUND(SUM(IFF(IS_ON_CONTRACT, 0, {USD}))) FROM {CONV}",
              "off-contract SPEND, USD-equivalent, DT_SPEND_360")
    f.sql_rows("spend_by_category_usd", f"""
        SELECT CATEGORY, ROUND(SUM({USD})) AS SPEND_USD,
               ROUND(100 * SUM(IFF(IS_ON_CONTRACT, {USD}, 0)) / NULLIF(SUM({USD}), 0), 1) AS ON_CONTRACT_PCT
        FROM {CONV} GROUP BY 1 ORDER BY 2 DESC""", "GROUP BY CATEGORY, USD-equivalent")
    f.sql_rows("top_suppliers_usd", f"""
        SELECT s.SUPPLIER, COALESCE(r.SUPPLIER_NAME, s.SUPPLIER) AS SUPPLIER_NAME, ROUND(SUM(s.SPEND_USD)) AS SPEND_USD
        FROM {CONV} s LEFT JOIN {A}.DT_SUPPLIER_RISK r ON r.SUPPLIER = s.SUPPLIER
        GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10""", "top 10 SUPPLIER, USD-equivalent")
    f.sql_one("top10_supplier_share_pct_usd", f"""
        WITH s AS (SELECT SUPPLIER, SUM({USD}) SP FROM {CONV} GROUP BY 1)
        SELECT ROUND(100 * SUM(IFF(RN <= 10, SP, 0)) / SUM(SP), 1)
        FROM (SELECT SP, ROW_NUMBER() OVER (ORDER BY SP DESC) RN FROM s)""",
        "share of USD-equivalent spend with top 10 suppliers")

    # ---- spend figures (raw, kept for reference; see FX note) ----------------
    f.sql_one("po_lines", f"SELECT COUNT(*) FROM {A}.DT_SPEND_360", "COUNT(*), DT_SPEND_360")
    f.sql_one("purchase_orders", f"SELECT COUNT(DISTINCT PO_ID) FROM {A}.DT_SPEND_360",
              "COUNT DISTINCT PO_ID, DT_SPEND_360")
    f.sql_one("total_spend", f"SELECT ROUND(SUM(SPEND)) FROM {A}.DT_SPEND_360", "SUM(SPEND), DT_SPEND_360")
    f.sql_one("currencies", f"SELECT LISTAGG(DISTINCT CURRENCY, ', ') FROM {A}.DT_SPEND_360",
              "DISTINCT CURRENCY, DT_SPEND_360")
    f.sql_one("suppliers", f"SELECT COUNT(DISTINCT SUPPLIER) FROM {A}.DT_SPEND_360",
              "COUNT DISTINCT SUPPLIER, DT_SPEND_360")
    f.sql_one("categories", f"SELECT COUNT(DISTINCT CATEGORY) FROM {A}.DT_SPEND_360",
              "COUNT DISTINCT CATEGORY, DT_SPEND_360")
    f.sql_one("companies", f"SELECT COUNT(DISTINCT COMPANY) FROM {A}.DT_SPEND_360",
              "COUNT DISTINCT COMPANY, DT_SPEND_360")
    f.sql_one("on_contract_pct", f"""
        SELECT ROUND(100 * SUM(IFF(IS_ON_CONTRACT, SPEND, 0)) / NULLIF(SUM(SPEND), 0), 1)
        FROM {A}.DT_SPEND_360""", "on-contract SPEND / total SPEND, DT_SPEND_360")
    f.sql_one("off_contract_spend", f"""
        SELECT ROUND(SUM(IFF(IS_ON_CONTRACT, 0, SPEND))) FROM {A}.DT_SPEND_360""",
        "SUM(SPEND) WHERE NOT IS_ON_CONTRACT, DT_SPEND_360")
    f.sql_rows("spend_by_category", f"""
        SELECT CATEGORY, ROUND(SUM(SPEND)) AS SPEND,
               ROUND(100 * SUM(IFF(IS_ON_CONTRACT, SPEND, 0)) / NULLIF(SUM(SPEND), 0), 1) AS ON_CONTRACT_PCT
        FROM {A}.DT_SPEND_360 GROUP BY 1 ORDER BY 2 DESC""", "GROUP BY CATEGORY, DT_SPEND_360")
    f.sql_rows("spend_by_company", f"""
        SELECT COMPANY, ROUND(SUM(SPEND)) AS SPEND FROM {A}.DT_SPEND_360 GROUP BY 1 ORDER BY 2 DESC""",
        "GROUP BY COMPANY, DT_SPEND_360")
    f.sql_rows("top_suppliers", f"""
        SELECT s.SUPPLIER, COALESCE(r.SUPPLIER_NAME, s.SUPPLIER) AS SUPPLIER_NAME, ROUND(SUM(s.SPEND)) AS SPEND
        FROM {A}.DT_SPEND_360 s LEFT JOIN {A}.DT_SUPPLIER_RISK r ON r.SUPPLIER = s.SUPPLIER
        GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10""", "top 10 SUPPLIER by SUM(SPEND)")
    f.sql_one("top10_supplier_share_pct", f"""
        WITH s AS (SELECT SUPPLIER, SUM(SPEND) SP FROM {A}.DT_SPEND_360 GROUP BY 1)
        SELECT ROUND(100 * SUM(IFF(RN <= 10, SP, 0)) / SUM(SP), 1)
        FROM (SELECT SP, ROW_NUMBER() OVER (ORDER BY SP DESC) RN FROM s)""",
        "share of spend with top 10 suppliers, DT_SPEND_360")

    # ---- enrichment (representative values) ---------------------------------
    f.sql_one("single_source_suppliers", f"""
        SELECT COUNT(*) FROM {A}.DT_SUPPLIER_RISK WHERE IS_SINGLE_SOURCE""",
        "COUNT WHERE IS_SINGLE_SOURCE, DT_SUPPLIER_RISK (representative)")
    f.sql_one("high_risk_suppliers", f"""
        SELECT COUNT(*) FROM {A}.DT_SUPPLIER_RISK WHERE RISK_SCORE >= 70""",
        "COUNT WHERE RISK_SCORE >= 70, DT_SUPPLIER_RISK (representative)")
    f.sql_one("avg_esg_score", f"SELECT ROUND(AVG(ESG_SCORE), 1) FROM {A}.DT_SUPPLIER_RISK",
              "AVG(ESG_SCORE), DT_SUPPLIER_RISK (representative)")
    f.sql_one("diverse_suppliers", f"SELECT COUNT(*) FROM {A}.DT_SUPPLIER_RISK WHERE IS_DIVERSE",
              "COUNT WHERE IS_DIVERSE, DT_SUPPLIER_RISK (representative)")
    f.sql_one("savings_opportunities", f"SELECT COUNT(*) FROM {A}.DT_SAVINGS_OPPORTUNITY",
              "COUNT(*), DT_SAVINGS_OPPORTUNITY (representative)")
    f.sql_one("savings_total", f"SELECT ROUND(SUM(ESTIMATED_SAVINGS)) FROM {A}.DT_SAVINGS_OPPORTUNITY",
              "SUM(ESTIMATED_SAVINGS), DT_SAVINGS_OPPORTUNITY (representative)")
    f.sql_rows("savings_by_type", f"""
        SELECT OPP_TYPE, COUNT(*) AS OPPS, ROUND(SUM(ESTIMATED_SAVINGS)) AS SAVINGS
        FROM {A}.DT_SAVINGS_OPPORTUNITY GROUP BY 1 ORDER BY 3 DESC""",
        "GROUP BY OPP_TYPE, DT_SAVINGS_OPPORTUNITY (representative)")
    f.sql_rows("savings_levers", f"""
        SELECT OPP_TYPE, COUNT(*) AS OPPS, ROUND(MEDIAN(SAVINGS_PCT), 1) AS SAVINGS_PCT
        FROM {A}.DT_SAVINGS_OPPORTUNITY GROUP BY 1 ORDER BY 3 DESC""",
        "savings % by lever, DT_SAVINGS_OPPORTUNITY (representative). Dollar values in "
        "this table were sized on the unconverted mixed-currency base - do not quote them.")
    SAV = (f"(SELECT o.*, o.ESTIMATED_SAVINGS * x.CONV / NULLIF(x.RAW, 0) AS SAVINGS_USD "
           f"FROM {A}.DT_SAVINGS_OPPORTUNITY o JOIN (SELECT CATEGORY, SUM(SPEND) RAW, SUM(SPEND_USD) CONV "
           f"FROM {CONV} GROUP BY 1) x ON x.CATEGORY = o.CATEGORY)")
    f.sql_one("savings_total_usd", f"SELECT ROUND(SUM(SAVINGS_USD)) FROM {SAV}",
              "savings rescaled to USD by category conversion ratio (as the app shows), representative")
    f.sql_rows("savings_by_status_usd", f"""
        SELECT STATUS, COUNT(*) AS OPPS, ROUND(SUM(SAVINGS_USD)) AS SAVINGS_USD FROM {SAV} GROUP BY 1 ORDER BY 3 DESC""",
        "GROUP BY STATUS, USD, DT_SAVINGS_OPPORTUNITY (representative)")
    f.sql_rows("savings_by_status", f"""
        SELECT STATUS, COUNT(*) AS OPPS FROM {A}.DT_SAVINGS_OPPORTUNITY GROUP BY 1 ORDER BY 2 DESC""",
        "GROUP BY STATUS, DT_SAVINGS_OPPORTUNITY (representative)")
    f.sql_one("addressable_categories", f"""
        SELECT COUNT(*) FROM {A}.DT_CATEGORY_HIERARCHY WHERE IS_ADDRESSABLE""",
        "COUNT WHERE IS_ADDRESSABLE, DT_CATEGORY_HIERARCHY (representative)")
    f.sql_one("invoice_lines", f"SELECT COUNT(*) FROM {A}.DT_INVOICE_SPEND",
              "COUNT(*), DT_INVOICE_SPEND (representative non-PO spend)")

    # ---- what the application reads ----------------------------------------
    sources: dict = {}
    if API_ROUTES.exists():
        for m in re.finditer(r"FROM\s+([A-Z_0-9]+)\.([A-Za-z_0-9]+)\.([A-Za-z_0-9]+)", API_ROUTES.read_text()):
            k = ".".join(m.groups())
            sources[k] = sources.get(k, 0) + 1
    f.put("app_data_sources", dict(sorted(sources.items(), key=lambda kv: -kv[1])),
          f"{API_ROUTES.name} FROM clauses")
    f.put("app_reads_share_directly", sorted(k for k in sources if k.startswith("SAP_BDC_DEMO_")),
          f"{API_ROUTES.name} FROM clauses on SAP_BDC_DEMO_*")
    target = None
    if ANALYST_SVC.exists():
        m = re.search(r"semantic_view:\s*[\"']([^\"']+)[\"']", ANALYST_SVC.read_text())
        target = m.group(1) if m else None
    f.put("analyst_semantic_view", target, f"{ANALYST_SVC.name} semantic_view literal")

    pages = []
    if SIDEBAR.exists():
        pages = [m.group(2) for m in re.finditer(
            r"""id:\s*['"]([\w-]+)['"]\s*,\s*label:\s*['"]([^'"]+)['"]""", SIDEBAR.read_text())]
    f.put("app_pages", pages, f"{SIDEBAR.name} NAV_ITEMS")
    f.put("app_page_count", len(pages), f"{SIDEBAR.name} NAV_ITEMS")

    chips = []
    if ANALYST_PAGE.exists():
        m = re.search(r"SUGGESTED_QUESTIONS\s*=\s*\[(.*?)\]", ANALYST_PAGE.read_text(), re.S)
        if m:
            chips = re.findall(r"['\"]([^'\"]{15,})['\"]", m.group(1))
    f.put("agent_questions", chips, f"{ANALYST_PAGE.name} SUGGESTED_QUESTIONS")

    app_kpis = None
    try:
        import urllib.request
        with urllib.request.urlopen(f"{APP_DEV_URL}/api/overview", timeout=8) as r:
            app_kpis = json.loads(r.read()).get("kpis")
    except Exception as e:  # noqa: BLE001
        app_kpis = {"error": f"app not running at {APP_DEV_URL}: {str(e)[:60]}"}
    f.put("app_kpis", app_kpis, f"GET {APP_DEV_URL}/api/overview (kpis block)")

    # ---- native app ------------------------------------------------------------
    url = None
    try:
        svc = show(cur, f"SHOW SERVICES IN APPLICATION {NATIVE_APP}")[0]
        eps = show(cur, f"SHOW ENDPOINTS IN SERVICE {NATIVE_APP}.{svc['schema_name']}.{svc['name']}")
        url = next((e["ingress_url"] for e in eps if e.get("ingress_url")), None)
        f.put("native_app_status", svc["status"], "SHOW SERVICES IN APPLICATION")
    except Exception as e:  # noqa: BLE001
        f.put("native_app_status", f"unavailable: {str(e)[:60]}", "SHOW SERVICES IN APPLICATION")
    f.put("native_app_url", url, "SHOW ENDPOINTS IN SERVICE")

    f.put("public_url", PUBLIC_URL, "constant")
    f.put("app_listing", APP_LISTING, "constant")
    f.put("repo", REPO, "constant")
    cur.execute("SELECT CURRENT_ACCOUNT(), CURRENT_REGION()")
    acct, region = cur.fetchone()
    f.put("account", acct, "CURRENT_ACCOUNT()")
    f.put("region", region, "CURRENT_REGION()")
    f.put("verified_on", dt.date.today().isoformat(), "extraction date")
    return f


def collect_regions(f: Facts):
    found = []
    for name in REGION_CONNS:
        try:
            cn = snowflake.connector.connect(**conn_params(name))
            cur = cn.cursor()
            cur.execute("SELECT CURRENT_REGION()")
            region = cur.fetchone()[0]
            rows = show(cur, "SHOW LISTINGS LIKE '%SPEND_360%'")
            found.append({"connection": name, "region": region,
                          "listings": [{"name": r["name"], "state": r["state"],
                                        "is_application": r["is_application"]} for r in rows]})
            cn.close()
        except Exception as e:  # noqa: BLE001
            found.append({"connection": name, "error": str(e)[:90]})
    f.put("regions", found, "SHOW LISTINGS LIKE '%SPEND_360%' per region")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", dest="show")
    args = ap.parse_args()
    cn = snowflake.connector.connect(**conn_params(CONN))
    try:
        f = collect(cn.cursor())
    finally:
        cn.close()
    collect_regions(f)
    OUT.write_text(json.dumps({"facts": f.data, "provenance": f.provenance}, indent=2))
    print(f"wrote {OUT}  ({len(f.data)} facts)")
    if args.show:
        for k, v in f.data.items():
            s = json.dumps(v) if not isinstance(v, (str, int, float, type(None))) else str(v)
            print(f"{k:28s} {s[:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
