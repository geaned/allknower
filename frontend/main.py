import random

import streamlit as st

st.set_page_config(page_title="Allknower", page_icon="🧠")
st.title("Allknower")


def search():
    st.session_state.search_triggered = True
    st.session_state.query = st.session_state.search_input


search_query = st.text_input(
    "", placeholder="Ask Allknower!", key="search_input", on_change=search
)


def get_mock_results(query):
    random_result_number = random.randint(0, 3)
    if random_result_number == 0:
        return [
            {
                "title": f"Result 1 for '{query}'",
                "url": "https://example.com/1",
                "snippet": f"This is a description of Result 1 for '{query}'.",
            },
            {
                "title": f"Result 2 for '{query}'",
                "url": "https://example.com/2",
                "snippet": f"This is a description of Result 2 for '{query}'.",
            },
            {
                "title": f"Result 3 for '{query}'",
                "url": "https://example.com/3",
                "snippet": f"This is a description of Result 3 for '{query}'.",
            },
        ]
    if random_result_number == 1:
        return [
            {
                "title": f"Result 1 for '{query}'",
                "url": "https://example.com/1",
                "snippet": f"This is a description of Result 1 for '{query}'.",
            }
        ]
    return []


if st.session_state.get("search_triggered", False) and st.session_state.get(
    "query", ""
):
    query = st.session_state.query
    results = get_mock_results(query)

    if len(results) > 0:
        st.write(f"### Search Results for: '{query}'")
        for result in results:
            st.write(f"**[{result['title']}]({result['url']})**")
            st.write(f"*{result['snippet']}*")
            st.write("---")
    else:
        st.write("### Allknower doesn't know")
elif st.session_state.get("search_triggered", False) and not st.session_state.get(
    "query", ""
):
    st.warning("Please enter a search query.")
