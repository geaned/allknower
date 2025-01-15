from uuid import uuid4

from pydantic import BaseModel, Field


class BaseSearchDocument(BaseModel):
    doc_id: str
    page_url: str
    title: str
    embedding: list[float]
    is_text: bool
    # if is_text = True, two fields below are not None
    content: str | None
    features: list[float] | None
    # if is_text = False, two fields below are not None
    metadata_title: str | None
    metadata_description: str | None


class BaseSearchResponse(BaseModel):
    documents: list[BaseSearchDocument]
    latency: float


class BlenderResponse(BaseModel):
    scores: list[float]
    latency: float


class MidwaySearchDocument(BaseModel):
    doc_id: str
    page_url: str
    title: str
    is_text: bool
    # if is_text = True, field below is not None
    content: str | None
    # if is_text = False, two fields below are not None
    metadata_title: str | None
    metadata_description: str | None


class MidwaySearchRequest(BaseModel):
    query: str
    request_id: str = Field(default_factory=uuid4)
    top_n: int = 10


class MetricsModel(BaseModel):
    fulltext_search_latency: float
    vector_search_text_latency: float
    vector_search_image_latency: float
    midway_latency: float
    blender_latency: float
    e2e_latency: float


class MidwaySearchResponse(BaseModel):
    full_text_search_docs: list[MidwaySearchDocument]
    vector_search_text_docs: list[MidwaySearchDocument]
    vector_search_image_docs: list[MidwaySearchDocument]
    blender_docs: list[MidwaySearchDocument]
    full_text_search_scores: list[float]
    vector_search_text_scores: list[float]
    vector_search_image_scortes: list[float]
    blender_scores: list[float]
    metrics: MetricsModel


class ErrorResponse(BaseModel):
    detail: str
