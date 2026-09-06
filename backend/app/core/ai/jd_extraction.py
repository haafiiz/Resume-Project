"""
Job description requirement extraction.

Provider-agnostic: takes any AIProvider and a JD description, returns a
validated JDExtractionResult. This is the only module that knows the
prompt shape and how to validate a provider's response - callers (e.g.
JDService) never see raw AI output or JSON parsing errors directly.
"""

import json

import pydantic

from app.core.ai.base import AIProvider, AIProviderResponseError, AIProviderUnavailableError
from app.core.ai.schemas import JDExtractionResult

SYSTEM_PROMPT = """You are extracting structured requirements from a job description.

Rules you must follow exactly:
- Only extract requirements that are literally stated in the text. Never invent, infer, or assume a requirement that isn't explicitly present.
- If you are not confident a piece of text describes a real requirement, omit it rather than guessing.
- Every requirement must include a `source_text` field containing the literal excerpt from the job description that it was derived from.
- Classify each requirement into exactly one of these types: required_skill, preferred_skill, technology, responsibility, education, experience, domain, keyword, soft_skill.
- Set `importance` to "required", "preferred", or "nice_to_have" based on the language used (e.g. "must have" -> required, "nice to have" / "a plus" -> nice_to_have, "preferred" -> preferred).
- Respond with ONLY a single JSON object matching this exact shape, and nothing else - no markdown fences, no commentary:

{"requirements": [{"requirement_type": "required_skill", "name": "...", "importance": "required", "description": "...", "source_text": "..."}]}
"""


def build_prompt(description: str) -> str:
    return (
        "Extract the structured requirements from the following job description.\n\n"
        "--- JOB DESCRIPTION ---\n"
        f"{description}\n"
        "--- END JOB DESCRIPTION ---"
    )


def _strip_markdown_fences(text: str) -> str:
    """Some models wrap JSON in ```json ... ``` fences despite being
    asked not to - strip them defensively before parsing."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def extract_requirements(provider: AIProvider, description: str) -> JDExtractionResult:
    """Run extraction against the given provider.

    Raises:
        AIProviderUnavailableError: the provider couldn't be reached.
        AIProviderResponseError: the provider responded, but with
            something that isn't valid JSON matching JDExtractionResult.
    """
    raw_response = provider.generate(prompt=build_prompt(description), system=SYSTEM_PROMPT)

    cleaned = _strip_markdown_fences(raw_response)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIProviderResponseError(f"AI response was not valid JSON: {exc}") from exc

    try:
        return JDExtractionResult.model_validate(data)
    except pydantic.ValidationError as exc:
        raise AIProviderResponseError(
            f"AI response did not match the expected schema: {exc}"
        ) from exc


__all__ = [
    "extract_requirements",
    "build_prompt",
    "AIProviderUnavailableError",
    "AIProviderResponseError",
]
