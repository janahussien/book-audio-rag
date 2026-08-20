# Book Audio RAG

Upload any book (PDF / EPUB / TXT) → chunk it → build a local RAG index over it
→ generate one detailed reading companion → ask grounded questions about it →
listen to the summary as audio.

Runs on **Gemini** for chat, uses local **SentenceTransformers** embeddings and
a local **Chroma** vector store for retrieval (built from the book's own text),
and **edge-tts** for free text-to-speech. Tavily is wired in as an
*optional* enrichment step (e.g. author background, historical context) —
it is a web-search API, not a vector database, so it cannot index the book
itself. Retrieval over the book always comes from the local vector store.

## Why not Tavily as the RAG engine?

Tavily searches the live web; it has no way to see the PDF/EPUB you upload.
RAG over *your* book requires: chunk the book → embed each chunk → store
embeddings → retrieve the most relevant chunks for a given prompt → feed
those chunks to the LLM. That pipeline lives entirely in `backend/rag/` and
`backend/ingestion/`, using local embeddings + Chroma. Tavily only gets
called (optionally) to pull in outside context that isn't in the book at all.

## Architecture

```
book-audio-rag/
├── backend/
│   ├── main.py                 # FastAPI app: wires routes, serves frontend
│   ├── config.py               # env-driven settings (pydantic-settings)
│   ├── models/schemas.py       # request/response models
│   │
│   ├── ingestion/
│   │   ├── loaders.py          # PDF/EPUB/TXT -> plain text
│   │   └── chunker.py          # plain text -> overlapping chunks
│   │
│   ├── rag/
│   │   ├── embeddings.py       # local SentenceTransformers embeddings
│   │   ├── vector_store.py     # Chroma collection per book (persisted)
│   │   └── retriever.py        # top-k relevant chunks for a query/prompt
│   │
│   ├── llm/
│   │   ├── gemini_client.py    # Gemini chat/generation wrapper
│   │   └── prompts.py          # 13 focused reading-companion prompts
│   │
│   ├── enrichment/
│   │   └── tavily_client.py    # optional web lookups (author, context)
│   │
│   ├── tts/
│   │   └── synthesizer.py      # edge-tts: text -> mp3
│   │
│   ├── pipeline/
│   │   └── book_pipeline.py    # orchestrates: ingest -> chunk -> embed
│   │                           #   -> index -> run prompts -> summarize -> tts
│   │
│   ├── api/
│   │   ├── books.py            # POST /books (upload), GET /books, GET /books/{id}
│   │   ├── summary.py          # summaries + POST /books/{id}/chat
│   │   └── audio.py            # summary narration endpoints
│   │
│   └── storage/
│       └── store.py            # simple JSON registry of books/summaries on disk
│
├── frontend/                   # plain HTML/CSS/JS single-page app (no build step)
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── data/                       # gitignored: uploaded books, vector db, audio files
├── scripts/run_dev.sh
├── tests/
├── requirements.txt
└── .env.example
```

### Data flow

1. **Upload** (`POST /api/books`) → `ingestion/loaders.py` extracts raw text
   from PDF/EPUB/TXT.
2. **Chunk** → `ingestion/chunker.py` splits into overlapping ~1800-char
   chunks (configurable), preserving order.
3. **Embed + index** → `rag/embeddings.py` creates local SentenceTransformers
   embeddings per chunk; `rag/vector_store.py` stores them in a per-book Chroma
   collection on disk (`data/vectorstore/<book_id>`).
4. **Generate summaries** (`POST /api/books/{id}/summaries`) →
   `rag/retriever.py` pulls the top-k most relevant chunks for each selected prompt
   and `llm/gemini_client.py` generates grounded answers. When `prompt_ids` is null,
   the 12 focused analyses are combined and passed into the `detailed_summary`
   prompt, which produces the final master reading companion.
5. **Ask questions** (`POST /api/books/{id}/chat`) → the question retrieves
   relevant chunks and Gemini answers from the book context.
6. **Narrate** (`GET /api/books/{id}/summaries/{summary_id}/audio`) → `tts/synthesizer.py`
   converts the summary text to an mp3 with edge-tts on first request, then
   caches it in `data/audio/`.

Everything is orchestrated by `pipeline/book_pipeline.py`, which the API
routes call into — keeps the FastAPI layer thin and the actual logic
testable/reusable outside the web server (e.g. from a script or notebook).

## Setup

```bash
cd book-audio-rag
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and paste your GEMINI_API_KEY (get one free at https://aistudio.google.com/apikey)
# TAVILY_API_KEY is optional - leave blank to skip web enrichment

bash scripts/run_dev.sh
# or directly: uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000 — the FastAPI app serves the frontend directly,
so there's nothing else to run.

## Summary and book chat

The app exposes 13 pre-written prompts in `backend/llm/prompts.py`. They cover
the master detailed summary plus structure, characters or concepts, arguments,
themes, evidence, turning points, practical tools, conflicts, symbols, endings,
critical perspective, and takeaways. They all support the same reading-companion
goal and can be selected individually through `prompt_ids` or run together with
`prompt_ids: null`; the full-generation path synthesizes the focused analyses into
the master detailed summary. The frontend keeps the master detailed summary and
book-grounded chat as its two primary views.

## Notes / things you'll likely want to adjust

- **Gemini model name**: set `GEMINI_CHAT_MODEL` in `.env`. Check
   https://ai.google.dev/gemini-api/docs/models if you hit a "model not found"
   error.
- **Embedding model**: set `EMBEDDING_MODEL_NAME` in `.env` to a model name
   supported by SentenceTransformers. The default is
   `sentence-transformers/all-MiniLM-L6-v2`.
- **TTS voice**: `edge-tts --list-voices` lists all free voices; set
  `TTS_VOICE` in `.env`.
- **Large books**: PDF/EPUB extraction + embedding hundreds of chunks takes
  a while on first upload — `book_pipeline.py` reports progress via logging;
  wire that into a proper job queue (e.g. Celery/RQ) if you need this to
  scale beyond single-user local use.
- **Storage**: `storage/store.py` uses a flat JSON file for simplicity. Swap
  in SQLite/Postgres if you outgrow it — it's isolated behind a small
  interface so the rest of the app doesn't need to change.
