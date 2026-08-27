"""
Resume domain models.

These tables represent the "structured source of truth" described in the
architecture: a Resume and the factual items extracted from it (skills,
experience, projects, education, certifications). Every extracted item
carries `source` and `verified` metadata so downstream stages (matching,
tailoring, validation - all future sprints) can tell the difference
between "the resume says this" and "the user has confirmed this".

Nothing in this module ever fabricates data - these tables only ever
hold what the parser extracted or what the user explicitly entered/edited.
"""

import enum
import uuid
from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)



from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ResumeStatus(str, enum.Enum):
    """Lifecycle state of a resume's profile.

    uploaded      - file stored, not parsed yet
    parsed        - parsing completed and produced structured data
    needs_review  - parsing completed but produced little/no data, or the
                    user has not yet reviewed the extracted data
    verified      - the user has explicitly confirmed the profile is
                    accurate; this is the only state a resume may later be
                    used as input to tailoring (enforced in a later sprint)
    """

    UPLOADED = "uploaded"
    PARSED = "parsed"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"


class SourceType(str, enum.Enum):
    """Where a factual claim about the candidate came from."""

    RESUME = "resume"
    USER = "user"


class Resume(Base):
    """A single uploaded resume and its parsed profile."""

    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # Original filename as provided by the client - shown to the user in
    # the UI, but never used to construct a filesystem path.
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # Name of the file as stored on disk under storage/uploads/ (a safe,
    # generated, collision-free name - see core/utils/file_storage.py).
    # This is an internal detail and is never returned to the frontend.
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[ResumeStatus] = mapped_column(
        Enum(ResumeStatus), nullable=False, default=ResumeStatus.UPLOADED
    )

    # Basic contact/identity fields extracted from the resume header.
    # These are simple enough not to warrant their own table.
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw extracted text, kept for debugging/re-parsing and so the parser
    # never needs to be treated as the only record of what the source
    # document contained.
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    sections: Mapped[list["ResumeSection"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    experiences: Mapped[list["Experience"]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="Experience.sort_order",
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", order_by="Project.sort_order"
    )
    education_entries: Mapped[list["Education"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", order_by="Education.sort_order"
    )
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )

    @property
    def is_verified(self) -> bool:
        return self.status == ResumeStatus.VERIFIED


class ResumeSection(Base):
    """A raw section detected in the source document (e.g. 'Experience').

    Kept separately from the structured tables below so the original
    section text is always available for the user to compare against
    what was extracted, even if structured extraction within that
    section was incomplete.
    """

    __tablename__ = "resume_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )

    section_type: Mapped[str] = mapped_column(String(50), nullable=False)
    heading: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    resume: Mapped["Resume"] = relationship(back_populates="sections")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    source: Mapped[SourceType] = mapped_column(
        Enum(SourceType), nullable=False, default=SourceType.RESUME
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    resume: Mapped["Resume"] = relationship(back_populates="skills")


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )

    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    source: Mapped[SourceType] = mapped_column(
        Enum(SourceType), nullable=False, default=SourceType.RESUME
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    resume: Mapped["Resume"] = relationship(back_populates="experiences")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    source: Mapped[SourceType] = mapped_column(
        Enum(SourceType), nullable=False, default=SourceType.RESUME
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    resume: Mapped["Resume"] = relationship(back_populates="projects")


class Education(Base):
    __tablename__ = "education"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )

    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    source: Mapped[SourceType] = mapped_column(
        Enum(SourceType), nullable=False, default=SourceType.RESUME
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    resume: Mapped["Resume"] = relationship(back_populates="education_entries")


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issue_date: Mapped[str | None] = mapped_column(String(50), nullable=True)

    source: Mapped[SourceType] = mapped_column(
        Enum(SourceType), nullable=False, default=SourceType.RESUME
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    resume: Mapped["Resume"] = relationship(back_populates="certifications")
