"""
Analysis service.

Orchestrates the matching engine against a specific (resume, job
description) pair: fetches both (requiring both to be verified - see
the critical rule below), converts them into the plain, ORM-independent
shapes core/matching operates on, runs the engine, and persists the
result as an Analysis with its SkillMatch rows.

CRITICAL RULE (enforced here, not just documented): a skill that appears
in the JD but not in the verified resume is *always* classified as
`missing` by the matching engine (see core/matching/matcher.py) - this
service never adds, infers, or "fills in" a skill on the resume side to
make a match. It only ever reads the resume/JD as already verified by
the user.
"""

import json

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.matching.matcher import (
    RequirementMatchResult,
    RequirementRef,
    ResumeProfileForMatching,
    SkillRef,
    TextRef,
    analyze_requirements,
)
from app.core.matching.scorer import ALL_CATEGORIES, MatchWeights, compute_score
from app.models.analysis import Analysis, SkillMatch
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.repositories.analysis_repository import AnalysisRepository
from app.services.jd_service import JDService
from app.services.jd_service import JobDescriptionVerificationError as _JDNotVerifiedError
from app.services.resume_service import ResumeService
from app.services.resume_service import ResumeVerificationError as _ResumeNotVerifiedError


class AnalysisNotFoundError(LookupError):
    pass


class AnalysisInputNotVerifiedError(ValueError):
    """Raised when either the resume or the job description used to
    request an analysis is not verified. Matching is only ever run
    against confirmed, truth-constrained data - never a draft."""


def get_default_weights() -> MatchWeights:
    settings = get_settings()
    return MatchWeights(
        required_skills=settings.match_weight_required_skills,
        responsibilities=settings.match_weight_responsibilities,
        experience=settings.match_weight_experience,
        education=settings.match_weight_education,
        preferred_skills=settings.match_weight_preferred_skills,
        keywords=settings.match_weight_keywords,
    )


def _build_resume_profile(resume: Resume) -> ResumeProfileForMatching:
    """Flatten a verified Resume ORM object into the plain shapes
    core/matching operates on. This is the only place resume data is
    read for matching purposes - it never writes back to the resume."""

    skills = [SkillRef(id=s.id, name=s.name) for s in resume.skills]

    experience_candidates = [
        TextRef(
            id=exp.id,
            label=f"Experience: {exp.job_title or 'Untitled role'}"
            + (f" at {exp.company}" if exp.company else ""),
            text=" ".join(filter(None, [exp.job_title, exp.company, exp.description])),
        )
        for exp in resume.experiences
    ]

    # Responsibilities are things the candidate *did* - experience and
    # project descriptions are the natural corpus.
    responsibility_candidates = list(experience_candidates) + [
        TextRef(
            id=proj.id,
            label=f"Project: {proj.name or 'Untitled project'}",
            text=" ".join(filter(None, [proj.name, proj.description, proj.technologies])),
        )
        for proj in resume.projects
    ]

    education_candidates = [
        TextRef(
            id=edu.id,
            label=f"Education: {edu.degree or 'Untitled credential'}"
            + (f" at {edu.institution}" if edu.institution else ""),
            text=" ".join(filter(None, [edu.degree, edu.field_of_study, edu.institution])),
        )
        for edu in resume.education_entries
    ]

    # Broad corpus for keyword/domain/soft_skill requirement types -
    # spans everything on the profile so contextual mentions anywhere
    # count.
    keyword_candidates: list[TextRef] = []
    if resume.summary:
        keyword_candidates.append(TextRef(id="summary", label="Summary", text=resume.summary))
    keyword_candidates += [TextRef(id=s.id, label="Skill", text=s.name) for s in resume.skills]
    keyword_candidates += experience_candidates
    keyword_candidates += responsibility_candidates
    keyword_candidates += education_candidates
    keyword_candidates += [
        TextRef(
            id=cert.id,
            label=f"Certification: {cert.name}",
            text=" ".join(filter(None, [cert.name, cert.issuer])),
        )
        for cert in resume.certifications
    ]

    return ResumeProfileForMatching(
        skills=skills,
        responsibility_candidates=responsibility_candidates,
        experience_candidates=experience_candidates,
        education_candidates=education_candidates,
        keyword_candidates=keyword_candidates,
    )


def _build_requirement_refs(job_description: JobDescription) -> list[RequirementRef]:
    return [
        RequirementRef(
            id=req.id,
            requirement_type=req.requirement_type.value,
            name=req.name,
            importance=req.importance.value,
        )
        for req in job_description.requirements
    ]


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalysisRepository(db)
        self.resume_service = ResumeService(db)
        self.jd_service = JDService(db)

    def create_analysis(
        self, resume_id: str, job_description_id: str, weights: MatchWeights | None = None
    ) -> Analysis:
        """Run the matching engine and persist the result.

        Both the resume and the job description must already be
        verified - this is the platform's core truth-constraint applied
        at the matching stage: only confirmed data is ever compared.
        """
        try:
            resume = self.resume_service.assert_verified(resume_id)
        except _ResumeNotVerifiedError as exc:
            raise AnalysisInputNotVerifiedError(
                f"Resume {resume_id} is not verified. Verify the resume profile "
                "before running an analysis."
            ) from exc

        try:
            job_description = self.jd_service.assert_verified(job_description_id)
        except _JDNotVerifiedError as exc:
            raise AnalysisInputNotVerifiedError(
                f"Job description {job_description_id} is not verified. Verify "
                "its requirements before running an analysis."
            ) from exc

        resolved_weights = weights or get_default_weights()

        profile = _build_resume_profile(resume)
        requirement_refs = _build_requirement_refs(job_description)
        match_results = analyze_requirements(requirement_refs, profile)

        confidences_by_category: dict[str, list[float]] = {c: [] for c in ALL_CATEGORIES}
        for result in match_results:
            confidences_by_category[result.scoring_category].append(result.outcome.confidence)

        score_result = compute_score(confidences_by_category, resolved_weights)

        analysis = Analysis(
            resume_id=resume_id,
            job_description_id=job_description_id,
            overall_score=score_result.overall_score,
            required_skills_score=round(
                score_result.category_scores["required_skills"].score * 100, 2
            ),
            responsibilities_score=round(
                score_result.category_scores["responsibilities"].score * 100, 2
            ),
            experience_score=round(score_result.category_scores["experience"].score * 100, 2),
            education_score=round(score_result.category_scores["education"].score * 100, 2),
            preferred_skills_score=round(
                score_result.category_scores["preferred_skills"].score * 100, 2
            ),
            keywords_score=round(score_result.category_scores["keywords"].score * 100, 2),
            weights_snapshot=json.dumps(
                {
                    "weights": resolved_weights.as_dict(),
                    "category_breakdown": {
                        category: {
                            "weight": cs.weight,
                            "requirement_count": cs.requirement_count,
                            "score": cs.score,
                            "weighted_contribution": cs.weighted_contribution,
                        }
                        for category, cs in score_result.category_scores.items()
                    },
                }
            ),
        )

        matches = [
            self._build_skill_match_row(result, index)
            for index, result in enumerate(match_results)
        ]

        return self.repo.create(analysis, matches)

    def _build_skill_match_row(
        self, result: RequirementMatchResult, sort_order: int
    ) -> SkillMatch:
        outcome = result.outcome
        return SkillMatch(
            jd_requirement_id=result.requirement.id,
            resume_skill_id=outcome.matched_skill.id if outcome.matched_skill else None,
            matched_resume_label=outcome.matched_text.label if outcome.matched_text else None,
            matched_resume_text=outcome.matched_text.text if outcome.matched_text else None,
            match_type=outcome.match_type,
            confidence=outcome.confidence,
            explanation=outcome.explanation,
            requirement_type=result.requirement.requirement_type,
            requirement_name=result.requirement.name,
            scoring_category=result.scoring_category,
            sort_order=sort_order,
        )

    def get_analysis(self, analysis_id: str) -> Analysis:
        analysis = self.repo.get(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError(analysis_id)
        return analysis

    def get_extra_resume_skills(self, analysis: Analysis) -> list[str]:
        """Resume skills that matched no JD requirement in this
        analysis - informational only, never scored."""
        resume = self.resume_service.get_resume(analysis.resume_id)
        matched_skill_ids = {
            match.resume_skill_id for match in analysis.matches if match.resume_skill_id
        }
        return sorted(skill.name for skill in resume.skills if skill.id not in matched_skill_ids)
