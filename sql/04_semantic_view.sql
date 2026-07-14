-- =====================================================================
-- Semantic layer — SAP_SPEND_360_ANALYTICS (Spend Intelligence)
-- Spend + supplier risk/ESG + category taxonomy + savings, with
-- relationships. Powers the Native App and the SAP_SPEND_ANALYST agent.
-- =====================================================================

create or replace semantic view SAP_SPEND_360.SEMANTIC.SAP_SPEND_360_ANALYTICS
	tables (
		SPEND as SAP_SPEND_360.ANALYTICS.DT_SPEND_360 primary key (PO_ID,PO_ITEM) with synonyms=('spend','purchases','procurement','purchase orders') comment='Purchase-order line-item spend fact.',
		SUPPLIER_RISK as SAP_SPEND_360.ANALYTICS.DT_SUPPLIER_RISK primary key (SUPPLIER) with synonyms=('supplier risk','vendor risk','esg','sustainability','diversity') comment='Per-supplier risk, ESG, diversity and tier enrichment.',
		CATEGORY_HIERARCHY as SAP_SPEND_360.ANALYTICS.DT_CATEGORY_HIERARCHY primary key (CATEGORY) with synonyms=('category hierarchy','taxonomy') comment='Spend category taxonomy and addressability.',
		SAVINGS as SAP_SPEND_360.ANALYTICS.DT_SAVINGS_OPPORTUNITY primary key (OPP_ID) with synonyms=('savings','opportunities','savings pipeline') comment='Identified savings opportunities pipeline.'
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
