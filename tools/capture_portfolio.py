#!/usr/bin/env python3
"""Capture dashboard screenshots, KPI cards and page lists for the asset index V2.

Public GitHub Pages builds need no login, so they are the source for every demo
that has one; Cloud ERP 360 has no public build and is captured from its local app.

Writes /tmp/portfolio/<key>/{01_overview,02_*,03_*}.png and /tmp/portfolio/portfolio.json.
"""
import json
import pathlib
import re

from playwright.sync_api import sync_playwright

OUT = pathlib.Path("/tmp/portfolio")
PAGES = "https://sfc-gh-dfreriks.github.io/"

# key -> (url, [feature pages to capture, by nav label])
TARGETS = {
    "finance": (PAGES + "finance-360-public/", ["General Ledger", "Accounts Receivable"]),
    "sales": (PAGES + "sales-360-public/", ["Sales Funnel", "Sales Forecast"]),
    "supply": (PAGES + "supply-chain-360-public/", ["Supply Chain Map", "Inventory & Warehouse"]),
    "ontology": (PAGES + "supply-chain-ontology/", ["Ontology Model", "Graph Traversal"]),
    "people": (PAGES + "people-360-public/", ["Attrition", "Diversity & Inclusion"]),
    "spend": (PAGES + "spend-360-public/", ["Supplier Risk", "Contract Compliance"]),
    "wc": (PAGES + "working-capital-360-public/", ["Cash & Liquidity", "Accounts Receivable"]),
    "erp": ("http://localhost:5182/", ["Company Comparison", "BDC Sources & Lineage"]),
}
# The last real page in each app; sidebar filter values follow it in DOM order.
LAST_PAGE = {"finance": "Cortex Analyst", "supply": "Cortex Analyst", "people": "Ask the Agent",
             "spend": "Ask the Agent", "wc": "Ask the Agent", "erp": "Ask the Agent"}
SKIP_NAV = {"All", "None", "USD", "EUR", "JPY"}
VALUE = re.compile(r"^[-+]?[$€¥£]?[-+]?\d[\d,.]*\s?(%|[KMBT]|d|x|days)?$|^[-+]?[$€¥£]\d")


def settle(pg):
    try:
        pg.wait_for_load_state("networkidle", timeout=30000)
    except Exception:  # noqa: BLE001
        pass
    pg.wait_for_timeout(3500)


def kpis(text, limit=8):
    """Pull (label, value, note) triples from KPI cards: an ALL-CAPS label line, then a value line."""
    lines = [x.strip() for x in text.split("\n") if x.strip()]
    out = []
    for i, ln in enumerate(lines[:-1]):
        nxt = lines[i + 1]
        if ln.upper() == ln and re.search(r"[A-Z]{3}", ln) and len(ln) < 48 and VALUE.search(nxt):
            note = lines[i + 2] if i + 2 < len(lines) and lines[i + 2].upper() != lines[i + 2] else ""
            out.append({"label": ln.title().replace("Dso", "DSO").replace("Dpo", "DPO").replace("Dio", "DIO")
                        .replace("Ccc", "CCC").replace("Oee", "OEE").replace("Ebitda", "EBITDA")
                        .replace("Crm", "CRM").replace("Sap", "SAP").replace("Po ", "PO "),
                        "value": nxt, "note": note[:60]})
        if len(out) >= limit:
            break
    return out


def ontology_kpis(text):
    """The ontology overview prints number, label, note (number above label)."""
    lines = [x.strip() for x in text.split("\n") if x.strip()]
    out = []
    for i in range(len(lines) - 2):
        if re.fullmatch(r"[\d,]+", lines[i]) and re.fullmatch(r"[a-z ]+", lines[i + 1]):
            out.append({"label": lines[i + 1].title(), "value": lines[i], "note": lines[i + 2][:60]})
        if len(out) >= 4:
            break
    return out


def nav_items(pg):
    items = []
    for t in pg.locator("aside button, aside a, nav button, nav a").all_inner_texts():
        t = t.strip()
        if t and t not in SKIP_NAV and t not in items and len(t) < 40 and not t.isdigit():
            items.append(t)
    return items


def main():
    OUT.mkdir(exist_ok=True)
    result = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.5)
        for key, (url, feats) in TARGETS.items():
            d = OUT / key
            d.mkdir(exist_ok=True)
            try:
                pg.goto(url, wait_until="domcontentloaded", timeout=60000)
                settle(pg)
            except Exception as e:  # noqa: BLE001
                print(key, "unreachable:", str(e)[:80])
                continue
            # ERP starts with its company filter cleared, so select all companies first.
            if key == "erp":
                pg.get_by_role("button", name="All", exact=True).first.click(timeout=10000)
                settle(pg)
            nav = nav_items(pg)
            if key in LAST_PAGE and LAST_PAGE[key] in nav:
                nav = nav[: nav.index(LAST_PAGE[key]) + 1]
            main_text = pg.inner_text("main") if pg.locator("main").count() else pg.inner_text("body")
            shots = [str(d / "01_overview.png")]
            pg.screenshot(path=shots[0])
            for i, label in enumerate(feats, start=2):
                try:
                    pg.get_by_role("button", name=label, exact=True).first.click(timeout=10000)
                    settle(pg)
                    f = d / f"0{i}_{re.sub(r'[^a-z]+', '_', label.lower()).strip('_')}.png"
                    pg.screenshot(path=str(f))
                    shots.append(str(f))
                except Exception as e:  # noqa: BLE001
                    print(key, "could not open", label, str(e)[:60])
            result[key] = {"url": url, "nav": nav, "kpis": ontology_kpis(main_text) if key == "ontology" else kpis(main_text), "shots": shots,
                           "shot_labels": ["Overview"] + feats[: len(shots) - 1]}
            print(f"{key:9s} {len(nav):2d} pages  {len(result[key]['kpis'])} KPIs  {len(shots)} shots")
        b.close()
    (OUT / "portfolio.json").write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
