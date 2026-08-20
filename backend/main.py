from __future__ import annotations
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.api import books, summary, audio

logging.basicConfig(level=logging.INFO)

for path in ["data/uploads", "data/vectorstore", "data/audio"]:
    os.makedirs(path, exist_ok=True)

app = FastAPI(title="Book Audio RAG", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)
app.include_router(summary.router)
app.include_router(audio.router)

@app.get("/api/health")
async def health():
    return {"status": "ok"}

FRONTEND_DIR = Path("/app/frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")