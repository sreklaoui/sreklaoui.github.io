#!/usr/bin/env python3
"""Generate the downloadable CV PDF from cv.json.

Usage:
    uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
    .venv/bin/python generate-cv.py

Writes output/pdf/said-reklaoui-cv.pdf, which index.html links from the header.
The layout mirrors the site: a dark header band, an AI focus strip, and
section rules in the same accent colour.
"""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageTemplate, Paragraph, Spacer,
)

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output" / "pdf" / "said-reklaoui-cv.pdf"

INK = colors.HexColor("#101a2e")
INK_SOFT = colors.HexColor("#24334d")
BODY = colors.HexColor("#414f66")
MUTED = colors.HexColor("#6b7890")
LINE = colors.HexColor("#d9dee7")
ACCENT = colors.HexColor("#c02e4c")
CHIP_BG = colors.HexColor("#f2f4f8")

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
BAND_H = 41 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

SANS = "Helvetica"
SANS_B = "Helvetica-Bold"
SANS_I = "Helvetica-Oblique"

S = {
    "summary": ParagraphStyle("summary", fontName=SANS, fontSize=8.6, leading=11.6,
                              textColor=BODY, spaceAfter=2),
    "section": ParagraphStyle("section", fontName=SANS_B, fontSize=8.2, leading=10,
                              textColor=ACCENT, spaceBefore=0, spaceAfter=0),
    "company": ParagraphStyle("company", fontName=SANS_B, fontSize=10, leading=12,
                              textColor=INK),
    "period": ParagraphStyle("period", fontName=SANS, fontSize=7.8, leading=12,
                             textColor=MUTED, alignment=2),
    "role": ParagraphStyle("role", fontName=SANS_B, fontSize=8.6, leading=10.5,
                           textColor=ACCENT, spaceBefore=2.5, spaceAfter=2.5),
    "bullet": ParagraphStyle("bullet", fontName=SANS, fontSize=8.4, leading=11,
                             textColor=BODY, leftIndent=8.5, firstLineIndent=-8.5,
                             spaceAfter=1.6),
    "tech": ParagraphStyle("tech", fontName=SANS_I, fontSize=7.7, leading=10,
                           textColor=MUTED, leftIndent=8.5, spaceBefore=1, spaceAfter=1),
    "proj": ParagraphStyle("proj", fontName=SANS, fontSize=8.4, leading=11,
                           textColor=BODY, leftIndent=8.5, firstLineIndent=-8.5,
                           spaceAfter=3),
    "skill": ParagraphStyle("skill", fontName=SANS, fontSize=8.3, leading=11,
                            textColor=BODY, leftIndent=52, firstLineIndent=-52,
                            spaceAfter=2.6),
    "edu": ParagraphStyle("edu", fontName=SANS, fontSize=8.4, leading=11,
                          textColor=BODY, spaceAfter=2),
}


def esc(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("—", "&#8212;").replace("–", "&#8211;")
            .replace("·", "&#183;"))


class Rule(Flowable):
    """Hairline that closes a section heading."""

    def __init__(self, width, thickness=0.6, color=LINE, space_before=2.5, space_after=5):
        Flowable.__init__(self)
        self.width = width
        self.thickness = thickness
        self.color = color
        self.space_before = space_before
        self.space_after = space_after
        self.height = thickness + space_before + space_after

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        y = self.space_after
        self.canv.line(0, y, self.width, y)


class Chips(Flowable):
    """Wrapping pill row, used for the AI focus strip."""

    PAD_X, PAD_Y, GAP, FONT_SIZE = 5.5, 3.0, 4.5, 7.6

    def __init__(self, labels, width):
        Flowable.__init__(self)
        self.labels = labels
        self.width = width
        self.rows = self._layout()
        row_h = self.FONT_SIZE + 2 * self.PAD_Y
        self.height = len(self.rows) * row_h + (len(self.rows) - 1) * 3.5

    def _chip_w(self, label):
        return stringWidth(label, SANS_B, self.FONT_SIZE) + 2 * self.PAD_X

    def _layout(self):
        rows, row, used = [], [], 0.0
        for label in self.labels:
            w = self._chip_w(label)
            if row and used + self.GAP + w > self.width:
                rows.append(row)
                row, used = [], 0.0
            used += w + (self.GAP if row else 0)
            row.append((label, w))
        if row:
            rows.append(row)
        return rows

    def draw(self):
        row_h = self.FONT_SIZE + 2 * self.PAD_Y
        y = self.height - row_h
        for row in self.rows:
            x = 0.0
            for label, w in row:
                self.canv.setFillColor(CHIP_BG)
                self.canv.setStrokeColor(LINE)
                self.canv.setLineWidth(0.5)
                self.canv.roundRect(x, y, w, row_h, 2.4, stroke=1, fill=1)
                self.canv.setFillColor(INK_SOFT)
                self.canv.setFont(SANS_B, self.FONT_SIZE)
                self.canv.drawString(x + self.PAD_X, y + self.PAD_Y + 1.4, label)
                x += w + self.GAP
            y -= row_h + 3.5


class HeaderRow(Flowable):
    """Company name on the left, period right-aligned on the same baseline."""

    def __init__(self, left, right, width):
        Flowable.__init__(self)
        self.left, self.right, self.width = left, right, width
        self.height = 12

    def draw(self):
        self.canv.setFillColor(INK)
        self.canv.setFont(SANS_B, 10)
        self.canv.drawString(0, 2.5, self.left)
        self.canv.setFillColor(MUTED)
        self.canv.setFont(SANS, 7.8)
        self.canv.drawRightString(self.width, 3.1, self.right)


def section(title, width=CONTENT_W):
    return [Paragraph(esc(title).upper(), S["section"]), Rule(width)]


def draw_band(canvas, doc, data):
    """Dark header band on page 1 with name, headline and contact line."""
    canvas.saveState()
    top = PAGE_H - BAND_H
    canvas.setFillColor(INK)
    canvas.rect(0, top, PAGE_W, BAND_H, stroke=0, fill=1)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, top, PAGE_W, 2.6, stroke=0, fill=1)

    x = MARGIN
    canvas.setFillColor(colors.white)
    canvas.setFont(SANS_B, 23)
    canvas.drawString(x, PAGE_H - 16.5 * mm, data["name"])

    canvas.setFillColor(colors.HexColor("#f0a4b4"))
    canvas.setFont(SANS_B, 9.4)
    canvas.drawString(x, PAGE_H - 22.2 * mm, data["headline"])

    canvas.setFillColor(colors.HexColor("#b9c4d8"))
    canvas.setFont(SANS, 8.4)
    canvas.drawString(x, PAGE_H - 27.4 * mm, data["tagline"])

    contact = "  |  ".join([data["location"], data["linkedin"], data["github"]])
    canvas.setFillColor(colors.HexColor("#93a1bb"))
    canvas.setFont(SANS, 7.6)
    canvas.drawString(x, PAGE_H - 33.4 * mm, contact)
    canvas.restoreState()


def draw_footer(canvas, doc, data):
    canvas.saveState()
    canvas.setFillColor(MUTED)
    canvas.setFont(SANS, 7)
    canvas.drawString(MARGIN, 9 * mm, f'{data["name"]}  |  {data["site"]}')
    canvas.drawRightString(PAGE_W - MARGIN, 9 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def build_story(data):
    story = []

    story += section("AI Focus")
    story += [Chips(data["ai_focus"], CONTENT_W), Spacer(1, 7)]

    story += section("Profile")
    story += [Paragraph(esc(data["summary"]), S["summary"]), Spacer(1, 7)]

    story += section("Selected AI Work")
    for project in data["projects"]:
        story.append(KeepTogether([
            Paragraph(
                f'•&nbsp;&nbsp;<font name="{SANS_B}" color="#24334d">{esc(project["name"])}</font> '
                f'&#8212; {esc(project["description"])} '
                f'<font name="{SANS_I}" color="#6b7890" size="7.7">{esc(project["tech"])}</font>',
                S["proj"]),
        ]))
    story.append(Spacer(1, 3))

    story += section("Experience")
    for job in data["experience"]:
        # Keep the company header glued to the first role and its first bullet, then let the
        # rest flow, so a long job can split across pages instead of leaving a gap behind.
        head = [HeaderRow(job["company"], f'{job["location"]}  |  {job["period"]}', CONTENT_W)]
        tail = []
        for index, role in enumerate(job["roles"]):
            target = head if index == 0 else tail
            target.append(Paragraph(esc(role["title"]), S["role"]))
            for pos, highlight in enumerate(role["highlights"]):
                para = Paragraph(f'\u2022&nbsp;&nbsp;{esc(highlight)}', S["bullet"])
                (head if index == 0 and pos == 0 else tail).append(para)
            if role.get("tech"):
                tail.append(Paragraph(esc(role["tech"]), S["tech"]))
        story.append(KeepTogether(head))
        story.extend(tail)
        story.append(Spacer(1, 6))

    story += section("Skills")
    for group, items in data["skills"].items():
        story.append(Paragraph(
            f'<font name="{SANS_B}" color="#24334d">{esc(group)}</font>&nbsp;&nbsp;{esc(items)}',
            S["skill"]))
    story.append(Spacer(1, 5))

    story += section("Education")
    for item in data["education"]:
        story.append(Paragraph(
            f'<font name="{SANS_B}" color="#24334d">{esc(item["title"])}</font>'
            f'&nbsp;&nbsp;&#183;&nbsp;&nbsp;{esc(item["school"])}'
            f'<font color="#6b7890">&nbsp;&nbsp;&#183;&nbsp;&nbsp;{esc(item["period"])}</font>',
            S["edu"]))
    story.append(Spacer(1, 5))

    story += section("Languages")
    story.append(Paragraph(esc(data["languages"]), S["summary"]))
    return story


def main():
    data = json.loads((ROOT / "cv.json").read_text())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(OUTPUT), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=14 * mm,
        title=f'{data["name"]} - CV', author=data["name"],
        subject=data["headline"],
    )

    first = Frame(MARGIN, 14 * mm, CONTENT_W,
                  PAGE_H - BAND_H - 14 * mm - 6 * mm, id="first",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    rest = Frame(MARGIN, 14 * mm, CONTENT_W,
                 PAGE_H - MARGIN - 14 * mm, id="rest",
                 leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    doc.addPageTemplates([
        PageTemplate(id="first", frames=[first],
                     onPage=lambda c, d: (draw_band(c, d, data), draw_footer(c, d, data)),
                     autoNextPageTemplate="rest"),
        PageTemplate(id="rest", frames=[rest],
                     onPage=lambda c, d: draw_footer(c, d, data)),
    ])

    doc.build(build_story(data))
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
