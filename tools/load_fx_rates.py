#!/usr/bin/env python3
"""Load historical ECB reference FX rates into SAP_SPEND_360 for currency conversion.

DT_SPEND_360.SPEND is in each PO's document currency (USD/EUR/JPY). The app
converts every PO line at the rate for its PO date, using:

    ANALYTICS.FX_RATES_DAILY     business-day rates, USD per 1 unit of currency
    ANALYTICS.FX_RATES_CALENDAR  every calendar day, last business-day rate carried forward

Source: https://api.frankfurter.dev (European Central Bank reference rates, free,
no key). Re-run to extend the window.

    python3 tools/load_fx_rates.py [--conn dfreriksdemo] [--start 2024-06-24] [--end 2026-06-30]
"""
import argparse
import json
import sys
import urllib.request

sys.path.insert(0, __import__("pathlib").Path(__file__).parent.as_posix())
from spend_facts import conn_params  # noqa: E402
import snowflake.connector  # noqa: E402

A = "SAP_SPEND_360.ANALYTICS"
CURRENCIES = ["EUR", "JPY"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conn", default="dfreriksdemo")
    ap.add_argument("--start", default="2024-06-24")   # a week before the first PO, to seed carry-forward
    ap.add_argument("--end", default="2026-06-30")
    a = ap.parse_args()

    url = (f"https://api.frankfurter.dev/v1/{a.start}..{a.end}"
           f"?base=USD&symbols={','.join(CURRENCIES)}")
    with urllib.request.urlopen(url, timeout=60) as r:
        rates = json.loads(r.read())["rates"]
    rows = []
    for day, r in sorted(rates.items()):
        rows.append((day, "USD", 1.0))
        rows += [(day, c, 1.0 / v) for c, v in r.items()]
    print(f"{len(rates)} business days, {min(rates)} to {max(rates)}")

    cn = snowflake.connector.connect(**conn_params(a.conn))
    c = cn.cursor()
    c.execute(f"""CREATE OR REPLACE TABLE {A}.FX_RATES_DAILY (
        RATE_DATE DATE, CURRENCY VARCHAR(3), USD_PER_UNIT FLOAT)
        COMMENT='ECB reference rates via api.frankfurter.dev (base USD). USD value of one unit of CURRENCY. Business days only.'""")
    c.executemany(f"INSERT INTO {A}.FX_RATES_DAILY VALUES (%s, %s, %s)", rows)
    c.execute(f"""CREATE OR REPLACE VIEW {A}.FX_RATES_CALENDAR
        COMMENT='Daily FX calendar: each date carries the most recent ECB business-day rate.' AS
        WITH days AS (SELECT DATEADD(day, SEQ4(), '{a.start}'::DATE) AS D
                      FROM TABLE(GENERATOR(ROWCOUNT => 5000))),
             ccy AS (SELECT DISTINCT CURRENCY FROM {A}.FX_RATES_DAILY)
        SELECT d.D AS RATE_DATE, c.CURRENCY,
               LAST_VALUE(f.USD_PER_UNIT) IGNORE NULLS OVER (
                 PARTITION BY c.CURRENCY ORDER BY d.D
                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS USD_PER_UNIT
        FROM days d CROSS JOIN ccy c
        LEFT JOIN {A}.FX_RATES_DAILY f ON f.RATE_DATE = d.D AND f.CURRENCY = c.CURRENCY
        WHERE d.D <= '{a.end}'""")
    c.execute(f"""SELECT COUNT(*), COUNT_IF(f.USD_PER_UNIT IS NULL) FROM {A}.DT_SPEND_360 s
        LEFT JOIN {A}.FX_RATES_CALENDAR f ON f.RATE_DATE = s.PO_DATE AND f.CURRENCY = s.CURRENCY""")
    total, missing = c.fetchone()
    print(f"PO lines {total}, without a rate {missing}")
    cn.close()
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
