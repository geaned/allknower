import argparse
import logging
import os
import time
from contextlib import asynccontextmanager

import torch
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from pydantic import BaseModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the model with the specified device at startup
    if (
        "BLENDER_SCORING_SERVICE_DEVICE" in os.environ
        or "BLENDER_MODEL_PATH" not in os.environ
    ):
        load_dotenv()
    device = torch.device(os.environ.get("BLENDER_SCORING_SERVICE_DEVICE", "cuda:0"))
    model = torch.jit.load(os.environ["BLENDER_MODEL_PATH"], map_location=device)
    model.eval()
    app.state.model = model
    yield


logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.ERROR)

app = FastAPI(lifespan=lifespan)


class RequestSchema(BaseModel):
    query_embedding: list[float]
    doc_embeddings: list[list[float]]
    is_text: bool


class ResponseSchema(BaseModel):
    scores: list[float]
    latency: float


@app.post("/score")
async def score(scoring_request: RequestSchema, request: Request) -> ResponseSchema:
    start_time = time.perf_counter()

    if not scoring_request.doc_embeddings:
        latency = time.perf_counter() - start_time
        return ResponseSchema.model_validate({"scores": [], "latency": latency})

    with torch.no_grad():
        device = os.environ.get("BLENDER_SCORING_SERVICE_DEVICE", "cuda:0")

        query_embedding = torch.as_tensor(scoring_request.query_embedding).to(device)
        doc_embeddings = torch.as_tensor(scoring_request.doc_embeddings).to(device)

        query_embeddings = query_embedding.unsqueeze(0).expand(len(doc_embeddings), -1)

        if scoring_request.is_text:
            outputs = request.app.state.model(
                query_embeddings, text_embs=doc_embeddings
            )
            scores = outputs["text_scores"].cpu().tolist()
        else:
            outputs = request.app.state.model(
                query_embeddings, image_embs=doc_embeddings
            )
            scores = outputs["image_scores"].cpu().tolist()

    latency = time.perf_counter() - start_time
    return ResponseSchema.model_validate({"scores": scores, "latency": latency})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FastAPI service for scoring documents vs queries "
        "using the blender model."
    )
    parser.add_argument(
        "--port", type=int, default=8767, help="The port to run the FastAPI service on."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of independent service instances to be started.",
    )
    args = parser.parse_args()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=args.port,
        workers=args.workers,
        log_config="log_conf.yaml",
    )
