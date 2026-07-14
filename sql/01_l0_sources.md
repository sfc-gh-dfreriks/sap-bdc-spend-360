# L0 — SAP BDC Standard Data Products (raw / bronze)

The **L0 (bronze)** layer is the set of **SAP Business Data Cloud procurement standard data products**, shared into Snowflake with **zero copy, no ETL**:

| Domain | SAP BDC Data Product | L1 object |
|---|---|---|
| Procurement | Purchase Order (item) | `SAP_BDC_L1.PURCHASE_ORDER_ITEM` |
| Master Data | Supplier | `SAP_BDC_L1.SUPPLIER` |

These land/curate into **L1** (`SAP_SPEND_360.SAP_BDC_L1`, see `02_l1_curated_views.sql`). All shaping + Spend Intelligence enrichment (supplier risk, ESG, category taxonomy, savings, non-PO spend) happens in **L2** (`SAP_SPEND_360.ANALYTICS`, see `03_l2_analytics_enrichment.sql`).

> Enrichment tables (`DT_SUPPLIER_RISK`, `DT_CATEGORY_HIERARCHY`, `DT_SAVINGS_OPPORTUNITY`, `DT_INVOICE_SPEND`) carry **representative demo values** aligned to SAP Spend Intelligence (risk scores, ESG/diversity, addressable spend, savings levers). In production these are fed by SAP BDC enrichment + third-party providers.
