from __future__ import annotations
import json
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from backend.storage import store
from backend.tts.synthesizer import synthesize_to_file

router = APIRouter(prefix="/api/books/{book_id}", tags=["audio"])


@router.post("/summaries/{summary_id}/audio")
async def generate_audio(book_id: str, summary_id: str):
    summary = store.get_summary(summary_id)
    if summary is None or summary["book_id"] != book_id:
        raise HTTPException(404, "Summary not found")

    try:
        path = await synthesize_to_file(summary["text"], summary_id, force=True)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"TTS failed: {exc}") from exc

    return FileResponse(path, media_type="audio/mpeg", filename=f"{summary_id}.mp3")


@router.get("/summaries/{summary_id}/audio")
async def get_audio(book_id: str, summary_id: str, range_header: str | None = Header(default=None, alias="Range")):
    from backend.config import settings
    summary = store.get_summary(summary_id)
    if summary is None or summary["book_id"] != book_id:
        raise HTTPException(404, "Summary not found")
    path = settings.audio_dir / f"{summary_id}.mp3"
    if not path.exists() or path.stat().st_size == 0:
        raise HTTPException(404, "Audio not generated yet - POST to this URL first")
    file_size = path.stat().st_size
    if not range_header:
        return FileResponse(
            path,
            media_type="audio/mpeg",
            filename=f"{summary_id}.mp3",
            headers={"Accept-Ranges": "bytes"},
        )

    if not range_header.startswith("bytes="):
        raise HTTPException(416, "Invalid audio range")
    try:
        start_text, end_text = range_header.removeprefix("bytes=").split("-", 1)
        if start_text:
            start = int(start_text)
            end = int(end_text) if end_text else file_size - 1
        else:
            start = max(0, file_size - int(end_text))
            end = file_size - 1
    except (TypeError, ValueError):
        raise HTTPException(416, "Invalid audio range") from None
    if start < 0 or start >= file_size or end < start:
        raise HTTPException(416, "Audio range not satisfiable")
    end = min(end, file_size - 1)
    content_length = end - start + 1

    def stream_audio():
        with path.open("rb") as audio_file:
            audio_file.seek(start)
            remaining = content_length
            while remaining:
                chunk = audio_file.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        stream_audio(),
        status_code=206,
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Disposition": f'inline; filename="{summary_id}.mp3"',
        },
    )


@router.get("/summaries/{summary_id}/audio-timings")
async def get_audio_timings(book_id: str, summary_id: str):
    from backend.config import settings
    summary = store.get_summary(summary_id)
    if summary is None or summary["book_id"] != book_id:
        raise HTTPException(404, "Summary not found")
    path = settings.audio_dir / f"{summary_id}.json"
    if not path.exists():
        raise HTTPException(404, "Timing data not generated yet - rebuild narration first")
    return json.loads(path.read_text(encoding="utf-8"))
