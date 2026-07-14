# Architecture — SAP BDC Spend 360 (Spend Intelligence)

Spend 360 is built on a **medallion architecture** inside Snowflake, reading SAP
procurement data via **SAP Business Data Cloud (BDC) zero-copy shares**, then
enriching it into a **Spend Intelligence** model (supplier risk, ESG, category
taxonomy, savings). No ETL, no copy, full SAP business context preserved.

```
 SAP S/4HANA (MM / Procurement)      SAP Business Data Cloud
 (source of record)   ─────  Purchase Order · Supplier products  ─────►  Snowflake
                                        (governed, zero-copy)
                                                                │
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  L0  BRONZE  — SAP BDC Standard Data Products                              │
 │      Purchase Order (item) · Supplier                                      │
 └──────────────────────────────────────────────────────────────────────────┘
                                                                │  (views)
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  L1  SILVER  — SAP_SPEND_360.SAP_BDC_L1 (PURCHASE_ORDER_ITEM, SUPPLIER)    │
 └──────────────────────────────────────────────────────────────────────────┘
                                                                │  (curate + enrich)
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  L2  GOLD  — SAP_SPEND_360.ANALYTICS                                       │
 │      DT_SPEND_360            PO line-item spend cube                       │
 │      DT_SUPPLIER_RISK        risk (financial/geo/compliance), ESG,         │
 │                              diversity, tier, single-source                │
 │      DT_CATEGORY_HIERARCHY   direct/indirect taxonomy + addressability     │
 │      DT_SAVINGS_OPPORTUNITY  savings pipeline (levers, status)             │
 │      DT_INVOICE_SPEND        non-PO / AP / T&E spend (total visibility)    │
 └──────────────────────────────────────────────────────────────────────────┘
                                                                │
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  SEMANTIC — SAP_SPEND_360_ANALYTICS (spend + risk + ESG + savings,         │
 │             with SPEND→SUPPLIER and SPEND→CATEGORY relationships)          │
 └──────────────────────────────────────────────────────────────────────────┘
              │                                        │
              ▼                                        ▼
   SAP_SPEND_ANALYST agent                  Native App "Ask the Agent"
   (Snowflake Intelligence)                 (Cortex Analyst in-app)
                                                        │
                                            React + Express on SPCS
```

## Spend Intelligence alignment (SAP)

| SAP Spend Intelligence pillar | Where it lives |
|-------------------------------|----------------|
| Total spend visibility | `DT_SPEND_360` (PO) + `DT_INVOICE_SPEND` (non-PO/AP/T&E) |
| Classification & taxonomy | `DT_CATEGORY_HIERARCHY` (direct/indirect, L2, addressable) |
| Savings / value leakage | `DT_SAVINGS_OPPORTUNITY` (off-contract, tail, price variance, terms, demand) |
| Supplier risk | `DT_SUPPLIER_RISK` (financial/geo/compliance, single-source) |
| Sustainability / ESG / diversity | `DT_SUPPLIER_RISK` (ESG pillars, sustainable & diverse spend) |
| AI / semantic / KPIs | `SAP_SPEND_360_ANALYTICS` + `SAP_SPEND_ANALYST` |

> Enrichment tables carry **representative demo values** aligned to SAP Spend
> Intelligence. In production these are populated by SAP BDC enrichment and
> third-party data (D&B, ESG providers, market indices).

## Native App packaging

The app bundles the 5 L2 tables into the package `SHARED_DATA` schema (no
consumer references) and rebuilds an in-app copy of `SAP_SPEND_360_ANALYTICS`
over `APP_DATA`. React client + Express server run on SPCS. See
[`app/`](../app) and [`INSTALL.md`](INSTALL.md).
