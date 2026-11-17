import streamlit as st

from legora.api_client import query_api


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Indian Legal Assistant",
    page_icon="⚖️",
    layout="wide"
)

# =====================================================
# SESSION STATE
# =====================================================

if "chat_history" not in st.session_state:

    st.session_state.chat_history = []

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.title("⚖️ Legal RAG")

    st.markdown("---")

    st.success("Constitution")

    st.success("BNS")

    st.success("BNSS")

    st.success("BSA")

    st.success("Indian Kanoon")

    st.markdown("---")

    if st.button("🗑 Clear Chat"):

        st.session_state.chat_history = []

        st.rerun()

# =====================================================
# HEADER
# =====================================================

st.title(
    "⚖️ Indian Legal Assistant"
)

st.caption(
    "Constitution • BNS • BNSS • BSA • Indian Kanoon"
)

# =====================================================
# DISPLAY CHAT HISTORY
# =====================================================

for chat in st.session_state.chat_history:

    with st.chat_message(
        chat["role"]
    ):

        st.markdown(
            chat["content"]
        )

# =====================================================
# USER INPUT
# =====================================================

query = st.chat_input(
    "Ask a legal question..."
)

# =====================================================
# PROCESS QUERY
# =====================================================

if query:

    # -----------------------------------------
    # User Message
    # -----------------------------------------

    st.session_state.chat_history.append(
        {
            "role": "user",
            "content": query
        }
    )

    with st.chat_message(
        "user"
    ):

        st.markdown(
            query
        )

    # -----------------------------------------
    # Assistant Message
    # -----------------------------------------

    with st.chat_message(
        "assistant"
    ):

        try:

            with st.spinner(
                "Searching Constitution, BNS, BNSS, BSA and Case Law..."
            ):

                result = (
                    query_api(query)
                )

            answer = (
                result.get(
                    "answer",
                    "No answer generated."
                )
            )

            st.markdown(answer)
            if result.get("unsupported_citations"):
                st.warning("Statutory citations not matched to retrieved context: " + ", ".join(result["unsupported_citations"]))

            with st.expander("📚 Retrieved Sources"):
                citations = result["citations"]
                if not citations:
                    st.info("No sources retrieved.")
                for citation in citations:
                    st.write(citation["title"] or citation["id"])
                    st.caption(f"{citation['source']}: {citation['id']}")
                    if citation.get("url"):
                        st.link_button("Open judgment", citation["url"])
                st.json(result["retrieval_debug"])

        except (RuntimeError, ValueError) as error:
            answer = str(error)
            st.error(answer)

    # -----------------------------------------
    # Save Assistant Response
    # -----------------------------------------

    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": answer
        }
    )