"""Per-book persistent Chroma collection. This is the actual RAG index over
the book's own text - Tavily is NOT used here (see README for why).
"""
from __future__ import annotations
import chromadb
from backend.config import settings
from backend.ingestion.chunker import Chunk
from backend.rag.embeddings import embed_texts, embed_query

_client = chromadb.PersistentClient(path=str(settings.vectorstore_dir))


def _collection_name(book_id: str) -> str:
    return f"book_{book_id}"


def index_chunks(book_id: str, chunks: list[Chunk]) -> None:
    """Embed and store all chunks for a book. Replaces any existing index."""
    try:
        _client.delete_collection(_collection_name(book_id))
    except Exception:
        pass
    collection = _client.create_collection(_collection_name(book_id))

    if not chunks:
        return

    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts, task_type="retrieval_document")
    collection.add(
        ids=[str(c.index) for c in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{"index": c.index, "char_start": c.char_start, "char_end": c.char_end} for c in chunks],
    )


def query(book_id: str, query_text: str, top_k: int) -> list[str]:
    """Return the top_k most relevant chunk texts for a query/prompt."""
    try:
        collection = _client.get_collection(_collection_name(book_id))
    except Exception:
        return []
    query_embedding = embed_query(query_text)
    result = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    documents = result.get("documents") or [[]]
    return documents[0]


def delete_book_index(book_id: str) -> None:
    try:
        _client.delete_collection(_collection_name(book_id))
    except Exception:
        pass
