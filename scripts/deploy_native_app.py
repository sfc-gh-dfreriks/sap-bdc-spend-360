#!/usr/bin/env python3
"""
Deploy the Spend 360 Native App into one account (run once per region).

Assumes:
  * The container image has been pushed (see build_and_push.sh)
  * The package data has been bundled (see migrate_data.py)

Steps performed:
  1. Upload the 4 app artifacts (manifest, setup.sql, service_spec, README)
     to SPEND_360_PKG.PUBLIC.APP_STAGE
  2. REGISTER VERSION v1 (release channels are enabled by default)
  3. Add v1 to the DEFAULT channel + set the default release directive
  4. CREATE APPLICATION SPEND_360_APP + grant account privileges
  5. Run version_init() and print service status + app URL

Usage:
  python deploy_native_app.py --target dfreriksdemo
  python deploy_native_app.py --target dfreriks_eu_demo --warehouse COMPUTE_WH
"""
import argparse
import os
import time
import json
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

PKG = "SPEND_360_PKG"
APP = "SPEND_360_APP"
APP_DIR = os.path.join(os.path.dirname(__file__), "..", "app")
FILES = ["manifest.yml", "setup.sql", "service_spec.yml", "README.md"]


def connect(conn_name, **kw):
    import tomllib
    with open(os.path.expanduser("~/.snowflake/connections.toml"), "rb") as f:
        cfg = tomllib.load(f)[conn_name]
    with open(cfg["private_key_path"], "rb") as f:
        pk = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    der = pk.private_bytes(serialization.Encoding.DER,
                           serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption())
    return snowflake.connector.connect(
        account=cfg["account"], user=cfg["user"], private_key=der,
        role=cfg.get("role", "ACCOUNTADMIN"), **kw)


def deploy(target, wh):
    conn = connect(target, warehouse=wh)
    cur = conn.cursor()
    cur.execute(f"USE WAREHOUSE {wh}")

    cur.execute(f"CREATE STAGE IF NOT EXISTS {PKG}.PUBLIC.APP_STAGE "
                f"ENCRYPTION=(TYPE='SNOWFLAKE_SSE')")
    for f in FILES:
        p = os.path.abspath(os.path.join(APP_DIR, f))
        cur.execute(f"PUT 'file://{p}' @{PKG}.PUBLIC.APP_STAGE "
                    f"AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
    print(f"{target}: artifacts staged")

    cur.execute(f"ALTER APPLICATION PACKAGE {PKG} REGISTER VERSION v1 "
                f"USING '@{PKG}.PUBLIC.APP_STAGE'")
    cur.execute(f"ALTER APPLICATION PACKAGE {PKG} MODIFY RELEASE CHANNEL DEFAULT ADD VERSION v1")
    cur.execute(f"ALTER APPLICATION PACKAGE {PKG} MODIFY RELEASE CHANNEL DEFAULT "
                f"SET DEFAULT RELEASE DIRECTIVE VERSION=v1 PATCH=0")
    print(f"{target}: version v1 registered + directive set")

    cur.execute(f"CREATE APPLICATION {APP} FROM APPLICATION PACKAGE {PKG} USING VERSION v1")
    for g in [
        f"GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO APPLICATION {APP}",
        f"GRANT CREATE COMPUTE POOL ON ACCOUNT TO APPLICATION {APP}",
        f"GRANT CREATE WAREHOUSE ON ACCOUNT TO APPLICATION {APP}",
        f"GRANT BIND SERVICE ENDPOINT ON ACCOUNT TO APPLICATION {APP}",
    ]:
        cur.execute(g)
    print(f"{target}: application created + privileges granted")

    cur.execute(f"CALL {APP}.CORE.VERSION_INIT()")
    print(f"{target}: version_init ->", cur.fetchone()[0])

    # poll for readiness + url
    for _ in range(30):
        time.sleep(15)
        cur.execute(f"CALL {APP}.CORE.GET_SERVICE_STATUS()")
        try:
            st = json.loads(cur.fetchone()[0])[0]["status"]
        except Exception:
            st = "PENDING"
        if st == "READY":
            break
    cur.execute(f"CALL {APP}.CORE.SELFTEST()")
    print(f"{target}: selftest ->", cur.fetchone()[0])
    cur.execute(f"CALL {APP}.CORE.APP_URL()")
    print(f"{target}: app url -> https://{cur.fetchone()[0]}")
    cur.close(); conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--warehouse", default="COMPUTE_WH")
    a = ap.parse_args()
    deploy(a.target, a.warehouse)
