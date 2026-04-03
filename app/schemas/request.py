import re
import unicodedata
from typing import Optional
from pydantic import BaseModel, field_validator


# ── Shared payload patterns ────────────────────────────────────────────────────
_DANGEROUS_PATTERNS = [
    r'(?i)ignore.*instructions?',
    r'(?i)system\s*prompt',
    r'(?i)bỏ\s*qua.*hướng\s*dẫn',
    r'(?i)quên.*đi',
    r'(?i)execute|system\(',
    r'(?i)disregard\s+(the\s+)?(rules|instructions|above)',
    r'(?i)act\s+as\s+(an?\s+)?(unrestricted|unfiltered|evil|DAN)',
    r'(?i)you\s+are\s+now',
    r'(?i)new\s+persona',
    r'(?i)from\s+now\s+on',
]


def _scan_text(v: str) -> str:
    """Normalize unicode then check for injection patterns."""
    v = unicodedata.normalize("NFKC", v)
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, v):
            raise ValueError("Phát hiện nội dung không an toàn. Yêu cầu bị từ chối.")
    return v


# ── Request Models ─────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    """Single turn in conversation history."""
    role: str     # "user" | "assistant"
    content: str


class QuestionRequest(BaseModel):
    question: str
    history: Optional[list[ChatMessage]] = []

    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        if len(v) > 2000:
            raise ValueError("Câu hỏi quá dài (tối đa 2000 ký tự).")
        return _scan_text(v).strip()

    @field_validator('history')
    @classmethod
    def validate_history(cls, messages: list[ChatMessage]) -> list[ChatMessage]:
        for msg in messages:
            if len(msg.content) > 2000:
                raise ValueError("Nội dung lịch sử quá dài.")
            _scan_text(msg.content)
        return messages


# ── Response Models ────────────────────────────────────────────────────────────
class SourceChunk(BaseModel):
    """A single retrieved document chunk used to generate the answer."""
    filename: str
    snippet: str   # First 200 chars of the chunk content


class ChatResponse(BaseModel):
    """Typed response envelope for POST /chat/."""
    status: str
    question: str
    answer: str
    sources: list[SourceChunk]