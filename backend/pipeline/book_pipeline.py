"""Orchestrates the full flow. Kept independent of FastAPI so it can be
called from the API layer, a CLI script, or tests without dragging in HTTP.
"""
from __future__ import annotations
import logging
from pathlib import Path

from backend.ingestion.loaders import load_book
from backend.ingestion.chunker import chunk_text
from backend.rag import vector_store
from backend.rag.retriever import retrieve_context
from backend.llm.gemini_client import generate
from backend.llm.prompts import PromptDef, list_prompts
from backend.enrichment.tavily_client import web_context, is_enabled as tavily_enabled
from backend.storage import store
from backend.config import settings

log = logging.getLogger(__name__)


def process_book(book_id: str, file_path: Path, title_override: str | None = None) -> None:
    """Ingest, chunk, and index a book. Updates the registry as it goes so
    the frontend can poll status. Call this from a background task.
    """
    try:
        title, text = load_book(file_path)
        if title_override:
            title = title_override

        chunks = chunk_text(
            text,
            chunk_size=settings.chunk_size_chars,
            overlap=settings.chunk_overlap_chars,
        )
        if not chunks:
            raise ValueError("Book produced no usable text chunks.")

        vector_store.index_chunks(book_id, chunks)

        store.update_book(
            book_id,
            title=title,
            status="ready",
            num_chunks=len(chunks),
        )
        log.info("Book %s indexed with %d chunks", book_id, len(chunks))
    except Exception as exc:  # noqa: BLE001 - surface any failure to the user
        log.exception("Failed to process book %s", book_id)
        store.update_book(book_id, status="error", error=str(exc))


def run_prompt(book_id: str, prompt: PromptDef, use_web_enrichment: bool = False) -> dict:
    """Retrieve context, run one prompt through Gemini, persist the result."""
    book = store.get_book(book_id)
    if book is None:
        raise ValueError("Book not found")

    context = retrieve_context(book_id, prompt.template)

    if use_web_enrichment and tavily_enabled():
        extra = web_context(f"{book['title']} background context")
        if extra:
            context = f"{context}\n\n---\n\n[Supplementary web context]\n{extra}"

    filled_prompt = prompt.template.format(context=context, book_title=book["title"])
    output_budget = 8192 if prompt.id == "detailed_summary" else 1800
    text = generate(filled_prompt, max_output_tokens=output_budget)

    return store.save_summary(book_id, prompt.id, prompt.title, text)


def run_prompt_set(book_id: str, prompt_ids: list[str] | None, use_web_enrichment: bool = False) -> list[dict]:
    """Run selected prompts, or synthesize all focused passes into one summary."""
    all_prompts = list_prompts()
    if prompt_ids:
        selected = [p for p in all_prompts if p.id in prompt_ids]
        return [run_prompt(book_id, p, use_web_enrichment) for p in selected]

    summary_prompt = next(p for p in all_prompts if p.id == "detailed_summary")
    focused_prompts = [p for p in all_prompts if p.id != summary_prompt.id]
    focused_results = [run_prompt(book_id, p, use_web_enrichment) for p in focused_prompts]
    research_context = "\n\n--- FOCUSED ANALYSIS ---\n\n".join(
        f"## {result['prompt_title']}\n{result['text']}" for result in focused_results
    )
    book = store.get_book(book_id)
    if book is None:
        raise ValueError("Book not found")
    synthesis_prompt = summary_prompt.template.format(
        context=research_context,
        book_title=book["title"],
    )
    final_text = generate(synthesis_prompt, max_output_tokens=8192)
    final_result = store.save_summary(
        book_id,
        summary_prompt.id,
        summary_prompt.title,
        final_text,
    )
    return focused_results + [final_result]


def answer_book_question(book_id: str, question: str, use_web_enrichment: bool = False) -> str:
    """Answer a question using the most relevant passages from one book."""
    book = store.get_book(book_id)
    if book is None:
        raise ValueError("Book not found")
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty")

    context = retrieve_context(book_id, question)
    if use_web_enrichment and tavily_enabled():
        extra = web_context(f"{book['title']} {question}")
        if extra:
            context = f"{context}\n\n---\n\n[Supplementary web context]\n{extra}"

    prompt = (
        f'You are answering a question about "{book["title"]}". Use ONLY the book context '
        "below. Give a direct, detailed answer and preserve names, facts, and nuance from "
        "the text. If the context does not answer the question, say so plainly instead of "
        "guessing.\n\n"
        f"Question: {question}\n\nBook context:\n{context}"
    )
    return generate(prompt, max_output_tokens=1000)
