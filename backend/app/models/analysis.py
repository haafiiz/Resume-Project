"""
Match analysis domain models.

An Analysis is one run of the matching engine against a specific
(resume, job description) pair. SkillMatch rows are the per-requirement
matching results that produced the analysis's scores - kept individually
so every number in the analysis can be traced back to exactly which
requirement was compared against exactly which resume item (or lack
thereof), and why.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MatchType(str, enum.Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    RELATED = "related"
    PARTIAL = "partial"
    MISSING = "missing"
    UNKNOWN = "unknown"


class Analysis(Base):
    """One matching-engine run comparing a verified resume against a
    verified job description."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    job_description_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False
    )

    overall_score: Mapped[float] = mapped_column(Float, nullable=False)

    required_skills_score: Mapped[float] = mapped_column(Float, nullable=False)
    responsibilities_score: Mapped[float] = mapped_column(Float, nullable=False)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False)
    education_score: Mapped[float] = mapped_column(Float, nullable=False)
    preferred_skills_score: Mapped[float] = mapped_column(Float, nullable=False)
    keywords_score: Mapped[float] = mapped_column(Float, nullable=False)

    # A JSON-encoded snapshot of the weights and per-category requirement
    # counts used to produce this analysis. Weights are configurable
    # (see core/matching/scorer.py) and may change over time - storing
    # the snapshot alongside the result is what keeps a past analysis
    # reproducible/explainable even if the configured defaults change
    # later.
    weights_snapshot: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    matches: Mapped[list["SkillMatch"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="SkillMatch.sort_order",
    )


class SkillMatch(Base):
    """The result of matching one JD requirement against the verified
    resume profile, as part of a specific Analysis."""

    __tablename__ = "skill_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )

    # The JD requirement this row evaluates. Not a hard FK-with-cascade
    # concern beyond normal referential integrity - every SkillMatch
    # corresponds to exactly one requirement, including ones that ended
    # up `missing`.
    jd_requirement_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jd_requirements.id", ondelete="CASCADE"), nullable=False
    )

    # Populated only when the match was found via the resume's Skill
    # table (required_skill / preferred_skill / technology categories).
    # Null for freetext-category matches (responsibility / experience /
    # education / domain / keyword / soft_skill) and for `missing`.
    resume_skill_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )

    # Populated for freetext-category matches instead of resume_skill_id
    # - there's no single-table FK target for "an experience entry's
    # description" or "an education entry's degree line", so the
    # matched passage is captured as a human-readable label + text
    # snapshot for transparency instead.
    matched_resume_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    matched_resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    match_type: Mapped[MatchType] = mapped_column(Enum(MatchType), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # Denormalized copies of the requirement's category-relevant fields,
    # captured at analysis time - so a SkillMatch remains fully
    # meaningful/displayable even if the underlying JDRequirement is
    # later edited or deleted, and so the frontend doesn't need a second
    # round-trip to group/label results.
    requirement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    requirement_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scoring_category: Mapped[str] = mapped_column(String(50), nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    analysis: Mapped["Analysis"] = relationship(back_populates="matches")
