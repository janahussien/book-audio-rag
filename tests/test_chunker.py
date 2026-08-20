from backend.ingestion.chunker import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_short_text_is_single_chunk():
    chunks = chunk_text("Hello world.", chunk_size=1800, overlap=200)
    assert len(chunks) == 1
    assert "Hello world." in chunks[0].text


def test_long_text_splits_into_multiple_chunks():
    paragraph = "Sentence about the plot and the characters. " * 40  # ~1900 chars
    text = "\n\n".join([paragraph] * 3)
    chunks = chunk_text(text, chunk_size=1800, overlap=200)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c.text) <= 1800 + 200 + 5  # allow small slack from overlap join


def test_chunks_are_indexed_sequentially():
    text = "para one.\n\npara two.\n\npara three."
    chunks = chunk_text(text, chunk_size=10, overlap=0)
    indices = [c.index for c in chunks]
    assert indices == list(range(len(chunks)))
