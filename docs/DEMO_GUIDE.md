# Demo Guide — SAP BDC Spend 360 (Spend Intelligence)

A ~10-minute flow showing how Snowflake × SAP Business Data Cloud turns SAP
procurement data into a live, AI-powered **Spend Intelligence** app. Full deck
(with presenter notes): [`SAP_Spend_360_Demo_Guide.pptx`](SAP_Spend_360_Demo_Guide.pptx).

## The story in one line
Two platforms, one governed data foundation: SAP BDC shares governed spend data
into Snowflake with **zero copy**; Snowflake enriches it (risk, ESG, savings) and
adds AI — no pipelines, full SAP context preserved.

## 10-minute flow
1. **Open the app** — no setup; data is already inside (bundled Native App).
2. **Spend Overview** — total spend, categories, suppliers, contract compliance.
3. **Categories & Suppliers** — spend cube, concentration, top vendors.
4. **Supplier Risk** — risk matrix, high-risk & single-source suppliers, risk by region.
5. **Sustainability & Diversity** — ESG pillars, sustainable spend, diverse spend.
6. **Savings Pipeline** — savings by lever & status, realized vs identified.
7. **Ask the Agent** — live questions to `SAP_SPEND_ANALYST`:
   - "What is our diverse and sustainable spend?"
   - "Which suppliers are highest risk and single-source?"
   - "What savings are identified by lever?"
8. **Recap** — zero-ETL, governed, enriched, AI-ready, one-click distribution.

## Key points to land
- Total spend visibility (PO + non-PO) — **already inside Snowflake**, no ETL.
- SAP context **enriched**: supplier risk, ESG/diversity, addressable spend, savings.
- `SAP_SPEND_ANALYST` answers live, in plain English, with governed SQL.
- One definition → **three regions** (US, EMEA, APAC), each its own governed install.

## Do / Don't
- **Do** open Supplier Risk + Sustainability — these are the SAP Spend Intelligence differentiators.
- **Don't** pre-load canned answers or dwell on architecture/SQL.
- **Note** enrichment values are representative demo data (production uses SAP BDC + third-party feeds).
