from pathlib import Path
from textwrap import dedent

import arxiv
from langchain_core.documents import Document
from pydantic import BaseModel, Field
from pydantic.fields import computed_field


class ArxivMetadata(BaseModel):
    arxiv_id: str = Field(description="Unique id of the research paper")
    title: str = Field(description="Title of the research paper")
    authors: list[str] = Field(description="List of names of author that contributed in the paper")
    abstract: str = Field(
        description=dedent("""Abstract of the research paper that summarizes
        the entire paper""")
    )

    @computed_field(description="short citation of the research paper, last name + et al. + year")
    @property
    def short_citation(self) -> str:
        last_name = self.authors[0].split()[-1]
        return f"{last_name} et al. {self.year}"

    year: int = Field(description="Year the research paper was published")
    pdf_url: str | None = Field(description="Url of the pdf of the research paper")


def fetch_arxiv_metadata(arxiv_id: str) -> ArxivMetadata:
    """Fetch a paper's metadata from arXiv given its ID."""
    if not isinstance(arxiv_id, str) or not arxiv_id.strip():
        raise ValueError("arxiv_id must be a non-empty string")
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(arxiv.Client(delay_seconds=5, num_retries=5).results(search))
    return ArxivMetadata(
        arxiv_id=paper.get_short_id(),
        title=paper.title,
        authors=[a.name for a in paper.authors],
        abstract=paper.summary,
        year=paper.published.year,
        pdf_url=paper.pdf_url,
    )


def download_paper(metadata: ArxivMetadata, paper_dir: Path = Path("data/papers")) -> Path:
    """
    Download the paper's PDF from arXiv and save it to disk. Returns the path to the downloaded PDF."""
    paper_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = paper_dir / f"{metadata.arxiv_id}.pdf"
    if pdf_path.exists():
        return pdf_path
    search = arxiv.Search(id_list=[metadata.arxiv_id])
    paper = next(arxiv.Client(delay_seconds=5, num_retries=5).results(search))
    paper.download_pdf(dirpath=str(paper_dir), filename=f"{metadata.arxiv_id}.pdf")
    return Path(pdf_path)


def enrich_chunks(chunks: list[Document], metadata: ArxivMetadata) -> list[Document]:
    """Add paper-level metadata to each chunk's metadata dict."""
    for chunk in chunks:  # since chunk.metadata is mutable, it can be updated in plcace
        chunk.metadata["arxiv_id"] = metadata.arxiv_id
        chunk.metadata["title"] = metadata.title
        chunk.metadata["short_citation"] = metadata.short_citation
        chunk.metadata["year"] = metadata.year
    return chunks
