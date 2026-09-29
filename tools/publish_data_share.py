#!/usr/bin/env python3
"""Publish a 360 product's analytics layer as a data share + organization listing.

Mirrors the Finance / Sales / Supply Chain data-share listings (SAP_BDC_*_360_DEMO):
one share per region over the product database, carrying the ANALYTICS tables, the
semantic view and the Cortex Agent, published as an INTERNAL organization listing.

The SAP BDC source shares for Spend / People / Working Capital exist only in the US
account, so for EU and APAC the analytics layer is COPIED from the US database
(tables materialised, semantic view and agent recreated from their DDL/spec under
the same fully-qualified names). The copies do not refresh; re-run to resync.

Usage:
  python tools/publish_data_share.py --product spend --target dfreriksdemo
  python tools/publish_data_share.py --product people --target dfreriks_eu_demo
  python tools/publish_data_share.py --product wc --target dfreriks_apac_demo --dry-run
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from spend_facts import conn_params  # noqa: E402

import snowflake.connector  # noqa: E402
from snowflake.connector.pandas_tools import write_pandas  # noqa: E402

SOURCE = "dfreriksdemo"
CONTACT = "dave.freriks@snowflake.com"

PRODUCTS = {
    "spend": dict(
        db="SAP_SPEND_360", agent="SAP_SPEND_ANALYST", sv="SAP_SPEND_360_ANALYTICS",
        share="SAP_SPEND_360_SHARE", listing="SAP_BDC_SPEND_360_DEMO",
        title="SAP BDC Spend 360 Demo", featured="DT_SPEND_360",
        description=(
            "SAP Spend 360 turns SAP procurement data into spend intelligence on Snowflake. Purchase "
            "orders and suppliers arrive from SAP Business Data Cloud with zero copy, and the analytics "
            "layer adds supplier risk, ESG and diversity, a category taxonomy and a savings pipeline. "
            "Subscribers receive the spend fact (3,000 PO lines across three companies buying in USD, "
            "EUR and JPY), the enrichment tables, and daily ECB reference exchange rates so spend can be "
            "converted at the rate for each PO date.\n\nThe listing also includes a governed semantic "
            "view over spend, suppliers, categories and savings, and a Cortex Agent for Snowflake "
            "Intelligence that answers questions like \"Which categories have the most off-contract "
            "spend?\" with no SQL. Risk, ESG, taxonomy and savings values are representative demo data. "
            "Spend in the semantic view is in each PO's own currency, so ask per company or group by currency.")),
    "people": dict(
        db="SAP_PEOPLE_360", agent="SAP_PEOPLE_ANALYST", sv="SAP_PEOPLE_360_ANALYTICS",
        share="SAP_PEOPLE_360_SHARE", listing="SAP_BDC_PEOPLE_360_DEMO",
        title="SAP BDC People 360 Demo", featured="DT_WORKFORCE_360",
        description=(
            "SAP People 360 turns SAP SuccessFactors workforce data into governed HR analytics on "
            "Snowflake, reached through SAP Business Data Cloud with zero copy. Subscribers receive the "
            "workforce table (headcount, attrition, compensation, diversity, tenure and org structure) "
            "plus performance, learning and recruiting tables.\n\nThe listing also includes a governed "
            "semantic view over the workforce and a Cortex Agent for Snowflake Intelligence that answers "
            "questions like \"What is attrition by department this year?\" with no SQL. The data is a "
            "synthetic demo dataset: no real employees. The agent covers the workforce table; "
            "performance, learning and recruiting are available as tables.")),
    "wc": dict(
        db="SAP_WORKING_CAPITAL_360", agent="SAP_WORKING_CAPITAL_ANALYST", sv="SAP_WORKING_CAPITAL_360_ANALYTICS",
        share="SAP_WORKING_CAPITAL_360_SHARE", listing="SAP_BDC_WORKING_CAPITAL_360_DEMO",
        title="SAP BDC Working Capital 360 Demo", featured="DT_WC_MONTHLY_KPI",
        description=(
            "SAP Working Capital 360 turns SAP receivables, payables, inventory and bank data into "
            "working-capital intelligence on Snowflake, reached through SAP Business Data Cloud with zero "
            "copy. Subscribers receive AR and AP open items, monthly inventory, weekly bank balances, "
            "monthly flows, a cash forecast and monthly DSO, DPO, DIO and cash-conversion-cycle KPIs, "
            "with company, customer, supplier and bank dimensions.\n\nThe listing also includes a "
            "governed semantic view and a Cortex Agent for Snowflake Intelligence that answers questions "
            "like \"Which customers drive the most overdue receivables?\" with no SQL.")),
}


def q(cur, sql):
    cur.execute(sql)
    cols = [d[0] for d in cur.description] if cur.description else []
    return [dict(zip(cols, r)) for r in cur.fetchall()] if cols else []


def connect(name):
    return snowflake.connector.connect(**{**conn_params(name), "warehouse": "LOAD_WH"})


def copy_analytics(p, src, dst_conn, dry):
    """Recreate DB.ANALYTICS / SEMANTIC / AGENTS in the target from the US source."""
    s, d = src.cursor(), dst_conn.cursor()
    db = p["db"]
    objs = q(s, f"SELECT TABLE_NAME FROM {db}.INFORMATION_SCHEMA.TABLES "
                f"WHERE TABLE_SCHEMA='ANALYTICS' ORDER BY 1")
    sv_ddl = s.execute(f"SELECT GET_DDL('SEMANTIC_VIEW','{db}.SEMANTIC.{p['sv']}')").fetchone()[0]
    spec = q(s, f"DESCRIBE AGENT {db}.AGENTS.{p['agent']}")[0]["agent_spec"]
    print(f"  copy {len(objs)} ANALYTICS objects, semantic view, agent -> target")
    if dry:
        return
    for sch in ("ANALYTICS", "SEMANTIC", "AGENTS"):
        d.execute(f"CREATE DATABASE IF NOT EXISTS {db}")
        d.execute(f"CREATE SCHEMA IF NOT EXISTS {db}.{sch}")
    for o in objs:
        t = o["TABLE_NAME"]
        df = s.execute(f"SELECT * FROM {db}.ANALYTICS.{t}").fetch_pandas_all()
        write_pandas(dst_conn, df, t, database=db, schema="ANALYTICS", auto_create_table=True,
                     overwrite=True, quote_identifiers=False, use_logical_type=True)
        n = d.execute(f"SELECT COUNT(*) FROM {db}.ANALYTICS.{t}").fetchone()[0]
        print(f"    {t}: {n} rows")
    d.execute(f"USE SCHEMA {db}.SEMANTIC")
    d.execute(sv_ddl)
    d.execute(f"CREATE OR REPLACE AGENT {db}.AGENTS.{p['agent']} FROM SPECIFICATION $${spec}$$")
    print("    semantic view + agent recreated")


def create_share(p, cur, dry):
    db, sh = p["db"], p["share"]
    objs = q(cur, f"SELECT TABLE_NAME, TABLE_TYPE, IS_DYNAMIC FROM {db}.INFORMATION_SCHEMA.TABLES "
                  f"WHERE TABLE_SCHEMA='ANALYTICS' ORDER BY 1")
    # only secure views can be shared; these are thin views over tables in the same DB
    stmts = [f"ALTER VIEW {db}.ANALYTICS.{o['TABLE_NAME']} SET SECURE"
             for o in objs if o["TABLE_TYPE"] == "VIEW"]
    stmts += [f"CREATE SHARE IF NOT EXISTS {sh} COMMENT = '{p['title']} data share'",
              f"GRANT USAGE ON DATABASE {db} TO SHARE {sh}"]
    stmts += [f"GRANT USAGE ON SCHEMA {db}.{x} TO SHARE {sh}" for x in ("ANALYTICS", "SEMANTIC", "AGENTS")]
    for o in objs:  # views one by one (no bulk grant for views); dynamic tables by their own kind
        kind = ("VIEW" if o["TABLE_TYPE"] == "VIEW"
                else "DYNAMIC TABLE" if o["IS_DYNAMIC"] == "YES" else "TABLE")
        stmts.append(f"GRANT SELECT ON {kind} {db}.ANALYTICS.{o['TABLE_NAME']} TO SHARE {sh}")
    stmts += [f"GRANT SELECT, REFERENCES ON SEMANTIC VIEW {db}.SEMANTIC.{p['sv']} TO SHARE {sh}",
              f"GRANT USAGE ON AGENT {db}.AGENTS.{p['agent']} TO SHARE {sh}"]
    print(f"  share {sh}: {len(stmts)} statements ({len(objs)} objects + semantic view + agent)")
    for st in stmts:
        if dry:
            print("    ", st)
        else:
            cur.execute(st)


def create_listing(p, cur, region, dry):
    manifest = {
        "title": p["title"],
        "description": p["description"],
        "data_dictionary": {"featured": {"database": p["db"], "objects": [
            {"schema": "ANALYTICS", "domain": "TABLE", "name": p["featured"]}]}},
        "data_preview": {"has_pii": False},
        "organization_profile": "INTERNAL",
        "organization_targets": {"access": [{"all_internal_accounts": True}],
                                 "discovery": [{"all_internal_accounts": True}]},
        # region-scoped, like the Native App listings: each region serves its own copy
        "locations": {"access_regions": [{"name": region}]},
        "support_contact": CONTACT,
        "approver_contact": CONTACT,
        "request_approval_type": "REQUEST_AND_APPROVE_OUTSIDE_SNOWFLAKE",
        "resharing": {"enabled": False},
    }
    yaml_text = json.dumps(manifest, indent=2)  # JSON is valid YAML
    exists = q(cur, f"SHOW LISTINGS LIKE '{p['listing']}'")
    if exists:
        print(f"  listing {p['listing']} already exists ({exists[0]['state']}); leaving it")
        return
    sql = (f"CREATE ORGANIZATION LISTING {p['listing']} SHARE {p['share']} "
           f"AS $$\n{yaml_text}\n$$ PUBLISH = TRUE")
    if dry:
        print("  would create listing", p["listing"], "for region", region)
        return
    cur.execute(sql)
    r = q(cur, f"SHOW LISTINGS LIKE '{p['listing']}'")[0]
    print(f"  listing {r['name']}: {r['state']} · global {r['global_name']} · {r['uniform_listing_locator']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", required=True, choices=sorted(PRODUCTS))
    ap.add_argument("--target", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    p = PRODUCTS[a.product]
    tgt = connect(a.target)
    cur = tgt.cursor()
    region = cur.execute("SELECT CURRENT_REGION()").fetchone()[0]
    if not region.startswith("PUBLIC."):
        region = "PUBLIC." + region
    print(f"{a.product} -> {a.target} ({region}){' [dry run]' if a.dry_run else ''}")
    if a.target != SOURCE:
        copy_analytics(p, connect(SOURCE), tgt, a.dry_run)
    create_share(p, cur, a.dry_run)
    create_listing(p, cur, region, a.dry_run)


if __name__ == "__main__":
    main()
