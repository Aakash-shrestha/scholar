from datetime import datetime

from pydantic import BaseModel, Field

from scholar.evaluation.schema import QuestionType


# ingest
class IngestPaperRequest(BaseModel):
    arxiv_id: str = Field(description="The arXiv ID of the paper to ingest")


class PaperResponse(BaseModel):
    arxiv_id: str = Field(description="The arXiv ID of the ingested paper")
    title: str = Field(description="The title of the ingested paper")
    short_citation: str = Field(description="The short citation of the ingested paper")
    abstract: str = Field(description="The abstract of the ingested paper")
    year: int = Field(description="The year the paper was published")
    ingested_at: datetime = Field(
        ..., description="The date the paper was ingested into the database"
    )


# for ingesting reference paper
class IngestRefPaperRequest(BaseModel):
    limit: int = Field(
        2,
        description="The maximum number of reference papers to ingest for the given paper",
        ge=1,
        le=10,
    )


class IngestRefPaperResponse(BaseModel):
    ingest: list[str] = Field(description="List of arXiv IDs of the ingested reference papers")
    skipped: list[str] = Field(
        description="""List of arXiv IDs of the reference papers that were
    skipped because they were already ingested or not found"""
    )
    total_found: int = Field(
        description="Total number of reference papers found for the given paper"
    )


class GraphNodeSchema(BaseModel):
    id: str
    title: str
    year: int
    short_citation: str


class GraphEdgeSchema(BaseModel):
    source: str
    target: str


class GraphSchema(BaseModel):
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]


# for asking questions
class HistoryItem(BaseModel):
    question: str
    answer: str


class AskRequest(BaseModel):
    question: str = Field(description="The question to ask about the paper")
    paper_ids: list[str] | None = None
    history: list[HistoryItem] = []


class AskResponse(BaseModel):
    answer: str = Field(description="The answer to the question about the paper")
    question: str = Field(description="The question that was asked")
    retrieved_arxiv_ids: list[str] = Field(
        description="List of arXiv IDs of the papers that were retrieved to answer the question"
    )
    question_type: QuestionType = Field(description="The type of the question that was asked")
    latency: int = Field(description="The latency in milliseconds to answer the question")


class ReferenceItem(BaseModel):
    title: str = Field(description="The title of the reference paper")
    arxiv_id: str = Field(description="The arXiv ID of the reference paper")
    is_ingested: bool = Field(
        description="Whether the reference paper is already ingested in the database"
    )
