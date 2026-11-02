"""PDF text extraction and chunking for the ingest path.

VULNERABILITY (intended, PRD §6 Day 1): no cleaning, normalization, or hidden-text
stripping happens here. Whatever PyMuPDF extracts — including white-on-white or
off-page runs planted by the Poisoning Engine — is chunked and embedded verbatim.
Day 5's input sanitizer is the only place allowed to change this.
"""

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ~4 chars per token; keeps a tokenizer out of the dependency set while honouring §7.
_CHARS_PER_TOKEN = 4


def extract_text(pdf_bytes: bytes) -> str:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def chunk_text(text: str, chunk_tokens: int) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_tokens * _CHARS_PER_TOKEN,
        chunk_overlap=0,
    )
    return splitter.split_text(text)
