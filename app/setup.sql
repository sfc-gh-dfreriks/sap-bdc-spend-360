-- =====================================================================
-- SAP Spend 360 Native App — SELF-CONTAINED setup script
-- Data is bundled in the package (SHARED_DATA). No consumer references.
-- Powers the SAP_SPEND_360_ANALYTICS Spend Intelligence semantic view
-- (the same model behind the account-level SAP_SPEND_ANALYST agent).
-- =====================================================================

CREATE APPLICATION ROLE IF NOT EXISTS app_public;

CREATE SCHEMA IF NOT EXISTS config;
GRANT USAGE ON SCHEMA config TO APPLICATION ROLE app_public;
CREATE TABLE IF NOT EXISTS config.settings(key STRING, value STRING);

CREATE SCHEMA IF NOT EXISTS app_data;
GRANT USAGE ON SCHEMA app_data TO APPLICATION ROLE app_public;

CREATE OR REPLACE VIEW app_data.DT_SPEND_360 AS SELECT * FROM shared_data.DT_SPEND_360;
GRANT SELECT ON VIEW app_data.DT_SPEND_360 TO APPLICATION ROLE app_public;
CREATE OR REPLACE VIEW app_data.DT_SUPPLIER_RISK AS SELECT * FROM shared_data.DT_SUPPLIER_RISK;
GRANT SELECT ON VIEW app_data.DT_SUPPLIER_RISK TO APPLICATION ROLE app_public;
CREATE OR REPLACE VIEW app_data.DT_CATEGORY_HIERARCHY AS SELECT * FROM shared_data.DT_CATEGORY_HIERARCHY;
GRANT SELECT ON VIEW app_data.DT_CATEGORY_HIERARCHY TO APPLICATION ROLE app_public;
CREATE OR REPLACE VIEW app_data.DT_SAVINGS_OPPORTUNITY AS SELECT * FROM shared_data.DT_SAVINGS_OPPORTUNITY;
GRANT SELECT ON VIEW app_data.DT_SAVINGS_OPPORTUNITY TO APPLICATION ROLE app_public;
CREATE OR REPLACE VIEW app_data.DT_INVOICE_SPEND AS SELECT * FROM shared_data.DT_INVOICE_SPEND;
GRANT SELECT ON VIEW app_data.DT_INVOICE_SPEND TO APPLICATION ROLE app_public;
-- Daily ECB reference rates (USD per unit), used to convert PO document currency.
CREATE OR REPLACE VIEW app_data.FX_RATES_CALENDAR AS SELECT * FROM shared_data.FX_RATES_CALENDAR;
GRANT SELECT ON VIEW app_data.FX_RATES_CALENDAR TO APPLICATION ROLE app_public;

-- Enriched Spend Intelligence semantic view over the bundled APP_DATA views.
create or replace semantic view app_data.SAP_SPEND_360_ANALYTICS
	tables (
		SPEND as APP_DATA.DT_SPEND_360 primary key (PO_ID,PO_ITEM) with synonyms=('spend','purchases','procurement','purchase orders') comment='Purchase-order line-item spend fact.',
		SUPPLIER_RISK as APP_DATA.DT_SUPPLIER_RISK primary key (SUPPLIER) with synonyms=('supplier risk','vendor risk','esg','sustainability','diversity') comment='Per-supplier risk, ESG, diversity and tier enrichment.',
		CATEGORY_HIERARCHY as APP_DATA.DT_CATEGORY_HIERARCHY primary key (CATEGORY) with synonyms=('category hierarchy','taxonomy') comment='Spend category taxonomy and addressability.',
		SAVINGS as APP_DATA.DT_SAVINGS_OPPORTUNITY primary key (OPP_ID) with synonyms=('savings','opportunities','savings pipeline') comment='Identified savings opportunities pipeline.'
	)
	relationships (
		SPEND_TO_CATEGORY as SPEND(CATEGORY) references CATEGORY_HIERARCHY(CATEGORY),
		SPEND_TO_SUPPLIER as SPEND(SUPPLIER) references SUPPLIER_RISK(SUPPLIER)
	)
	facts (
		SPEND.SPEND as SPEND comment='Net purchase amount.',
		SPEND.ORDER_QUANTITY as ORDER_QUANTITY comment='Ordered quantity.',
		SPEND.NET_PRICE as NET_PRICE comment='Net unit price.',
		SUPPLIER_RISK.RISK_SCORE as RISK_SCORE comment='Composite risk score 0-100.',
		SUPPLIER_RISK.ESG_SCORE as ESG_SCORE comment='ESG score 0-100.',
		SUPPLIER_RISK.ANNUAL_SPEND as ANNUAL_SPEND comment='Supplier annual spend.',
		CATEGORY_HIERARCHY.CATEGORY_SPEND as CATEGORY_SPEND comment='Category total spend.',
		SAVINGS.ESTIMATED_SAVINGS as ESTIMATED_SAVINGS comment='Estimated savings amount.'
	)
	dimensions (
		SPEND.PO_ID as PO_ID comment='Purchase order number.',
		SPEND.SUPPLIER as SUPPLIER with synonyms=('vendor') comment='Supplier identifier.',
		SPEND.CATEGORY as CATEGORY with synonyms=('spend category','commodity') comment='Spend category.',
		SPEND.COMPANY as COMPANY with synonyms=('company code','entity') comment='Operating company.',
		SPEND.PLANT as PLANT comment='Plant/site.',
		SPEND.BUYER as BUYER comment='Buyer.',
		SPEND.PO_YEAR as PO_YEAR with synonyms=('year') comment='PO year.',
		SPEND.PO_MONTH as PO_MONTH with synonyms=('month') comment='PO month (YYYY-MM).',
		SPEND.IS_ON_CONTRACT as IS_ON_CONTRACT with synonyms=('on contract','contract compliance') comment='True if against a contract.',
		SUPPLIER_RISK.SUPPLIER_TIER as TIER with synonyms=('supplier tier') comment='Strategic/Preferred/Approved/Tail.',
		SUPPLIER_RISK.SUPPLIER_COUNTRY as COUNTRY comment='Supplier country.',
		SUPPLIER_RISK.SUPPLIER_REGION as REGION comment='Supplier region.',
		SUPPLIER_RISK.IS_SINGLE_SOURCE as IS_SINGLE_SOURCE with synonyms=('single source') comment='True if single-source supplier.',
		SUPPLIER_RISK.IS_SUSTAINABLE as IS_SUSTAINABLE with synonyms=('sustainable supplier') comment='True if sustainable.',
		SUPPLIER_RISK.IS_DIVERSE as IS_DIVERSE with synonyms=('diverse supplier') comment='True if diverse-owned.',
		SUPPLIER_RISK.DIVERSITY_CLASS as DIVERSITY_CLASS comment='Diversity classification.',
		CATEGORY_HIERARCHY.L1_CATEGORY as L1_CATEGORY with synonyms=('direct indirect') comment='Direct vs Indirect.',
		CATEGORY_HIERARCHY.L2_CATEGORY as L2_CATEGORY comment='Category group.',
		CATEGORY_HIERARCHY.IS_ADDRESSABLE as IS_ADDRESSABLE with synonyms=('addressable') comment='Addressable spend flag.',
		SAVINGS.OPP_TYPE as OPP_TYPE with synonyms=('opportunity type','savings lever') comment='Savings lever type.',
		SAVINGS.SAVINGS_STATUS as STATUS comment='Identified/In-progress/Realized.'
	)
	metrics (
		SPEND.TOTAL_SPEND as SUM(SPEND.SPEND) comment='Total PO spend.',
		SPEND.PO_LINE_COUNT as COUNT(SPEND.PO_ID) comment='PO line count.',
		SPEND.ON_CONTRACT_SPEND as SUM(CASE WHEN SPEND.IS_ON_CONTRACT THEN SPEND.SPEND ELSE 0 END) comment='On-contract spend.',
		SUPPLIER_RISK.SUPPLIER_COUNT as COUNT(SUPPLIER_RISK.SUPPLIER) comment='Number of suppliers.',
		SUPPLIER_RISK.AVG_RISK_SCORE as AVG(SUPPLIER_RISK.RISK_SCORE) comment='Average supplier risk score.',
		SUPPLIER_RISK.AVG_ESG_SCORE as AVG(SUPPLIER_RISK.ESG_SCORE) comment='Average supplier ESG score.',
		SUPPLIER_RISK.SINGLE_SOURCE_SPEND as SUM(CASE WHEN SUPPLIER_RISK.IS_SINGLE_SOURCE THEN SUPPLIER_RISK.ANNUAL_SPEND ELSE 0 END) comment='Spend with single-source suppliers.',
		SUPPLIER_RISK.DIVERSE_SPEND as SUM(CASE WHEN SUPPLIER_RISK.IS_DIVERSE THEN SUPPLIER_RISK.ANNUAL_SPEND ELSE 0 END) comment='Spend with diverse suppliers.',
		SUPPLIER_RISK.SUSTAINABLE_SPEND as SUM(CASE WHEN SUPPLIER_RISK.IS_SUSTAINABLE THEN SUPPLIER_RISK.ANNUAL_SPEND ELSE 0 END) comment='Spend with sustainable suppliers.',
		CATEGORY_HIERARCHY.ADDRESSABLE_SPEND as SUM(CASE WHEN CATEGORY_HIERARCHY.IS_ADDRESSABLE THEN CATEGORY_HIERARCHY.CATEGORY_SPEND ELSE 0 END) comment='Addressable spend.',
		SAVINGS.TOTAL_IDENTIFIED_SAVINGS as SUM(SAVINGS.ESTIMATED_SAVINGS) comment='Total identified savings.',
		SAVINGS.REALIZED_SAVINGS as SUM(CASE WHEN SAVINGS.SAVINGS_STATUS = 'Realized' THEN SAVINGS.ESTIMATED_SAVINGS ELSE 0 END) comment='Realized savings.',
		SAVINGS.OPPORTUNITY_COUNT as COUNT(SAVINGS.OPP_ID) comment='Number of savings opportunities.'
	)
	comment='SAP Spend 360 Spend Intelligence: total spend, supplier risk & ESG, category taxonomy, savings pipeline.';
GRANT SELECT ON SEMANTIC VIEW app_data.SAP_SPEND_360_ANALYTICS TO APPLICATION ROLE app_public;

DELETE FROM config.settings WHERE key = 'semantic_view';
INSERT INTO config.settings(key, value)
  SELECT 'semantic_view', CURRENT_DATABASE() || '.APP_DATA.SAP_SPEND_360_ANALYTICS';

CREATE SCHEMA IF NOT EXISTS services;
GRANT USAGE ON SCHEMA services TO APPLICATION ROLE app_public;

CREATE OR ALTER VERSIONED SCHEMA core;
GRANT USAGE ON SCHEMA core TO APPLICATION ROLE app_public;

CREATE OR REPLACE PROCEDURE core.version_init()
  RETURNS STRING LANGUAGE SQL EXECUTE AS OWNER
AS $$
DECLARE
  pool_name VARCHAR; wh_name VARCHAR; svc_count INTEGER;
BEGIN
  pool_name := (SELECT CURRENT_DATABASE()) || '_POOL';
  wh_name   := (SELECT CURRENT_DATABASE()) || '_WH';
  CREATE COMPUTE POOL IF NOT EXISTS IDENTIFIER(:pool_name)
    MIN_NODES = 1 MAX_NODES = 1 INSTANCE_FAMILY = CPU_X64_XS
    AUTO_RESUME = TRUE AUTO_SUSPEND_SECS = 300;
  CREATE WAREHOUSE IF NOT EXISTS IDENTIFIER(:wh_name)
    WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;
  SHOW SERVICES LIKE 'SPEND_360_SERVICE' IN SCHEMA services;
  svc_count := (SELECT COUNT(*) FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())));
  IF (:svc_count = 0) THEN
    CREATE SERVICE services.spend_360_service
      IN COMPUTE POOL IDENTIFIER(:pool_name)
      FROM SPECIFICATION_FILE = '/service_spec.yml'
      MIN_INSTANCES = 1 MAX_INSTANCES = 1;
    GRANT USAGE ON SERVICE services.spend_360_service TO APPLICATION ROLE app_public;
    GRANT SERVICE ROLE services.spend_360_service!spend_360_role TO APPLICATION ROLE app_public;
  ELSE
    ALTER SERVICE services.spend_360_service FROM SPECIFICATION_FILE = '/service_spec.yml';
    CALL SYSTEM$WAIT_FOR_SERVICES(600, 'services.spend_360_service');
  END IF;
  RETURN 'version_init ok';
END;
$$;
GRANT USAGE ON PROCEDURE core.version_init() TO APPLICATION ROLE app_public;

CREATE OR REPLACE PROCEDURE core.suspend_service() RETURNS STRING LANGUAGE SQL EXECUTE AS OWNER
AS $$ BEGIN ALTER SERVICE services.spend_360_service SUSPEND; RETURN 'suspended'; END; $$;
GRANT USAGE ON PROCEDURE core.suspend_service() TO APPLICATION ROLE app_public;

CREATE OR REPLACE PROCEDURE core.resume_service() RETURNS STRING LANGUAGE SQL EXECUTE AS OWNER
AS $$ BEGIN ALTER SERVICE services.spend_360_service RESUME; RETURN 'resumed'; END; $$;
GRANT USAGE ON PROCEDURE core.resume_service() TO APPLICATION ROLE app_public;

CREATE OR REPLACE PROCEDURE core.get_service_status() RETURNS STRING LANGUAGE SQL EXECUTE AS OWNER
AS $$ DECLARE status VARCHAR; BEGIN CALL SYSTEM$GET_SERVICE_STATUS('services.spend_360_service') INTO :status; RETURN :status; END; $$;
GRANT USAGE ON PROCEDURE core.get_service_status() TO APPLICATION ROLE app_public;

CREATE OR REPLACE PROCEDURE core.get_service_logs(instance_id STRING, container_name STRING) RETURNS STRING LANGUAGE SQL EXECUTE AS OWNER
AS $$ DECLARE logs VARCHAR; BEGIN CALL SYSTEM$GET_SERVICE_LOGS('services.spend_360_service', :instance_id, :container_name, 200) INTO :logs; RETURN :logs; END; $$;
GRANT USAGE ON PROCEDURE core.get_service_logs(STRING, STRING) TO APPLICATION ROLE app_public;

CREATE OR REPLACE PROCEDURE core.app_url() RETURNS STRING LANGUAGE SQL EXECUTE AS OWNER
AS $$ DECLARE url VARCHAR;
BEGIN
  SHOW ENDPOINTS IN SERVICE services.spend_360_service;
  SELECT "ingress_url" INTO :url FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" = 'spend360';
  RETURN :url;
END; $$;
GRANT USAGE ON PROCEDURE core.app_url() TO APPLICATION ROLE app_public;

CREATE OR REPLACE PROCEDURE core.selftest() RETURNS STRING LANGUAGE SQL EXECUTE AS OWNER
AS $$ DECLARE sp INTEGER; sr INTEGER;
BEGIN
  SELECT COUNT(*) INTO :sp FROM app_data.DT_SPEND_360;
  SELECT COUNT(*) INTO :sr FROM app_data.DT_SUPPLIER_RISK;
  RETURN 'bundled data OK — DT_SPEND_360=' || :sp || ' rows, DT_SUPPLIER_RISK=' || :sr || ' rows';
END; $$;
GRANT USAGE ON PROCEDURE core.selftest() TO APPLICATION ROLE app_public;
