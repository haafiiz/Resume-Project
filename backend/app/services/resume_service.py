"""
Resume service.

Orchestrates the resume upload -> parse -> review -> verify flow. This is
where core/parsing, utils/file_storage, utils/upload_validation, and the
repository are wired together - API routes stay thin and just call into
here.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.parsing import docx_parser, pdf_parser
from app.core.parsing.resume_parser import ParsedResume, parse_resume_text
from app.models.resume import (
    Certification,
    Education,
    Experience,
    Project,
    Resume,
    ResumeSection,
    ResumeStatus,
    Skill,
    SourceType,
)
from app.repositories.resume_repository import ResumeRepository
from app.schemas.resume import ResumeUpdateRequest
from app.utils import file_storage
from app.utils.upload_validation import validate_upload


class ResumeNotFoundError(LookupError):
    pass


class ResumeVerificationError(ValueError):
    """Raised when an action requires a verified resume but the resume
    is not verified (or requires an unverified resume but it already
    is)."""


class ResumeService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ResumeRepository(db)

    # --- Upload + parse ---------------------------------------------------

    def upload_and_parse(
        self, filename: str | None, content: bytes, declared_content_type: str | None
    ) -> Resume:
        """Validate, store, and parse an uploaded resume file.

        Raises UploadValidationError if the file itself is invalid. If
        the file is valid but parsing fails or produces little/no
        structured data, the resume is still created (status
        `needs_review`) rather than the whole request failing - a
        document that can't be auto-parsed still deserves to exist so
        the user can fill in details manually.
        """
        validated = validate_upload(filename, content, declared_content_type)

        stored_filename, _path = file_storage.save_upload(content, validated.extension)

        resume = Resume(
            original_filename=filename or "resume",
            stored_filename=stored_filename,
            file_extension=validated.extension,
            content_type=validated.content_type,
            file_size_bytes=validated.size_bytes,
            status=ResumeStatus.UPLOADED,
        )
        resume = self.repo.create(resume)

        self._parse_and_populate(resume, content, validated.extension)

        return self.repo.get(resume.id)

    def _parse_and_populate(self, resume: Resume, content: bytes, extension: str) -> None:
        try:
            if extension == ".docx":
                text = docx_parser.extract_text(content)
            elif extension == ".pdf":
                text = pdf_parser.extract_text(content)
            else:  # pragma: no cover - validate_upload already restricts this
                raise ValueError(f"Unsupported extension: {extension}")

            resume.raw_text = text

            if not text.strip():
                resume.status = ResumeStatus.NEEDS_REVIEW
                resume.parse_error = (
                    "No readable text was found in this document. It may be "
                    "an image-based scan, which isn't supported yet - please "
                    "fill in your profile manually."
                )
                self.repo.save(resume)
                return

            parsed = parse_resume_text(text)
            self._apply_parsed_resume(resume, parsed)

            resume.status = (
                ResumeStatus.PARSED if parsed.has_meaningful_content else ResumeStatus.NEEDS_REVIEW
            )
            if not parsed.has_meaningful_content:
                resume.parse_error = (
                    "We couldn't confidently identify structured sections "
                    "(skills, experience, education, etc.) in this document. "
                    "Please review and fill in your profile manually."
                )
            else:
                resume.parse_error = None

        except (docx_parser.DocxParseError, pdf_parser.PdfParseError) as exc:
            resume.status = ResumeStatus.NEEDS_REVIEW
            resume.parse_error = str(exc)

        self.repo.save(resume)

    def _apply_parsed_resume(self, resume: Resume, parsed: ParsedResume) -> None:
        resume.full_name = parsed.full_name
        resume.email = parsed.email
        resume.phone = parsed.phone
        resume.location = parsed.location
        resume.summary = parsed.summary

        self.repo.replace_sections(
            resume,
            [
                ResumeSection(
                    section_type=section.section_type,
                    heading=section.heading,
                    content=section.content,
                    sort_order=section.sort_order,
                )
                for section in parsed.sections
            ],
        )
        self.repo.replace_skills(
            resume,
            [
                Skill(name=skill.name, source=SourceType.RESUME, verified=False)
                for skill in parsed.skills
            ],
        )
        self.repo.replace_experiences(
            resume,
            [
                Experience(
                    job_title=exp.job_title,
                    company=exp.company,
                    location=exp.location,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    is_current=exp.is_current,
                    description=exp.description,
                    sort_order=i,
                    source=SourceType.RESUME,
                    verified=False,
                )
                for i, exp in enumerate(parsed.experiences)
            ],
        )
        self.repo.replace_projects(
            resume,
            [
                Project(
                    name=proj.name,
                    description=proj.description,
                    technologies=proj.technologies,
                    sort_order=i,
                    source=SourceType.RESUME,
                    verified=False,
                )
                for i, proj in enumerate(parsed.projects)
            ],
        )
        self.repo.replace_education(
            resume,
            [
                Education(
                    institution=edu.institution,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    start_date=edu.start_date,
                    end_date=edu.end_date,
                    sort_order=i,
                    source=SourceType.RESUME,
                    verified=False,
                )
                for i, edu in enumerate(parsed.education)
            ],
        )
        self.repo.replace_certifications(
            resume,
            [
                Certification(
                    name=cert.name,
                    issuer=cert.issuer,
                    issue_date=cert.issue_date,
                    source=SourceType.RESUME,
                    verified=False,
                )
                for cert in parsed.certifications
            ],
        )

    # --- Reads --------------------------------------------------------------

    def list_resumes(self) -> list[Resume]:
        return self.repo.list_all()

    def get_resume(self, resume_id: str) -> Resume:
        resume = self.repo.get(resume_id)
        if resume is None:
            raise ResumeNotFoundError(resume_id)
        return resume

    # --- Update / correction --------------------------------------------

    def update_resume(self, resume_id: str, payload: ResumeUpdateRequest) -> Resume:
        """Apply user corrections to a resume's profile.

        Any item the user submits is treated as user-confirmed: source is
        set to `user` and verified defaults to whatever the client sent
        (the frontend sets `verified=true` when the user explicitly
        confirms a field, but a correction alone doesn't imply
        verification of the whole profile - that's a separate, explicit
        action via verify_resume()).
        """
        resume = self.get_resume(resume_id)

        if resume.status == ResumeStatus.VERIFIED:
            raise ResumeVerificationError(
                "This resume is already verified. Corrections can no longer "
                "be made through this endpoint once a resume is verified."
            )

        if payload.full_name is not None:
            resume.full_name = payload.full_name
        if payload.email is not None:
            resume.email = payload.email
        if payload.phone is not None:
            resume.phone = payload.phone
        if payload.location is not None:
            resume.location = payload.location
        if payload.summary is not None:
            resume.summary = payload.summary

        if payload.skills is not None:
            self.repo.replace_skills(
                resume,
                [
                    Skill(
                        name=item.name,
                        category=item.category,
                        source=SourceType.USER,
                        verified=item.verified,
                    )
                    for item in payload.skills
                ],
            )

        if payload.experiences is not None:
            self.repo.replace_experiences(
                resume,
                [
                    Experience(
                        job_title=item.job_title,
                        company=item.company,
                        location=item.location,
                        start_date=item.start_date,
                        end_date=item.end_date,
                        is_current=item.is_current,
                        description=item.description,
                        sort_order=i,
                        source=SourceType.USER,
                        verified=item.verified,
                    )
                    for i, item in enumerate(payload.experiences)
                ],
            )

        if payload.projects is not None:
            self.repo.replace_projects(
                resume,
                [
                    Project(
                        name=item.name,
                        description=item.description,
                        technologies=item.technologies,
                        sort_order=i,
                        source=SourceType.USER,
                        verified=item.verified,
                    )
                    for i, item in enumerate(payload.projects)
                ],
            )

        if payload.education_entries is not None:
            self.repo.replace_education(
                resume,
                [
                    Education(
                        institution=item.institution,
                        degree=item.degree,
                        field_of_study=item.field_of_study,
                        start_date=item.start_date,
                        end_date=item.end_date,
                        sort_order=i,
                        source=SourceType.USER,
                        verified=item.verified,
                    )
                    for i, item in enumerate(payload.education_entries)
                ],
            )

        if payload.certifications is not None:
            self.repo.replace_certifications(
                resume,
                [
                    Certification(
                        name=item.name,
                        issuer=item.issuer,
                        issue_date=item.issue_date,
                        source=SourceType.USER,
                        verified=item.verified,
                    )
                    for item in payload.certifications
                ],
            )

        # Editing a needs_review resume with real content promotes it to
        # parsed, since the user has now supplied the data manually.
        if resume.status == ResumeStatus.NEEDS_REVIEW and (
            resume.full_name or resume.skills or resume.experiences
        ):
            resume.status = ResumeStatus.PARSED

        return self.repo.save(resume)

    # --- Verification --------------------------------------------------------

    def verify_resume(self, resume_id: str) -> Resume:
        """Mark a resume's profile as verified by the user.

        This is the only state transition that makes a resume eligible
        to be used as input to matching/tailoring in a later sprint.
        """
        resume = self.get_resume(resume_id)

        if resume.status == ResumeStatus.UPLOADED:
            raise ResumeVerificationError(
                "This resume hasn't been parsed yet and cannot be verified."
            )
        if resume.status == ResumeStatus.VERIFIED:
            return resume

        resume.status = ResumeStatus.VERIFIED
        resume.verified_at = datetime.now(timezone.utc)
        return self.repo.save(resume)

    def assert_verified(self, resume_id: str) -> Resume:
        """Helper for future sprints (matching/tailoring): raises unless
        the resume is verified. Not used by any route in this sprint."""
        resume = self.get_resume(resume_id)
        if resume.status != ResumeStatus.VERIFIED:
            raise ResumeVerificationError(
                "This resume profile has not been verified yet. Verify it "
                "before using it for matching or tailoring."
            )
        return resume
