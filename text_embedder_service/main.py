import argparse
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import List

import numpy as np
import torch
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer

TEXT_EMBEDDER_REPO_ID = "HIT-TMG/KaLM-embedding-multilingual-mini-instruct-v1.5"


class TextEmbedderModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        if "TEXT_EMBEDDER_SERVICE_DEVICE" not in os.environ:
            load_dotenv()
        self.te_model = SentenceTransformer(
            TEXT_EMBEDDER_REPO_ID,
            device=os.environ.get("TEXT_EMBEDDER_SERVICE_DEVICE", "cuda:0"),
        )
        self.te_model.max_seq_length = 512

    def embed_texts(self, x: List[str]) -> np.ndarray:
        text_embeddings = self.te_model.encode(
            x, normalize_embeddings=True, batch_size=256, show_progress_bar=False
        )
        return text_embeddings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the model with the specified device at startup
    model = TextEmbedderModel()
    model.eval()
    app.state.model = model
    yield


logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.ERROR)

app = FastAPI(lifespan=lifespan)


@app.post("/embed/texts")
async def embed_texts(texts: List[str], request: Request):
    start_time = time.perf_counter()
    if not texts:
        latency = time.perf_counter() - start_time
        return JSONResponse({"embeddings": [], "latency": latency})
    with torch.no_grad():
        embeddings = request.app.state.model.embed_texts(texts)
    latency = time.perf_counter() - start_time
    return JSONResponse({"embeddings": embeddings.tolist(), "latency": latency})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FastAPI service for text embeddings generation."
    )
    parser.add_argument(
        "--port", type=int, default=8766, help="The port to run the FastAPI service on."
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
