"""Extract plain text from an uploaded book file. Supports PDF, EPUB, and TXT.
Each loader returns (title, full_text) - title is a best-effort guess from
metadata/filename, the caller can let the user override it.
"""
from __future__ import annotations
from pathlib import Path

from pypdf import PdfReader
from ebooklib import epub
import ebooklib
from bs4 import BeautifulSoup


def load_txt(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    title = path.stem
    return title, text


def load_pdf(path: Path) -> tuple[str, str]:
    reader = PdfReader(str(path))
    title = (reader.metadata.title if reader.metadata and reader.metadata.title else path.stem)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return title, "\n\n".join(pages)


def load_epub(path: Path) -> tuple[str, str]:
    book = epub.read_epub(str(path))

    title = path.stem
    if book.get_metadata("DC", "title"):
        title = book.get_metadata("DC", "title")[0][0]

    parts = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text(separator="\n")
            if text.strip():
                parts.append(text)
    return title, "\n\n".join(parts)


LOADERS = {
    ".txt": load_txt,
    ".pdf": load_pdf,
    ".epub": load_epub,
}


def load_book(path: Path) -> tuple[str, str]:
    """Dispatch on file extension. Raises ValueError for unsupported types."""
    suffix = path.suffix.lower()
    loader = LOADERS.get(suffix)
    if loader is None:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported: {', '.join(LOADERS)}"
        )
    title, text = loader(path)
    text = text.strip()
    if not text:
        raise ValueError(
            "No extractable text found - this may be a scanned/image-only PDF "
            "(would need OCR, not currently supported)."
        )
    return title, text
