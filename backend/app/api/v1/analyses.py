"""
Analysis API routes.

Thin routes: validate the HTTP-level shape, delegate to AnalysisService,
translate service-level exceptions into HTTP errors. All scoring logic
lives in core/matching/ - nothing is computed here.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analysis import (
    AnalysisCreateRequest,
    AnalysisMatchesOut,
    AnalysisOut,
    AnalysisSummaryOut,
    CategoryScoreOut,
    SkillMatchOut,
)
from app.services.analysis_service import (
    AnalysisInputNotVerifiedError,
    AnalysisNotFoundError,
    AnalysisService,
)
from app.services.jd_service import JobDescriptionNotFoundError
from app.services.resume_service import ResumeNotFoundError

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _to_analysis_out(analysis) -> AnalysisOut:
    snapshot = json.loads(analysis.weights_snapshot)
    return AnalysisOut(
        id=analysis.id,
        resume_id=analysis.resume_id,
        job_description_id=analysis.job_description_id,
        overall_score=analysis.overall_score,
        required_skills_score=analysis.required_skills_score,
        responsibilities_score=analysis.responsibilities_score,
        experience_score=analysis.experience_score,
        education_score=analysis.education_score,
        preferred_skills_score=analysis.preferred_skills_score,
        keywords_score=analysis.keywords_score,
        category_breakdown=[
            CategoryScoreOut(category=category, **fields)
            for category, fields in snapshot["category_breakdown"].items()
        ],
        weights=snapshot["weights"],
        created_at=analysis.created_at,
    )


@router.post("", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
def create_analysis(payload: AnalysisCreateRequest, db: Session = Depends(get_db)) -> AnalysisOut:
    service = AnalysisService(db)
    try:
        analysis = service.create_analysis(payload.resume_id, payload.job_description_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found."
        ) from exc
    except JobDescriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found."
        ) from exc
    except AnalysisInputNotVerifiedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return _to_analysis_out(analysis)


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisOut:
    service = AnalysisService(db)
    try:
        analysis = service.get_analysis(analysis_id)
    except AnalysisNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found."
        ) from exc

    return _to_analysis_out(analysis)


@router.get("/{analysis_id}/matches", response_model=AnalysisMatchesOut)
def get_analysis_matches(analysis_id: str, db: Session = Depends(get_db)) -> AnalysisMatchesOut:
    service = AnalysisService(db)
    try:
        analysis = service.get_analysis(analysis_id)
    except AnalysisNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found."
        ) from exc

    extra_skills = service.get_extra_resume_skills(analysis)

    return AnalysisMatchesOut(
        analysis_id=analysis.id,
        matches=[SkillMatchOut.model_validate(m) for m in analysis.matches],
        extra_resume_skills=extra_skills,
    )
