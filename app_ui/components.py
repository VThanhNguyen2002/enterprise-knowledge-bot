"""
components.py — Reusable Streamlit UI components.
Role: Web_Frontend | Clean Architecture layer: Presentation / Components
"""
import time
import streamlit as st
from app_ui.api_client import KnowledgeBotClient


# ------------------------------------------------------------------ #
# Sidebar — document upload                                            #
# ------------------------------------------------------------------ #
def render_sidebar(client: KnowledgeBotClient) -> None:
    """
    Renders the sidebar with:
    - API health badge
    - .txt file uploader with spinner + toast feedback
    """
    with st.sidebar:
        st.title("⚙️ Controls")
        st.divider()

        # --- Health badge ---
        is_healthy = client.check_health()
        if is_healthy:
            st.success("🟢 API Online", icon=None)
        else:
            st.error("🔴 API Offline", icon=None)

        st.divider()

        # --- File upload ---
        st.subheader("📄 Upload Document")
        st.caption("Supported format: `.txt` · Max size: 5 MB")

        uploaded = st.file_uploader(
            label="Choose a .txt file",
            type=["txt"],
            label_visibility="collapsed",
        )

        if uploaded is not None:
            if st.button("Upload", use_container_width=True, type="primary"):
                with st.spinner(f"Submitting **{uploaded.name}**…"):
                    try:
                        result = client.upload_document(
                            file_bytes=uploaded.getvalue(),
                            filename=uploaded.name,
                        )
                        task_id = result.get("task_id", "n/a")
                        short_id = task_id[:8] if task_id != "n/a" else "n/a"

                        if result.get("status") == "processing":
                            st.toast(
                                f"⏳ Uploaded! Processing in background (Task: {short_id}…)",
                                icon="⏳",
                            )
                            st.info(
                                f"📄 **{uploaded.name}** is being embedded in the background. "
                                f"Wait ~30–60s before querying this document.  "
                                f"Task ID: `{task_id}`",
                                icon="ℹ️",
                            )
                        else:
                            # Fallback: synchronous success (e.g. Celery not configured)
                            st.toast(
                                f"✅ {result.get('message', 'Uploaded successfully!')}",
                                icon="✅",
                            )
                    except Exception as e:
                        st.toast(f"❌ Upload failed: {e}", icon="❌")


# ------------------------------------------------------------------ #
# Chat — message history display                                       #
# ------------------------------------------------------------------ #
def render_chat_messages(messages: list) -> None:
    """
    Renders the full chat history.
    Each message is a dict: {"role": "user"|"assistant", "content": str}
    """
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


# ------------------------------------------------------------------ #
# Chat — input + streaming reply                                       #
# ------------------------------------------------------------------ #
def render_chat_input(client: KnowledgeBotClient, messages: list) -> list:
    """
    Renders the chat input box.
    On submit: sends the question to the backend, streams the answer
    token-by-token for a typing effect, and returns the updated message list.
    """
    if prompt := st.chat_input("Ask a question about your documents…"):
        # Show user message immediately
        messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Fetch and stream assistant reply
        with st.chat_message("assistant"):
            placeholder = st.empty()
            with st.spinner("Thinking…"):
                try:
                    # Pass all messages before the current user prompt as history
                    result = client.chat(
                        question=prompt,
                        history=messages[:-1],  # exclude current user msg
                    )
                    answer = result.get("answer", "")
                    sources = result.get("sources", [])
                except Exception as e:
                    answer = ""
                    sources = []
                    st.toast(f"❌ Error: {e}", icon="❌")

            # Simulate streaming / typing effect
            streamed = ""
            for word in answer.split(" "):
                streamed += word + " "
                placeholder.markdown(streamed + "▌")
                time.sleep(0.03)
            placeholder.markdown(streamed.strip())

            # 📄 Source citation expander
            if sources:
                with st.expander(f"📄 Sources ({len(sources)} chunks used)"):
                    seen = set()
                    for src in sources:
                        fname = src.get("filename", "unknown")
                        snippet = src.get("snippet", "")
                        if fname not in seen:
                            seen.add(fname)
                            st.markdown(
                                f"`📁 {fname}`",
                                help="Source document",
                            )
                        st.caption(f"“{snippet}…”")

        messages.append({"role": "assistant", "content": answer})

    return messages
