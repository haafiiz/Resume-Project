"""
Pydantic schemas: the API contract for job descriptions.

Kept separate from the SQLAlchemy models (app/models/job_description.py)
and from the AI-output contract (app/core/ai/schemas.py) - three
different concerns that happen to overlap in shape:
  - models: what's persisted
  - core/ai/schemas: what the AI must return
  - here: what crosses the HTTP boundary
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.job_description import Importance, JobDescriptionStatus, RequirementType

# --- Requirement schemas ---------------------------------------------------


class JDRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    requirement_type: RequirementType
    name: str
    normalized_name: str
    importance: Importance
    description: str | None = None
    source_text: str | None = None
    verified: bool


class JDRequirementIn(BaseModel):
    """Payload shape for a single requirement in a correction (PUT)
    request. `id` is accepted for the client's own bookkeeping but is
    not used server-side to upsert - see ResumeUpdateRequest's docstring
    for the same pattern and rationale."""

    id: str | None = None
    requirement_type: RequirementType
    name: str = Field(min_length=1, max_length=255)
    importance: Importance = Importance.REQUIRED
    description: str | None = None
    source_text: str | None = None
    verified: bool = False


# --- Job description schemas ------------------------------------------------


class JobDescriptionCreateRequest(BaseModel):
    title: str | None = None
    company: str | None = None
    description: str = Field(min_length=1)


class JobDescriptionSummaryOut(BaseModel):
    """Lightweight representation for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    company: str | None = None
    status: JobDescriptionStatus
    created_at: datetime
    updated_at: datetime


class JobDescriptionOut(BaseModel):
    """The full job description including its extracted requirements, as
    returned by GET /job-descriptions/{id}."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str | None = None
    company: str | None = None
    description: str
    status: JobDescriptionStatus
    extraction_error: str | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    requirements: list[JDRequirementOut] = []


class JobDescriptionUpdateRequest(BaseModel):
    """Payload for PUT /job-descriptions/{id}. Any scalar field left
    unset is left unchanged. If `requirements` is provided, it fully
    replaces the existing requirement list (same full-replace contract
    as the resume domain's PUT)."""

    title: str | None = None
    company: str | None = None
    description: str | None = Field(default=None, min_length=1)
    requirements: list[JDRequirementIn] | None = None
