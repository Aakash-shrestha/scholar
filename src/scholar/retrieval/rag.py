from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from langchain_core.runnables.passthrough import RunnablePassthrough


def build_rag_chain(retriever, model) -> Runnable:
    """Return a Runnable that takes a question string and returns an answer string."""
    rag_chain = {"context": retriever, "question": RunnablePassthrough} | model | StrOutputParser()
    return rag_chain
