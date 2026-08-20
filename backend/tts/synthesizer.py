"""Free, local text-to-speech via edge-tts (Microsoft Edge's online neural
voices, no API key required). Produces an mp3 file per summary, cached on disk.

This is async because it's always called from an async FastAPI route, which
already has an event loop running - using asyncio.run() here would try to
start a second loop inside the first and crash with exactly the
"coroutine was never awaited" error. Await this directly from the route.
"""
from __future__ import annotations
from pathlib import Path
import os
import json
import re
import tempfile
import edge_tts
from backend.config import settings


def _speech_text(markdown: str) -> str:
    """Remove Markdown syntax that should not be spoken aloud."""
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", markdown)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
    text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[`*_~]", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


async def synthesize_to_file(
    text: str,
    summary_id: str,
    voice: str | None = None,
    force: bool = False,
) -> Path:
    """Generate an mp3, replacing a cached file when force is requested."""
    out_path = settings.audio_dir / f"{summary_id}.mp3"
    timing_path = settings.audio_dir / f"{summary_id}.json"
    if not force and out_path.exists() and out_path.stat().st_size > 0:
        return out_path

    speech_text = _speech_text(text)
    communicate = edge_tts.Communicate(
        speech_text,
        voice or settings.tts_voice,
        boundary="WordBoundary",
    )
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f"{summary_id}-", suffix=".mp3", dir=settings.audio_dir)
    os.close(fd)
    temp_path = Path(temp_name)
    timing_temp_path = temp_path.with_suffix(".json")
    audio_data = bytearray()
    timings = []
    try:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                timings.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                })
        temp_path.write_bytes(audio_data)
        if temp_path.stat().st_size == 0:
            raise RuntimeError("TTS returned an empty audio file")
        temp_path.replace(out_path)
        timing_temp_path.write_text(json.dumps({"words": timings}), encoding="utf-8")
        timing_temp_path.replace(timing_path)
    finally:
        temp_path.unlink(missing_ok=True)
        timing_temp_path.unlink(missing_ok=True)
    return out_path