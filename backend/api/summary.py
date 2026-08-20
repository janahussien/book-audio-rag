from __future__ import annotations
from fastapi import APIRouter, HTTPException

from backend.storage import store
from backend.llm.prompts import list_prompts
from backend.pipeline.book_pipeline import run_prompt_set
from backend.models.schemas import ChatRequest, ChatOut, SummaryRequest, SummaryOut, PromptOut
from backend.pipeline.book_pipeline import answer_book_question

router = APIRouter(prefix="/api/books/{book_id}", tags=["summaries"])


@router.get("/prompts", response_model=list[PromptOut])
async def get_prompt_library():
    return [PromptOut(id=p.id, title=p.title) for p in list_prompts()]


@router.post("/summaries", response_model=list[SummaryOut])
async def create_summaries(book_id: str, body: SummaryRequest):
    book = store.get_book(book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    if book["status"] != "ready":
        raise HTTPException(409, f"Book is not ready yet (status: {book['status']})")

    try:
        results = run_prompt_set(book_id, body.prompt_ids, body.use_web_enrichment)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Generation failed: {exc}") from exc

    return [SummaryOut(**r, audio_ready=False) for r in results]


@router.get("/summaries", response_model=list[SummaryOut])
async def get_summaries(book_id: str):
    from backend.config import settings
    results = store.list_summaries(book_id)
    out = []
    for r in results:
        audio_ready = (settings.audio_dir / f"{r['id']}.mp3").exists()
        out.append(SummaryOut(**r, audio_ready=audio_ready))
    return out


@router.post("/chat", response_model=ChatOut)
async def chat_about_book(book_id: str, body: ChatRequest):
    book = store.get_book(book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    if book["status"] != "ready":
        raise HTTPException(409, f"Book is not ready yet (status: {book['status']})")

    try:
        answer = answer_book_question(book_id, body.question, body.use_web_enrichment)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Chat failed: {exc}") from exc
    return ChatOut(answer=answer)
