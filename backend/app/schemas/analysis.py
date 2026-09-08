"""
Pydantic schemas: the API contract for match analyses.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.analysis import MatchType


class AnalysisCreateRequest(BaseModel):
    resume_id: str = Field(min_length=1)
    job_description_id: str = Field(min_length=1)


class CategoryScoreOut(BaseModel):
    category: str
    weight: float
    requirement_count: int
    score: float
    weighted_contribution: float


class SkillMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    jd_requirement_id: str
    requirement_type: str
    requirement_name: str
    scoring_category: str
    resume_skill_id: str | None = None
    matched_resume_label: str | None = None
    matched_resume_text: str | None = None
    match_type: MatchType
    confidence: float
    explanation: str


class AnalysisSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resume_id: str
    job_description_id: str
    overall_score: float
    created_at: datetime


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resume_id: str
    job_description_id: str

    overall_score: float
    required_skills_score: float
    responsibilities_score: float
    experience_score: float
    education_score: float
    preferred_skills_score: float
    keywords_score: float

    category_breakdown: list[CategoryScoreOut]
    weights: dict[str, float]

    created_at: datetime


class AnalysisMatchesOut(BaseModel):
    analysis_id: str
    matches: list[SkillMatchOut]
    extra_resume_skills: list[str] = Field(
        default_factory=list,
        description=(
            "Verified resume skills that don't correspond to any JD requirement. "
            "Informational only - never counted as a match or penalty."
        ),
    )
