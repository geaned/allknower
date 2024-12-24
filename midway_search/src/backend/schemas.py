from typing import Any

from pydantic import BaseModel


class ContentItem(BaseModel):
    content_id: str
    content: str


class Image(BaseModel):
    crc64: str
    image: str
    metadata: dict[str, Any]


class BaseSearchDocument(BaseModel):
    doc_id: str
    page_url: str
    title: str
    contents: list[ContentItem]
    images: list[Image]
    references: list[str]
    categories: list[str]
    redirect: bool
    features: list[int | float]


class MidwaySearchDocument(BaseModel):
    doc_id: str
    page_url: str
    title: str
    contents: list[ContentItem]
    images: list[Image]
    references: list[str]
    categories: list[str]
    redirect: bool


class MidwaySearchRequest(BaseModel):
    query: str
    top_n: int = 10


class MidwaySearchResponse(BaseModel):
    documents: list[MidwaySearchDocument]


class ErrorResponse(BaseModel):
    detail: str
