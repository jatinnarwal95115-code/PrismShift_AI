import re
from pathlib import Path
from uuid import uuid4

from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from pptx import Presentation
from pptx.util import Inches as PptInches, Pt as PptPt

from Backend.services.database import REPORT_DIR


# --------------------------------------------------
# PARSING
# --------------------------------------------------

_LABEL = re.compile(
    r"^(Subject|Date|To|From|Title|Prepared by|Submitted to|Location)\s*:",
    re.IGNORECASE
)


def split_blocks(content: str) -> list[list[str]]:
    """Split a document into blocks separated by blank lines.

    Each block is a list of lines, so address blocks and signatures keep their
    line breaks instead of turning into separate, widely spaced paragraphs.
    """

    blocks, current = [], []

    for raw_line in (content or "").replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()

        if line:
            current.append(re.sub(r"^[-*•]\s+", "• ", line))
        elif current:
            blocks.append(current)
            current = []

    if current:
        blocks.append(current)

    return blocks


def is_heading(block: list[str]) -> bool:
    """A short single line without a final full stop, e.g. '2. Observations'."""

    if len(block) != 1:
        return False

    line = block[0]

    return (
        len(line) <= 70
        and not line.endswith((".", ",", ";"))
        and not line.startswith("•")
        and not _LABEL.match(line)
        and bool(re.match(r"^(\d+[.)]\s+)?[A-Z]", line))
        and (line.endswith(":") or bool(re.match(r"^\d+[.)]\s+", line)))
    )


def find_title(blocks: list[list[str]]) -> str:
    for block in blocks:
        for line in block:
            match = re.match(r"^(Subject|Title)\s*:\s*(.+)$", line, re.IGNORECASE)

            if match:
                return match.group(2).strip()[:90]

    return "PrismShift AI Report"


# --------------------------------------------------
# PDF
# --------------------------------------------------

_FONT_CANDIDATES = [
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    # Windows (Nirmala UI also covers Devanagari / Hindi)
    "C:/Windows/Fonts/Nirmala.ttf",
    "C:/Windows/Fonts/arial.ttf",
    # macOS
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

_BOLD_CANDIDATES = {
    "DejaVuSans.ttf": "DejaVuSans-Bold.ttf",
    "Nirmala.ttf": "NirmalaB.ttf",
    "arial.ttf": "arialbd.ttf",
}

_font_cache = None


def _pdf_fonts() -> tuple[str, str]:
    """Return (regular, bold) font names. Prefer a Unicode TTF so names and
    text outside basic Latin (e.g. Hindi) do not turn into black squares."""

    global _font_cache

    if _font_cache:
        return _font_cache

    _font_cache = ("Helvetica", "Helvetica-Bold")

    for candidate in _FONT_CANDIDATES:
        path = Path(candidate)

        if not path.exists():
            continue

        try:
            pdfmetrics.registerFont(TTFont("PS-Body", str(path)))
            bold_path = path.with_name(_BOLD_CANDIDATES.get(path.name, ""))

            if bold_path.is_file():
                pdfmetrics.registerFont(TTFont("PS-Bold", str(bold_path)))
                _font_cache = ("PS-Body", "PS-Bold")
            else:
                _font_cache = ("PS-Body", "PS-Body")

            break
        except Exception:
            continue

    return _font_cache


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def generate_pdf(content: str) -> str:
    filepath = REPORT_DIR / f"report_{uuid4().hex}.pdf"
    regular, bold = _pdf_fonts()

    document = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title="PrismShift AI Report",
        author="PrismShift AI"
    )

    body = ParagraphStyle(
        "PSBody",
        parent=getSampleStyleSheet()["BodyText"],
        fontName=regular,
        fontSize=11,
        leading=16,
        spaceAfter=0
    )
    heading = ParagraphStyle("PSHeading", parent=body, fontName=bold, fontSize=12)

    story = []

    for block in split_blocks(content):
        style = heading if is_heading(block) else body
        lines = []

        for line in block:
            safe = _escape(line)
            label = _LABEL.match(line)

            if label and style is body:
                end = label.end()
                safe = f"<b>{_escape(line[:end])}</b>{_escape(line[end:])}"

            lines.append(safe)

        story.append(Paragraph("<br/>".join(lines), style))
        story.append(Spacer(1, 10))

    if not story:
        story.append(Paragraph("(empty report)", body))

    document.build(story)

    return str(filepath)


# --------------------------------------------------
# DOCX
# --------------------------------------------------

def generate_docx(content: str) -> str:
    filepath = REPORT_DIR / f"report_{uuid4().hex}.docx"

    document = Document()

    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(10)

    for block in split_blocks(content):
        paragraph = document.add_paragraph()
        heading = is_heading(block)

        for index, line in enumerate(block):
            label = _LABEL.match(line)

            if label and not heading:
                paragraph.add_run(line[:label.end()]).bold = True
                paragraph.add_run(line[label.end():])
            else:
                run = paragraph.add_run(line)
                run.bold = heading

            if index < len(block) - 1:
                paragraph.add_run().add_break()

    document.save(str(filepath))

    return str(filepath)


# --------------------------------------------------
# PPTX
# --------------------------------------------------

# Cost of a slide = lines + a little extra for the gap between blocks.
_MAX_SLIDE_COST = 20
_MAX_CHARS_PER_SLIDE = 1100


def _slide_groups(blocks: list[list[str]]) -> list[list[list[str]]]:
    """Pack whole blocks into slides so a paragraph is never cut in half."""

    groups, current, lines, chars = [], [], 0, 0

    for block in blocks:
        block_lines = len(block) + 0.6
        block_chars = sum(len(line) for line in block)

        if current and (
            lines + block_lines > _MAX_SLIDE_COST
            or chars + block_chars > _MAX_CHARS_PER_SLIDE
        ):
            groups.append(current)
            current, lines, chars = [], 0, 0

        current.append(block)
        lines += block_lines
        chars += block_chars

    if current:
        groups.append(current)

    return groups


def generate_pptx(content: str) -> str:
    filepath = REPORT_DIR / f"report_{uuid4().hex}.pptx"

    blocks = split_blocks(content)
    title = find_title(blocks)

    presentation = Presentation()

    for index, group in enumerate(_slide_groups(blocks) or [[["(empty report)"]]]):
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])

        slide.shapes.title.text = title if index == 0 else f"{title} (continued)"
        slide.shapes.title.text_frame.paragraphs[0].font.size = PptPt(28)

        body = slide.placeholders[1]
        # Use more of the slide than the default layout does.
        body.top, body.height = PptInches(1.45), PptInches(5.6)

        frame = body.text_frame
        frame.clear()
        frame.word_wrap = True

        first = True

        for block in group:
            for line in block:
                paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
                first = False
                paragraph.text = line
                paragraph.font.size = PptPt(14)

            # Space between blocks.
            paragraph.space_after = PptPt(10)

    presentation.save(str(filepath))

    return str(filepath)


# --------------------------------------------------
# PUBLIC ENTRY POINT
# --------------------------------------------------

def generate_report(content: str, file_format: str) -> str:
    """Export a report in the requested format."""

    file_format = file_format.lower().strip()

    exporters = {
        "pdf": generate_pdf,
        "docx": generate_docx,
        "pptx": generate_pptx
    }

    if file_format not in exporters:
        raise ValueError("Format must be PDF, DOCX, or PPTX.")

    return exporters[file_format](content)
