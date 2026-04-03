"""
api_client.py — HTTP client for the Enterprise Knowledge Bot FastAPI backend.
Role: Web_Frontend | Clean Architecture layer: Infrastructure / Data Layer
"""
import os
import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class KnowledgeBotClient:
    """Wraps all HTTP calls to the FastAPI backend."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------ #
    # Health                                                               #
    # ------------------------------------------------------------------ #
    def check_health(self) -> bool:
        """
        GET /health
        Returns True if backend is reachable and healthy, False otherwise.
        Never raises — safe for UI status indicators.
        """
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=3)
            resp.raise_for_status()
            return resp.json().get("status") == "healthy"
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Upload                                                               #
    # ------------------------------------------------------------------ #
    def upload_document(self, file_bytes: bytes, filename: str) -> dict:
        """
        POST /upload/
        Sends a .txt file as multipart/form-data.
        Returns the JSON response dict.
        Raises requests.HTTPError on 4xx/5xx or requests.RequestException on
        network issues — callers are responsible for handling.
        """
        resp = requests.post(
            f"{self.base_url}/upload/",
            files={"file": (filename, file_bytes, "text/plain")},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------ #
    # Chat                                                                 #
    # ------------------------------------------------------------------ #
    def chat(self, question: str, history: list | None = None) -> dict:
        """
        POST /chat/
        Sends {question: str, history: list} as JSON.
        Returns the JSON response dict containing at least {"answer": str}.
        Raises requests.HTTPError on 4xx/5xx or requests.RequestException on
        network issues — callers are responsible for handling.
        """
        resp = requests.post(
            f"{self.base_url}/chat/",
            json={"question": question, "history": history or []},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
