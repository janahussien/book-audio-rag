"""Thin wrapper around Gemini's chat/generation endpoint."""
from __future__ import annotations
import google.generativeai as genai
from backend.config import settings

genai.configure(api_key=settings.gemini_api_key)

_model = genai.GenerativeModel(settings.gemini_chat_model)


def generate(prompt: str, *, temperature: float = 0.4, max_output_tokens: int = 700) -> str:
    """Single-shot generation. Raises on empty/blocked response so callers
    can surface a clear error instead of silently returning ''.
    """
    response = _model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
    )
    if not response.candidates:
        raise RuntimeError("Gemini returned no candidates (likely blocked by safety filters).")
    return response.text.strip()
