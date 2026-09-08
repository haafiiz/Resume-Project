"""
Transparent, deterministic match scoring.

Scoring is pure arithmetic over already-computed match confidences - no
LLM, no hidden heuristics. Given the same set of per-requirement match
confidences and the same weights, the score is always identical
(reproducibility). Every number that goes into the final score is
retained on the result, so a score can always be explained by pointing
at exactly which requirements contributed what.

## The six scoring categories

The spec's initial weighting names six categories:

    Required Skills       50%
    Responsibilities      25%
    Experience            10%
    Education              5%
    Preferred Skills       5%
    Keywords               5%

JD requirements are extracted into nine `requirement_type` values (see
app/models/job_description.py), three more than the six weighted
categories above. The three extra types are folded into a weighted
category as follows - this is a deliberate, documented interpretive
choice (see docs/matching-engine.md for the full rationale), not an
arbitrary default:

    technology    -> required_skills   (a required tool/tech is treated
                                          the same as a required skill)
    domain        -> keywords          (domain expertise is assessed the
                                          same way generic keyword
                                          coverage is - contextual
                                          presence in the resume)
    soft_skill    -> keywords          (same reasoning as domain)

## Category score formula

For a given category, let R be the set of JD requirements folded into
it. If R is empty, the category score is 1.0 - see `EMPTY_CATEGORY_SCORE`
below for why. Otherwise:

    category_score = (sum of each requirement's best-match confidence) / len(R)

This is confidence-weighted, not a binary matched/not-matched count:
a `partial` match contributes 0.4, not a full 1.0 or a full 0 - so the
score reflects the quality of the match, not just its presence.

## Overall score

    overall_score = sum(weight[category] * category_score[category] for category in categories) * 100

Expressed as a 0-100 percentage. Weights must sum to 1.0 (validated by
MatchWeights).
"""

from dataclasses import dataclass

# Category keys used throughout the scoring/matching pipeline. These are
# the six weighted buckets from the spec.
REQUIRED_SKILLS = "required_skills"
RESPONSIBILITIES = "responsibilities"
EXPERIENCE = "experience"
EDUCATION = "education"
PREFERRED_SKILLS = "preferred_skills"
KEYWORDS = "keywords"

ALL_CATEGORIES: tuple[str, ...] = (
    REQUIRED_SKILLS,
    RESPONSIBILITIES,
    EXPERIENCE,
    EDUCATION,
    PREFERRED_SKILLS,
    KEYWORDS,
)

# Maps every JD requirement_type (plain string value - see the note
# below) to the scoring category it feeds into. See the module
# docstring for the rationale behind folding `technology`, `domain`, and
# `soft_skill` into existing categories.
#
# Deliberately keyed by plain strings rather than importing
# app.models.job_description.RequirementType: core/matching is pure
# business logic and must not depend on the ORM layer, mirroring the
# same separation core/ai/schemas.py established in Sprint 3 (its own
# RequirementType enum, independent of the DB model's). The service
# layer is responsible for translating ORM enum values to/from these
# plain strings at the boundary.
CATEGORY_BY_REQUIREMENT_TYPE: dict[str, str] = {
    "required_skill": REQUIRED_SKILLS,
    "technology": REQUIRED_SKILLS,
    "preferred_skill": PREFERRED_SKILLS,
    "responsibility": RESPONSIBILITIES,
    "experience": EXPERIENCE,
    "education": EDUCATION,
    "keyword": KEYWORDS,
    "domain": KEYWORDS,
    "soft_skill": KEYWORDS,
}

# A category with zero JD requirements contributes a neutral "full
# marks" score rather than zero. Rationale: an empty category means the
# JD made no ask in that area, so there is nothing for the candidate to
# be missing - scoring it as 0 would incorrectly punish the candidate
# for a gap the JD itself never specified. This is a deliberate,
# documented choice (see docs/matching-engine.md), not an accident of
# division-by-zero handling.
EMPTY_CATEGORY_SCORE = 1.0


@dataclass(frozen=True)
class MatchWeights:
    """Configurable category weights. Must sum to 1.0."""

    required_skills: float = 0.50
    responsibilities: float = 0.25
    experience: float = 0.10
    education: float = 0.05
    preferred_skills: float = 0.05
    keywords: float = 0.05

    def as_dict(self) -> dict[str, float]:
        return {
            REQUIRED_SKILLS: self.required_skills,
            RESPONSIBILITIES: self.responsibilities,
            EXPERIENCE: self.experience,
            EDUCATION: self.education,
            PREFERRED_SKILLS: self.preferred_skills,
            KEYWORDS: self.keywords,
        }

    def validate(self, tolerance: float = 1e-6) -> None:
        total = sum(self.as_dict().values())
        if abs(total - 1.0) > tolerance:
            raise ValueError(
                f"Match weights must sum to 1.0, got {total} ({self.as_dict()})"
            )


DEFAULT_WEIGHTS = MatchWeights()


@dataclass(frozen=True)
class CategoryScore:
    category: str
    weight: float
    requirement_count: int
    score: float  # 0.0 - 1.0, average confidence across requirements (or EMPTY_CATEGORY_SCORE)
    weighted_contribution: float  # weight * score, in [0, weight] - this category's slice of the overall score


@dataclass(frozen=True)
class ScoreResult:
    overall_score: float  # 0-100
    category_scores: dict[str, CategoryScore]
    weights: MatchWeights


def score_category(confidences: list[float]) -> float:
    """Average confidence across a category's requirements, or the
    neutral empty-category score if there are none."""
    if not confidences:
        return EMPTY_CATEGORY_SCORE
    return sum(confidences) / len(confidences)


def compute_score(
    confidences_by_category: dict[str, list[float]],
    weights: MatchWeights = DEFAULT_WEIGHTS,
) -> ScoreResult:
    """Compute the full weighted score from per-category lists of
    per-requirement match confidences.

    `confidences_by_category` should have one entry per category in
    ALL_CATEGORIES; a missing or empty list is treated as "no
    requirements in this category" (see EMPTY_CATEGORY_SCORE).
    """
    weights.validate()
    weight_map = weights.as_dict()

    category_scores: dict[str, CategoryScore] = {}
    overall = 0.0

    for category in ALL_CATEGORIES:
        confidences = confidences_by_category.get(category, [])
        score = score_category(confidences)
        weight = weight_map[category]
        contribution = weight * score
        overall += contribution

        category_scores[category] = CategoryScore(
            category=category,
            weight=weight,
            requirement_count=len(confidences),
            score=score,
            weighted_contribution=contribution,
        )

    return ScoreResult(
        overall_score=round(overall * 100, 2),
        category_scores=category_scores,
        weights=weights,
    )
