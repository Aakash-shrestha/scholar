from textwrap import dedent

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.runnables.passthrough import RunnablePassthrough


def format_docs(docs: list[Document]) -> str:
    """takes the list of documents from retriever and adds metadata to pagecontent of the chunks
    args: docs: list of documents returned by retriever, each document has page_content and metadata
    with short_citation and page number as keys.
    returns:
    a string with page content and metadata formatted as [short_citation, p{page number}]
    page_content
    """
    block = []
    for doc in docs:
        citation = doc.metadata.get("short_citation", "unknown")
        page = doc.metadata.get("page", "?")
        page_label = f"p.{page + 1}" if isinstance(page, int) else "p.?"
        block.append(f"[{citation}, p{page_label}]\n{doc.page_content}")
    return "\n\n--\n\n".join(block)


def build_rag_chain(retriever, model) -> Runnable:
    """Return a Runnable that takes a question string and returns an answer string. The chain
    retrieves relevant chunks from the retriever, formats them with citations, and then prompts the
    model to answer the question based on the retrieved context."""
    prompt = ChatPromptTemplate.from_template(
        dedent("""
    You are an expert research assistant. Answer the query using only the provided context.
    Cite every fact with its source label. If the context lacks sufficient information, say so explicitly.

    Formatting rules:
    - Use $...$ for inline math expressions (e.g. $\\sqrt{{d_k}}$).
    - Use $$...$$ on its own line for display/block equations (e.g. standalone formulas).
    - Never use plain text or code blocks for mathematical notation.

    context: {context}
    question: {question}
        """).strip()
    )
    rag_chain = (
        {"context": retriever | RunnableLambda(format_docs), "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )
    return rag_chain


def build_rag_chain_from_docs(docs: list[Document], model) -> Runnable:
    """
    Helper function to build a RAG chain directly from a list of documents, without needing a
    retriever.
    """
    prompt = ChatPromptTemplate.from_template(
        dedent("""
    You are an expert research assistant. Answer the query using only the provided context.
    Cite every fact with its source label. If the context lacks sufficient information, say so explicitly.

    Formatting rules:
    - Use $...$ for inline math expressions (e.g. $\\sqrt{{d_k}}$).
    - Use $$...$$ on its own line for display/block equations (e.g. standalone formulas).
    - Never use plain text or code blocks for mathematical notation.

    context: {context}
    question: {question}
        """).strip()
    )

    rag_chain = (
        {"context": RunnableLambda(lambda _: format_docs(docs)), "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )
    return rag_chain
