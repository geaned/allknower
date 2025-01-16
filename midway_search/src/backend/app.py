import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
import requests
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from common.log import setup_logging
from common.log.handler import StreamJsonHandler

from src.backend.constants import DEFAULT_LATENCY_VALUE
from src.backend.enums import VectorSearchType
from src.backend.exceptions import NoDocumentsFoundError, RankingError
from src.backend.metrics import error_count
from src.backend.middlewares import LatencyMiddleware
from src.backend.schemas import (
    BaseSearchDocument,
    BaseSearchResponse,
    BlenderResponse,
    DefaultBlenderResponse,
    ErrorResponse,
    MidwaySearchDocument,
    MidwaySearchRequest,
    MidwaySearchResponse,
)
from src.model.ranker import Ranker, RankerConfig


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await logger.complete()


setup_logging(
    extra_handlers=[StreamJsonHandler(stream=sys.stdout, prepend_value_types=False)]
)

app = FastAPI(
    lifespan=lifespan,
    root_path=os.getenv("FASTAPI_ROOT_PATH", ""),
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    },
)
app.add_middleware(LatencyMiddleware)

ranker = Ranker(RankerConfig.from_file("configs/ranker_config.json"))


def get_vector_search_documents(
    query: str,
    request_id: str,
    search_type: str,
    default_latency_value: float = DEFAULT_LATENCY_VALUE,
) -> BaseSearchResponse:
    e2e_latency = time.monotonic()
    with logger.contextualize(search_type=search_type):
        logger.info("Getting query embedding from QueryEmbedder")
        query_embedder_response = requests.post(
            os.environ[f"MIDWAY_SEARCH_BACKEND__QUERYEMBEDDER__{search_type.upper()}_ENDPOINT"],
            json=[query],
            headers={"X-Request-Id": request_id},
            # timeout=20,
        )

        if query_embedder_response.status_code == httpx.codes.ok:
            logger.info("Got query embedding from QueryEmbedder")
            logger.info("Getting documents from VectorSearch")
            vector_search_response = requests.post(
                os.path.join(
                    os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH__BASE_URL"],
                    os.environ[f"MIDWAY_SEARCH_BACKEND__BASESEARCH__VECTOR_SEARCH_ENDPOINT"],
                ),
                json={
                    "embedding": query_embedder_response.json()["embeddings"][0],
                    "isText": search_type == "text",
                },
                headers={"X-Request-Id": request_id},
                # timeout=20,
            )

            if vector_search_response.status_code == httpx.codes.ok:
                logger.info("Got documents from VectorSearch")
                return BaseSearchResponse.model_validate(vector_search_response.json())

            logger.bind(vector_search_response=vector_search_response.content).warning(
                "Failed to get documents from VectorSearch",
            )
            try:
                latency = vector_search_response.json()["latency"]
            except:
                latency = default_latency_value

            return BaseSearchResponse.model_validate({"documents": [], "latency": latency})

        logger.bind(query_embedder_response=query_embedder_response).warning(
            "Failed to get query embedding from QueryEmbedder",
        )
        return BaseSearchResponse.model_validate({"documents": [], "latency": default_latency_value})


def convert_docs(docs: list[BaseSearchDocument]) -> list[MidwaySearchDocument]:
    output = []
    for doc in docs:
        doc_dict = doc
        output.append(
            MidwaySearchDocument.model_validate(
                {
                    "doc_id": doc_dict.docId if hasattr(doc_dict, "docId") else doc_dict["docId"],
                    "page_url": doc_dict.pageUrl if hasattr(doc_dict, "pageUrl") else doc_dict["pageUrl"],
                    "title": doc_dict.title if hasattr(doc_dict, "title") else doc_dict["title"],
                    "is_text": doc_dict.isText if hasattr(doc_dict, "isText") else doc_dict["isText"],
                    "content": doc_dict.content if hasattr(doc_dict, "content") else doc_dict["content"],
                    "metadata_title": doc_dict.metadataTitle if hasattr(doc_dict, "metadataTitle") else doc_dict["metadataTitle"],
                    "metadata_description": doc_dict.metadataDescription if hasattr(doc_dict, "metadataDescription") else doc_dict["metadataDescription"],
                }
            )
        )

    return output

@app.post("/search")
def search(request: MidwaySearchRequest, default_latency_value: float = DEFAULT_LATENCY_VALUE) -> MidwaySearchResponse:
    e2e_latency = time.monotonic()
    with logger.contextualize(request=request.model_dump(mode="json")):
        request_json = request.model_dump(mode="json")
        query = request_json["query"]
        request_id = request_json["request_id"]
        # skip_blending = False

        logger.info("Got rank request")

        try:
            logger.info("Getting text documents from full-text search")
            full_text_search_docs_response = requests.post(
                os.path.join(
                    os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH__BASE_URL"],
                    os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH__FULL_TEXT_SEARCH_ENDPOINT"],
                ),
                json={"query": query},
                headers={"X-Request-Id": request_id},
                # timeout=20,
            )

            midway_latency = time.monotonic()
            if full_text_search_docs_response.status_code == httpx.codes.OK:
                full_text_search_docs = full_text_search_docs_response.json()["documents"]
                logger.bind(documents_length=len(full_text_search_docs)).info(
                    "Got documents from full-text search"
                )
                logger.info("Ranking documents from full-text search")
                full_text_search_docs_ranked, full_text_search_scores = ranker.rank(
                    [
                        BaseSearchDocument(**doc)
                        for doc in full_text_search_docs
                    ],
                    top_n=request.top_n,
                )

                logger.bind(
                    docs_samples=[
                        doc["content"][:50] 
                        for doc in full_text_search_docs_ranked
                    ]
                ).info("Ranked documents from full-text search")
            else:
                logger.bind(full_text_search_docs_response=full_text_search_docs_response).warning("Failed to get documents from full-text search")
                full_text_search_docs_ranked, full_text_search_scores  = [], []
            
            midway_latency = time.monotonic() - midway_latency

            vector_search_text_docs_response = get_vector_search_documents(
                query,
                request_id,
                # client,
                VectorSearchType.text.value,
                default_latency_value=default_latency_value,
            )

            vector_search_image_docs_response = get_vector_search_documents(
                query,
                request_id,
                # client,
                VectorSearchType.image.value,
                default_latency_value=default_latency_value,
            )

            logger.bind(search_type=VectorSearchType.text.value).info("Getting query embedding from QueryEmbedder")
            query_embedder_response = requests.post(
                os.environ[f"MIDWAY_SEARCH_BACKEND__QUERYEMBEDDER__{VectorSearchType.text.value.upper()}_ENDPOINT"],
                json=[query],
                headers={"X-Request-Id": request_id},
                # timeout=20,
            )

            # (
            #     full_text_search_docs_response, 
            #     vector_search_text_docs_response, 
            #     vector_search_image_docs_response,
            #     query_embedder_response
            # ) = await asyncio.gather(
            #     full_text_search_docs_request, 
            #     vector_search_text_docs_request, 
            #     vector_search_image_docs_request,
            #     query_embedder_request,
            # )

            if query_embedder_response.status_code == httpx.codes.OK:
                logger.bind(search_type="text").info("Got query embedding from QueryEmbedder")

                if full_text_search_docs_ranked:
                    logger.info("Getting scored full-text search documents from Blender")
                    full_text_search_docs_blender_response = requests.post(
                        os.environ[f"MIDWAY_SEARCH_BACKEND__BLENDER__ENDPOINT"],
                        json={
                            "query_embedding": query_embedder_response.json()["embeddings"][0],
                            "doc_embeddings": [doc["embedding"] for doc in full_text_search_docs_ranked],
                            "is_text": True,
                        },
                        headers={"X-Request-Id": request_id},
                        # timeout=20,
                    )
                else:
                    logger.warning("Skipping Blender scoring for full-text search documents")
                    # full_text_search_docs_blender_response = BlenderResponse.model_validate(
                    #     {"scores": [], "latency": default_latency_value},
                    # )
                    full_text_search_docs_blender_response = DefaultBlenderResponse()

                if vector_search_text_docs_response.documents:
                    logger.info("Getting scored VectorSearch text documents from Blender")
                    vector_search_text_docs_blender_response = requests.post(
                        os.environ[f"MIDWAY_SEARCH_BACKEND__BLENDER__ENDPOINT"],
                        json={
                            "query_embedding": query_embedder_response.json()["embeddings"][0],
                            "doc_embeddings": [doc.embedding for doc in vector_search_text_docs_response.documents],
                            "is_text": True,
                        },
                        headers={"X-Request-Id": request_id},
                        # timeout=20,
                    )
                else:
                    logger.warning("Skipping Blender scoring for VectorSearch text documents")
                    vector_search_text_docs_blender_response = DefaultBlenderResponse()
                
                if vector_search_image_docs_response.documents:
                    logger.info("Getting scored VectorSearch image documents from Blender")
                    vector_search_image_docs_blender_response = requests.post(
                        os.environ[f"MIDWAY_SEARCH_BACKEND__BLENDER__ENDPOINT"],
                        json={
                            "query_embedding": query_embedder_response.json()["embeddings"][0],
                            "doc_embeddings": [doc.embedding for doc in vector_search_image_docs_response.documents],
                            "is_text": False,
                        },
                        headers={"X-Request-Id": request_id},
                        # timeout=20,
                    )
                else:
                    logger.warning("Skipping Blender scoring for VectorSearch image documents")
                    vector_search_image_docs_blender_response = DefaultBlenderResponse()
                
                # (
                #     full_text_search_docs_blender_response,
                #     vector_search_text_docs_blender_response,
                #     vector_search_image_docs_blender_response,
                # ) = await asyncio.gather(
                #     full_text_search_docs_blender_response,
                #     vector_search_text_docs_blender_response,
                #     vector_search_image_docs_blender_response,
                # )

                blender_docs_scores = \
                list(
                    zip(full_text_search_docs_ranked, full_text_search_docs_blender_response.json()["scores"]),
                ) + \
                list(
                    zip(vector_search_text_docs_response.documents, vector_search_text_docs_blender_response.json()["scores"]),
                ) + \
                list(
                    zip(vector_search_image_docs_response.documents, vector_search_image_docs_blender_response.json()["scores"]),
                )

                blender_docs_scores.sort(key=lambda x: x[1], reverse=True)
            else:
                logger.warning("Skipping Blender scoring for all documents")
                blender_docs_scores = []

            return MidwaySearchResponse.model_validate(
                {
                    "full_text_search_docs": convert_docs(full_text_search_docs_ranked),
                    "vector_search_text_docs": convert_docs(vector_search_text_docs_response.documents),
                    "vector_search_image_docs": convert_docs(vector_search_image_docs_response.documents),
                    "blender_docs": convert_docs([doc for doc, _ in blender_docs_scores]),
                    "full_text_search_scores": full_text_search_scores,
                    "vector_search_text_scores": [doc["features"][0] for doc in vector_search_text_docs_response.model_dump()["documents"]],
                    "vector_search_image_scores": [doc["features"][0] for doc in vector_search_image_docs_response.model_dump()["documents"]],
                    "blender_scores": [score for _, score in blender_docs_scores],
                    "metrics": {
                        "fulltext_search_latency": full_text_search_docs_response.json()["latency"],
                        "vector_search_text_latency": vector_search_text_docs_response.model_dump()["latency"],
                        "vector_search_image_latency": vector_search_image_docs_response.model_dump()["latency"],
                        "midway_latency": midway_latency * 1000,
                        "blender_latency": (full_text_search_docs_blender_response.json()["latency"] + vector_search_text_docs_blender_response.json()["latency"] + vector_search_image_docs_blender_response.json()["latency"]) * 1000,
                        "e2e_latency": (time.monotonic() - e2e_latency) * 1000,
                    }
                }
            )
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            return MidwaySearchResponse()


@app.exception_handler(requests.RequestException)
def requests_exception_handler(
    _request: Request, exc: requests.RequestException
) -> JSONResponse:
    return JSONResponse(
        content={"detail": str(exc)}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE
    )


@app.exception_handler(NoDocumentsFoundError)
def no_documents_found_errors_handler(
    _request: Request, exc: NoDocumentsFoundError
) -> JSONResponse:
    return JSONResponse(content={"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
def exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.bind(error=exc).error("An unknown error occurred while ranking documents")
    error_count.labels(
        os.environ["MIDWAY_SEARCH_BACKEND__PROMETHEUS__APP_NAME"], "/rank"
    ).inc()
    return JSONResponse(
        content={"detail": str(exc), "type": type(exc).__name__},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
