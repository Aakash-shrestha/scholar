from textwrap import dedent

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.runnables.passthrough import RunnablePassthrough


def build_rag_chain(retriever, model) -> Runnable:
    """Return a Runnable that takes a question string and returns an answer string."""
    prompt = ChatPromptTemplate.from_template(
        dedent("""
    You are an expert research assistant. You need to answer the query based on the given context
    only. Also, cite the page number when it is relevant and important to do so.
    context: {context}
    question: {question}
        """)
    )
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
    )
    return rag_chain
