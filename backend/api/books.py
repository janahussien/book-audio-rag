from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException

from backend.config import settings
from backend.storage import store
from backend.rag import vector_store
from backend.pipeline.book_pipeline import process_book
from backend.models.schemas import BookSummaryOut

router = APIRouter(prefix="/api/books", tags=["books"])

ALLOWED_EXTENSIONS = {".pdf", ".epub", ".txt"}


@router.post("", response_model=BookSummaryOut)
async def upload_book(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{suffix}'. Use PDF, EPUB, or TXT.")

    record = store.create_book(title=Path(file.filename).stem, filename=file.filename)
    dest = settings.books_dir / f"{record['id']}{suffix}"
    with dest.open("wb") as f:
        f.write(await file.read())

    background_tasks.add_task(process_book, record["id"], dest)
    return record


@router.get("", response_model=list[BookSummaryOut])
async def get_books():
    return store.list_books()


@router.get("/{book_id}", response_model=BookSummaryOut)
async def get_book(book_id: str):
    record = store.get_book(book_id)
    if record is None:
        raise HTTPException(404, "Book not found")
    return record


@router.delete("/{book_id}")
async def remove_book(book_id: str):
    record = store.get_book(book_id)
    if record is None:
        raise HTTPException(404, "Book not found")
    vector_store.delete_book_index(book_id)
    store.delete_book(book_id)
    return {"deleted": book_id}
