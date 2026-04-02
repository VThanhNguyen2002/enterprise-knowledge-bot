"""
main_app.py — Streamlit application entry point.
Role: Web_Frontend | Clean Architecture layer: Application / Composition Root

Run with:
    streamlit run app_ui/main_app.py
"""
import streamlit as st
from app_ui.api_client import KnowledgeBotClient
from app_ui.components import (
    render_sidebar,
    render_chat_messages,
    render_chat_input,
)

# ------------------------------------------------------------------ #
# Page config (must be the very first Streamlit call)                  #
# ------------------------------------------------------------------ #
st.set_page_config(
    page_title="Enterprise Knowledge Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------ #
# Session state initialisation                                         #
# ------------------------------------------------------------------ #
if "messages" not in st.session_state:
    st.session_state.messages: list = []

# ------------------------------------------------------------------ #
# Dependency construction                                              #
# ------------------------------------------------------------------ #
client = KnowledgeBotClient()

# ------------------------------------------------------------------ #
# Layout                                                               #
# ------------------------------------------------------------------ #
# Sidebar (upload + health badge)
render_sidebar(client)

# Main area
st.title("🤖 Enterprise Knowledge Bot")
st.caption("Powered by FastAPI · LangChain · Groq / llama-3.3-70b · ChromaDB")
st.divider()

# Chat history
render_chat_messages(st.session_state.messages)

# Chat input (updates session state in-place)
st.session_state.messages = render_chat_input(client, st.session_state.messages)
