"""Optional web-search enrichment via Tavily. This is NOT the RAG index for
the book (see README) - it's a supplementary lookup for context that can't
live in the book's own text, e.g. "who is this author" or "when was this
written and what was happening at the time". Disabled by default; only
called when a request explicitly opts in and TAVILY_API_KEY is set.
"""
from __future__ import annotations
from backend.config import settings

_client = None
if settings.tavily_api_key:
    from tavily import TavilyClient
    _client = TavilyClient(api_key=settings.tavily_api_key)


def is_enabled() -> bool:
    return _client is not None


def web_context(query: str, max_results: int = 3) -> str:
    """Return a short block of web search snippets for the given query, or
    an empty string if Tavily isn't configured.
    """
    if _client is None:
        return ""
    result = _client.search(query=query, max_results=max_results)
    snippets = [r.get("content", "") for r in result.get("results", [])]
    return "\n\n".join(s for s in snippets if s)
