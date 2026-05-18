from textwrap import dedent

import arxiv
from pydantic import BaseModel, Field

search = arxiv.Search(id_list=["2305.10403v1"])
paper = next(arxiv.Client().results(search))


class ArxivMetadata(BaseModel):
    arxiv_id: str = Field(description="Unique id of the research paper")
    title: str = Field(description="Title of the research paper")
    authors: list[str] = Field(description="List of names of author that contributed in the paper")
    short_citation: str = Field(
        description="""Short citation format like Vaswani et al. 2017, last
        name + et al. + published date"""
    )
    abstract: str = Field(
        description=dedent("""Abstract of the research paper that summarizes
        the entire paper""")
    )
    year: int = Field(description="Year the research paper was published")
    pdf_url: str | None = Field(description="Url of the pdf of the research paper")


def extract_short_citations(paper) -> str:
    return f"{paper.authors[0].name.split()[-1]} et al. {paper.published.year}"


def fetch_arxiv_metadata(arxiv_id: str) -> ArxivMetadata:
    """Fetch a paper's metadata from arXiv given its ID."""
    if not isinstance(arxiv_id, str) or not arxiv_id.strip():
        raise ValueError("arxiv_id must be a non-empty string")
    search = arxiv.Search(id_list=[arxiv_id])
    paper = next(arxiv.Client().results(search))
    print("paper: ", paper)
    return ArxivMetadata(
        arxiv_id=paper.get_short_id(),
        title=paper.title,
        authors=[a.name for a in paper.authors],
        short_citation=extract_short_citations(paper),
        abstract=paper.summary,
        year=paper.published.year,
        pdf_url=paper.pdf_url,
    )
