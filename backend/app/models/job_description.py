"""
Job description domain models.

A JobDescription holds the raw pasted text plus lifecycle status.
JDRequirement rows are the structured items extracted from it (or added
by hand) - each one traceable to its source text and independently
markable as verified, mirroring the resume domain's source-of-truth
pattern (see app/models/resume.py).
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobDescriptionStatus(str, enum.Enum):
    """Lifecycle state of a job description.

    created       - saved, extraction not yet run (or not yet successful)
    extracted     - extraction found at least one requirement
    needs_review  - extraction ran but failed, was unavailable, or found
                    nothing usable; explained via `extraction_error`
    verified      - the user has confirmed the requirements are accurate
    """

    CREATED = "created"
    EXTRACTED = "extracted"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"


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


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[JobDescriptionStatus] = mapped_column(
        Enum(JobDescriptionStatus), nullable=False, default=JobDescriptionStatus.CREATED
    )

    # Raw AI response text, kept for debugging a bad extraction - never
    # shown to the user as-is, and never itself treated as a source of
    # truth (the persisted JDRequirement rows are).
    raw_ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    requirements: Mapped[list["JDRequirement"]] = relationship(
        back_populates="job_description",
        cascade="all, delete-orphan",
        order_by="JDRequirement.sort_order",
    )

    @property
    def is_verified(self) -> bool:
        return self.status == JobDescriptionStatus.VERIFIED


class JDRequirement(Base):
    __tablename__ = "jd_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_description_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False
    )

    requirement_type: Mapped[RequirementType] = mapped_column(
        Enum(RequirementType), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    importance: Mapped[Importance] = mapped_column(
        Enum(Importance), nullable=False, default=Importance.REQUIRED
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0)

    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    job_description: Mapped["JobDescription"] = relationship(back_populates="requirements")
