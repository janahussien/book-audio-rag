"""Flat-file JSON registry for books and summaries. Deliberately simple -
swap for SQLite/Postgres behind this same interface if you outgrow it.
Not safe for concurrent writers beyond a single dev/local-use process.
"""
from __future__ import annotations
import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any
from backend.config import settings

_lock = threading.Lock()


def _load() -> dict[str, Any]:
    if not settings.registry_path.exists():
        return {"books": {}, "summaries": {}}
    with settings.registry_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict[str, Any]) -> None:
    settings.registry_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.registry_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- Books ----------------------------------------------------------------

def create_book(title: str, filename: str) -> dict[str, Any]:
    with _lock:
        data = _load()
        book_id = new_id()
        record = {
            "id": book_id,
            "title": title,
            "filename": filename,
            "status": "processing",
            "num_chunks": 0,
            "created_at": now(),
            "error": None,
        }
        data["books"][book_id] = record
        _save(data)
        return record


def update_book(book_id: str, **fields: Any) -> None:
    with _lock:
        data = _load()
        if book_id in data["books"]:
            data["books"][book_id].update(fields)
            _save(data)


def get_book(book_id: str) -> dict[str, Any] | None:
    return _load()["books"].get(book_id)


def list_books() -> list[dict[str, Any]]:
    return sorted(_load()["books"].values(), key=lambda b: b["created_at"], reverse=True)


def delete_book(book_id: str) -> None:
    with _lock:
        data = _load()
        data["books"].pop(book_id, None)
        data["summaries"] = {
            sid: s for sid, s in data["summaries"].items() if s["book_id"] != book_id
        }
        _save(data)


# ---- Summaries --------------------------------------------------------------

def save_summary(book_id: str, prompt_id: str, prompt_title: str, text: str) -> dict[str, Any]:
    with _lock:
        data = _load()
        summary_id = new_id()
        record = {
            "id": summary_id,
            "book_id": book_id,
            "prompt_id": prompt_id,
            "prompt_title": prompt_title,
            "text": text,
            "created_at": now(),
        }
        data["summaries"][summary_id] = record
        _save(data)
        return record


def list_summaries(book_id: str) -> list[dict[str, Any]]:
    summaries = [s for s in _load()["summaries"].values() if s["book_id"] == book_id]
    return sorted(summaries, key=lambda summary: summary["created_at"], reverse=True)


def get_summary(summary_id: str) -> dict[str, Any] | None:
    return _load()["summaries"].get(summary_id)
