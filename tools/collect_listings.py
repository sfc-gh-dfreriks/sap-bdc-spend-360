#!/usr/bin/env python3
"""Read SHOW LISTINGS and 360 Native App endpoints from all three demo accounts
into /tmp/listings.json and /tmp/apps.json (inputs to the listings doc and asset index)."""
import json
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from spend_facts import conn_params  # noqa: E402
import snowflake.connector  # noqa: E402

CONNS = ["dfreriksdemo", "dfreriks_eu_demo", "dfreriks_apac_demo"]


def rows(c, sql):
    c.execute(sql)
    cols = [d[0] for d in c.description]
    return [dict(zip(cols, r)) for r in c.fetchall()]


listings, apps = {}, {}
for n in CONNS:
    c = snowflake.connector.connect(**conn_params(n)).cursor()
    org, acct, reg = c.execute("SELECT CURRENT_ORGANIZATION_NAME(), CURRENT_ACCOUNT_NAME(), CURRENT_REGION()").fetchone()
    listings[n] = {"org": org, "account": acct, "region": reg,
                   "rows": [{k: str(v) for k, v in r.items()} for r in rows(c, "SHOW LISTINGS")]}
    res = []
    for a in rows(c, "SHOW APPLICATIONS"):
        if "360" not in a["name"]:
            continue
        url = None
        for s in rows(c, f"SHOW SERVICES IN APPLICATION {a['name']}"):
            for e in rows(c, f"SHOW ENDPOINTS IN SERVICE {a['name']}.{s['schema_name']}.{s['name']}"):
                url = e.get("ingress_url") or url
        res.append({"app": a["name"], "version": a.get("version"), "patch": a.get("patch"), "url": url})
    apps[n] = res
    print(n, len(listings[n]["rows"]), "listings,", len(res), "apps")
pathlib.Path("/tmp/listings.json").write_text(json.dumps(listings, indent=1))
pathlib.Path("/tmp/apps.json").write_text(json.dumps(apps, indent=1))
