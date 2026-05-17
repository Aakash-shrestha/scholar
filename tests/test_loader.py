from pathlib import Path

import pytest as pyt

from scholar.ingestion.loader import load_and_chunk


def test_load_and_chunk_return_documents() -> None:
    pdf = Path("data/papers/attention.pdf")
    if not pdf.exists():
        pyt.skip("PDF file not found, skipping test.")
    chunks = load_and_chunk(pdf)
    assert len(chunks) > 0
    assert all(c.page_content for c in chunks)
    assert all("source" in c.metadata for c in chunks)
