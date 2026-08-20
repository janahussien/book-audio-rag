"""Split a book's full text into overlapping chunks for embedding/retrieval.

Simple, dependency-free recursive splitter: prefers to break on paragraph
boundaries, falls back to sentence-ish boundaries, falls back to a hard cut.
Good enough for prose; swap for something smarter (e.g. langchain's
RecursiveCharacterTextSplitter) if you need better boundary detection.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Chunk:
    index: int
    text: str
    char_start: int
    char_end: int


_SEPARATORS = ["\n\n", "\n", ". ", " "]


def _split_on(text: str, sep: str, max_len: int) -> list[str]:
    pieces = text.split(sep)
    out, buf = [], ""
    for piece in pieces:
        candidate = (buf + sep + piece) if buf else piece
        if len(candidate) <= max_len:
            buf = candidate
        else:
            if buf:
                out.append(buf)
            buf = piece
    if buf:
        out.append(buf)
    return out


def chunk_text(text: str, chunk_size: int = 1800, overlap: int = 200) -> list[Chunk]:
    text = text.strip()
    if not text:
        return []

    # Coarse split on paragraphs first, then re-merge into ~chunk_size blocks.
    blocks = _split_on(text, "\n\n", chunk_size)
    # Any block still too long gets broken down further.
    refined: list[str] = []
    for block in blocks:
        if len(block) <= chunk_size:
            refined.append(block)
            continue
        for sep in _SEPARATORS[1:]:
            sub = _split_on(block, sep, chunk_size)
            if all(len(s) <= chunk_size for s in sub):
                refined.extend(sub)
                break
        else:
            # hard cut as last resort
            refined.extend(
                block[i : i + chunk_size] for i in range(0, len(block), chunk_size)
            )

    # Apply overlap by prepending the tail of the previous chunk.
    chunks: list[Chunk] = []
    cursor = 0
    for i, block in enumerate(refined):
        block = block.strip()
        if not block:
            continue
        if i > 0 and overlap > 0:
            prev_tail = refined[i - 1][-overlap:]
            block = prev_tail + "\n" + block
        start = cursor
        end = start + len(block)
        chunks.append(Chunk(index=len(chunks), text=block, char_start=start, char_end=end))
        cursor = end

    return chunks
