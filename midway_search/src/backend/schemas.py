from pydantic import BaseModel


class BaseSearchDocument(BaseModel):
    text: str
    bm25_score: float
    proximity_score: float = 0
    additional_features: dict | None = (
        None  # Placeholder for additional features, unused for now
    )


class MidwaySearchDocument(BaseModel):
    text: str


class MidwaySearchRequest(BaseModel):
    query: str
    top_n: int = 10


class MidwaySearchResponse(BaseModel):
    documents: list[MidwaySearchDocument]


class ErrorResponse(BaseModel):
    detail: str
