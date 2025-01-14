import json
from random import shuffle
import requests
import streamlit as st
from typing import Any, Dict


# TODO: switch to actual endpoint
ALLKNOWER_ENDPOINT = ""
DEBUG = True


class Renderer:
    @staticmethod
    def render(doc: Dict[str, Any]) -> None:
        if doc["is_text"]:
            Renderer.render_text(doc)
        else:
            Renderer.render_image(doc)

    @staticmethod
    def render_text(doc: Dict[str, Any]) -> None:
        st.caption(f"[{doc["title"]}]({doc["page_url"]}) - ID {doc["doc_id"]}")
        st.write(doc["content"])

    @staticmethod
    def render_image(doc: Dict[str, Any]) -> None:
        image_url = (
            f"http://commons.wikimedia.org/wiki/Special:FilePath/"
            f"{doc["metadata_title"].replace(" ", "_")}"
        )
        st.caption(f"[{doc["title"]}]({doc["page_url"]}) - ID {doc["doc_id"]}")
        st.markdown(f"![{doc["title"]}]({image_url})")
        st.write(
            f"{".".join(doc["metadata_title"].split(".")[:-1]).replace("_", " ")}"
        )
        st.caption(doc["metadata_description"])


def main() -> None:
    st.set_page_config(page_title="Allknower", page_icon=":brain:", layout="wide")
    st.title("Allknower")

    query = st.text_area("Query", key="query_input")

    if st.button("Ask") and query:
        fail = False

        if DEBUG:
            full_text_search_docs = json.load(open("mock_text.json"))
            vector_search_text_docs = json.load(open("mock_text.json"))
            vector_search_image_docs = json.load(open("mock_image.json"))
            all_docs = (
                vector_search_text_docs +
                vector_search_image_docs
            ).copy()
            shuffle(all_docs)
            blender_docs = all_docs[:3]

        else:
            # TODO: input format
            resp = requests.get(
                ALLKNOWER_ENDPOINT,
                json=query
            )

            match resp.status_code:
                case 200:
                    contents = json.loads(resp.content)
                    full_text_search_docs = contents["full_text_search_docs"]
                    vector_search_text_docs = contents["vector_search_text_docs"]
                    vector_search_image_docs = contents["vector_search_image_docs"]
                    blender_docs = contents["blender_docs"]
                
                case _:
                    fail = True
                    st.markdown(f"**Oops! Something went wrong...**")
                    st.markdown(f"![Epic Fail](https://i.imgur.com/gqzhrUg.png)")

        if not fail:
            cols = st.columns(4, gap="medium")

            with cols[0]:
                st.subheader("Full-text Search Docs")
                for item in full_text_search_docs:
                    Renderer.render_text(item)

            with cols[1]:
                st.subheader("Vector Search Text Docs")
                for item in vector_search_text_docs:
                    Renderer.render_text(item)

            with cols[2]:
                st.subheader("Vector Search Image Docs")
                for item in vector_search_image_docs:
                    Renderer.render_image(item)

            with cols[3]:
                st.subheader("Blended Results")
                for item in blender_docs:
                    Renderer.render(item)


if __name__ == '__main__':
    main()
