"""Pydantic request/response models shared across the API layer."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BookSummaryOut(BaseModel):
    id: str
    title: str
    filename: str
    status: str  # "processing" | "ready" | "error"
    num_chunks: int = 0
    created_at: datetime
    error: Optional[str] = None


class PromptOut(BaseModel):
    id: str
    title: str


class SummaryRequest(BaseModel):
    prompt_ids: Optional[list[str]] = None
    use_web_enrichment: bool = False        # opt-in Tavily context


class SummaryOut(BaseModel):
    id: str
    book_id: str
    prompt_id: str
    prompt_title: str
    text: str
    created_at: datetime
    audio_ready: bool = False


class ChatRequest(BaseModel):
    question: str
    use_web_enrichment: bool = False


class ChatOut(BaseModel):
    answer: str


class ErrorOut(BaseModel):
    detail: str
