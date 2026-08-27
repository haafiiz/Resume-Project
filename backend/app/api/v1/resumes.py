"""
Resume API routes.

Routes stay thin: validate the HTTP-level shape of the request, delegate
to ResumeService, translate service-level exceptions into HTTP errors.
No business logic lives here.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.resume import (
    ResumeProfileOut,
    ResumeSummaryOut,
    ResumeUpdateRequest,
    ResumeUploadResponse,
)
from app.services.resume_service import (
    ResumeNotFoundError,
    ResumeService,
    ResumeVerificationError,
)
from app.utils.upload_validation import UploadValidationError

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> ResumeUploadResponse:
    content = await file.read()

    service = ResumeService(db)
    try:
        resume = service.upload_and_parse(file.filename, content, file.content_type)
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return ResumeUploadResponse.model_validate(resume)


@router.get("", response_model=list[ResumeSummaryOut])
def list_resumes(db: Session = Depends(get_db)) -> list[ResumeSummaryOut]:
    service = ResumeService(db)
    resumes = service.list_resumes()
    return [ResumeSummaryOut.model_validate(resume) for resume in resumes]


@router.get("/{resume_id}/profile", response_model=ResumeProfileOut)
def get_resume_profile(resume_id: str, db: Session = Depends(get_db)) -> ResumeProfileOut:
    service = ResumeService(db)
    try:
        resume = service.get_resume(resume_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found."
        ) from exc

    return ResumeProfileOut.model_validate(resume)


@router.put("/{resume_id}", response_model=ResumeProfileOut)
def update_resume(
    resume_id: str, payload: ResumeUpdateRequest, db: Session = Depends(get_db)
) -> ResumeProfileOut:
    service = ResumeService(db)
    try:
        resume = service.update_resume(resume_id, payload)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found."
        ) from exc
    except ResumeVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ResumeProfileOut.model_validate(resume)


@router.post("/{resume_id}/verify", response_model=ResumeProfileOut)
def verify_resume(resume_id: str, db: Session = Depends(get_db)) -> ResumeProfileOut:
    service = ResumeService(db)
    try:
        resume = service.verify_resume(resume_id)
    except ResumeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found."
        ) from exc
    except ResumeVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ResumeProfileOut.model_validate(resume)
