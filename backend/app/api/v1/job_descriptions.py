"""
Job description API routes.

Mirrors app/api/v1/resumes.py's pattern: thin routes that validate the
HTTP-level shape and delegate to JDService, translating service-level
exceptions into HTTP errors.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.job_description import (
    JobDescriptionCreateRequest,
    JobDescriptionOut,
    JobDescriptionSummaryOut,
    JobDescriptionUpdateRequest,
)
from app.services.jd_service import (
    JDService,
    JobDescriptionNotFoundError,
    JobDescriptionVerificationError,
)

router = APIRouter(prefix="/job-descriptions", tags=["job-descriptions"])


@router.post("", response_model=JobDescriptionOut, status_code=status.HTTP_201_CREATED)
def create_job_description(
    payload: JobDescriptionCreateRequest, db: Session = Depends(get_db)
) -> JobDescriptionOut:
    service = JDService(db)
    job_description = service.create(payload)
    return JobDescriptionOut.model_validate(job_description)


@router.get("", response_model=list[JobDescriptionSummaryOut])
def list_job_descriptions(db: Session = Depends(get_db)) -> list[JobDescriptionSummaryOut]:
    service = JDService(db)
    job_descriptions = service.list_job_descriptions()
    return [JobDescriptionSummaryOut.model_validate(jd) for jd in job_descriptions]


@router.get("/{job_description_id}", response_model=JobDescriptionOut)
def get_job_description(job_description_id: str, db: Session = Depends(get_db)) -> JobDescriptionOut:
    service = JDService(db)
    try:
        job_description = service.get_job_description(job_description_id)
    except JobDescriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found."
        ) from exc

    return JobDescriptionOut.model_validate(job_description)


@router.post("/{job_description_id}/extract", response_model=JobDescriptionOut)
def extract_requirements(job_description_id: str, db: Session = Depends(get_db)) -> JobDescriptionOut:
    service = JDService(db)
    try:
        job_description = service.extract_requirements_for(job_description_id)
    except JobDescriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found."
        ) from exc
    except JobDescriptionVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return JobDescriptionOut.model_validate(job_description)


@router.put("/{job_description_id}", response_model=JobDescriptionOut)
def update_job_description(
    job_description_id: str, payload: JobDescriptionUpdateRequest, db: Session = Depends(get_db)
) -> JobDescriptionOut:
    service = JDService(db)
    try:
        job_description = service.update_job_description(job_description_id, payload)
    except JobDescriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found."
        ) from exc
    except JobDescriptionVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return JobDescriptionOut.model_validate(job_description)


@router.post("/{job_description_id}/verify", response_model=JobDescriptionOut)
def verify_job_description(job_description_id: str, db: Session = Depends(get_db)) -> JobDescriptionOut:
    service = JDService(db)
    try:
        job_description = service.verify_job_description(job_description_id)
    except JobDescriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found."
        ) from exc
    except JobDescriptionVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return JobDescriptionOut.model_validate(job_description)
