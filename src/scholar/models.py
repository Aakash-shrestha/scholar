"""Factory functions for building LLM clients.

The whole point of LangChain's standard interfaces is that the rest of the
codebase shouldn't care WHICH provider it's talking to. This module is the
single place where we instantiate models, so swapping providers later is a
one-file change.

This is the practical payoff of LangChain's abstraction layer:
    - In Phase 1, we use Gemini (free)
    - In Phase 6, you might swap to Claude/GPT-4 for production
    - Nothing else in the codebase changes
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from scholar.config import settings


def get_chat_model(
    *,
    pro: bool = False,
    temperature: float = 0.0,
    streaming: bool = False,
) -> BaseChatModel:
    """Build a chat model.

    Args:
        pro: Use the larger, slower Pro model. Reserve for synthesis steps
            where reasoning quality matters more than latency.
        temperature: 0.0 for deterministic factual tasks; ~0.7 for creative.
        streaming: Whether to stream tokens. Off by default for simplicity.
    """
    model_name = settings.chat_model_pro if pro else settings.chat_model
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=settings.google_api_key,
        # disable_streaming inverts the boolean for the SDK
        disable_streaming=not streaming,
    )


def get_embeddings() -> Embeddings:
    """Build the embeddings model.

    We use Gemini's text-embedding-004 (768 dims) — free, fast, and
    quality is mid-pack on academic content. We can swap to something
    better (Voyage AI, Cohere, BGE) in Phase 3 if the eval suite shows
    retrieval is the bottleneck.
    """
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )
