#!/usr/bin/env python3
"""Build the SAP Spend 360 presales decks on the SAP branded template.

    00_Presales_Overview.pptx  ten slides: problem, architecture, app, agent, regions, ask
    SAP_Spend_360_Demo.pptx    screenshot-led walkthrough of every page

Figures come from /tmp/spend_facts.json and screenshots from /tmp/spend_shots
(all companies, reporting currency USD), so neither deck can drift from the account
or the application. Money is USD, each PO line converted at its PO-date ECB rate.

    python3 tools/spend_facts.py
    python3 ../sap-bdc-finance-360/tools/capture_shots.py --app spend
    python3 tools/build_decks.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _deck_helpers import (  # noqa: E402
    BODY_GREY, DK1, DK2, FULLW, LEFT, LIGHT_BG, MSO_SHAPE, RED, SF_BLUE, TEAL, TOP,
    VIOLET, WHITE, add_shape_text, banner, box, caption, card, content,
    new_presentation, note, picture, region_label, set_ph, stack, stat, verify_deck,
    verify_slide,
)

FACTS = pathlib.Path("/tmp/spend_facts.json")
SHOTS = pathlib.Path("/tmp/spend_shots")
KIT = pathlib.Path.home() / "Documents" / "SAP" / "Spend_360_Presales_Kit"


def load():
    f = json.loads(FACTS.read_text())["facts"]
    shots = {s["id"]: s["file"] for s in json.loads((SHOTS / "manifest.json").read_text())}
    for sid, p in shots.items():
        if not pathlib.Path(p).exists():
            raise FileNotFoundError(f"screenshot missing for '{sid}': {p}")
    return f, shots


def usd(v):
    v = float(v)
    return f"${v / 1e6:,.2f}M" if v >= 1e6 else f"${v / 1e3:,.0f}K"


def us(f):
    return next(c for c in f["spend_by_company_native"] if c["CURRENCY"] == "USD")


def cover(prs, f, subtitle):
    s = prs.slides.add_slide(prs.slide_layouts[13])
    set_ph(s, 3, "SAP SPEND 360")
    set_ph(s, 0, "SAP procurement data as governed spend intelligence")
    set_ph(s, 2, f"{subtitle} · verified {f['verified_on']}")
    return s


def shot_slide(prs, f, shots, sid, title, subtitle, cards, foot):
    s = content(prs, title, subtitle)
    picture(s, shots[sid], LEFT, TOP, 5.9, 3.5)
    y = TOP
    for kicker, text_, accent, h in cards:
        card(s, LEFT + 6.1, y, 3.0, h, kicker, [(text_, 10, False, DK1, 0)], accent=accent)
        y += h + 0.12
    note(s, foot)
    return s


# ------------------------------------------------------------ overview deck

def o02_problem(prs, f):
    s = content(prs, "The spend data exists. Seeing it is the project.",
                "Procurement questions that should take minutes take weeks")
    card(s, LEFT, TOP, 4.4, 2.5, "what procurement is asked", [
        ("Where does our money go, by category and supplier?", 12, False, DK1, 8),
        ("How much of it is under contract?", 12, False, DK1, 8),
        ("Which suppliers could hurt us if they failed?", 12, False, DK1, 8),
        ("Where is the next round of savings?", 12, False, DK1, 0)], accent=SF_BLUE)
    card(s, LEFT + 4.7, TOP, 4.4, 2.5, "why it is slow", [
        ("PO and supplier data sit in SAP, reachable by extract.", 12, False, DK1, 8),
        ("Each extract is cleaned and categorised again in a spreadsheet.", 12, False, DK1, 8),
        ("Risk, ESG and contract data live somewhere else entirely.", 12, False, DK1, 0)], accent=RED)
    banner(s, 4.05, [("The blocker is not analytics. It is getting SAP spend data into one "
                      "governed place without copying it.", 12.5, True, WHITE, 0)])
    note(s, "SAP BDC removes the copy: PO and supplier data are shared into Snowflake zero copy.")
    return s


def o03_pattern(prs, f):
    sv = next(iter(f["semantic_view_detail"].values()))
    s = content(prs, "One medallion stack, entirely inside Snowflake", "Zero copy in, governed model out")
    layers = [
        ("L0", "SAP BDC data products · Purchase Order, Supplier", "Shared zero copy, treated as immutable", TEAL),
        ("L1", f"SAP BDC L1 · {len(f['l1_objects'])} views", "Typed, renamed projections over the shares", SF_BLUE),
        ("L2", f"Analytics — {len(f['analytics_objects'])} tables, {f['analytics_rows']:,} rows",
         f"Spend fact plus {len(f['enrichment_tables'])} enrichment tables (risk, ESG, taxonomy, savings)", SF_BLUE),
        ("SEM", "SAP Spend 360 Analytics semantic view",
         f"{sv['tables']} tables · {sv['dimensions']} dimensions · {sv['metrics']} metrics", VIOLET),
        ("AI", "SAP Spend Analyst agent", "Cortex Agent, and Cortex Analyst inside the app", VIOLET),
        ("APP", f"Native App — {f['app_page_count']} pages", "React + Express, data bundled, nothing to configure", DK2),
    ]
    y = TOP
    for tag, name, detail, accent in layers:
        add_shape_text(s, MSO_SHAPE.RECTANGLE, LEFT, y, 0.62, 0.52, tag, accent,
                       DK1 if accent is TEAL else WHITE, 11, True)
        box(s, LEFT + 0.68, y, FULLW - 0.68, 0.52, LIGHT_BG, None)
        stack(s, LEFT + 0.88, y + 0.07, FULLW - 1.1, 0.40, [(name, 11, True, DK1, 1), (detail, 9, False, BODY_GREY, 0)])
        y += 0.60
    note(s, f"Nothing is extracted and no second copy is created. Object counts read on {f['verified_on']}.")
    return s


def o04_app(prs, f, shots):
    s = content(prs, f"{f['app_page_count']} pages, and nothing to set up",
                "Installs from the internal Marketplace with its data bundled in")
    picture(s, shots["overview"], LEFT, TOP, 5.9, 3.5)
    pages = f["app_pages"]
    half = (len(pages) + 1) // 2
    caption(s, LEFT + 6.1, TOP, 3.0, "every page")
    stack(s, LEFT + 6.1, TOP + 0.30, 1.5, 3.0, [(f"· {p}", 9.5, False, DK1, 6) for p in pages[:half]])
    stack(s, LEFT + 7.65, TOP + 0.30, 1.5, 3.0, [(f"· {p}", 9.5, False, DK1, 6) for p in pages[half:]])
    note(s, "Category, Company and Reporting Currency apply across every page. Shown: Spend Overview in USD.")
    return s


def o05_spend(prs, f, shots):
    s = content(prs, "Spend, as SAP records it", "Category, supplier and contract status on every PO line")
    picture(s, shots["categories"], LEFT, TOP, 5.9, 3.5)
    x = LEFT + 6.1
    stat(s, x, TOP, 3.0, 0.82, usd(f["total_spend_usd"]), "spend in scope", f"{f['po_lines']:,} PO lines, in USD", accent=SF_BLUE)
    stat(s, x, TOP + 0.92, 3.0, 0.82, f"{f['suppliers']}", "suppliers", f"in {f['categories']} categories", accent=TEAL)
    stat(s, x, TOP + 1.84, 3.0, 0.82, f"{f['top10_supplier_share_pct_usd']}%", "top 10 supplier share", "the rest is the tail", accent=DK2)
    stat(s, x, TOP + 2.76, 3.0, 0.74, f"{f['companies']}", "companies", "USD, EUR and JPY, converted", accent=VIOLET)
    note(s, "Each PO line converts at the ECB rate for its PO date; switch USD, EUR or JPY in the sidebar.")
    return s


def o06_compliance(prs, f, shots):
    s = content(prs, "Contract leakage, by category", "The fastest savings are the ones already negotiated")
    picture(s, shots["contracts"], LEFT, TOP, 5.9, 3.5)
    stat(s, LEFT + 6.1, TOP, 3.0, 0.90, f"{f['on_contract_pct_usd']}%", "spend on contract", "all companies, in USD", accent=TEAL)
    stat(s, LEFT + 6.1, TOP + 1.02, 3.0, 0.90, usd(f["off_contract_spend_usd"]), "off contract", "the controllable number", accent=RED)
    stat(s, LEFT + 6.1, TOP + 2.04, 3.0, 0.90, usd(f["savings_total_usd"]), "savings pipeline",
         "5 levers, 2-6% each (representative)", accent=DK2)
    note(s, "Savings opportunities are representative enrichment values, converted to USD with the spend they address.")
    return s


def o07_agent(prs, f, shots):
    sv = next(iter(f["semantic_view_detail"].values()))
    s = content(prs, "Plain-English questions, governed SQL underneath",
                f"{len(f['agent_questions'])} questions ship with the app")
    picture(s, shots["analyst"], LEFT, TOP, 5.5, 3.5)
    stack(s, LEFT + 5.75, TOP - 0.02, 3.4, 2.4, [(f"· {q}", 9.5, False, DK1, 5) for q in f["agent_questions"]])
    card(s, LEFT + 5.75, TOP + 2.35, 3.4, 1.15, "what it covers", [
        (f"{sv['tables']} tables, {sv['metrics']} metrics. Spend here is native currency: "
         f"ask per company.", 9.5, False, DK1, 0)], accent=VIOLET)
    note(s, "The generated SQL expands on screen, constrained to the model.")
    return s


def o08_regions(prs, f):
    s = content(prs, "One definition, three governed installs", "Region-scoped organization listing")
    y = TOP
    for r in f["regions"]:
        listings = ", ".join(f"{x['name']} ({x['state']})" for x in r.get("listings", [])) or r.get("error", "none found")
        box(s, LEFT, y, FULLW, 0.72, LIGHT_BG, SF_BLUE)
        stack(s, LEFT + 0.28, y + 0.12, FULLW - 0.5, 0.50,
              [(region_label(r.get("region", "—")), 12.5, True, DK1, 2), (listings, 9.5, False, BODY_GREY, 0)])
        y += 0.80
    banner(s, y + 0.12, [("Each region is its own governed install of the same Native App.", 11.5, True, WHITE, 0)], h=0.56)
    note(s, f"Live demo app running in {region_label(f['region'])}; public static build for rehearsal.")
    return s


def o09_caveats(prs, f):
    s = content(prs, "What is SAP data, and what is representative", "Say this before you are asked")
    rows = [
        ("Medallion stack, semantic view, agent, app", "Real — this is the deliverable", TEAL, DK1),
        ("Purchase orders and suppliers", "SAP BDC data products, shared zero copy", TEAL, DK1),
        ("Risk, ESG, diversity, taxonomy, savings", f"Representative values in {len(f['enrichment_tables'])} enrichment tables", RED, RED),
        ("Currency", "Converted per PO at ECB rates; agent still reads native amounts", TEAL, DK1),
        ("Refresh", f"{len(f['dynamic_tables'])} of {len(f['analytics_objects'])} gold tables is dynamic", RED, RED),
    ]
    y = TOP
    for label, status, accent, colour in rows:
        box(s, LEFT, y, FULLW, 0.50, LIGHT_BG, accent)
        stack(s, LEFT + 0.28, y + 0.13, 4.6, 0.26, [(label, 10.5, True, DK1, 0)])
        stack(s, LEFT + 5.0, y + 0.13, 4.0, 0.26, [(status, 10.5, False, colour, 0)])
        y += 0.56
    card(s, LEFT, y + 0.04, FULLW, 0.62, "data window", [(f"POs dated {f['po_window'][0]} to {f['po_window'][1]}", 9.5, False, DK1, 0)], accent=DK2)
    note(s, "In production, swap the ECB rates table for the customer's own treasury rates (SAP TCURR).")
    return s


def o10_next(prs, f):
    s = content(prs, "Where to take it", "Four options, in order of effort")
    opts = [
        ("Demo it", "Install the Native App listing in your region and present. Nothing to build."),
        ("Show the architecture", "Run the SQL in your own account and demo through Snowflake Intelligence."),
        ("Extend currency to the agent", "Add a converted spend measure to the semantic view."),
        ("Point it at customer data", "Swap L0 for the customer's own BDC procurement data products."),
    ]
    y = TOP
    for i, (head, detail) in enumerate(opts, 1):
        box(s, LEFT, y, FULLW, 0.68, LIGHT_BG, SF_BLUE)
        stack(s, LEFT + 0.30, y + 0.11, FULLW - 0.6, 0.46, [(f"{i}.  {head}", 12, True, DK2, 2), (detail, 10, False, DK1, 0)])
        y += 0.78
    banner(s, y + 0.10, [(f"Kit on SAP Partnership Compass · start with 03_SE_Quick_Start.docx · {f['repo']}", 10.5, True, WHITE, 0)], h=0.50)
    return s


def overview(f, shots):
    prs = new_presentation()
    slides = [cover(prs, f, "SE presales kit"), o02_problem(prs, f), o03_pattern(prs, f), o04_app(prs, f, shots),
              o05_spend(prs, f, shots), o06_compliance(prs, f, shots), o07_agent(prs, f, shots),
              o08_regions(prs, f), o09_caveats(prs, f), o10_next(prs, f)]
    return prs, slides, KIT / "00_Presales_Overview.pptx"


# ---------------------------------------------------------------- demo deck

REP = "Representative enrichment values, converted to USD with the spend they sit on."


def demo(f, shots):
    prs = new_presentation()
    slides = [cover(prs, f, "App walkthrough")]
    slides.append(shot_slide(prs, f, shots, "overview", "Spend Overview", "Where the money goes, at a glance", [
        ("shown", f"{usd(f['total_spend_usd'])} across {f['po_lines']:,} PO lines, all three companies.", SF_BLUE, 1.05),
        ("say", "Each company buys in its own currency; every line converts at its PO-date rate.", TEAL, 1.05),
        ("then", "Flip USD, EUR, JPY in the sidebar; point at trend and top suppliers.", DK2, 1.05)],
        "Shown in USD, all companies."))
    slides.append(shot_slide(prs, f, shots, "categories", "Categories", "Spend by category and taxonomy", [
        ("largest category", f"{f['spend_by_category_usd'][0]['CATEGORY']}, {usd(f['spend_by_category_usd'][0]['SPEND_USD'])} across all companies.", SF_BLUE, 1.3),
        ("taxonomy", f"L1/L2/L3 hierarchy; {f['addressable_categories']} of {f['categories']} categories addressable.", TEAL, 1.3)],
        "Contract compliance by category sits on the same page."))
    slides.append(shot_slide(prs, f, shots, "suppliers", "Suppliers", "Concentration and the tail", [
        ("concentration", f"Top 10 suppliers hold {f['top10_supplier_share_pct_usd']}% of spend.", SF_BLUE, 1.3),
        ("the tail", "The long tail is the consolidation target.", TEAL, 1.0)],
        "Supplier detail lists spend, PO lines and contract share."))
    slides.append(shot_slide(prs, f, shots, "supplier-risk", "Supplier Risk", "Risk score by tier and region", [
        ("exposure", f"{f['high_risk_suppliers']} suppliers score 70+; {f['single_source_suppliers']} are single-source.", RED, 1.2),
        ("caution", REP, DK2, 1.2)],
        "Supplier spend is re-derived from converted PO spend."))
    slides.append(shot_slide(prs, f, shots, "sustainability", "Sustainability & Diversity", "ESG and diverse-supplier spend", [
        ("esg", f"Average supplier ESG score {f['avg_esg_score']}; {f['diverse_suppliers']} diverse suppliers.", TEAL, 1.2),
        ("caution", REP, DK2, 1.2)],
        "Supplier spend is re-derived from converted PO spend."))
    slides.append(shot_slide(prs, f, shots, "savings", "Savings Pipeline", "Opportunities by lever and status", [
        ("levers", "; ".join(f"{x['OPP_TYPE']} {x['SAVINGS_PCT']:.0f}%" for x in f["savings_levers"]), SF_BLUE, 1.6),
        ("pipeline", f"{usd(f['savings_total_usd'])} across three statuses, in USD.", DK2, 0.9)],
        f"{f['savings_opportunities']} representative opportunities across identified, in-progress and realised."))
    slides.append(shot_slide(prs, f, shots, "contracts", "Contract Compliance", "On- versus off-contract spend", [
        ("coverage", f"{f['on_contract_pct_usd']}% on contract across all companies.", TEAL, 1.2),
        ("off contract", f"{usd(f['off_contract_spend_usd'])} — the controllable number.", RED, 1.2)],
        "Shown in USD, all companies."))
    slides.append(shot_slide(prs, f, shots, "purchase-orders", "Purchase Orders", "The PO-line grain", [
        ("grain", f"{f['po_lines']:,} PO lines, dated {f['po_window'][0]} to {f['po_window'][1]}.", SF_BLUE, 1.2),
        ("fields", "Supplier, category, company, buyer, plant, contract flag.", DK2, 1.2)],
        "Filterable record-level table."))
    slides.append(shot_slide(prs, f, shots, "lineage", "BDC Sources & Lineage", "The zero-copy proof", [
        ("path", "SAP BDC data product → L1 view → gold table → semantic view → app.", VIOLET, 1.3),
        ("sources", "Purchase Order (item) and Supplier data products.", TEAL, 1.0)],
        "Close here for a technical audience."))
    slides.append(shot_slide(prs, f, shots, "analyst", "Ask the Agent", "Plain-English questions, governed SQL", [
        ("try", f"'{f['agent_questions'][3]}'", SF_BLUE, 1.0),
        ("then", "Expand the generated SQL.", DK2, 0.8),
        ("tip", "Agent spend is native currency: ask per company.", RED, 1.0)],
        f"{len(f['agent_questions'])} suggested questions ship with the app."))
    slides.append(o09_caveats(prs, f))
    slides.append(o10_next(prs, f))
    return prs, slides, KIT / "SAP_Spend_360_Demo.pptx"


def build(fn, f, shots):
    prs, slides, out = fn(f, shots)
    issues = 0
    for n, s in enumerate(slides, 1):
        for msg in verify_slide(s, prs, n):
            print(f"  {out.name} slide {n}: {msg}")
            issues += 1
    issues += len(verify_deck(prs))
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    print(f"wrote {out}  ({len(prs.slides)} slides, {issues} verifier issue(s))")


def main():
    f, shots = load()
    build(overview, f, shots)
    build(demo, f, shots)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
