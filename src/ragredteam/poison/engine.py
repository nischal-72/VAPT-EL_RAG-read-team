"""Poisoning Engine (skeleton) — generates test PDFs for the local injection fuzzer.

Research fixture for the RAGRedTeam defensive project (docs/PRD.md): local only, own
Ollama, no external targets. The hidden-text technique here is precisely what Day 5's
input sanitizer is built to detect and strip; this engine exists so that defense has
something to measure against.

`payload_text` is supplied by the caller (Day 3's payload library). This module only
provides the PDF carrier mechanism, not the injection content.
"""

import io
from enum import Enum

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

_BENIGN_COVER = (
    "Quarterly Operations Summary\n"
    "This document reviews routine logistics metrics for the period.\n"
    "Shipment volumes were stable and no incidents were reported."
)


class Technique(str, Enum):
    HIDDEN_TEXT = "hidden_text"  # #1: white-on-white run at page bottom


def make_text_pdf(body: str) -> bytes:
    """A plain, fully-visible text PDF. Used for benign test docs and as a base layer."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    _, height = letter
    c.setFillColorRGB(0, 0, 0)
    text = c.beginText(72, height - 72)
    for line in body.splitlines() or [body]:
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
    return buf.getvalue()


def generate_malicious_pdf(
    payload_text: str,
    technique: Technique = Technique.HIDDEN_TEXT,
    *,
    cover: str = _BENIGN_COVER,
) -> bytes:
    """Carrier PDF with a benign visible cover and `payload_text` planted via `technique`."""
    technique = Technique(technique)
    if technique is Technique.HIDDEN_TEXT:
        return _hidden_text_pdf(payload_text, cover)
    # Skeleton: later techniques (off-page position, tiny font, metadata fields) land here.
    raise NotImplementedError(f"technique not implemented yet: {technique}")


def _hidden_text_pdf(payload_text: str, cover: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    _, height = letter

    # Visible, benign cover text.
    c.setFillColorRGB(0, 0, 0)
    visible = c.beginText(72, height - 72)
    for line in cover.splitlines():
        visible.textLine(line)
    c.drawText(visible)

    # Hidden run: white text on the white page background near the bottom. Invisible to a
    # human reader, but extracted verbatim by PyMuPDF get_text() in the unsanitized path.
    c.setFillColorRGB(1, 1, 1)
    hidden = c.beginText(72, 90)
    for line in payload_text.splitlines() or [payload_text]:
        hidden.textLine(line)
    c.drawText(hidden)

    c.showPage()
    c.save()
    return buf.getvalue()
