"""
AIProvider abstraction.

Nothing outside this package should ever import a specific provider
(e.g. Ollama) directly. Callers depend only on this interface, so a
future OpenAIProvider or GeminiProvider can be swapped in without
touching JD extraction, matching, or tailoring logic.
"""

from abc import ABC, abstractmethod


class AIProviderError(Exception):
    """Base class for all AI provider failures."""


class AIProviderUnavailableError(AIProviderError):
    """The provider could not be reached at all (connection refused,
    timed out, DNS failure, etc.) - as opposed to reaching it and
    getting back a bad response."""


class AIProviderResponseError(AIProviderError):
    """The provider was reached but its response could not be used -
    not valid JSON, or valid JSON that doesn't match the expected
    schema."""


class AIProvider(ABC):
    """Minimal interface every AI provider must implement.

    Deliberately generic (a single text-in, text-out method) rather than
    JD-specific - domain logic like prompt construction and response
    validation belongs in the caller (e.g. core/ai/jd_extraction.py),
    not in the provider itself.
    """

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        """Send a prompt to the model and return its raw text response.

        Raises AIProviderUnavailableError if the provider can't be
        reached at all.
        """
        raise NotImplementedError
