"""Clickable-hyperlink helpers shared by the index and listings builders."""
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


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
