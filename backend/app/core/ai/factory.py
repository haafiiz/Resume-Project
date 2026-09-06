"""
AIProvider factory.

Single place that knows how to construct the "current" AI provider from
application settings. Services depend on the AIProvider interface and
receive an instance from here (or have one injected directly in tests) -
they never construct a specific provider themselves.
"""

from app.config import get_settings
from app.core.ai.base import AIProvider
from app.core.ai.ollama_provider import OllamaProvider


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)
