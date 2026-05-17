from zipfile._path import Path

from langchain_core.documents import Document
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_and_chunk(
    pdf_path: str | Path, chunk_size: int = 1000, overlap: int = 150
) -> list[Document]:
    loader = PyMuPDF4LLMLoader(pdf_path if type(pdf_path) is str else str(pdf_path))
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, overlap=overlap)
    chunks = splitter.split_documents(docs)
    return chunks
