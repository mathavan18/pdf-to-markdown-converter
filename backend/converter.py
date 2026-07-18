"""PDF -> Markdown conversion using pdfplumber.

Extracts text and tables per page, keeping their original vertical order,
and renders the result as Markdown with `## Page N` section headings.
"""

import io
import re
from typing import List, Tuple

import pdfplumber

# Gap (in PDF points) between two text lines that is treated as a paragraph break.
PARAGRAPH_GAP_THRESHOLD = 8


class ScannedPDFError(Exception):
    """Raised when a PDF has no extractable text (likely scanned/image-only)."""


def _collapse_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _escape_cell(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", "<br>").replace("|", "\\|").strip()


def _table_to_markdown(rows: List[List[str]]) -> str:
    rows = [row for row in rows if any(cell not in (None, "") for cell in row)]
    if not rows:
        return ""

    header, *body = rows
    header_cells = [_escape_cell(c) for c in header]
    width = len(header_cells)
    if width == 0:
        return ""

    lines = [
        "| " + " | ".join(header_cells) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for row in body:
        cells = [_escape_cell(c) for c in row]
        cells = (cells + [""] * width)[:width]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _page_to_markdown(page) -> str:
    tables = page.find_tables()
    table_bboxes = [t.bbox for t in tables]

    text_source = page
    for bbox in table_bboxes:
        text_source = text_source.outside_bbox(bbox)

    items = []
    for line in text_source.extract_text_lines() or []:
        text = line["text"].strip()
        if text:
            items.append({
                "top": line["top"],
                "bottom": line.get("bottom", line["top"] + 12),
                "type": "text",
                "text": text,
            })

    for table, bbox in zip(tables, table_bboxes):
        md_table = _table_to_markdown(table.extract())
        if md_table:
            items.append({"top": bbox[1], "bottom": bbox[3], "type": "table", "text": md_table})

    items.sort(key=lambda item: item["top"])

    blocks: List[str] = []
    paragraph: List[str] = []
    prev_bottom = None

    def flush():
        if paragraph:
            blocks.append(" ".join(paragraph))
            paragraph.clear()

    for item in items:
        if item["type"] == "table":
            flush()
            blocks.append(item["text"])
            prev_bottom = item["bottom"]
            continue

        if prev_bottom is not None and (item["top"] - prev_bottom) > PARAGRAPH_GAP_THRESHOLD:
            flush()

        paragraph.append(item["text"])
        prev_bottom = item["bottom"]

    flush()
    return "\n\n".join(blocks)


def convert_pdf_to_markdown(file_bytes: bytes, include_page_headers: bool = True) -> Tuple[str, int]:
    try:
        pdf = pdfplumber.open(io.BytesIO(file_bytes))
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as a clear message
        raise ValueError("The uploaded file could not be read as a PDF.") from exc

    page_blocks: List[str] = []
    has_any_text = False

    with pdf:
        page_count = len(pdf.pages)
        for index, page in enumerate(pdf.pages, start=1):
            page_markdown = _page_to_markdown(page)
            if page_markdown.strip():
                has_any_text = True

            if include_page_headers:
                section = f"## Page {index}\n\n{page_markdown}".strip()
            else:
                section = page_markdown
            page_blocks.append(section)

    if not has_any_text:
        raise ScannedPDFError(
            "No extractable text was found in this PDF. It looks like a scanned or "
            "image-only document. OCR isn't supported here — please upload a text-based PDF."
        )

    markdown = "\n\n".join(block for block in page_blocks if block.strip())
    markdown = _collapse_whitespace(markdown)
    return markdown, page_count
