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

# serve each file explicitly -- avoids mount conflict
@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/styles.css")
async def styles():
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")

@app.get("/app.js")
async def appjs():
    return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")