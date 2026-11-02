"""Input-side defense (PRD §6 Day 5): strip hidden/off-page text before chunking.

Walks PyMuPDF spans and drops any that a human reader would never see — near-white
text (white-on-white) or text positioned outside the page rectangle. This is the
countermeasure to the Poisoning Engine's hidden-text techniques; toggled by
DEFENSE_INPUT_SANITIZER. When off, ingest uses the raw unsanitized path (the vuln).
"""

import pymupdf

# Per-channel threshold: a span this light on a white page is effectively invisible.
_NEAR_WHITE_MIN = 0xF0


def _is_near_white(color_int: int) -> bool:
    r, g, b = (color_int >> 16) & 0xFF, (color_int >> 8) & 0xFF, color_int & 0xFF
    return min(r, g, b) >= _NEAR_WHITE_MIN


def _is_off_page(bbox, rect) -> bool:
    x0, y0, x1, y1 = bbox
    return x1 <= rect.x0 or y1 <= rect.y0 or x0 >= rect.x1 or y0 >= rect.y1


def extract_visible_text(pdf_bytes: bytes) -> tuple[str, list[dict]]:
    """Visible text only, plus a report of the spans that were stripped and why."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    kept: list[str] = []
    stripped: list[dict] = []
    try:
        for page in doc:
            rect = page.rect
            for block in page.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "")
                        if not text.strip():
                            continue
                        bbox = span.get("bbox")
                        if _is_near_white(span.get("color", 0)):
                            stripped.append({"reason": "near_white", "text": text})
                        elif bbox and _is_off_page(bbox, rect):
                            stripped.append({"reason": "off_page", "text": text})
                        else:
                            kept.append(text)
    finally:
        doc.close()
    return "\n".join(kept), stripped
