import json
import logging
import sys
from random import shuffle
from typing import Any, Dict, Optional

import requests
import streamlit as st

ALLKNOWER_ENDPOINT = "http://158.160.39.15:7866/search"
DEBUG = False


class Renderer:
    @staticmethod
    def render(doc: Dict[str, Any], score: Optional[float]) -> None:
        if doc["is_text"]:
            Renderer.render_text(doc, score)
        else:
            Renderer.render_image(doc, score)

    @staticmethod
    def render_text(doc: Dict[str, Any], score: Optional[float]) -> None:
        st.caption(
            f"[{doc["title"]}]({doc["page_url"]}) - ID {doc["doc_id"]}"
            f" (score: {score:.5f})"
            if score is not None
            else ""
        )
        st.write(doc["content"])

    @staticmethod
    def render_image(doc: Dict[str, Any], score: Optional[float]) -> None:
        image_url = (
            f"http://commons.wikimedia.org/wiki/Special:FilePath/"
            f"{doc["metadata_title"].replace(" ", "_")}"
        )
        st.caption(
            f"[{doc["title"]}]({doc["page_url"]}) - ID {doc["doc_id"]}"
            f" (score: {score:.5f})"
            if score is not None
            else ""
        )
        st.markdown(f"![{doc["title"]}]({image_url})")
        st.write(f"{".".join(doc["metadata_title"].split(".")[:-1]).replace("_", " ")}")
        st.caption(doc["metadata_description"])


def epic_fail(msg: str) -> bool:
    st.markdown("**Oops! Something went wrong...**")
    st.write(msg)
    st.markdown("![Epic Fail](https://i.imgur.com/gqzhrUg.png)")
    return True


def main() -> None:  # noqa: PLR0912, PLR0915
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    st.set_page_config(page_title="Allknower", page_icon=":brain:", layout="wide")
    st.title("Allknower")

    query = st.text_area("Query", key="query_input")

    if st.button("Ask") and query:
        fail = False

        if DEBUG:
            with open("./mock_text.json") as mock_text:
                text_data = json.load(mock_text)
                full_text_search_docs = text_data
                full_text_search_scores = []
                full_text_search_latency = None
                vector_search_text_docs = text_data
                vector_search_text_scores = []
                vector_search_text_latency = None

            with open("./mock_image.json") as mock_image:
                vector_search_image_docs = json.load(mock_image)
                vector_search_image_scores = []
                vector_search_image_latency = None

            midway_latency = None
            blender_latency = None
            e2e_latency = None

            all_docs = (vector_search_text_docs + vector_search_image_docs).copy()
            shuffle(all_docs)
            blender_docs = all_docs[:3]
            blender_scores = []

        else:
            try:
                resp = requests.post(
                    ALLKNOWER_ENDPOINT, json={"query": query}, timeout=60
                )

                match resp.status_code:
                    case 200:
                        contents = json.loads(resp.content)
                        full_text_search_docs = contents["full_text_search_docs"]
                        full_text_search_scores = contents["full_text_search_scores"]
                        full_text_search_latency = contents["metrics"][
                            "fulltext_search_latency"
                        ]
                        vector_search_text_docs = contents["vector_search_text_docs"]
                        vector_search_text_scores = contents[
                            "vector_search_text_scores"
                        ]
                        vector_search_text_latency = contents["metrics"][
                            "vector_search_text_latency"
                        ]
                        vector_search_image_docs = contents["vector_search_image_docs"]
                        vector_search_image_scores = contents[
                            "vector_search_image_scores"
                        ]
                        vector_search_image_latency = contents["metrics"][
                            "vector_search_image_latency"
                        ]
                        blender_docs = contents["blender_docs"]
                        blender_scores = contents["blender_scores"]
                        midway_latency = contents["metrics"]["midway_latency"]
                        blender_latency = contents["metrics"]["blender_latency"]
                        e2e_latency = contents["metrics"]["e2e_latency"]

                    case _:
                        logging.error(
                            f"Unexpected return code {resp.status_code}: "
                            f"{resp.content.decode("utf-8")}"
                        )
                        fail = epic_fail(
                            f"[{resp.status_code}] {resp.content.decode("utf-8")}"
                        )

            except Exception as e:  # noqa: BLE001
                logging.error(f"Unexpected Allknower error: {str(e)}")
                fail = epic_fail(str(e))

        if len(full_text_search_docs) != len(full_text_search_scores):
            full_text_search_scores = [None] * len(full_text_search_docs)

        if len(vector_search_text_docs) != len(vector_search_text_scores):
            vector_search_text_scores = [None] * len(vector_search_text_docs)

        if len(vector_search_image_docs) != len(vector_search_image_scores):
            vector_search_image_scores = [None] * len(vector_search_image_docs)

        if len(blender_docs) != len(blender_scores):
            blender_scores = [None] * len(blender_docs)

        if e2e_latency is not None:
            st.markdown(f"It took Allknower **{e2e_latency:.2f}ms** in total to answer")

        if not fail:
            cols = st.columns(4, gap="medium")

            with cols[0]:
                st.subheader("Full-text Search Docs")
                if full_text_search_latency is not None:
                    st.caption(
                        f"Full-text search took {full_text_search_latency:.2f}ms, "
                        f"midway took {midway_latency:.2f}ms"
                    )
                for item, score in zip(
                    full_text_search_docs, full_text_search_scores, strict=False
                ):
                    Renderer.render_text(item, score)

            with cols[1]:
                st.subheader("Vector Search Text Docs")
                if vector_search_text_latency is not None:
                    st.caption(
                        f"Text vector search took {vector_search_text_latency:.2f}ms"
                    )
                for item, score in zip(
                    vector_search_text_docs, vector_search_text_scores, strict=False
                ):
                    Renderer.render_text(item, score)

            with cols[2]:
                st.subheader("Vector Search Image Docs")
                if vector_search_image_latency is not None:
                    st.caption(
                        f"Image vector search took {vector_search_image_latency:.2f}ms"
                    )
                for item, score in zip(
                    vector_search_image_docs, vector_search_image_scores, strict=False
                ):
                    Renderer.render_image(item, score)

            with cols[3]:
                st.subheader("Blended Results")
                if blender_latency is not None:
                    st.caption(f"Blender service took {blender_latency:.2f}ms")
                for item, score in zip(blender_docs, blender_scores, strict=False):
                    Renderer.render(item, score)


if __name__ == "__main__":
    main()
