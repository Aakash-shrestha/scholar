"""test for arxiv injection"""

import pytest

from scholar.ingestion.arxiv_fetch import fetch_arxiv_metadata


@pytest.mark.network
def test_fetch_arxiv_metadata_fetch_attention_metadata() -> None:
    """fetch_arxiv_metadata should return metadata for the Transformer paper."""
    metadata = fetch_arxiv_metadata("1706.03762")
    assert "Attention" in metadata.title
    assert "Vaswani" in metadata.authors[0]
    assert metadata.year == 2017
    assert metadata.pdf_url is not None
    assert metadata.short_citation.startswith("Vaswani")
