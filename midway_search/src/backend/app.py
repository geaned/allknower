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

from src.backend.exceptions import NoDocumentsFoundError, RankingError
from src.backend.metrics import error_count
from src.backend.middlewares import LatencyMiddleware
from src.backend.schemas import (
    BaseSearchDocument,
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


async def get_vector_search_documents(query: str) -> ...:
    logger.info("Fetching query embedding from text embedder")
    text_embedder_request = client.post(
        os.environ["MIDWAY_SEARCH_BACKEND__QUERY_EMBEDDER__TEXT_EMBEDDER_ENDPOINT"],
        json=[request_json["query"]],
    )





@app.post("/rank", response_model=list[MidwaySearchDocument])
async def rerank_documents(request: MidwaySearchRequest) -> list[MidwaySearchDocument]:
    with logger.contextualize(request=request.model_dump(mode="json")):
        request_json = request.model_dump(mode="json")
        skip_blending = False

        logger.info("Got rank request")

        async with httpx.AsyncClient() as client:
            try:
                logger.info("Fetching text documents from full-text BaseSearch")
                full_text_search_docs_request = client.post(
                    os.path.join(
                        os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH__BASE_URL"],
                        os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH__FULL_TEXT_SEARCH_ENDPOINT"],
                    ),
                    json=request_json,
                )

                logger.info("Fetching query embedding from text embedder")
                text_embedder_request = client.post(
                    os.environ["MIDWAY_SEARCH_BACKEND__QUERY_EMBEDDER__TEXT_EMBEDDER_ENDPOINT"],
                    json=[request_json["query"]],
                )

                logger.info("Fetching query embedding from text-image embedder")
                image_embedder_request = client.post(
                    os.environ["MIDWAY_SEARCH_BACKEND__QUERY_EMBEDDER__IMAGE_EMBEDDER_ENDPOINT"],
                    json=[request_json["query"]],
                )

                (
                    full_text_docs_response, 
                    text_embedder_response, 
                    image_embedder_response
                ) = await asyncio.gather(
                    full_text_search_docs_request, 
                    text_embedder_request, 
                    image_embedder_request,
                )

                if text_embedder_response.status_code == httpx.codes.OK and image_embedder_response.status_code  == httpx.codes.OK:
                    logger.info("Fetching text documents from VectorSearch")
                    vector_search_docs_response = await client.post(
                        os.path.join(
                            os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH__BASE_URL"],
                            os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH__VECTOR_SEARCH_ENDPOINT"],
                        ),
                        json={
                            "text_embedding": text_embedder_response.json()["embeddings"][0],
                            "image_embedding": image_embedder_response.json()["embeddings"][0],
                        },
                    )

                    if vector_search_docs_response.status_code == httpx.codes.OK:
                        vector_search_docs = vector_search_docs_response.json()

                        vector_search_text_docs = vector_search_docs["text_docs"]
                        vector_search_image_docs = vector_search_docs["image_docs"]
                        vector_search_metrics = vector_search_docs["metrics"]
                    else:
                        logger.warning("No documents were received from VectorSearch")
                        skip_blending = True
                else:
                    logger.warning("No query embeddings were received from QueryEmbedder")
                    skip_blending = True

                if full_text_docs_response.status_code == httpx.codes.OK:
                    logger.info("Ranking documents from full-text search")
                    full_text_docs_ranked = ranker.rank(
                        [
                            BaseSearchDocument(**doc)
                            for doc in full_text_docs_response.json()
                        ],
                        top_n=request.top_n,
                    )

                    logger.bind(
                        docs_samples=[
                            doc.contents[0].content[:50] 
                            for doc in full_text_docs_ranked
                        ]
                    ).info("Successfully documents ranked")
                else:
                    logger.warning("No documents were received from full-text BaseSearch")
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
