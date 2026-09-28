#!/usr/bin/env python3
"""Build the SAP Spend 360 presales kit documents.

Mirrors the People 360, Finance 360 and Sales 360 builders so the kits read as a set:

    00_START_HERE.docx               what is in the kit and which file to open
    01_Management_Summary.docx       customer-safe summary
    02_Demo_Scripts_by_Persona.docx  one script per persona in the room
    03_SE_Quick_Start.docx           positioning, demo path, objections
    05_Architecture_and_Install.docx the medallion stack and how to stand it up
    06_Setup_and_Access.docx         the three regions, the listing, access

Every figure comes from /tmp/spend_facts.json, produced by tools/spend_facts.py
against the live account. Nothing is transcribed by hand.

Two Spend-specific rules are enforced everywhere:
  * Money is quoted in USD, each PO line converted at the ECB reference rate for
    its PO date - the same conversion the app applies when USD is selected.
  * Risk, ESG, diversity and savings live in representative enrichment tables.
    Savings are quoted by lever percentage and as a converted USD pipeline.

    python3 tools/spend_facts.py && python3 tools/build_presales_kit.py
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import date

from docx import Document
from docx.shared import Pt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from docx_kit import (  # noqa: E402
    GREY,
    SAP_NAVY,
    SNOW_BLUE,
    body,
    bullet,
    callout,
    h1,
    h2,
    setup_page,
    table,
)

KIT = pathlib.Path.home() / "Documents" / "SAP" / "Spend_360_Presales_Kit"
FACTS_FILE = pathlib.Path("/tmp/spend_facts.json")
DATE = date.today().strftime("%d %B %Y")
NAME = "SAP Spend 360"

PAGE_PURPOSE = {
    "Spend Overview": "Total spend, PO lines, suppliers, contract coverage, trend",
    "Categories": "Spend by category and the L1/L2/L3 taxonomy, addressable spend",
    "Suppliers": "Top suppliers, concentration, tail spend",
    "Supplier Risk": "Risk score by tier and region, single-source exposure",
    "Sustainability & Diversity": "ESG scores and diverse-supplier spend",
    "Savings Pipeline": "Savings opportunities by lever and status",
    "Contract Compliance": "On- versus off-contract spend by category and buyer",
    "Purchase Orders": "The PO-line table, filterable",
    "BDC Sources & Lineage": "Which SAP BDC data products feed each layer",
    "Ask the Agent": "Natural-language questions over the spend semantic view",
}


def load_facts() -> dict:
    if not FACTS_FILE.exists():
        sys.exit(f"{FACTS_FILE} missing — run tools/spend_facts.py first")
    return json.loads(FACTS_FILE.read_text())["facts"]


def usd(v) -> str:
    v = float(v)
    return f"${v / 1e6:,.2f}M" if v >= 1e6 else f"${v / 1e3:,.0f}K"


def fx_text(F) -> str:
    r = {x["CURRENCY"]: x for x in F["fx_ranges"]}
    return (f"ECB reference rate on each PO date; EUR {r['EUR']['MIN_PER_USD']}-{r['EUR']['MAX_PER_USD']} "
            f"and JPY {r['JPY']['MIN_PER_USD']:.0f}-{r['JPY']['MAX_PER_USD']:.0f} per USD over the window")


def title_block(doc, title, subtitle, strap):
    for text_, size, bold, color, after in (
        (title, 20, True, SAP_NAVY, 2),
        (subtitle, 11.5, False, SNOW_BLUE, 2),
        (strap, 9, False, GREY, 14),
    ):
        p = doc.add_paragraph()
        r = p.add_run(text_)
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        p.paragraph_format.space_after = Pt(after)


def new_doc(subtitle, strap):
    doc = Document()
    setup_page(doc)
    title_block(doc, NAME, subtitle, strap)
    return doc


def currency_callout(doc, F):
    comps = "; ".join(f"{c['COMPANY']} {c['CURRENCY']} {c['SPEND_NATIVE']:,.0f} ({usd(c['SPEND_USD'])})"
                      for c in F["spend_by_company_native"])
    callout(
        doc,
        "Currency: pick the reporting currency",
        f"Each company buys in its own currency: {comps}. The Reporting Currency switch in "
        f"the sidebar (USD, EUR, JPY) converts every PO line at the ECB reference rate for its "
        f"PO date, on every page, so all three companies can be shown together. This kit quotes "
        f"USD: about {usd(F['total_spend_usd'])} in total. It is worth showing the switch: most "
        f"spend tools convert at one period-end rate, not per transaction.",
    )


def enrichment_callout(doc, F):
    callout(
        doc,
        "What is SAP data and what is representative",
        f"Purchase orders and suppliers come from SAP BDC data products, shared zero copy. "
        f"Supplier risk, ESG and diversity, the category taxonomy, savings opportunities "
        f"and non-PO invoices live in {len(F['enrichment_tables'])} enrichment tables "
        f"({', '.join(F['enrichment_tables'])}) holding representative demo values, aligned "
        f"to how SAP Spend Intelligence enriches spend. In production these come from SAP "
        f"BDC enrichment and third-party providers. Say so when you show those pages.",
    )


def agent_scope_callout(doc, F):
    sv = next(iter(F["semantic_view_detail"].values()))
    callout(
        doc,
        "What the agent knows",
        f"Ask the Agent reads the semantic view, which covers {sv['tables']} tables "
        f"({', '.join(sv['table_names'])}) with {sv['dimensions']} dimensions, {sv['facts']} "
        f"facts and {sv['metrics']} metrics, and {sv['verified_queries']} verified queries. "
        f"It does not cover non-PO invoice spend. The agent does not yet use the currency "
        f"switch: its spend is in each PO's own currency, so ask it about one company, or ask "
        f"it to group by currency.",
    )


def headline_rows(F):
    sv = next(iter(F["semantic_view_detail"].values()))
    return [
        ["Spend in scope", f"{usd(F['total_spend_usd'])} across {F['po_lines']:,} PO lines, converted to USD"],
        ["Data window", f"POs dated {F['po_window'][0]} to {F['po_window'][1]}"],
        ["Supply base", f"{F['suppliers']} suppliers in {F['categories']} categories, {F['companies']} companies"],
        ["Contract coverage", f"{F['on_contract_pct_usd']}% of spend on contract; {usd(F['off_contract_spend_usd'])} off contract"],
        ["Concentration", f"Top 10 suppliers hold {F['top10_supplier_share_pct_usd']}% of spend"],
        ["Risk (representative)", f"{F['high_risk_suppliers']} suppliers with risk score 70+, {F['single_source_suppliers']} single-source"],
        ["Semantic view", f"{sv['tables']} tables, {sv['dimensions']} dimensions, {sv['metrics']} metrics"],
        ["App", f"{F['app_page_count']} pages, published in {len(F['regions'])} regions"],
    ]


# ---------------------------------------------------------------- START HERE

def build_start_here(F):
    doc = new_doc("Presales kit — start here", f"SAP Partnership Compass  ·  {DATE}  ·  Owner: Dave Freriks")
    body(doc,
         "Spend 360 shows SAP procurement data working as spend analytics on Snowflake, "
         "reached through SAP Business Data Cloud with zero copy. Spend by category and "
         "supplier, contract compliance, supplier risk, sustainability and a savings "
         "pipeline in one governed model, with a Cortex Agent over it. It installs as a "
         "self-contained Native App — nothing to configure, no data to load.")
    callout(doc, "Fastest path to a demo",
            f"Install the Native App listing {F['app_listing']} from the internal Marketplace "
            f"in your nearest region, open it, and you have a {F['app_page_count']}-page "
            f"spend dashboard with its own data already inside. See 06_Setup_and_Access.")
    currency_callout(doc, F)
    table(doc, ["The demo in eight numbers", "Value"], headline_rows(F), widths=[2.2, 4.5])
    body(doc,
         f"Every figure above was read from the account on {F['verified_on']}, not copied "
         f"from a previous deck. Money is USD, converted at the {fx_text(F)}.", italic=True)

    h1(doc, "Which file to open")
    table(doc, ["File", "Use it when", "Read time"], [
        ["03_SE_Quick_Start.docx", "You are demoing this week. Positioning, a ten-minute path, the agent "
         "questions, discovery questions, objections. Start here.", "10 min"],
        ["02_Demo_Scripts_by_Persona.docx", "You know who is in the room — CPO, category manager, supply "
         "risk, CFO, architect. Each script opens on a different page.", "per script"],
        ["01_Management_Summary.docx", "Leaving something with the customer, or briefing an exec. "
         "Customer-safe and explicit about what is representative.", "15 min"],
        ["00_Presales_Overview.pptx", "You need slides: the problem, the architecture, the app, the agent, "
         "regions, and the ask.", "10 slides"],
        ["SAP_Spend_360_Demo.pptx", "A screenshot-led walkthrough of the app to present or leave behind.", "slides"],
        ["SAP_Spend_360_Walkthrough.mp4", "Watch before your first demo, or send ahead of a meeting.", "video"],
        ["05_Architecture_and_Install.docx", "An architect is in the room, or you are standing it up yourself.", "reference"],
        ["06_Setup_and_Access.docx", "You need access: the listing, the three regions, the public build.", "5 min"],
    ], widths=[2.1, 3.8, 0.8])
    enrichment_callout(doc, F)

    h1(doc, "The companion kits")
    body(doc,
         "Sibling kits follow the same pattern on the same Compass page: Finance 360, Sales "
         "360, People 360, Supply Chain 360 and Supply Chain Ontology. Spend pairs naturally "
         "with Finance 360 (spend against P&L) and Supply Chain 360 (supplier quality "
         "against supplier risk). Cloud ERP 360 joins Finance, Spend and People by company.")
    h1(doc, "Support")
    body(doc, f"Source and documentation: {F['repo']}. Questions: Dave Freriks.")
    out = KIT / "00_START_HERE.docx"
    doc.save(out)
    return out


# ---------------------------------------------------------- MANAGEMENT SUMMARY

def build_management_summary(F):
    doc = new_doc("Management summary", f"Procurement spend intelligence on SAP BDC data  ·  {DATE}")
    h1(doc, "The problem")
    body(doc,
         "Procurement leaders are asked where the money goes, how much of it is under "
         "contract, and which suppliers the business depends on. The data exists in SAP, "
         "but answering usually means an extract, a spreadsheet, and a week of cleanup — "
         "by which time the question has changed.")
    h1(doc, "What Spend 360 does")
    for t in [
        "Reads SAP purchase-order and supplier data through SAP Business Data Cloud zero-copy shares — no extract, no second copy.",
        "Builds one governed spend model: category, supplier, company, buyer, plant and contract status on every PO line.",
        "Adds the lenses spend intelligence needs: supplier risk, single-source exposure, ESG and diversity, and a savings pipeline by lever.",
        "Lets anyone ask questions in plain English through a Cortex Agent over the same governed model the dashboards use.",
        "Installs as a Native App, published in three Snowflake regions.",
    ]:
        bullet(doc, t)

    h1(doc, "What the demo dataset shows")
    table(doc, ["Measure", "Value"], headline_rows(F)[:6], widths=[2.2, 4.5])
    body(doc, f"USD, converted at the {fx_text(F)}. "
              f"Figures read from the account on {F['verified_on']}.", italic=True)

    h2(doc, "Where the spend sits")
    table(doc, ["Category", "Spend (USD eq.)", "On contract"],
          [[c["CATEGORY"], usd(c["SPEND_USD"]), f"{c['ON_CONTRACT_PCT']}%"] for c in F["spend_by_category_usd"][:8]],
          widths=[2.8, 2.0, 1.9])

    h2(doc, "Savings pipeline")
    table(doc, ["Lever", "Opportunities", "Typical saving"],
          [[x["OPP_TYPE"], str(x["OPPS"]), f"{x['SAVINGS_PCT']}% of addressed spend"] for x in F["savings_levers"]],
          widths=[2.8, 1.5, 2.4])
    table(doc, ["Status", "Opportunities", "Savings (USD)"],
          [[x["STATUS"], str(x["OPPS"]), usd(x["SAVINGS_USD"])] for x in F["savings_by_status_usd"]],
          widths=[2.8, 1.5, 2.4])
    body(doc, f"{usd(F['savings_total_usd'])} of representative opportunities, converted to USD. "
              "Treat the pipeline as illustrative of the method rather than a forecast.", italic=True)

    h1(doc, "What is real, and what is representative")
    enrichment_callout(doc, F)
    body(doc,
         "Each company buys in its own currency (USD, EUR, JPY). The app converts every PO line "
         "at the European Central Bank reference rate for its PO date into the reporting "
         "currency the user picks, so totals are comparable across companies.")

    h1(doc, "Why Snowflake")
    for t in [
        "Zero copy: SAP data is governed once, not duplicated into a separate analytics store.",
        "One semantic model serves dashboards, the agent and any BI tool — the same definition of spend everywhere.",
        "Governance is enforced in the platform: row access by company or buyer, masking on sensitive supplier terms.",
        "It extends cleanly: add invoices, contracts or third-party risk feeds as further data products.",
    ]:
        bullet(doc, t)
    h1(doc, "Suggested next step")
    body(doc,
         "A scoped proof of value on the customer's own SAP BDC procurement data products: "
         "the same medallion SQL, semantic view and agent, pointed at their L0 layer, with "
         "currency conversion and their category taxonomy built in.")
    out = KIT / "01_Management_Summary.docx"
    doc.save(out)
    return out


# -------------------------------------------------------------- DEMO SCRIPTS

PERSONAS = [
    ("Chief Procurement Officer", "Where does our money go, and how much of it do we control?",
     "Spend Overview", [
         ("Spend Overview", lambda F: f"Show spend, suppliers ({F['suppliers']}) and contract coverage ({F['on_contract_pct_usd']}% USD-equivalent)."),
         ("Contract Compliance", lambda F: f"{usd(F['off_contract_spend_usd'])} is off contract. That is the controllable number."),
         ("Savings Pipeline", lambda F: "Walk the five levers and their typical percentages. Identified, in progress and realised."),
         ("Ask the Agent", lambda F: "Ask: 'Which categories have the most off-contract spend?'"),
     ], "Contract leakage is the fastest money in procurement, and this shows it by category and buyer."),
    ("Category manager", "Which categories are fragmented, and where can I consolidate?",
     "Categories", [
         ("Categories", lambda F: f"Spend by category; {F['spend_by_category_usd'][0]['CATEGORY']} is the largest. Show the L1/L2/L3 taxonomy."),
         ("Suppliers", lambda F: f"Top 10 suppliers hold {F['top10_supplier_share_pct_usd']}% of spend. The long tail is the consolidation target."),
         ("Savings Pipeline", lambda F: "Point at tail-spend and off-contract consolidation levers."),
         ("Ask the Agent", lambda F: "Ask: 'What is supplier concentration in IT Hardware?'"),
     ], "Consolidation starts with seeing the tail, and the tail is visible here without a spreadsheet."),
    ("Supply risk manager", "Which suppliers could hurt us if they failed?",
     "Supplier Risk", [
         ("Supplier Risk", lambda F: f"{F['high_risk_suppliers']} suppliers score 70+; {F['single_source_suppliers']} are single-source. Say the scores are representative."),
         ("Suppliers", lambda F: "Cross-check: which high-risk suppliers also carry significant spend?"),
         ("Sustainability & Diversity", lambda F: f"Average ESG score {F['avg_esg_score']}; ESG is part of supplier risk now."),
     ], "Risk and spend in one model lets you prioritise mitigation by exposure, not by alphabet."),
    ("CFO / finance partner", "Is procurement delivering savings we can see in the P&L?",
     "Savings Pipeline", [
         ("Spend Overview", lambda F: "Switch the reporting currency: every PO line converts at its own PO-date ECB rate, not one period-end rate."),
         ("Savings Pipeline", lambda F: "Show status: identified versus realised. Realised is what finance counts."),
         ("Contract Compliance", lambda F: "Off-contract spend is where negotiated savings leak."),
     ], "Pair with Finance 360 or Cloud ERP 360 to put spend next to the P&L by company."),
    ("Data architect", "How is this built, and could we run it on our data?",
     "BDC Sources & Lineage", [
         ("BDC Sources & Lineage", lambda F: "Show the path: SAP BDC data product to L1 view to gold table to semantic view to app."),
         ("Ask the Agent", lambda F: "Ask a question, then expand the generated SQL: governed and explainable."),
         ("Purchase Orders", lambda F: f"Record-level PO lines ({F['po_lines']:,}) are the grain of the gold table."),
     ], "The deliverable is the SQL, the semantic view and the agent. Swap the L0 layer for your own data products."),
]


def build_demo_scripts(F):
    doc = new_doc("Demo scripts by persona", f"Five scripts, each opening on a different page  ·  {DATE}")
    body(doc, "Pick the script for the most senior person in the room. Each runs five to eight minutes.")
    currency_callout(doc, F)
    for name, question, opener, steps, close in PERSONAS:
        h1(doc, name)
        body(doc, f"Their question: {question}", italic=True)
        body(doc, f"Open on: {opener}")
        table(doc, ["#", "Page", "Do and say"],
              [[str(i), p, fn(F)] for i, (p, fn) in enumerate(steps, 1)], widths=[0.3, 1.7, 4.7])
        callout(doc, "Close with", close)
    out = KIT / "02_Demo_Scripts_by_Persona.docx"
    doc.save(out)
    return out


# --------------------------------------------------------------- QUICK START

def build_quick_start(F):
    doc = new_doc("SE quick start", f"Ten-minute demo path, the agent's scope, and objection handling  ·  {DATE}")
    body(doc, "Read once, the day before you demo. It assumes you have not opened the app.")
    h1(doc, "Positioning, in three sentences")
    bullet(doc, "Procurement leaders need to know where money goes, how much is under contract and which "
                "suppliers they depend on — and the data sits in SAP behind an extract request.")
    bullet(doc, "SAP Business Data Cloud shares purchase-order and supplier data into Snowflake with zero "
                "copy, keeping SAP's structure rather than rebuilding it in a spreadsheet.")
    bullet(doc, "Snowflake adds the governed spend model, the natural-language agent and the app.")
    h1(doc, "Before you start")
    bullet(doc, f"Install the Native App ({F['app_listing']}) in your nearest region, or open the public build to rehearse. Open it once to warm the container.")
    bullet(doc, "Pick the reporting currency for the audience (USD, EUR or JPY) in the sidebar before the call.")
    bullet(doc, f"Know the window: POs dated {F['po_window'][0]} to {F['po_window'][1]}.")
    bullet(doc, "Decide how you will introduce the representative enrichment data. Say it when you open Supplier Risk.")
    currency_callout(doc, F)

    h1(doc, "The ten-minute path")
    table(doc, ["#", "Page", "Do and say", "Time"], [
        ["1", "—", "Open the app cold. Nothing installed, nothing loaded; purchase orders and suppliers are SAP BDC data products.", "1 min"],
        ["2", "Spend Overview", f"Spend, suppliers, contract coverage: {F['on_contract_pct_usd']}% on contract. Flip the currency switch once.", "1 min"],
        ["3", "Categories", f"Spend by category and taxonomy. {F['spend_by_category_usd'][0]['CATEGORY']} leads.", "1 min"],
        ["4", "Contract Compliance", f"{usd(F['off_contract_spend_usd'])} off contract. This is where procurement leaders lean in.", "2 min"],
        ["5", "Supplier Risk", f"{F['high_risk_suppliers']} high-risk and {F['single_source_suppliers']} single-source suppliers. Representative scores.", "1 min"],
        ["6", "Savings Pipeline", f"Five levers, 2-6% each; {usd(F['savings_total_usd'])} pipeline by status (representative).", "1 min"],
        ["7", "Ask the Agent", "Ask a built-in question, then expand the generated SQL.", "2 min"],
        ["8", "BDC Sources & Lineage", "Close here for a technical room: the zero-copy proof.", "1 min"],
    ], widths=[0.3, 1.5, 4.2, 0.7])

    h2(doc, "The questions the agent ships with")
    body(doc, "Read from the app's source, so these are exactly the chips on screen.")
    for q in F["agent_questions"]:
        bullet(doc, q)
    agent_scope_callout(doc, F)

    h1(doc, "What is on each page")
    table(doc, ["Page", "What it shows"], [[p, PAGE_PURPOSE.get(p, "—")] for p in F["app_pages"]], widths=[1.9, 4.8])

    h1(doc, "Discovery questions")
    for q in [
        "How long does it take today to answer 'how much did we spend with this supplier last year'?",
        "What share of spend do you believe is under contract, and how do you know?",
        "Do you run SAP Ariba or SAP Spend Intelligence today, and what do you do with the output?",
        "How do you assess supplier risk now, and does it connect to spend?",
        "Do you report spend in one currency, and where does the conversion happen?",
        "Are you on RISE with SAP, and is BDC part of that subscription?",
    ]:
        bullet(doc, q)

    h1(doc, "Objections, and what to say")
    table(doc, ["They say", "You say"], [
        ["What exchange rate did you use?", "The ECB reference rate on each PO date, loaded into Snowflake as a rates table. "
         "In production you would use the customer's own treasury rates (SAP TCURR) the same way."],
        ["Are these risk and ESG scores real?", "They are representative demo values in enrichment tables. In production they come from "
         "SAP BDC enrichment or a third-party provider joined on supplier ID."],
        ["Our procurement data cannot leave SAP.", "It does not. BDC shares it zero copy; there is no extract and no second copy."],
        ["We already have Ariba / Spend Intelligence.", "Good — this is where that data meets finance, supply chain and HR in one "
         "governed model, and where anyone can ask it questions in plain English."],
        ["Can we use our own category taxonomy?", "Yes. The taxonomy is a table in the gold layer (DT_CATEGORY_HIERARCHY); replace it."],
        ["Can we point it at our own data?", "Yes, and that is the follow-on: swap the L0 layer for your BDC procurement data products."],
    ], widths=[1.9, 4.8])

    h1(doc, "If it goes wrong")
    bullet(doc, "A page is empty — check the Category and Company filters; they persist across pages.")
    bullet(doc, "The app is slow on first open — the container is cold. Open it before the call.")
    bullet(doc, "A number disagrees with this document — check the reporting currency is USD; the kit is generated from the account and can be regenerated.")
    out = KIT / "03_SE_Quick_Start.docx"
    doc.save(out)
    return out


# ------------------------------------------------- ARCHITECTURE AND INSTALL

def build_architecture(F):
    doc = new_doc("Architecture and install", f"The medallion stack, every object, and the build order  ·  {DATE}")
    body(doc, "Everything sits inside Snowflake and reads SAP procurement data through SAP Business Data "
              f"Cloud zero-copy shares. Object counts below were read from the account on {F['verified_on']}.")
    sv_fqn, sv = next(iter(F["semantic_view_detail"].items()))
    agent = F["agents"][0].split(".", 1)[1] if F["agents"] else "—"
    h1(doc, "The stack")
    table(doc, ["Layer", "Objects", "What it does"], [
        ["L0 Bronze", "SAP BDC data products", "Purchase Order (item) and Supplier, shared zero copy: " + ", ".join(F["app_reads_share_directly"])],
        ["L1 Silver", f"{len(F['l1_objects'])} views in SAP_BDC_L1", ", ".join(o["TABLE_NAME"] for o in F["l1_objects"]) + " — typed, renamed projections over the shares."],
        ["L2 Gold", f"{len(F['analytics_objects'])} tables in ANALYTICS, {F['analytics_rows']:,} rows",
         "DT_SPEND_360 (the spend fact) plus " + ", ".join(F["enrichment_tables"]) + "."],
        ["Semantic", sv_fqn.split(".", 1)[1], f"{sv['tables']} tables, {sv['dimensions']} dimensions, {sv['facts']} facts, {sv['metrics']} metrics, {sv['relationships']} relationships."],
        ["Agent", agent, "Cortex Agent for natural-language spend questions; behind the Ask the Agent page."],
        ["App", f"{F['app_page_count']} pages", "React client and Express server, packaged as a Native App."],
    ], widths=[0.9, 2.1, 3.7])

    h1(doc, "Only one of the gold tables is a dynamic table")
    body(doc, f"A DT_ prefix is not evidence. SHOW DYNAMIC TABLES returns exactly one: {', '.join(F['dynamic_tables'])}. "
              f"The others — {', '.join(F['dt_prefixed_not_dynamic'])} — are base tables holding representative "
              f"enrichment values and do not refresh.")
    d = F["dynamic_table_detail"][0] if F["dynamic_table_detail"] else {}
    if d:
        table(doc, ["Dynamic table", "Target lag", "Refresh mode", "Last refreshed"],
              [[d["name"], d["target_lag"], d["refresh_mode"], d["data_timestamp"]]], widths=[2.2, 1.5, 1.5, 1.5])
        body(doc, f"Target lag {d['target_lag']} means it refreshes only when a downstream object asks. On live BDC "
                  f"data, set an explicit TARGET_LAG.")

    h1(doc, "Currency conversion")
    table(doc, ["Company", "Currency", "PO lines", "Spend (native)", "Spend (USD)"],
          [[c["COMPANY"], c["CURRENCY"], f"{c['PO_LINES']:,}", f"{c['SPEND_NATIVE']:,.0f}", usd(c["SPEND_USD"])] for c in F["spend_by_company_native"]],
          widths=[1.7, 0.9, 0.9, 1.6, 1.6])
    body(doc, f"DT_SPEND_360.SPEND is in document currency. ANALYTICS.FX_RATES_DAILY holds ECB reference rates "
              f"(loaded by tools/load_fx_rates.py) and FX_RATES_CALENDAR carries them across weekends and holidays. "
              f"The app joins each PO line to the rate for its PO date and converts to the selected reporting "
              f"currency; supplier and savings values are re-derived from the converted fact. The Native App "
              f"bundles the calendar as a table. The semantic view and agent still read native amounts; adding "
              f"a converted measure there is the next step. Rates: {fx_text(F)}.")

    h1(doc, "What reads what")
    table(doc, ["Consumer", "Reads"], [
        ["The application", ", ".join(sorted(F["app_data_sources"]))],
        ["Cortex Analyst / agent", F.get("analyst_semantic_view") or "—"],
    ], widths=[1.6, 5.1])
    body(doc, "The dashboards read the gold spend table; the lineage page reads the raw BDC shares to prove the "
              "zero-copy path; the agent reads the semantic view.")

    h1(doc, "Build order")
    table(doc, ["Step", "What to run", "Result"], [
        ["0", "tools/load_fx_rates.py", "FX_RATES_DAILY and FX_RATES_CALENDAR"],
        ["1", "sql/02_l1_curated_views.sql", "SAP_BDC_L1 views over the BDC shares"],
        ["2", "sql/03_l2_analytics_enrichment.sql", "DT_SPEND_360 and the enrichment tables"],
        ["3", "sql/04_semantic_view.sql", sv_fqn.split(".", 1)[1]],
        ["4", "sql/05_cortex_agent.sql", agent],
        ["5", "scripts/build_and_push.sh, deploy_native_app.py", "Native App package and version"],
        ["5b", "scripts/migrate_data.py, upgrade_native_app.py", "Refresh bundled data; ship a new patch"],
        ["6", "scripts/create_org_listing.py", "Region-scoped organization listing"],
    ], widths=[0.5, 3.0, 3.2])
    body(doc, "After step 4 you can demo through Snowflake Intelligence without the app.")
    out = KIT / "05_Architecture_and_Install.docx"
    doc.save(out)
    return out


# ------------------------------------------------------------- SETUP, ACCESS

def build_setup(F):
    doc = new_doc("Setup and access", f"The listing, the three regions, and the public build  ·  {DATE}")
    h1(doc, "How to get to it")
    table(doc, ["Route", "What you get", "Notes"], [
        ["Native App listing", f"The {F['app_page_count']}-page dashboard with data bundled in. No grants, no data setup.",
         f"{F['app_listing']} — install the one for your region"],
        ["Live demo app", "The running Native App in the demo account.", F.get("native_app_url") or "—"],
        ["Public static build", "A credential-free browser build for rehearsal. No Snowflake behind it, so Ask the Agent will not answer.", F["public_url"]],
        ["Your own account", "Run the SQL, then demo through Snowflake Intelligence.", "See 05_Architecture_and_Install"],
    ], widths=[1.3, 3.0, 2.4])

    h1(doc, "Where it is published")
    rows = []
    for r in F["regions"]:
        if "error" in r:
            rows.append([r["connection"], "—", f"check failed: {r['error']}"])
        else:
            rows.append([r["connection"], r["region"], ", ".join(f"{x['name']} ({x['state']})" for x in r["listings"]) or "none found"])
    table(doc, ["Connection", "Snowflake region", "Listing"], rows, widths=[1.7, 2.1, 2.9])

    h1(doc, "Snowflake objects")
    sv_fqn, _ = next(iter(F["semantic_view_detail"].items()))
    table(doc, ["Object", "Detail"], [
        ["Database", "SAP_SPEND_360"],
        ["L0 shares", ", ".join(F["app_reads_share_directly"])],
        ["L1", ", ".join(f"SAP_BDC_L1.{o['TABLE_NAME']}" for o in F["l1_objects"])],
        ["ANALYTICS", f"{len(F['analytics_objects'])} tables, {F['analytics_rows']:,} rows — {len(F['dynamic_tables'])} dynamic, {len(F['dt_prefixed_not_dynamic'])} base"],
        ["Semantic view", sv_fqn],
        ["Agent", F["agents"][0] if F["agents"] else "—"],
        ["Native App", f"SPEND_360_APP — service {F.get('native_app_status')}"],
        ["Account checked", f"{F['account']} ({F['region']})"],
    ], widths=[1.6, 5.1])
    callout(doc, "Agent location", f"The agent lives in the AGENTS schema — {F['agents'][0] if F['agents'] else '—'} — as in "
                                   f"People 360, not ANALYTICS as in Supply Chain 360.")

    h1(doc, "Related assets")
    table(doc, ["Asset", "Where"], [
        ["Finance 360 kit", "Spend against the P&L — Compass"],
        ["Supply Chain 360 kit", "Supplier quality alongside supplier risk — Compass"],
        ["People 360 and Sales 360 kits", "Same pattern, other domains — Compass"],
        ["Cloud ERP 360", "Joins Finance, Spend and People by company"],
        ["Use cases", "docs/USE_CASES.md in the repo; SAP_BDC_360_Use_Case_Catalog.docx"],
    ], widths=[2.2, 4.5])
    h1(doc, "Contact")
    body(doc, "Dave Freriks — for access help, or to scope pointing this at a customer's own BDC procurement data.")
    out = KIT / "06_Setup_and_Access.docx"
    doc.save(out)
    return out


def main() -> int:
    F = load_facts()
    KIT.mkdir(parents=True, exist_ok=True)
    for fn in (build_start_here, build_management_summary, build_demo_scripts, build_quick_start,
               build_architecture, build_setup):
        print(f"wrote {fn(F)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
