"""
Structured output contract for JD requirement extraction.

The AI provider must return JSON matching JDExtractionResult exactly.
This is the single source of truth for what "valid AI output" means -
core/ai/jd_extraction.py validates every response against it, and
anything that doesn't fit (invalid JSON, wrong shape, unknown enum
values) is treated as a malformed-response error rather than being
coerced or guessed at.
"""

import enum

from pydantic import BaseModel, Field


class RequirementType(str, enum.Enum):
    REQUIRED_SKILL = "required_skill"
    PREFERRED_SKILL = "preferred_skill"
    TECHNOLOGY = "technology"
    RESPONSIBILITY = "responsibility"
    EDUCATION = "education"
    EXPERIENCE = "experience"
    DOMAIN = "domain"
    KEYWORD = "keyword"
    SOFT_SKILL = "soft_skill"


class Importance(str, enum.Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    NICE_TO_HAVE = "nice_to_have"


class ExtractedRequirement(BaseModel):
    requirement_type: RequirementType
    name: str = Field(min_length=1, max_length=255)
    importance: Importance = Importance.REQUIRED
    description: str | None = None
    # The literal excerpt of the JD text this requirement was derived
    # from, so every extracted item is traceable back to real source
    # text rather than being an unattributed AI claim.
    source_text: str | None = None


class JDExtractionResult(BaseModel):
    # No default: a response missing this key entirely is a schema
    # violation (malformed output), distinct from a response that
    # explicitly returns an empty list (legitimate "found nothing").
    requirements: list[ExtractedRequirement]
