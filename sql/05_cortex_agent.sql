-- =====================================================================
-- Cortex Agent — SAP_SPEND_ANALYST (Snowflake Intelligence)
-- Prereqs: 04_semantic_view.sql + SNOWFLAKE.CORTEX_USER.
-- =====================================================================

CREATE OR REPLACE AGENT SAP_SPEND_360.AGENTS.SAP_SPEND_ANALYST
WITH PROFILE='{"display_name":"SAP Spend Analyst"}'
COMMENT='Natural-language analytics over SAP Spend 360 (spend by category/supplier, contract compliance, trends).'
FROM SPECIFICATION $$
{
  "models": {
    "orchestration": "auto"
  },
  "instructions": {
    "response": "Format spend as currency. Break out by category, supplier, or company where relevant. Contract compliance = on-contract spend / total spend.",
    "orchestration": "You are an SAP Spend/Procurement Analyst. Answer questions about total spend, spend by category (material group), by supplier (vendor), by company/entity, spend trends over time (PO_MONTH/PO_YEAR), supplier concentration, and contract compliance (IS_ON_CONTRACT). Spend is the SPEND fact (net PO amount). Use the SPEND table."
  },
  "tools": [
    {
      "tool_spec": {
        "type": "cortex_analyst_text_to_sql",
        "name": "query_spend_data",
        "description": "Query SAP procurement spend: by category, supplier, company, time; contract compliance; supplier concentration."
      }
    }
  ],
  "tool_resources": {
    "query_spend_data": {
      "execution_environment": {
        "query_timeout": 299,
        "type": "warehouse",
        "warehouse": "LOAD_WH"
      },
      "semantic_view": "SAP_SPEND_360.SEMANTIC.SAP_SPEND_360_ANALYTICS"
    }
  }
}
$$;
