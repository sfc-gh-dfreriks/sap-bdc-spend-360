# SAP BDC Spend 360 — Spend Intelligence

A reference implementation showing how to turn **SAP Business Data Cloud (BDC)
Standard Data Products** into a live, AI-powered **Spend Intelligence** app on
Snowflake — using a **medallion architecture**, a governed **semantic view**, a
**Cortex Agent**, and a self-contained **Snowflake Native App** (React + Express
on Snowpark Container Services), deployable across multiple regions.

Zero ETL. Zero copy. Full SAP business context — **enriched** with supplier risk,
ESG/diversity, category taxonomy, and savings.

## What's in here
```
sap-bdc-spend-360/
├── sql/     01_l0_sources.md · 02_l1_curated_views · 03_l2_analytics_enrichment · 04_semantic_view · 05_cortex_agent
├── app/     Native App package (manifest, setup.sql, service_spec, snowflake.yml)
├── service/app/  React (Vite) client + Express server + Dockerfile
├── scripts/ build_and_push · migrate_data · deploy_native_app · create_org_listing
└── docs/    ARCHITECTURE.md · INSTALL.md · DEMO_GUIDE.md · demo deck (.pptx)
```

## Architecture at a glance
`SAP BDC Procurement (L0)` → `SAP_BDC_L1 curated views (L1)` →
`ANALYTICS spend + risk/ESG/savings (L2)` → `SAP_SPEND_360_ANALYTICS semantic view` →
`SAP_SPEND_ANALYST` + Native App "Ask the Agent". Detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Spend Intelligence coverage
Total spend visibility (PO + non-PO), spend **classification/taxonomy**,
**savings** pipeline, supplier **risk**, and **sustainability/diversity** — plus
AI/semantic + KPIs. See the coverage table in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## The app
A React dashboard: **Spend Overview, Categories, Suppliers, Supplier Risk,
Sustainability & Diversity, Savings Pipeline, Contract Compliance, Purchase
Orders**, plus an **Ask the Agent** page (Cortex Analyst over the bundled
`SAP_SPEND_360_ANALYTICS` view).

## Live reference deployment
Region-scoped organization listing (`ORGDATACLOUD$INTERNAL$SPEND_360_ORG`), 3 regions:

| Region | App URL |
|--------|---------|
| North America | https://aszht4-sfsenorthamerica-dfreriks-aws1-w2.snowflakecomputing.app |
| EMEA | https://eb3ite-sfseeurope-dfreriks-eu-demo.snowflakecomputing.app |
| APAC | https://ebhbbd-sfseapac-sap-data-product-demo.snowflakecomputing.app |

> URLs are the internal reference deployment; consumers get their own URL on install.

## Note on enrichment data
The supplier-risk, ESG, category-hierarchy and savings tables carry
**representative demo values** aligned to SAP Spend Intelligence. In production
these are fed by SAP BDC enrichment and third-party providers (D&B, ESG feeds,
market indices).

## Security notes
- No credentials committed. Scripts read key-pair connections from
  `~/.snowflake/connections.toml` by name; `.gitignore` excludes `*.p8`, `.env`, `connections.toml`.

## Sibling projects
`sap-bdc-finance-360` · `sap-bdc-supply-chain-360` · `sap-bdc-people-360` · `sap-bdc-sales-360`
