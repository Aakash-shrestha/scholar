import re
from pathlib import Path
from textwrap import dedent

import fitz
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from scholar.models import get_chat_model


class ExtractedReference(BaseModel):
    title: str
    authors: list[str]
    year: int | None
    arxiv_id: str | None
    doi: str | None


def find_reference_section(original_paper: Path) -> int:
    """
    finds the starting page of the reference section from the original research paper
    """
    docs = fitz.open(original_paper)
    pattern = re.compile(
        r"^\s*(references|bibliography|works cited)\s*$", re.IGNORECASE | re.MULTILINE
    )
    for page_num in range(len(docs) - 1, -1, -1):
        text = str(docs[page_num].get_text("text"))
        if pattern.search(text):
            return page_num
    return -1


def extract_references(pdf_path: Path) -> list[ExtractedReference]:
    """
    finds all the referenced papers from the original paper and returns extracted metadata like
    title, authors, year, arxiv_id and doi if available
    """
    prompt = ChatPromptTemplate.from_template(
        dedent("""
        Extract all references from this text and return a JSON array.
        For each reference extract: title, authors, year, arxiv_id (if arxiv link present), doi.

        Reference text:
        {references_text}

        Return ONLY a JSON array, no other text.
        """).strip()
    )

    model = get_chat_model(fast=True, pro=False)
    reference_page_start = find_reference_section(pdf_path)
    if reference_page_start == -1:
        raise ValueError("Could not find reference section in the paper.")

    reference_text: list[str] = []
    paper_pages = fitz.open(pdf_path)
    for page_num in range(reference_page_start, len(paper_pages)):
        reference_text.append(str(paper_pages[page_num].get_text("text")))

    model_chain = prompt | model | JsonOutputParser()
    result = model_chain.invoke({"references_text": "\n".join(reference_text)})
    references = []
    for item in result:
        try:
            references.append(ExtractedReference(**item))
        except Exception:
            continue

    return references
