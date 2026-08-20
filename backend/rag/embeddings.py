"""Local embeddings via sentence-transformers. Free, no API key, no network
call per chunk — runs on CPU fine for MiniLM's size.
"""
from __future__ import annotations
from sentence_transformers import SentenceTransformer
from backend.config import settings

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model_name)
    return _model


def embed_texts(texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
    """task_type is accepted for interface-compatibility with the old Gemini
    version but unused here — MiniLM doesn't need query/document prefixes.
    """
    if not texts:
        return []
    embeddings = _get_model().encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]