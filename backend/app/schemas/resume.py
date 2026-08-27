"""
Pydantic schemas: the API contract for resumes.

These are deliberately separate from the SQLAlchemy models in
app/models/resume.py - schemas define what crosses the HTTP boundary,
models define what's persisted. Nothing here ever includes a filesystem
path; resumes are only ever addressed by id from the frontend's
perspective.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.resume import ResumeStatus, SourceType

# --- Nested item schemas ---------------------------------------------------


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str | None = None
    source: SourceType
    verified: bool


class SkillIn(BaseModel):
    id: str | None = None  # present when updating an existing skill
    name: str = Field(min_length=1, max_length=255)
    category: str | None = None
    verified: bool = False


class ExperienceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_title: str | None = None
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool
    description: str | None = None
    source: SourceType
    verified: bool


class ExperienceIn(BaseModel):
    id: str | None = None
    job_title: str | None = None
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    description: str | None = None
    verified: bool = False


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str | None = None
    description: str | None = None
    technologies: str | None = None
    source: SourceType
    verified: bool


class ProjectIn(BaseModel):
    id: str | None = None
    name: str | None = None
    description: str | None = None
    technologies: str | None = None
    verified: bool = False


class EducationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    source: SourceType
    verified: bool


class EducationIn(BaseModel):
    id: str | None = None
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    verified: bool = False


class CertificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    issuer: str | None = None
    issue_date: str | None = None
    source: SourceType
    verified: bool


class CertificationIn(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1, max_length=255)
    issuer: str | None = None
    issue_date: str | None = None
    verified: bool = False


class ResumeSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    section_type: str
    heading: str | None = None
    content: str
    sort_order: int


# --- Resume-level schemas ---------------------------------------------------


class ResumeSummaryOut(BaseModel):
    """Lightweight representation for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    status: ResumeStatus
    full_name: str | None = None
    created_at: datetime
    updated_at: datetime


class ResumeUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    status: ResumeStatus
    parse_error: str | None = None


class ResumeProfileOut(BaseModel):
    """The full structured profile for a resume, as returned by
    GET /resumes/{id}/profile."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    status: ResumeStatus
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    parse_error: str | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    sections: list[ResumeSectionOut] = []
    skills: list[SkillOut] = []
    experiences: list[ExperienceOut] = []
    projects: list[ProjectOut] = []
    education_entries: list[EducationOut] = []
    certifications: list[CertificationOut] = []


class ResumeUpdateRequest(BaseModel):
    """Payload for PUT /resumes/{id} - lets the user correct extracted
    information. Any scalar field left unset is left unchanged. Any list
    field that is provided fully replaces the corresponding collection -
    submit the complete, corrected list for that section (the `id` on an
    existing item is accepted for the client's own bookkeeping but is not
    used server-side to upsert; every PUT rewrites the collection from
    scratch). This keeps the contract simple for a form-based editor that
    submits an entire section at once.
    """

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None

    skills: list[SkillIn] | None = None
    experiences: list[ExperienceIn] | None = None
    projects: list[ProjectIn] | None = None
    education_entries: list[EducationIn] | None = None
    certifications: list[CertificationIn] | None = None
