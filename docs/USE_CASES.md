# Use Cases — SAP BDC Spend 360

> Procurement spend intelligence over SAP purchasing data products: categories, suppliers, contracts, risk, savings, ESG.

- **App:** spend_360_react (React, server 3007 / client 5181)
- **Semantic view:** `SAP_SPEND_360.SEMANTIC.SAP_SPEND_360_ANALYTICS`
- **Analytics tables:** DT_SPEND_360, DT_SUPPLIER_RISK, DT_CATEGORY_HIERARCHY, DT_SAVINGS_OPPORTUNITY
- **Catalog audited:** 2026-09-28. Each use case maps to an existing app page and to fields in the semantic view or API.

| # | Use case | Persona | App page |
|---|---|---|---|
| 1 | Spend cube | CPO / category manager | Overview; Categories |
| 2 | Contract compliance | Procurement ops | Contracts; Purchase Orders |
| 3 | Supplier consolidation | Category manager | Suppliers |
| 4 | Supplier risk | Supply risk manager | Supplier Risk |
| 5 | Savings pipeline | CPO / finance | Savings |
| 6 | Sustainable and diverse sourcing | ESG / supplier diversity lead | Sustainability |
| 7 | Procurement copilot | Any buyer | Analyst (Cortex Agent) |

## 1. Spend cube

- **Persona:** CPO / category manager
- **Business question:** Where does our money go by category, supplier and region?
- **Where in the app:** Overview; Categories
- **Data used:** SPEND, CATEGORY, L1_CATEGORY, L2_CATEGORY, SUPPLIER, REGION
- **Ask the agent:**
  - "What is spend by L1 category and region?"
- **Value:** Baseline for every sourcing decision.

## 2. Contract compliance

- **Persona:** Procurement ops
- **Business question:** How much spend is off-contract (maverick)?
- **Where in the app:** Contracts; Purchase Orders
- **Data used:** IS_ON_CONTRACT, SPEND, BUYER, PLANT
- **Ask the agent:**
  - "What percentage of spend is on contract by category?"
- **Value:** Recovers negotiated savings lost to maverick buying.

## 3. Supplier consolidation

- **Persona:** Category manager
- **Business question:** Where are we fragmented across too many suppliers?
- **Where in the app:** Suppliers
- **Data used:** SUPPLIER, CATEGORY_SPEND, TIER, ANNUAL_SPEND
- **Ask the agent:**
  - "Which categories have the most suppliers?"
- **Value:** Leverages volume for better terms.

## 4. Supplier risk

- **Persona:** Supply risk manager
- **Business question:** Which suppliers are single-source or high risk?
- **Where in the app:** Supplier Risk
- **Data used:** RISK_SCORE, IS_SINGLE_SOURCE, COUNTRY, TIER
- **Ask the agent:**
  - "Which single-source suppliers have the highest risk score?"
- **Value:** Prioritizes dual-sourcing and mitigation.

## 5. Savings pipeline

- **Persona:** CPO / finance
- **Business question:** What savings opportunities exist and how big are they?
- **Where in the app:** Savings
- **Data used:** ESTIMATED_SAVINGS, OPP_TYPE, IS_ADDRESSABLE, CATEGORY
- **Ask the agent:**
  - "What are the largest estimated savings opportunities by type?"
- **Value:** Builds a defensible savings plan.

## 6. Sustainable and diverse sourcing

- **Persona:** ESG / supplier diversity lead
- **Business question:** How much spend goes to sustainable and diverse suppliers?
- **Where in the app:** Sustainability
- **Data used:** ESG_SCORE, IS_SUSTAINABLE, IS_DIVERSE, DIVERSITY_CLASS, SPEND
- **Ask the agent:**
  - "What share of spend is with diverse suppliers by region?"
- **Value:** Tracks ESG and diversity commitments with real spend.

## 7. Procurement copilot

- **Persona:** Any buyer
- **Business question:** Ask spend questions in plain English.
- **Where in the app:** Analyst (Cortex Agent)
- **Data used:** Semantic view SAP_SPEND_360_ANALYTICS
- **Ask the agent:**
  - "Which suppliers grew spend the most year over year?"
- **Value:** Self-service analysis for buyers.

---
Example agent questions are suggested prompts; validate answers in the app before customer demos.
