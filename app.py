import streamlit as st

from LegalRag.rag_pipeline import RAGPipeline


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Indian Legal Assistant",
    page_icon="⚖️",
    layout="wide"
)

# =====================================================
# LOAD RAG ONCE
# =====================================================

@st.cache_resource
def load_rag():

    return RAGPipeline()


rag = load_rag()

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
                    rag.search(
                        query
                    )
                )

            answer = (
                result.get(
                    "answer",
                    "No answer generated."
                )
            )

            retrieval = (
                result.get(
                    "retrieval",
                    {}
                )
            )

            st.markdown(
                answer
            )

            # =====================================================
            # DEBUG / SOURCES
            # =====================================================

            with st.expander(
                "📚 Retrieved Sources"
            ):

                # -----------------------------------------
                # Statutory Retrieval
                # -----------------------------------------

                st.subheader(
                    "Statutory Retrieval"
                )

                statutory_results = (
                    retrieval.get(
                        "statutory_results",
                        []
                    )
                )

                if statutory_results:

                    for idx, item in enumerate(
                        statutory_results,
                        start=1
                    ):

                        payload = item.payload

                        st.markdown(
                            f"""
### Result {idx}

**Document:** {payload.get('document')}

**Chunk ID:** {payload.get('chunk_id')}
"""
                        )

                        st.text(
                            payload.get(
                                "text",
                                ""
                            )[:1500]
                        )

                        st.divider()

                else:

                    st.info(
                        "No statutory results."
                    )

                # -----------------------------------------
                # Graph Context
                # -----------------------------------------

                st.subheader(
                    "Knowledge Graph Context"
                )

                graph_context = (
                    retrieval.get(
                        "graph_context",
                        {}
                    )
                )

                if graph_context:

                    for node_id, graph_data in (
                        graph_context.items()
                    ):

                        st.markdown(
                            f"### {node_id}"
                        )

                        st.write(
                            f"Ancestors: {len(graph_data.get('ancestors', []))}"
                        )

                        st.write(
                            f"Children: {len(graph_data.get('children', []))}"
                        )

                        st.write(
                            f"References: {len(graph_data.get('references', []))}"
                        )

                        st.divider()

                else:

                    st.info(
                        "No graph context."
                    )

                # -----------------------------------------
                # Judgments
                # -----------------------------------------

                st.subheader(
                    "Judgments"
                )

                judgments = (
                    retrieval.get(
                        "judgments",
                        []
                    )
                )

                if judgments:

                    for idx, judgment in enumerate(
                        judgments,
                        start=1
                    ):

                        st.markdown(
                            f"### Judgment {idx}"
                        )

                        if isinstance(
                            judgment,
                            dict
                        ):

                            title = (
                                judgment.get(
                                    "title"
                                )
                                or
                                judgment.get(
                                    "docsource"
                                )
                                or
                                "Unknown Judgment"
                            )

                            st.write(
                                title
                            )

                            st.text(
                                str(
                                    judgment
                                )[:3000]
                            )

                        else:

                            st.text(
                                str(
                                    judgment
                                )[:3000]
                            )

                        st.divider()

                else:

                    st.info(
                        "No judgments retrieved."
                    )

        except Exception as e:

            st.error(
                f"Error: {str(e)}"
            )

            answer = (
                f"System Error:\n\n{str(e)}"
            )

    # -----------------------------------------
    # Save Assistant Response
    # -----------------------------------------

    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": answer
        }
    )