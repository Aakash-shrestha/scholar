from typing import Sequence

from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever


def get_reranked_retriever(
    base_retriever: BaseRetriever, top_n: int
) -> ContextualCompressionRetriever:
    """
    Build a reranking retriever that uses a cross-encoder to rerank retrieved documents.
    """
    model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
    compressor = CrossEncoderReranker(model=model, top_n=top_n)

    reranking_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=base_retriever
    )
    return reranking_retriever


def rerank_documents(
    docs: list[Document], query: str, top_n: int, cross_encoder: HuggingFaceCrossEncoder
) -> list[Document]:
    """
    Rerank the retrieved documents based on their relevance to the query using a cross-encoder
    model.
    """
    compressor = CrossEncoderReranker(model=cross_encoder, top_n=top_n)
    return list(compressor.compress_documents(query=query, documents=docs))
