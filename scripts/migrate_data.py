#!/usr/bin/env python3
"""
Bundle the 5 Spend 360 tables into the application package's SHARED_DATA schema
so the Native App is self-contained (no consumer references).

Modes:
  * local  — CTAS from SAP_SPEND_360.ANALYTICS into SPEND_360_PKG.SHARED_DATA.
  * remote — fast cross-region load: extract from SOURCE, write_pandas into a
             scratch DB in TARGET, then CTAS into the package (parquet+COPY,
             far faster than row-by-row inserts).

Auth uses key-pair connections in ~/.snowflake/connections.toml (names only).

Usage:
  python migrate_data.py --target dfreriksdemo --mode local
  python migrate_data.py --source dfreriksdemo --target dfreriks_eu_demo --mode remote
"""
import argparse
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# FX_RATES_CALENDAR is a view in the source (tools/load_fx_rates.py); it is
# materialised as a table in the package so the app can convert PO currencies.
TABLES = ["DT_SPEND_360", "DT_SUPPLIER_RISK", "DT_CATEGORY_HIERARCHY",
          "DT_SAVINGS_OPPORTUNITY", "DT_INVOICE_SPEND", "FX_RATES_CALENDAR", "LINEAGE_COUNTS"]
SRC_SCHEMA = "SAP_SPEND_360.ANALYTICS"
PKG = "SPEND_360_PKG"
STG = "SPEND_STAGING"


def connect(conn_name, **kw):
    import tomllib, os
    with open(os.path.expanduser("~/.snowflake/connections.toml"), "rb") as f:
        cfg = tomllib.load(f)[conn_name]
    with open(cfg["private_key_path"], "rb") as f:
        pk = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    der = pk.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption())
    return snowflake.connector.connect(account=cfg["account"], user=cfg["user"], private_key=der,
                                       role=cfg.get("role", "ACCOUNTADMIN"), **kw)


def ensure_pkg(cur):
    cur.execute(f"CREATE APPLICATION PACKAGE IF NOT EXISTS {PKG}")
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {PKG}.SHARED_DATA")
    cur.execute(f"GRANT USAGE ON SCHEMA {PKG}.SHARED_DATA TO SHARE IN APPLICATION PACKAGE {PKG}")


def local_bundle(target, wh):
    conn = connect(target, warehouse=wh); cur = conn.cursor(); cur.execute(f"USE WAREHOUSE {wh}")
    ensure_pkg(cur)
    for t in TABLES:
        cur.execute(f"CREATE OR REPLACE TABLE {PKG}.SHARED_DATA.{t} AS SELECT * FROM {SRC_SCHEMA}.{t}")
        cur.execute(f"GRANT SELECT ON TABLE {PKG}.SHARED_DATA.{t} TO SHARE IN APPLICATION PACKAGE {PKG}")
        cur.execute(f"SELECT COUNT(*) FROM {PKG}.SHARED_DATA.{t}")
        print(f"  {target}/{t}: {cur.fetchone()[0]} rows")
    cur.close(); conn.close()


def remote_bundle(source, target, wh):
    from snowflake.connector.pandas_tools import write_pandas
    s = connect(source, warehouse=wh); sc = s.cursor(); sc.execute(f"USE WAREHOUSE {wh}")
    dfs = {}
    for t in TABLES:
        sc.execute(f"SELECT * FROM {SRC_SCHEMA}.{t}")
        dfs[t] = sc.fetch_pandas_all()
    sc.close(); s.close()
    conn = connect(target, warehouse=wh); cur = conn.cursor(); cur.execute(f"USE WAREHOUSE {wh}")
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {STG}"); cur.execute(f"CREATE SCHEMA IF NOT EXISTS {STG}.PUBLIC")
    ensure_pkg(cur)
    for t in TABLES:
        write_pandas(conn, dfs[t], t, database=STG, schema="PUBLIC",
                     auto_create_table=True, overwrite=True, quote_identifiers=False, use_logical_type=True)
        cur.execute(f"CREATE OR REPLACE TABLE {PKG}.SHARED_DATA.{t} AS SELECT * FROM {STG}.PUBLIC.{t}")
        cur.execute(f"GRANT SELECT ON TABLE {PKG}.SHARED_DATA.{t} TO SHARE IN APPLICATION PACKAGE {PKG}")
        cur.execute(f"SELECT COUNT(*) FROM {PKG}.SHARED_DATA.{t}")
        print(f"  {target}/{t}: {cur.fetchone()[0]} rows")
    cur.execute(f"DROP DATABASE IF EXISTS {STG}")
    cur.close(); conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source"); ap.add_argument("--target", required=True)
    ap.add_argument("--mode", choices=["local", "remote"], default="local")
    ap.add_argument("--warehouse", default="COMPUTE_WH")
    a = ap.parse_args()
    if a.mode == "local":
        local_bundle(a.target, a.warehouse)
    else:
        assert a.source, "--source required for remote mode"
        remote_bundle(a.source, a.target, a.warehouse)
    print("DONE")
