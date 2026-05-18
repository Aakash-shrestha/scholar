from textwrap import dedent

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.runnables.passthrough import RunnablePassthrough


def format_docs(docs: list[Document]) -> str:
    """takes the list of documents from retriever and adds metadata to pagecontent of the chunks"""
    block = []
    for doc in docs:
        citation = doc.metadata.get("short_citation", "unknown")
        page = doc.metadata.get("page", "?")
        block.append(f"[{citation}, p{page + 1}]\n{doc.page_content}")
    return "\n\n--\n\n".join(block)


def build_rag_chain(retriever, model) -> Runnable:
    """Return a Runnable that takes a question string and returns an answer string."""
    prompt = ChatPromptTemplate.from_template(
        dedent("""
    You are an expert research assistant. You need to answer the query based on the given context
    only. Also, when you state the fact, cite the source using that label. If the context
    does not contain enough information, say it explicitly.
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
