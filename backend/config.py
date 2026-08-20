"""Central, env-driven settings. Nothing else in the app should read os.environ
directly - import `settings` from here instead.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # repo root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Gemini
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-2.0-flash"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Tavily (optional enrichment only, never used for book indexing)
    tavily_api_key: str = ""

    # TTS
    tts_voice: str = "en-US-AndrewNeural"

    # Chunking
    chunk_size_chars: int = 1800
    chunk_overlap_chars: int = 200

    # Retrieval
    retrieval_top_k: int = 6

    # Storage paths
    data_dir: Path = BASE_DIR / "data"
    books_dir: Path = BASE_DIR / "data" / "books"
    vectorstore_dir: Path = BASE_DIR / "data" / "vectorstore"
    audio_dir: Path = BASE_DIR / "data" / "audio"
    registry_path: Path = BASE_DIR / "data" / "registry.json"


settings = Settings()

for _dir in (settings.books_dir, settings.vectorstore_dir, settings.audio_dir):
    _dir.mkdir(parents=True, exist_ok=True)
