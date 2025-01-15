import argparse
import concurrent.futures
import os
import random
from typing import List

import pandas as pd
import requests
from dotenv import load_dotenv
from more_itertools import chunked
from tqdm import tqdm

load_dotenv()
CLIP_EMBEDDING_SERVICE_URL = os.environ["CLIP_EMBEDDING_SERVICE_URL"]
TEXT_ENCODER_EMBEDDING_SERVICE_URL = os.environ["TEXT_ENCODER_EMBEDDING_SERVICE_URL"]


def prepare_data(metadata_path: str, duplication_factor: int) -> pd.DataFrame:
    base_path = os.path.dirname(metadata_path)

    df = pd.read_csv(metadata_path)  # cols: ['query', 'image', 'image_title', 'text']

    # filter out rows with non-existent images
    df = df[df["image"].apply(lambda x: os.path.exists(os.path.join(base_path, x)))]
    df.reset_index(drop=True, inplace=True)

    # replace paths to absolute
    df["image"] = df["image"].apply(
        lambda x: os.path.abspath(os.path.join(base_path, x))
    )

    data = [
        {"query": row["query"], "image": row["image"], "text": row["text"]}
        for _, row in df.iterrows()
    ]

    # generate embeddings for the data
    def generate_embeddings(data_chunk: List[dict]) -> List[dict]:
        # generate query embeddings
        queries = [triplet_data["query"] for triplet_data in data_chunk]
        response = requests.post(
            f"{TEXT_ENCODER_EMBEDDING_SERVICE_URL}/embed/texts",
            json=queries,
            timeout=60,
        )
        query_embeddings = response.json()["embeddings"]

        # generate image embeddings
        image_paths = [triplet_data["image"] for triplet_data in data_chunk]
        response = requests.post(
            f"{CLIP_EMBEDDING_SERVICE_URL}/embed/images/paths",
            json=image_paths,
            timeout=60,
        )
        image_embeddings = response.json()["embeddings"]

        # generate text embeddings
        texts = [triplet_data["text"] for triplet_data in data_chunk]
        response = requests.post(
            f"{TEXT_ENCODER_EMBEDDING_SERVICE_URL}/embed/texts", json=texts, timeout=60
        )
        text_embeddings = response.json()["embeddings"]

        for data_row, query_embedding, image_embedding, text_embedding in zip(
            data_chunk,
            query_embeddings,
            image_embeddings,
            text_embeddings,
            strict=False,
        ):
            data_row["query_embedding"] = query_embedding
            data_row["image_embedding"] = image_embedding
            data_row["text_embedding"] = text_embedding

        return data_chunk

    chunk_size = 1
    data_with_embeddings = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(generate_embeddings, data_chunk)
            for data_chunk in chunked(data, chunk_size)
        ]
        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=(len(data) - 1) // chunk_size + 1,
            desc="Generating embeddings",
        ):
            result = future.result()
            data_with_embeddings.extend(result)

    df = pd.DataFrame(data_with_embeddings)

    triplets_data = []
    for index, row in tqdm(
        df.iterrows(), total=len(df), desc="Generating negative samples"
    ):
        all_rows_minus_this = list(range(len(df)))
        all_rows_minus_this.pop(index)

        # case where image is a positive example
        negative_text_indices = random.sample(all_rows_minus_this, duplication_factor)

        negative_texts = df.loc[negative_text_indices, "text"]
        negative_text_embeddings = df.loc[negative_text_indices, "text_embedding"]

        for negative_text, negative_text_embedding in zip(
            negative_texts, negative_text_embeddings, strict=False
        ):
            triplets_data.append(
                {
                    "query": row["query"],
                    "query_embedding": row["query_embedding"],
                    "text": negative_text,
                    "text_embedding": negative_text_embedding,
                    "image": row["image"],
                    "image_embedding": row["image_embedding"],
                    "label": "image",
                }
            )

        # case where text is a positive example
        negative_image_indices = random.sample(all_rows_minus_this, duplication_factor)

        negative_images = df.loc[negative_image_indices, "image"]
        negative_image_embeddings = df.loc[negative_image_indices, "image_embedding"]

        for negative_image, negative_image_embedding in zip(
            negative_images, negative_image_embeddings, strict=False
        ):
            triplets_data.append(
                {
                    "query": row["query"],
                    "query_embedding": row["query_embedding"],
                    "text": row["text"],
                    "text_embedding": row["text_embedding"],
                    "image": negative_image,
                    "image_embedding": negative_image_embedding,
                    "label": "text",
                }
            )

    triplets_df = pd.DataFrame(triplets_data)
    return triplets_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script for transforming Wiki IR data into triplet format."
    )
    parser.add_argument(
        "data_path",
        type=str,
        help="Path to the csv file with metadata for Wiki IR data.",
    )
    parser.add_argument(
        "--duplicate",
        "-d",
        type=int,
        default=5,
        help="The number of negative samples for each (query, positive_sample) pair",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="wiki_ir_processed.csv",
        help="The path to which the final dataframe with metadata will be written.",
    )
    args = parser.parse_args()

    wiki_ir_dataset = prepare_data(args.data_path, args.duplicate)

    wiki_ir_dataset.to_csv(args.output, index=False)
