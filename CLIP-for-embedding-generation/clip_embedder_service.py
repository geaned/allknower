import argparse
import base64
import io
import logging
import os
from contextlib import asynccontextmanager
from typing import List

import torch
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from PIL import Image, ImageFile
from transformers import CLIPModel, CLIPProcessor

CLIP_REPO_ID = "openai/clip-vit-base-patch32"
ImageFile.LOAD_TRUNCATED_IMAGES = True


class ClipWithPreprocessingModel(torch.nn.Module):
    def __init__(self):
        super().__init__()

        self.clip_model = CLIPModel.from_pretrained(
            CLIP_REPO_ID,
            device_map=os.environ.get("CLIP_SERVICE_DEVICE", "cuda:0"),
            torch_dtype=torch.bfloat16,
        )
        self.clip_processor = CLIPProcessor.from_pretrained(CLIP_REPO_ID)

    def embed_images(self, x: List[Image.Image]) -> torch.FloatTensor:
        inputs = self.clip_processor(images=x, return_tensors="pt").to(
            self.clip_model.device
        )
        image_embeddings = self.clip_model.get_image_features(**inputs)
        return image_embeddings

    def embed_texts(self, x: List[str]) -> torch.FloatTensor:
        inputs = self.clip_processor(
            text=x, return_tensors="pt", padding=True, truncation=True, max_length=75
        ).to(self.clip_model.device)
        text_embeddings = self.clip_model.get_text_features(**inputs)
        return text_embeddings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the model with the specified device at startup
    model = ClipWithPreprocessingModel()
    model.eval()
    app.state.model = model
    yield


logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.ERROR)

app = FastAPI(lifespan=lifespan)


@app.post("/embed/images/paths")
async def embed_images(image_paths: List[str], request: Request):
    images = []
    for image_path in image_paths:
        try:
            images.append(Image.open(image_path))
        except Exception as e:
            logger.error(f"Error opening image at path {image_path}")
            raise e
    if not images:
        return JSONResponse({"embeddings": []})
    with torch.no_grad():
        embeddings = request.app.state.model.embed_images(images).float().cpu().numpy()
    return JSONResponse({"embeddings": embeddings.tolist()})


@app.post("/embed/images/base64")
async def embed_images_base64(image_base64s: List[str], request: Request):
    images = []
    for image_base64 in image_base64s:
        try:
            image_base64_no_prefix = image_base64
            if image_base64.startswith("data:"):
                image_base64_no_prefix = image_base64.split(",")[1]
            image_data = base64.b64decode(image_base64_no_prefix)
            image = Image.open(io.BytesIO(image_data))
            images.append(image)
        except Exception as e:
            logger.error("Error opening image from base64")
            raise e
    if not images:
        return JSONResponse({"embeddings": []})
    with torch.no_grad():
        embeddings = request.app.state.model.embed_images(images).float().cpu().numpy()
    return JSONResponse({"embeddings": embeddings.tolist()})


@app.post("/embed/texts")
async def embed_texts(texts: List[str], request: Request):
    if not texts:
        return JSONResponse({"embeddings": []})
    with torch.no_grad():
        embeddings = request.app.state.model.embed_texts(texts).float().cpu().numpy()
    return JSONResponse({"embeddings": embeddings.tolist()})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FastAPI service for CLIP embeddings generation."
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="The port to run the FastAPI service on."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of independent service instances to be started.",
    )
    args = parser.parse_args()

    uvicorn.run(
        "clip_embedder_service:app",
        host="0.0.0.0",
        port=args.port,
        workers=args.workers,
    )
