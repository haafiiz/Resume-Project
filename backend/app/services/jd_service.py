"""
Job description service.

Orchestrates the JD save -> extract -> review -> verify flow. Mirrors
app/services/resume_service.py's structure and rules. This is where
core/ai/jd_extraction, utils/text_normalization, and the repository are
wired together - API routes stay thin and just call into here.

Crucially, this module depends only on the generic AIProvider interface
(injected via the constructor, defaulting to the configured provider
from core/ai/factory.py) - it never imports OllamaProvider directly, so
swapping providers later never requires touching this file.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.ai.base import AIProvider, AIProviderResponseError, AIProviderUnavailableError
from app.core.ai.factory import get_ai_provider
from app.core.ai.jd_extraction import extract_requirements
from app.models.job_description import JDRequirement, JobDescription, JobDescriptionStatus
from app.repositories.jd_repository import JDRepository
from app.schemas.job_description import JobDescriptionCreateRequest, JobDescriptionUpdateRequest
from app.utils.text_normalization import normalize_name


class JobDescriptionNotFoundError(LookupError):
    pass


class JobDescriptionVerificationError(ValueError):
    """Raised when an action requires a JD to be (or not be) verified
    and it isn't in the required state."""


class JDService:
    def __init__(self, db: Session, ai_provider: AIProvider | None = None):
        self.db = db
        self.repo = JDRepository(db)
        # Resolved lazily via the factory only if not injected, so a
        # provider is never constructed unless extraction is actually
        # requested (e.g. plain create/list/get calls never touch AI).
        self._ai_provider = ai_provider

    def _get_ai_provider(self) -> AIProvider:
        if self._ai_provider is None:
            self._ai_provider = get_ai_provider()
        return self._ai_provider

    # --- Create -------------------------------------------------------------

    def create(self, payload: JobDescriptionCreateRequest) -> JobDescription:
        """Save a job description. Does not run extraction - that's a
        separate, explicit step (extract_requirements_for) so the user
        can save now and extract when ready (or retry extraction without
        re-pasting the JD if the AI provider was unavailable)."""
        job_description = JobDescription(
            title=payload.title,
            company=payload.company,
            description=payload.description,
            status=JobDescriptionStatus.CREATED,
        )
        return self.repo.create(job_description)

    # --- Reads --------------------------------------------------------------

    def list_job_descriptions(self) -> list[JobDescription]:
        return self.repo.list_all()

    def get_job_description(self, job_description_id: str) -> JobDescription:
        job_description = self.repo.get(job_description_id)
        if job_description is None:
            raise JobDescriptionNotFoundError(job_description_id)
        return job_description

    # --- Extraction -----------------------------------------------------------

    def extract_requirements_for(self, job_description_id: str) -> JobDescription:
        """Run AI-based requirement extraction against the saved
        description and persist the results.

        Never raises on an AI failure - a provider being unreachable or
        returning something unusable is an expected, recoverable
        situation (the JD is still saved; the user can retry, or add
        requirements manually), so it's reflected in `status` /
        `extraction_error` rather than surfaced as a request failure.
        """
        job_description = self.get_job_description(job_description_id)

        if job_description.status == JobDescriptionStatus.VERIFIED:
            raise JobDescriptionVerificationError(
                "This job description is already verified. Extraction can "
                "no longer be re-run once verified."
            )

        try:
            provider = self._get_ai_provider()
            result = extract_requirements(provider, job_description.description)
        except AIProviderUnavailableError as exc:
            job_description.status = JobDescriptionStatus.NEEDS_REVIEW
            job_description.extraction_error = (
                f"The AI extraction service is currently unavailable: {exc} "
                "You can retry extraction later, or add requirements manually."
            )
            return self.repo.save(job_description)
        except AIProviderResponseError as exc:
            job_description.status = JobDescriptionStatus.NEEDS_REVIEW
            job_description.extraction_error = (
                f"The AI extraction service returned an unusable response: {exc} "
                "You can retry extraction later, or add requirements manually."
            )
            return self.repo.save(job_description)

        requirements = [
            JDRequirement(
                requirement_type=item.requirement_type,
                name=item.name,
                normalized_name=normalize_name(item.name),
                importance=item.importance,
                description=item.description,
                source_text=item.source_text,
                sort_order=i,
                verified=False,
            )
            for i, item in enumerate(result.requirements)
        ]
        self.repo.replace_requirements(job_description, requirements)

        job_description.status = (
            JobDescriptionStatus.EXTRACTED if requirements else JobDescriptionStatus.NEEDS_REVIEW
        )
        job_description.extraction_error = (
            None
            if requirements
            else "Extraction completed but found no identifiable requirements in this "
            "job description. You can add requirements manually."
        )

        return self.repo.save(job_description)

    # --- Update / correction --------------------------------------------

    def update_job_description(
        self, job_description_id: str, payload: JobDescriptionUpdateRequest
    ) -> JobDescription:
        job_description = self.get_job_description(job_description_id)

        if job_description.status == JobDescriptionStatus.VERIFIED:
            raise JobDescriptionVerificationError(
                "This job description is already verified. Corrections can "
                "no longer be made through this endpoint once verified."
            )

        if payload.title is not None:
            job_description.title = payload.title
        if payload.company is not None:
            job_description.company = payload.company
        if payload.description is not None:
            job_description.description = payload.description

        if payload.requirements is not None:
            self.repo.replace_requirements(
                job_description,
                [
                    JDRequirement(
                        requirement_type=item.requirement_type,
                        name=item.name,
                        normalized_name=normalize_name(item.name),
                        importance=item.importance,
                        description=item.description,
                        source_text=item.source_text,
                        sort_order=i,
                        verified=item.verified,
                    )
                    for i, item in enumerate(payload.requirements)
                ],
            )

            # Editing a not-yet-extracted (or failed-extraction) JD with
            # real requirements promotes it to extracted, since the user
            # has now supplied what the AI hasn't (or couldn't) - mirrors
            # the resume domain's equivalent rule.
            if (
                job_description.status in (
                    JobDescriptionStatus.CREATED,
                    JobDescriptionStatus.NEEDS_REVIEW,
                )
                and job_description.requirements
            ):
                job_description.status = JobDescriptionStatus.EXTRACTED
                job_description.extraction_error = None

        return self.repo.save(job_description)

    # --- Verification --------------------------------------------------------

    def verify_job_description(self, job_description_id: str) -> JobDescription:
        job_description = self.get_job_description(job_description_id)

        if job_description.status == JobDescriptionStatus.CREATED:
            raise JobDescriptionVerificationError(
                "This job description hasn't been extracted yet and cannot "
                "be verified. Run extraction, or add requirements manually, first."
            )
        if job_description.status == JobDescriptionStatus.VERIFIED:
            return job_description

        job_description.status = JobDescriptionStatus.VERIFIED
        job_description.verified_at = datetime.now(timezone.utc)
        return self.repo.save(job_description)

    def assert_verified(self, job_description_id: str) -> JobDescription:
        """Helper for a future sprint (matching): raises unless the JD is
        verified. Not used by any route in this sprint."""
        job_description = self.get_job_description(job_description_id)
        if job_description.status != JobDescriptionStatus.VERIFIED:
            raise JobDescriptionVerificationError(
                "This job description has not been verified yet. Verify it "
                "before using it for matching."
            )
        return job_description
