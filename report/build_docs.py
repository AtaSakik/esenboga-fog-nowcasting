"""Build single-column Word documents (and PDFs through MS Word) from simple Markdown:
the TÜBİTAK 2209-A project proposal and the plain-language summary.

Markup
------
front matter between ``---`` lines: title, subtitle, lines (``|``-separated), header, lang, font,
size; ``#`` / ``##`` / ``###`` headings; blank line = new paragraph; ``- `` bullets; ``1. ``
numbered items; ``> `` lines = shaded box; pipe tables (first row = header) preceded by an
optional ``Table: caption`` line; ``![caption](results/figures/tr/x.png){width=6.2}`` figures;
``\\pagebreak``; inline ``**bold**`` and ``*italic*``; citations ``[@key; @key2]`` from
report/references.json, numbered in order of first use, listed where ``{{references}}`` stands.

Usage: python report/build_docs.py [proposal_tr summary_tr ...]   (default: all documents)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "report"))
from build_paper import render_pages, to_pdf  # noqa: E402

DOCS = {  # source -> output file name
    "proposal_tr": "TUBITAK_2209A_Proje_Onerisi.docx",
    "summary_tr": "Herkes_Icin_Ozet.docx",
}
INK = RGBColor(0x13, 0x23, 0x3A)
BOX_FILL = "EAF1F8"
HEAD_FILL = "DCE6F0"
INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*)")
CITE = re.compile(r"\[(@[^\]]+)\]")


def resolve_citations(lines: list[str], lang: str) -> tuple[list[str], list[str]]:
    """Replace [@a; @b] by [1], [2] in order of first citation; return the numbered list."""
    bib = json.loads((ROOT / "report" / "references.json").read_text(encoding="utf-8"))
    order: list[str] = []

    def number(m):
        nums = []
        for key in (k.strip().lstrip("@") for k in m.group(1).split(";")):
            if key not in bib:
                raise KeyError(f"unknown reference: {key}")
            if key not in order:
                order.append(key)
            nums.append(str(order.index(key) + 1))
        return "[" + ", ".join(nums) + "]"

    out = [CITE.sub(number, line) for line in lines]
    refs = []
    for i, key in enumerate(order, 1):
        entry = bib[key]
        refs.append(f"[{i}] " + (entry.get(lang, entry["en"]) if isinstance(entry, dict) else entry))
    return out, refs


def shade(cell, fill: str) -> None:
    pr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), fill)
    pr.append(sh)


def add_field(par, code: str) -> None:
    """Insert a Word field (e.g. PAGE) into a paragraph."""
    run = par.add_run()
    for kind, text in (("begin", None), (None, code), ("end", None)):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)


class Doc:
    def __init__(self, meta: dict):
        self.meta = meta
        self.lang = meta.get("lang", "tr")
        self.d = docx.Document()
        cp = self.d.core_properties          # otherwise the library's default name is the author
        cp.author = cp.last_modified_by = meta.get("author", "")
        cp.title = meta.get("title", "")
        st = self.d.styles["Normal"]
        st.font.name = meta.get("font", "Calibri")
        st.element.rPr.rFonts.set(qn("w:eastAsia"), st.font.name)
        st.font.size = Pt(float(meta.get("size", 10.5)))
        pf = st.paragraph_format
        pf.space_after = Pt(5)
        pf.line_spacing = 1.12
        for s in self.d.sections:
            s.top_margin = s.bottom_margin = Cm(2.2)
            s.left_margin = s.right_margin = Cm(2.3)
        for name, size in (("Heading 1", 13), ("Heading 2", 11.5), ("Heading 3", 10.5)):
            h = self.d.styles[name]
            h.font.name, h.font.size, h.font.bold = st.font.name, Pt(size), True
            h.font.color.rgb = INK
            fonts = h.element.rPr.rFonts                 # drop the theme fonts of the template
            for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
                fonts.attrib.pop(qn(a), None)
            h.paragraph_format.space_before = Pt(10 if name == "Heading 1" else 7)
            h.paragraph_format.space_after = Pt(4)
            h.paragraph_format.keep_with_next = True
        self.nfig = self.ntab = 0
        self._footer()

    # ------------------------------------------------------------------ pieces
    def _footer(self) -> None:
        sec = self.d.sections[0]
        p = sec.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if self.meta.get("header"):
            r = p.add_run(self.meta["header"] + "  ·  ")
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        add_field(p, "PAGE")

    def inline(self, par, text: str, size: float | None = None, bold: bool | None = None) -> None:
        for tok in INLINE.split(text):
            if not tok:
                continue
            if tok.startswith("**") and tok.endswith("**"):
                run = par.add_run(tok[2:-2])
                run.bold = True
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
                run = par.add_run(tok[1:-1])
                run.italic = True
            else:
                run = par.add_run(tok)
                if bold is not None:
                    run.bold = bold
            if size:
                run.font.size = Pt(size)

    def title_block(self) -> None:
        m = self.meta
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(m["title"])
        r.bold, r.font.size, r.font.color.rgb = True, Pt(16), INK
        if m.get("subtitle"):
            p = self.d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(m["subtitle"])
            r.font.size, r.italic = Pt(11.5), True
        for line in [x.strip() for x in m.get("lines", "").split("|") if x.strip()]:
            p = self.d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(1)
            self.inline(p, line, size=10)

    def heading(self, level: int, text: str) -> None:
        self.d.add_heading(text, level=level)

    def paragraph(self, text: str) -> None:
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        self.inline(p, text)

    def listing(self, items: list[str], numbered: bool) -> None:
        for it in items:
            p = self.d.add_paragraph(style="List Number" if numbered else "List Bullet")
            p.paragraph_format.space_after = Pt(2)
            self.inline(p, it)

    def box(self, paras: list[str]) -> None:
        t = self.d.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.rows[0].cells[0]
        shade(cell, BOX_FILL)
        cell.paragraphs[0].text = ""
        for k, text in enumerate(paras):
            p = cell.paragraphs[0] if k == 0 else cell.add_paragraph()
            p.paragraph_format.space_after = Pt(3)
            self.inline(p, text)
        self.d.add_paragraph().paragraph_format.space_after = Pt(0)

    def table(self, rows: list[list[str]], caption: str | None) -> None:
        if caption:
            self.ntab += 1
            p = self.d.add_paragraph()
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(6)
            self.inline(p, f"**{'Tablo' if self.lang == 'tr' else 'Table'} {self.ntab}.** {caption}",
                        size=9.5)
        t = self.d.add_table(rows=len(rows), cols=len(rows[0]))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(rows):
            for j, text in enumerate(row):
                cell = t.cell(i, j)
                cell.paragraphs[0].text = ""
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                self.inline(p, text, size=8.8, bold=True if i == 0 else None)
                if i == 0:
                    shade(cell, HEAD_FILL)
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)

    def figure(self, path: Path, caption: str, width: float) -> None:
        self.nfig += 1
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(str(path), width=Inches(width))
        c = self.d.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.inline(c, f"**{'Şekil' if self.lang == 'tr' else 'Figure'} {self.nfig}.** {caption}",
                    size=9)

    def pagebreak(self) -> None:
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def reference(self, text: str) -> None:
        p = self.d.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.first_line_indent = Cm(-0.8)
        p.paragraph_format.space_after = Pt(2)
        self.inline(p, text, size=9)


# ============================================================================ parsing
def parse(path: Path) -> tuple[dict, list[str]]:
    text = path.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---"):
        head, text = text[3:].split("\n---", 1)
        for line in head.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, text.strip("\n").split("\n")


def build(name: str) -> Path:
    meta, lines = parse(ROOT / "report" / f"{name}.md")
    doc = Doc(meta)
    lines, refs = resolve_citations(lines, doc.lang)
    doc.title_block()
    i = 0
    para: list[str] = []

    def flush():
        if para:
            doc.paragraph(" ".join(s.strip() for s in para))
            para.clear()

    caption = None
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            flush()
            i += 1
            continue
        if line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            doc.heading(min(level, 3), line[level:].strip())
        elif line.strip() == r"\pagebreak":
            flush()
            doc.pagebreak()
        elif line.strip() == "{{references}}":
            flush()
            for ref in refs:
                doc.reference(ref)
        elif line.startswith("Table:"):
            flush()
            caption = line[6:].strip()
        elif line.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            doc.table(rows, caption)
            caption = None
            continue
        elif line.startswith("!["):
            flush()
            m = re.match(r"!\[(.*)\]\((.+?)\)(\{width=([\d.]+)\})?", line)
            doc.figure(ROOT / m.group(2), m.group(1), float(m.group(4) or 6.2))
        elif line.startswith("> "):
            flush()
            box = []
            while i < len(lines) and lines[i].startswith(">"):
                box.append(lines[i][1:].strip())
                i += 1
            doc.box([b for b in " ".join(x if x else "\n" for x in box).split("\n") if b.strip()])
            continue
        elif re.match(r"^(- |\d+\. )", line):
            flush()
            numbered = bool(re.match(r"^\d+\. ", line))
            items = []
            while i < len(lines) and re.match(r"^(- |\d+\. )", lines[i]):
                items.append(re.sub(r"^(- |\d+\. )", "", lines[i]).strip())
                i += 1
            doc.listing(items, numbered)
            continue
        else:
            para.append(line)
        i += 1
    flush()
    out = ROOT / "report" / DOCS[name]
    doc.d.save(out)
    print(f"{name}: {out.name} | {doc.nfig} figures, {doc.ntab} tables")
    return out


if __name__ == "__main__":
    for nm in sys.argv[1:] or list(DOCS):
        pdf = to_pdf(build(nm))
        print(f"  -> {pdf.name}: {len(render_pages(pdf, ROOT / 'report' / 'preview'))} pages")
