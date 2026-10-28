#!/usr/bin/env python3
"""Build docs/SAP_Spend_360_Demo_Guide.pptx and copy it into the presales kit.

The template is the original July guide as committed (git HEAD~ history of
docs/SAP_Spend_360_Demo_Guide.pptx, first commit), so re-running never compounds
edits. Each text frame is rewritten in place, keeping its run formatting, and three
screenshot slides are added after Demo Act 1. Same method as
sap-bdc-working-capital-360/tools/build_demo_guide.py.

Figures come from /tmp/spend_facts.json (run tools/spend_facts.py); screenshots from
/tmp/spend_shots (run ../sap-bdc-finance-360/tools/capture_shots.py --app spend).
    python3 tools/build_demo_guide.py
"""
import copy
import json
import pathlib
import shutil
import subprocess
import tempfile

from pptx import Presentation
from pptx.util import Emu

ROOT = pathlib.Path(__file__).resolve().parents[1]
GUIDE = "docs/SAP_Spend_360_Demo_Guide.pptx"
TEMPLATE_COMMIT = "ead818c"  # initial commit: the untouched template
OUT = ROOT / GUIDE
KIT = pathlib.Path.home() / "Documents/SAP/Spend_360_Presales_Kit/07_SAP_Spend_360_Demo_Guide.pptx"
SHOTS = pathlib.Path("/tmp/spend_shots")
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
F = json.load(open("/tmp/spend_facts.json"))
F = F.get("facts", F)

TOTAL_M = F["total_spend_usd"] / 1e6
OFF_M = F["off_contract_spend_usd"] / 1e6
SAV_K = F["savings_total_usd"] / 1e3
REAL_K = next(s["SAVINGS_USD"] for s in F["savings_by_status_usd"] if s["STATUS"] == "Realized") / 1e3
TOPCAT = F["spend_by_category_usd"][0]
NATIVE = {c["COMPANY"]: c for c in F["spend_by_company_native"]}
EU, JP = NATIVE["EU Operations"], NATIVE["Japan Operations"]
HONEST = ("Purchase order lines, amounts, dates, suppliers and currencies are real BDC Purchase Order "
          "and Supplier data. Supplier risk, ESG and diversity, the category taxonomy and the savings "
          "pipeline are demo enrichment aligned to SAP Spend Intelligence. Currency conversion uses ECB "
          "reference rates on each PO date.")


def set_text(shape, *texts):
    """Replace the non-empty paragraphs of a shape, in order, keeping formatting."""
    paras = [p for p in shape.text_frame.paragraphs if p.text.strip()]
    for p, t in zip(paras, texts):
        runs = p.runs
        runs[0].text = t
        for r in runs[1:]:
            r._r.getparent().remove(r._r)
        for br in p._p.findall(f"{{{A}}}br"):
            p._p.remove(br)
        if "\v" in t:  # soft line break: run, <a:br/>, cloned run
            first, rest = t.split("\v", 1)
            runs[0].text = first
            br = copy.deepcopy(runs[0]._r); br.tag = f"{{{A}}}br"
            for c in list(br):
                if c.tag != f"{{{A}}}rPr":
                    br.remove(c)
            r2 = copy.deepcopy(runs[0]._r)
            runs[0]._r.addnext(br); br.addnext(r2)
            r2.find(f"{{{A}}}t").text = rest
    for p in paras[len(texts):]:
        p._p.getparent().remove(p._p)


# (slide index 1-based) -> {shape index: texts}, notes
CONTENT = {
    1: ({0: ["Demo Guide & the Snowflake × SAP Business Data Cloud story"],
         1: ["Dave Freriks  |  Sales Engineering"],
         2: ["SAP SPEND 360\vON SNOWFLAKE"]},
        "Welcome. Today I'm showing SAP Spend 360, a Snowflake Native App built on SAP Business Data "
        "Cloud procurement data. It mirrors SAP Spend Intelligence. The story: the CPO asks where our "
        "money goes, and how much of it escapes our contracts."),
    2: ({0: ["Why Snowflake + SAP Business Data Cloud"],
         1: ["SAP runs procurement, but a spend view needs purchase orders, suppliers and risk data "
             "together, across companies and currencies. That usually means weeks of ETL, and the "
             "business context is lost along the way."],
         2: ["SAP BDC Connect shares governed purchase order and supplier data products into Snowflake "
             "with zero copy. Snowflake adds risk, ESG and FX data and AI. No pipelines are needed."],
         3: ["The Challenge"], 4: ["The Opportunity"],
         6: ["Two platforms, one governed data foundation"]},
        "Set up the problem. Spend sits in three companies and three currencies, and risk and ESG data "
        "sit outside SAP. BDC shares the SAP side zero-copy; Snowflake joins the rest."),
    3: ({0: ["What Is Spend 360?"],
         1: [f"{F['app_page_count']} pages: spend, suppliers, risk, ESG, savings and contracts, in USD, EUR or JPY."],
         2: ["A Cortex Agent answers plain-English questions over a governed semantic view."],
         3: ["Runs on SPCS with data, semantic view and UI bundled; nothing leaves Snowflake."],
         5: ["A self-contained Snowflake Native App built on SAP BDC data"],
         9: ["Dashboards"], 10: ["Ask Cortex"], 11: ["Runs In Snowflake"]},
        f"Tell them what they're about to see: {F['app_page_count']} pages covering {F['po_lines']:,} PO "
        f"lines from {F['suppliers']} suppliers in {F['categories']} categories, plus a live Cortex agent."),
    4: ({0: ["How It’s Built: BDC → Snowflake → App"],
         1: ["SAP BDC Connect shares the Purchase Order and Supplier data products with zero copy and no ETL."],
         2: ["L1 views feed an incremental dynamic table, enriched with supplier risk, ESG, a category "
             "taxonomy, savings levers and ECB daily FX rates."],
         3: ["A Native App packages the data, the semantic view and an SPCS React UI with a Cortex "
             "agent. It installs in one click."],
         4: ["1. BDC Data Products"], 5: ["2. Snowflake Curation"], 6: ["3. Native App + Cortex"],
         8: ["From SAP data product to a shareable AI app"]},
        "Walk the three steps: zero-copy in, enriched into a Spend Intelligence model, packaged as a "
        "one-click app. Each PO line converts at the ECB rate on its PO date."),
    5: ({0: ["DEMOING SPEND 360", "THE 10-MINUTE FLOW"]},
        "Transition: 'Let me show you the app. The CPO wants to know where the money goes and how much "
        "of it is off contract.'"),
    6: ({0: ["The Demo Flow"],
         1: ["Open the app: no setup, it opens on the Executive Dashboard",
             f"Executive Dashboard: USD {TOTAL_M:.2f}M across {F['suppliers']} suppliers",
             "Switch currency: EUR and JPY at historical ECB rates",
             f"Contracts: only {F['on_contract_pct_usd']:.0f}% of spend is on contract",
             f"Supplier Risk and ESG: {F['high_risk_suppliers']} high-risk suppliers",
             f"Savings Pipeline: USD {SAV_K:.0f}K across {F['savings_opportunities']} opportunities",
             "Ask Cortex, then recap: zero-ETL, governed, AI-ready"]},
        "Roadmap for the live demo; don't read it aloud. Spend most time on Contract Compliance: "
        f"USD {OFF_M:.2f}M off contract is the headline."),
    7: ({0: ["Demo Act 1: The Dashboards"],
         1: [f"USD {TOTAL_M:.2f}M total spend; {TOPCAT['CATEGORY']} is the largest category at "
             f"USD {TOPCAT['SPEND_USD'] / 1e6:.2f}M."],
         2: [f"{F['high_risk_suppliers']} high-risk and {F['single_source_suppliers']} single-source "
             f"suppliers; the top 10 suppliers hold {F['top10_supplier_share_pct_usd']:.1f}% of spend."],
         3: [f"Average ESG score {F['avg_esg_score']}; {F['diverse_suppliers']} diverse suppliers."],
         4: [f"USD {SAV_K:.0f}K savings pipeline, USD {REAL_K:.0f}K already realized."],
         6: ["Answer the CPO: where does the money go?"],
         10: ["Overview"], 11: ["Supplier Risk"], 12: ["Sustainability"], 14: ["Savings"]},
        f"Click through and narrate outcomes: 'We spend USD {TOTAL_M:.1f}M, but only "
        f"{F['on_contract_pct_usd']:.0f}% is on contract, so USD {OFF_M:.1f}M escapes our negotiated "
        "prices.' Switch the currency to EUR to show EU Operations in its own currency."),
    8: ({0: ["Demo Act 2: Ask Cortex"],
         1: ["Ask in plain English: “What percent of spend is on contract by category?”, “Which suppliers "
             "are highest risk?” or “What is our savings pipeline by lever?”"],
         2: ["Ask Cortex (first in the sidebar) answers from the app's live numbers. In Snowflake Intelligence, "
             "{ag} maps the question to the bundled semantic view, generates governed SQL "
             "and returns a chart with the exact query, so the answer is explainable."],
         4: ["Cortex Agent over a governed semantic view"]},
        "The highlight. Type a question live into Ask Cortex; do NOT pre-load it. To show governed "
        "SQL, ask the same question of the Cortex Agent in Snowflake Intelligence."),
    9: ({0: ["Lead with the CPO question, not architecture. PO lines, suppliers and currencies are real "
             "BDC data; risk, ESG, taxonomy and savings are demo enrichment. Currency conversion uses "
             "ECB rates on each PO date."],
         1: ["Key Points to Land During the Demo"], 3: ["Say these out loud"]},
        "Reinforce: no ETL, Spend Intelligence on live SAP data, AI-ready and governed. Always state "
        "the data honesty line; it builds trust with procurement audiences."),
    10: ({0: ["The Snowflake × SAP BDC Value"],
          1: ["BDC Connect zero-copy sharing means no pipelines; purchase order data is live in Snowflake."],
          2: ["SAP semantics are preserved and joined with risk, ESG and FX data from outside SAP."],
          3: ["A Cortex Agent brings natural-language analytics directly to SAP spend data."],
          4: ["Native Apps package data + AI + UI into a one-click, distributable product."],
          6: ["Why this partnership matters"]},
         "Zoom out to the partnership value. Cover each of the four pillars in one sentence."),
    11: ({0: ["Takeaways by the Numbers"],
          1: ["ETL pipelines to build: BDC Connect shares data zero-copy."],
          2: ["Regions live now: US, EMEA and APAC from one definition."],
          3: ["Currencies, converted at historical ECB rates."],
          4: ["Of spend off contract, surfaced for recovery."],
          5: ["0"], 6: ["3"], 7: ["3"], 8: [f"{100 - F['on_contract_pct_usd']:.0f}%"],
          10: ["What this demo proves"]},
         f"Make it concrete: zero pipelines, three regions, three currencies, and USD {OFF_M:.2f}M of "
         "off-contract spend surfaced."),
    12: ({21: ["One App. Three Regions. Zero Rework."]},
         "Spend 360 is live in US West (Oregon), EU (Frankfurt) and APAC (Sydney) as "
         f"{F['app_listing']}, V1.1 in every region. Each region is its own governed install."),
    13: ({0: ["Demo Do’s and Don’ts"],
          1: ["Lead with the CPO question. Show the app already has data. Switch currency once to prove "
              "the FX conversion. Ask SAP_SPEND_ANALYST a real question live."],
          2: ["Don’t pre-load canned answers or dwell on SQL. Don’t present risk, ESG or savings figures "
              "as real tenant data. Don’t add EUR and JPY amounts together without converting."],
          3: ["Do"], 4: ["Don’t"], 6: ["Keep it crisp and outcome-focused"]},
         "Presenter coaching. " + HONEST),
    14: ({0: ["Next Steps"],
          1: ["For SEs: install from the internal marketplace (or use the public demo) and rehearse "
              "the 10-minute flow."],
          2: ["For customers: map their SAP procurement data products in BDC and pick the first Spend "
              "Intelligence use case, usually contract compliance."],
          3: ["For partners: co-build Native Apps on BDC data with risk and ESG enrichment to reach every "
              "Snowflake region."],
          5: ["Take the story forward"]},
         f"Close with a clear ask per audience. Public demo: {F['public_url']}"),
    15: ({}, f"Thank the audience. Share the listing {F['app_listing']} (role SPEND_360_APP_USERS) so "
             "they can install Spend 360."),
}

SHOT_SLIDES = [
    ("The Dashboards: Spend, Categories & Contracts",
     ["overview", "categories", "contracts", "purchase-orders"],
     "Screens for Act 1: Executive Dashboard, Categories, Contract Compliance and Purchase Orders."),
    ("The Dashboards: Suppliers, Risk, ESG & Savings",
     ["suppliers", "supplier-risk", "sustainability", "savings"],
     "Suppliers and concentration, the supplier risk matrix, Sustainability & Diversity, and the "
     "Savings Pipeline by lever and status."),
    ("Ask Cortex", ["analyst"],
     "The Ask Cortex page (first in the sidebar). Ask a live question of your own."),
]


def add_shot_slide(prs, title_src, title, shots, notes, files):
    s = prs.slides.add_slide(title_src.slide_layout)
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    tbox = copy.deepcopy(title_src.shapes[0]._element)  # same title font as the template
    s.shapes._spTree.append(tbox)
    set_text(s.shapes[-1], title)
    W, H = prs.slide_width, prs.slide_height
    top, gap = Emu(int(H * 0.2)), Emu(int(W * 0.015))
    if len(shots) == 1:
        h = H - top - Emu(int(H * 0.05)); w = int(h * 1.6)
        s.shapes.add_picture(files[shots[0]], (W - w) // 2, top, w, h)
    else:
        h = (H - top - Emu(int(H * 0.04)) - gap) // 2; w = int(h * 1.6)
        x0 = (W - 2 * w - gap) // 2
        for i, sid in enumerate(shots):
            s.shapes.add_picture(files[sid], x0 + (i % 2) * (w + gap), top + (i // 2) * (h + gap), w, h)
    s.notes_slide.notes_text_frame.text = notes
    return s


def main():
    files = {m["id"]: m["file"] for m in json.loads((SHOTS / "manifest.json").read_text())}
    with tempfile.TemporaryDirectory() as td:
        tpl = pathlib.Path(td) / "template.pptx"
        tpl.write_bytes(subprocess.run(["git", "-C", str(ROOT), "show", f"{TEMPLATE_COMMIT}:{GUIDE}"],
                                       capture_output=True, check=True).stdout)
        prs = Presentation(tpl)
    slides = list(prs.slides)
    for idx, (shapes, notes) in CONTENT.items():
        sl = slides[idx - 1]
        for j, texts in shapes.items():
            set_text(sl.shapes[j], *texts)
        sl.notes_slide.notes_text_frame.text = notes
    ids = prs.slides._sldIdLst
    new = [add_shot_slide(prs, slides[7], *spec, files) for spec in SHOT_SLIDES]
    elems = list(ids)[-len(new):]
    for e in elems:
        ids.remove(e)
    for k, e in enumerate(elems):
        ids.insert(7 + k, e)
    prs.save(OUT)
    shutil.copy(OUT, KIT)
    print(OUT, len(prs.slides), "slides ->", KIT)


if __name__ == "__main__":
    main()
