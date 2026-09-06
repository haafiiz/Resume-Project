"""
Ollama implementation of AIProvider.

Talks to a local Ollama instance's HTTP API
(https://github.com/ollama/ollama/blob/main/docs/api.md). This is the
only module in the codebase allowed to know Ollama's request/response
shape - everything else depends on the generic AIProvider interface.
"""

import httpx

from app.core.ai.base import AIProvider, AIProviderUnavailableError


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str, system: str | None = None) -> str:
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            # Ask Ollama to constrain output to valid JSON where the
            # model supports it - an extra guardrail on top of our own
            # response validation, not a replacement for it.
            "format": "json",
        }
        if system:
            payload["system"] = system

        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout_seconds,
            )
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            raise AIProviderUnavailableError(
                f"Could not reach Ollama at {self.base_url}: {exc}"
            ) from exc

        if response.status_code != 200:
            raise AIProviderUnavailableError(
                f"Ollama returned HTTP {response.status_code}: {response.text[:500]}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise AIProviderUnavailableError(
                f"Ollama returned a non-JSON response envelope: {exc}"
            ) from exc

        return body.get("response", "")
