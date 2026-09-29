#!/usr/bin/env python3
"""Build the SAP BDC 360 demo asset index (one indexed Word document).

Inputs are read live beforehand into /tmp/listings.json (SHOW LISTINGS per region)
and /tmp/apps.json (SHOW APPLICATIONS + SHOW ENDPOINTS per region); repo, kit and
local-app facts are read from disk here. Nothing is typed in by hand except the
one-line product descriptions.
"""
import datetime as dt
import json
import pathlib
import subprocess
import sys

from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from docx_kit import GREY, SAP_NAVY, SNOW_BLUE, body, bullet, callout, h1, h2, setup_page, table  # noqa: E402

HOME = pathlib.Path.home()
SK = HOME / "Documents/SAP/SAP Skills"
SAP = HOME / "Documents/SAP"
GH = "https://github.com/sfc-gh-dfreriks/"
PAGES = "https://sfc-gh-dfreriks.github.io/"
OUT = HOME / "Downloads/SAP_BDC_360_Demo_Asset_Index.docx"

L = json.loads(pathlib.Path("/tmp/listings.json").read_text())
A = json.loads(pathlib.Path("/tmp/apps.json").read_text())
REG = [("dfreriksdemo", "US West (Oregon)"), ("dfreriks_eu_demo", "EU (Frankfurt)"),
       ("dfreriks_apac_demo", "APAC (Sydney)")]

P = [  # key, title, blurb, asset repo, public repo, local app dir, ports, app, listings, kit dir
    ("finance", "SAP Finance 360", "GL, cost and profit centres, AP/AR and period analysis on SAP finance data.",
     "sap-bdc-finance-360", "finance-360-public", "finance_dashboard_react", "3002 / 5175",
     "FINANCE_360_APP", ["FINANCE_360_ORG", "SAP_BDC_FINANCE_360_DEMO"], "Finance_360_Presales_Kit"),
    ("sales", "SAP Sales 360", "Pipeline, funnel, customer health, products, leaderboard and forecast.",
     "sap-bdc-sales-360", "sales-360-public", "sales_360_react", "3003 / 5176",
     "SALES_360_APP", ["SALES_360_ORG", "SAP_BDC_SALES_360_DEMO"], "Sales_360_Presales_Kit"),
    ("supply", "SAP Supply Chain 360", "Production orders, inventory, deliveries, supplier quality and work centres.",
     "sap-bdc-supply-chain-360", "supply-chain-360-public", "../SAP-Qlikstarts/supply_chain_dashboard_react",
     "3001 / 5174", "SUPPLY_CHAIN_360_APP", ["SUPPLY_CHAIN_360_ORG", "SAP_BDC_SUPPLY_CHAIN_360"],
     "Supply_Chain_360_Presales_Kit"),
    ("ontology", "SAP Supply Chain Ontology", "Ontology layer over supply chain data: classes, relations, knowledge graph and disruption scenarios.",
     "supply-chain-ontology", "supply-chain-ontology", "supply_chain_ontology_react", "3009 / 5179",
     None, [], "Supply_Chain_Ontology_Presales_Kit"),
    ("people", "SAP People 360", "Headcount, attrition, compensation, diversity, performance, learning and recruiting.",
     "sap-bdc-people-360", "people-360-public", "people_360_react", "3006 / 5180",
     "PEOPLE_360_APP", ["PEOPLE_360_ORG"], "People_360_Presales_Kit"),
    ("spend", "SAP Spend 360", "Spend by category and supplier, contract compliance, supplier risk, ESG and savings, with currency conversion.",
     "sap-bdc-spend-360", "spend-360-public", "spend_360_react", "3007 / 5181",
     "SPEND_360_APP", ["SPEND_360_ORG"], "Spend_360_Presales_Kit"),
    ("wc", "SAP Working Capital 360", "Receivables, payables and inventory working capital: DSO, DPO, DIO and cash conversion.",
     "sap-bdc-working-capital-360", "working-capital-360-public", "working_capital_360_react", "3010 / 5185",
     "WORKING_CAPITAL_360_APP", ["WORKING_CAPITAL_360_ORG"], "Working_Capital_360_Presales_Kit"),
    ("erp", "SAP Cloud ERP 360", "Cross-line-of-business command centre joining Finance, Spend and People by company.",
     None, None, "erp_360_react", "3008 / 5182", None, [], None),
]


# --------------------------------------------------------------- docx helpers
def hyperlink(paragraph, url, text=None):
    """Insert a real clickable hyperlink run."""
    part = paragraph.part
    rid = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                         is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rid)
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    c = OxmlElement("w:color"); c.set(qn("w:val"), "0563C1"); rpr.append(c)
    u = OxmlElement("w:u"); u.set(qn("w:val"), "single"); rpr.append(u)
    r.append(rpr)
    t = OxmlElement("w:t"); t.text = text or url; t.set(qn("xml:space"), "preserve")
    r.append(t)
    h.append(r)
    paragraph._p.append(h)


def link_cell(cell, url, text=None):
    p = cell.paragraphs[0]
    for r in list(p.runs):
        r.text = ""
    hyperlink(p, url, text)
    for h in p._p.iter(qn("w:hyperlink")):
        for rpr in h.iter(qn("w:rPr")):
            sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "17"); rpr.append(sz)


def link_table(doc, headers, rows, widths):
    """rows: list of cells; a cell may be ("url", link, text) to render as a hyperlink."""
    plain = [[c[2] if isinstance(c, tuple) else c for c in row] for row in rows]
    t = table(doc, headers, plain, widths=widths)
    for i, row in enumerate(rows, start=1):
        for j, c in enumerate(row):
            if isinstance(c, tuple) and c[1]:
                link_cell(t.rows[i].cells[j], c[1], c[2])
    return t


def toc(doc):
    p = doc.add_paragraph()
    r = p.add_run()
    for kind, text in (("begin", None), (None, 'TOC \\o "1-2" \\h \\z \\u'), ("separate", None), (None, None), ("end", None)):
        if kind:
            f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), kind); r._r.append(f)
        elif text:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = text; r._r.append(it)
        else:
            t = OxmlElement("w:t"); t.text = "Right-click and choose Update Field to build the table of contents."; r._r.append(t)
    # ask Word to refresh fields on open
    s = doc.settings.element
    uf = OxmlElement("w:updateFields"); uf.set(qn("w:val"), "true"); s.append(uf)


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ------------------------------------------------------------------ facts
def repo_meta(name):
    if not name:
        return None
    for base in (SK, HOME / "Documents/GitHub"):
        d = base / name
        if (d / ".git").exists():
            br = subprocess.run(["git", "-C", str(d), "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
            last = subprocess.run(["git", "-C", str(d), "log", "-1", "--format=%cs"], capture_output=True, text=True).stdout.strip()
            return {"path": str(d), "branch": br, "last": last}
    return {"path": "(not cloned locally)", "branch": "", "last": ""}


VIS = {}
try:
    out = subprocess.run(["gh", "repo", "list", "sfc-gh-dfreriks", "--limit", "200", "--json", "name,visibility"],
                         capture_output=True, text=True, timeout=60).stdout
    VIS = {r["name"]: r["visibility"].title() for r in json.loads(out or "[]")}
except Exception:  # noqa: BLE001
    pass


def listing(conn, name):
    return next((r for r in L[conn]["rows"] if r["name"] == name and r["state"] == "PUBLISHED"), None)


def app(conn, name):
    return next((a for a in A.get(conn, []) if a["app"] == name), None)


def kit_files(kit):
    d = SAP / kit if kit else None
    if not d or not d.exists():
        return []
    return sorted(str(p.relative_to(d)) for p in d.rglob("*")
                  if p.suffix.lower() in (".docx", ".pptx", ".mp4", ".pdf", ".xlsx"))


def acct_url(conn):
    return f"https://app.snowflake.com/{L[conn]['org'].lower()}/{L[conn]['account'].lower()}/"


# ------------------------------------------------------------------ build
doc = Document()
setup_page(doc)
for t, sz, b, c, a in (("SAP BDC 360 Demo Portfolio", 22, True, SAP_NAVY, 2),
                       ("Index of every demo, repository, public site, Native App, listing and presales asset", 11.5, False, SNOW_BLUE, 2),
                       (f"Read live from GitHub, the three demo accounts and the local file system on {dt.date.today():%d %B %Y}  ·  Owner: Dave Freriks", 9, False, GREY, 14)):
    p = doc.add_paragraph(); r = p.add_run(t); r.font.size = Pt(sz); r.font.bold = b; r.font.color.rgb = c
    p.paragraph_format.space_after = Pt(a)
h1(doc, "Contents")
toc(doc)
# static index as well: the TOC field only fills in when Word updates fields
body(doc, "Section index", italic=True)
for line in (["1. Portfolio at a glance", "2. Demo accounts by region", "3. Demos"]
             + [f"    3.{i} {p[1]}" for i, p in enumerate(P, start=1)]
             + ["4. Shared tooling, skills and cross-demo documents", "5. Known gaps"]):
    q = doc.add_paragraph(line); q.paragraph_format.space_after = Pt(1)
page_break(doc)

# 1. coverage matrix
h1(doc, "1. Portfolio at a glance")
body(doc, "Each row is one demo. A tick means the asset exists and was verified today; a dash means it does not exist yet.")
rows = []
for k, title, _, repo, pub, local, ports, appn, lst, kit in P:
    regions = [lbl.split(" ")[0] for conn, lbl in REG if appn and app(conn, appn)]
    rows.append([title, "✓" if repo else "—", "✓" if pub else "—", "✓",
                 ", ".join(regions) or "—", "✓" if any(listing(c, n) for c, _ in REG for n in lst) else "—",
                 "✓" if kit_files(kit) else "—"])
table(doc, ["Demo", "Source repo", "Public site", "Local app", "Native App", "Listings", "Presales kit"], rows,
      widths=[1.75, 0.8, 0.8, 0.7, 1.05, 0.75, 0.85])

# 2. accounts
h1(doc, "2. Demo accounts by region")
link_table(doc, ["Region", "Connection", "Organisation / account", "Snowsight"],
           [[lbl, conn, f"{L[conn]['org']} / {L[conn]['account']}", ("url", acct_url(conn), acct_url(conn))] for conn, lbl in REG],
           widths=[1.3, 1.3, 2.0, 2.1])

# 3. per product
h1(doc, "3. Demos")
for i, (k, title, blurb, repo, pub, local, ports, appn, lst, kit) in enumerate(P, start=1):
    page_break(doc) if i > 1 else None
    h2(doc, f"3.{i} {title}")
    body(doc, blurb)

    links = []
    rm = repo_meta(repo)
    if repo:
        links.append(["Source repository", ("url", GH + repo, GH + repo),
                      f"{VIS.get(repo, '?')} · branch {rm['branch'] or '—'} · last commit {rm['last'] or '—'}"])
    if pub:
        links.append(["Public demo (GitHub Pages)", ("url", PAGES + pub + "/", PAGES + pub + "/"), "Static snapshot, no login"])
        if pub != repo:
            links.append(["Public site repository", ("url", GH + pub, GH + pub), VIS.get(pub, "?")])
    local_path = (SK / local).resolve()
    links.append(["Local app", f"{local_path}", f"server / client ports {ports}"])
    if rm and repo:
        links.append(["Local clone", rm["path"], ""])
    link_table(doc, ["Asset", "Link / location", "Notes"], links, widths=[1.6, 3.4, 1.7])

    if appn:
        rws = []
        for conn, lbl in REG:
            a = app(conn, appn)
            rws.append([lbl, ("url", "https://" + a["url"], a["url"]) if a and a["url"] else "not installed",
                        f"{a['version']} patch {a['patch']}" if a else "—"])
        h2(doc, "Native App")
        link_table(doc, ["Region", "App URL (Snowflake sign-in)", "Version"], rws, widths=[1.4, 4.0, 1.3])

    if lst:
        rws = []
        for n in lst:
            for conn, lbl in REG:
                r = listing(conn, n)
                rws.append([("Native App" if r and r["is_application"] == "true" else "Data share") if conn == REG[0][0] else "",
                            lbl, r["global_name"] if r else "not published", r["uniform_listing_locator"] if r else "—"])
        h2(doc, "Internal Marketplace listings")
        table(doc, ["Listing", "Region", "Global name", "Uniform listing locator"], rws, widths=[1.0, 1.4, 1.3, 3.0])

    files = kit_files(kit)
    if files:
        h2(doc, "Presales kit")
        body(doc, f"{SAP / kit}")
        for f in files:
            bullet(doc, f)
    uc = SK / repo / "docs/USE_CASES.md" if repo else None
    if uc and uc.exists():
        body(doc, f"Use cases: docs/USE_CASES.md in the source repository ({GH}{repo}/blob/{rm['branch'] or 'main'}/docs/USE_CASES.md).", italic=True)

# 4. shared
page_break(doc)
h1(doc, "4. Shared tooling, skills and cross-demo documents")
link_table(doc, ["Item", "Location", "Purpose"], [
    ["Shared Word / PowerPoint kits", "sap-bdc-finance-360/tools/sap_docx_kit.py, sap_pptx_kit.py", "Branding and slide checks used by every kit"],
    ["Screenshot tool", "sap-bdc-finance-360/tools/capture_shots.py", "Captures every app page for decks"],
    ["Narrated video engine", "sap-bdc-finance-360/tools/video/build.py + segments_<domain>.py", "Builds the walkthrough MP4s"],
    ["SAP BDC data products", ("url", GH + "sap-bdc-data-products", GH + "sap-bdc-data-products"), "Data product catalog and CSN"],
    ["SAP BDC CDC", ("url", GH + "sap-bdc-cdc", GH + "sap-bdc-cdc"), "CDC recommendation for BDC shares"],
    ["SAP BDC MCP server", ("url", GH + "sap-bdc-snowflake-mcp-server", GH + "sap-bdc-snowflake-mcp-server"), "MCP tools for BDC Connect on Snowflake"],
    ["Use case catalog", str(HOME / "Downloads/SAP_BDC_360_Use_Case_Catalog.docx"), "42 use cases across the 360 apps"],
    ["Marketplace listing index", str(HOME / "Downloads/SAP_BDC_360_Marketplace_Listings.docx"), "Listings in all three regions"],
    ["Skill: sap-bdc-360-app-lifecycle", "~/.snowflake/cortex/skills/sap-bdc-360-app-lifecycle", "Build, ship, publish and kit a 360 app"],
    ["Skill: launch_core_apps", "~/.snowflake/cortex/skills/launch_core_apps", "Start every local app on its port"],
    ["Skill: provision-360-access", "~/.snowflake/cortex/skills/provision-360-access", "Give a user access to a 360 Native App"],
], widths=[1.8, 3.1, 1.8])

# 5. gaps
h1(doc, "5. Known gaps")
gaps = []
for k, title, _, repo, pub, local, ports, appn, lst, kit in P:
    if appn:
        missing = [lbl for conn, lbl in REG if not app(conn, appn)]
        if missing:
            gaps.append(f"{title}: Native App not installed in {', '.join(missing)}.")
        unv = [lbl for conn, lbl in REG if (app(conn, appn) or {}).get("version") == "UNVERSIONED"]
        if unv:
            gaps.append(f"{title}: Native App is installed unversioned (development mode) in {', '.join(unv)}; upgrades go through a versioned patch.")
    if not repo:
        gaps.append(f"{title}: no source repository, public site, Native App or presales kit yet; local only.")
    elif VIS.get(repo) == "Private":
        gaps.append(f"{title}: source repository {repo} is private.")
    kf = kit_files(kit)
    if kit and not any(f.endswith(".mp4") for f in kf):
        gaps.append(f"{title}: presales kit has no narrated walkthrough video.")
for g in gaps:
    bullet(doc, g)

doc.save(OUT)
print(OUT, len(gaps), "gaps")
