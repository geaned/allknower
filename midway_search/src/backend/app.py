import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
import requests
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from common.log import setup_logging
from common.log.handler import StreamJsonHandler

from src.backend.enums import VectorSearchType
from src.backend.exceptions import NoDocumentsFoundError, RankingError
from src.backend.metrics import error_count
from src.backend.middlewares import LatencyMiddleware
from src.backend.schemas import (
    BaseSearchDocument,
    BaseSearchResponse,
    ErrorResponse,
    MidwaySearchDocument,
    MidwaySearchRequest,
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


async def get_vector_search_documents(
    query: str,
    request_id: str,
    client: httpx.AsyncClient,
    search_type: str,
    default_latency_value: float = 0,
) -> BaseSearchResponse:
    with logger.contextualize(search_type=search_type):
        logger.info("Getting query embedding from QueryEmbedder")
        query_embedder_response = await client.post(
            os.environ[f"MIDWAY_SEARCH_BACKEND__QUERY_EMBEDDER__{search_type.upper()}_ENDPOINT"],
            json=[query],
            headers={"x-request-id": request_id},
            # timeout=20,
        )

        if query_embedder_response.status_code == httpx.codes.ok:
            logger.info("Successfully got query embedding from QueryEmbedder")
            logger.info("Getting documents from VectorSearch")
            vector_search_response = await client.post(
                os.environ[f"MIDWAY_SEARCH_BACKEND__BASESEARCH__VECTOR_SEARCH_ENDPOINT"],
                json={
                    "embedding": query_embedder_response.json()["embeddings"][0],
                    "is_text": search_type == "text",
                },
                headers={"x-request-id": request_id},
                # timeout=20,
            )

            if vector_search_response.status_code == httpx.codes.ok:
                logger.info("Successfully got documents from VectorSearch")
                return BaseSearchResponse.model_validate(vector_search_response.json())

            logger.warning("Failed to get documents from VectorSearch")
            try:
                latency = vector_search_response.json()["latency"]
            except:
                latency = default_latency_value

            return BaseSearchResponse.model_validate({"documents": [], "latency": latency})
        
        logger.warning("Failed to get query embedding from QueryEmbedder")
        return BaseSearchResponse.model_validate({"documents": [], "latency": default_latency_value})


def get_blender_scores(
    query_embedding: list[float], 
) -> :


@app.post("/rank", response_model=list[MidwaySearchDocument])
async def search(request: MidwaySearchRequest) -> list[MidwaySearchDocument]:
    with logger.contextualize(request=request.model_dump(mode="json")):
        request_json = request.model_dump(mode="json")
        query = request_json["query"]
        request_id = request_json["request_id"]
        # skip_blending = False

        logger.info("Got rank request")

        async with httpx.AsyncClient() as client:
            try:
                logger.info("Getting text documents from full-text search")
                full_text_search_docs_request = client.post(
                    os.path.join(
                        os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH__BASE_URL"],
                        os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH__FULL_TEXT_SEARCH_ENDPOINT"],
                    ),
                    json={"query": query},
                    headers={"x-request-id": request_id},
                    # timeout=20,
                )

                vector_search_text_docs_request = get_vector_search_documents(
                    query,
                    request_id,
                    client,
                    VectorSearchType.text.value,
                )

                vector_search_image_docs_request = get_vector_search_documents(
                    query,
                    request_id,
                    client,
                    VectorSearchType.image.value,
                )

                logger.bind(search_type=VectorSearchType.text.value).info("Getting query embedding from QueryEmbedder")
                query_embedder_request = client.post(
                    os.environ[f"MIDWAY_SEARCH_BACKEND__QUERY_EMBEDDER__{VectorSearchType.text.value.upper()}_ENDPOINT"],
                    json=[query],
                    headers={"x-request-id": request_id},
                    # timeout=20,
                )

                (
                    full_text_docs_response, 
                    vector_search_text_docs_response, 
                    vector_search_image_docs_response,
                    query_embedder_request
                ) = await asyncio.gather(
                    full_text_search_docs_request, 
                    vector_search_text_docs_request, 
                    vector_search_image_docs_request,
                    query_embedder_request,
                )

                if query_embedder_request.status_code == httpx.codes.OK:
                    logger.info("Successfully got query embedding from QueryEmbedder")

                else:
                    skip_blending = True


                if full_text_docs_response.status_code == httpx.codes.OK:
                    logger.bind(documents_length=len(docs)).info(
                        "Got documents from full-text search"
                    )
                    logger.info("Ranking documents from full-text search")
                    full_text_docs_ranked = ranker.rank(
                        [
                            BaseSearchDocument(**doc)
                            for doc in full_text_docs_response.json()["documents"]
                        ],
                        top_n=request.top_n,
                    )

                    logger.bind(
                        docs_samples=[
                            doc.contents[0].content[:50] 
                            for doc in full_text_docs_ranked
                        ]
                    ).info("Successfully ranked documents from full-text search")
                else:
                    logger.warning("No documents were received from full-text search")
                    full_text_docs_ranked = []
                
                if 
                vector_search_text_docs_response.raise_for_status()
                vector_search_text_docs = vector_search_text_docs_response.json()

                blender_scored_vector_search_text_docs = client.post(
                    os.environ["MIDWAY_SEARCH_BACKEND__BLENDER_API_ENDPOINT"],
                    json={
                        "documents": scored_text_docs
                    },
                )

                vector_search_image_docs_response.raise_for_status()

                full_text_docs_response.raise_for_status()
                full_text_docs = full_text_docs_response.json()
                
                vector_search_image_docs = vector_search_image_docs_response.json()

                try:
                    logger.info("Ranking documents")
                    docs_ranked = ranker.rank(
                        [BaseSearchDocument(**doc) for doc in docs], top_n=request.top_n
                    )
                except Exception as error:
                    logger.bind(error=error).error("Error occurred during ranking")
                    raise RankingError("Error occurred during ranking") from error



            except:
                ...
        try:
            logger.info("Fetching documents from BaseSearch")
            response = requests.get(
                os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH_ENDPOINT"],
                json=request.model_dump(mode="json"),
                timeout=20,
            )
            response.raise_for_status()
            docs = response.json()

            if len(docs) == 0:
                logger.bind(query=request.query).error(
                    "No documents found by given query"
                )
                raise NoDocumentsFoundError(
                    f"No documents found by given query {request.query}"
                )
        except requests.RequestException as error:
            logger.bind(error=error).error("Error fetching documents from base search")
            raise error
        else:
            logger.bind(documents_length=len(docs)).info(
                "Fetched documents from base search"
            )

        try:
            logger.info("Ranking documents")
            docs_ranked = ranker.rank(
                [BaseSearchDocument(**doc) for doc in docs], top_n=request.top_n
            )
        except Exception as error:
            logger.bind(error=error).error("Error occurred during ranking")
            raise RankingError("Error occurred during ranking") from error

        logger.bind(
            docs_samples=[doc.contents[0].content[:50] for doc in docs_ranked]
        ).info("Successfully documents ranked")

        return docs_ranked


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
