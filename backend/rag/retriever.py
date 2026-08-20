"""Retrieval convenience layer sitting on top of the vector store."""
from __future__ import annotations
from backend.config import settings
from backend.rag import vector_store


def retrieve_context(book_id: str, prompt_text: str, top_k: int | None = None) -> str:
    """Fetch the most relevant chunks for a given prompt and join them into
    a single context block ready to drop into an LLM call.
    """
    k = top_k or settings.retrieval_top_k
    chunks = vector_store.query(book_id, prompt_text, top_k=k)
    return "\n\n---\n\n".join(chunks)
