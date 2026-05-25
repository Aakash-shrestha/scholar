"""Central configuration for Scholar.

Loads environment variables from .env and provides typed access to settings.
Importing this module is the canonical way to ensure env vars are loaded
before any LangChain code runs.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env before any other imports that might need env vars
load_dotenv()


class Settings(BaseSettings):
    """Application settings, populated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google AI Studio (Gemini) — primary LLM + embeddings
    google_api_key: str = Field(..., alias="GOOGLE_API_KEY")  # elipses mean reauired

    # Groq — optional, for fast Llama inference
    groq_api_key: str | None = Field(
        default=None, alias="GROQ_API_KEY"
    )  # groq api key many not always be available, so it can have none as default, no error thrown

    # LangSmith
    langsmith_tracing: bool = Field(default=True, alias="LANGSMITH_TRACING")
    langsmith_api_key: str | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="scholar-dev", alias="LANGSMITH_PROJECT")

    chat_model: str = "llama-3.1-8b-instant"
    chat_model_pro: str = "llama-3.3-70b-versatile"

    embedding_model: str = "models/text-embedding-004"
    embedding_dimensions: int = 768

    # Paths
    data_dir: Path = Field(default=Path("./data"), alias="SCHOLAR_DATA_DIR")

    @property
    def papers_dir(self) -> Path:
        return self.data_dir / "papers"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"


settings = Settings()  # type: ignore[call-arg]

# Ensure data directories exist
settings.papers_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_dir.mkdir(parents=True, exist_ok=True)
