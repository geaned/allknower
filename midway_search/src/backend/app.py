import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

import requests
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from common.log import setup_logging
from common.log.handler import StreamJsonHandler

from src.backend.exceptions import NoDocumentsFoundError, RankingError
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
    extra_handlers=[StreamJsonHandler(stream=sys.stdout, prepend_value_types=True)]
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

ranker = Ranker(RankerConfig.from_file("configs/ranker_config.json"))


@app.post("/rank", response_model=list[MidwaySearchDocument])
def rerank_documents(request: MidwaySearchRequest) -> list[MidwaySearchDocument]:
    with logger.contextualize(request=request.model_dump(mode="json")):
        logger.info("Got rank request")

        try:
            logger.info("Fetching documents from BaseSearch")
            response = requests.post(
                os.environ["MIDWAY_SEARCH_BACKEND__BASESEARCH_ENDPOINT"],
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            docs = response.json()

            if len(docs) == 0:
                raise NoDocumentsFoundError(
                    f"No documents found by given query {request.query}"
                )
        except requests.RequestException as error:
            logger.bind(error=error).error("Error fetching documents from base search")
            raise HTTPException(
                status_code=500, detail="Failed to fetch documents from base search"
            ) from error
        else:
            logger.bind(documents_length=len(docs)).info(
                "Fetched documents from base search"
            )

        try:
            logger.info("Ranking documents")
            docs_ranked = ranker.rank(
                request.query, list(map(lambda doc: BaseSearchDocument(**doc), docs))
            )
        except Exception as error:
            logger.bind(error=error).error("Error occurred during ranking")
            raise RankingError("Error occurred during ranking") from error

        logger.bind(docs_samples=[doc.text[:50] for doc in docs_ranked]).info(
            "Successfully documents ranked"
        )

        return docs_ranked


@app.exception_handler(Exception)
def exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.bind(error=exc).error("An unknown error occurred while ranking documents")
    return JSONResponse(
        content={"detail": str(exc), "type": type(exc).__name__},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
