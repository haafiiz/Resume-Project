"""
Deterministic skill matching.

Classifies how well a set of resume skills satisfies a single JD
requirement, with a fixed, explainable rule ladder - no LLM involved, no
fuzzy/statistical similarity scoring. Every classification traces back
to an explicit rule, which is what makes results reproducible: the same
resume and JD will always produce the same matches.

Match types, in descending confidence order:
    exact       - the resume skill's raw name is identical to the
                  requirement's raw name (case-insensitive)
    normalized   - not identical, but equivalent after normalization
                    (e.g. "REST APIs" vs "RESTful API")
    related       - different terms, but explicitly known to be in the
                     same family (e.g. a specific SQL dialect vs "SQL")
    partial        - meaningful word-token overlap without either being
                       a formatting/synonym variant of the other (e.g.
                       "AWS" vs "AWS Lambda")
    missing         - no resume skill satisfies the requirement at all
    unknown          - the requirement or every candidate skill has no
                        usable name to compare (defensive fallback;
                        should not occur with valid data)

CRITICAL RULE (see also normalizer.py's docstring): nothing here is ever
allowed to turn a JD requirement the resume doesn't have into a match.
If no rule fires, the requirement is `missing` - full stop. This module
has no mechanism to invent or assume a skill exists.
"""

import enum
from dataclasses import dataclass

from app.core.matching.normalizer import normalize_skill_name, tokenize
from app.core.matching.scorer import CATEGORY_BY_REQUIREMENT_TYPE

# A conservative set of explicitly-related-but-not-equivalent term
# groups. Membership in the same group produces a `related` match at
# reduced confidence - it never produces `exact` or `normalized`.
# Deliberately small and deliberately does NOT include genuinely
# different technologies that are merely often compared (Java/
# JavaScript, Selenium/Playwright, AWS/Azure, React/Angular, etc.).
RELATED_GROUPS: list[frozenset[str]] = [
    frozenset({"sql", "mysql", "postgresql", "sql server", "oracle sql", "sqlite", "mariadb"}),
    frozenset({"ci cd", "jenkins", "github actions", "gitlab ci", "circleci", "travis ci"}),
    frozenset({"nosql", "mongodb", "dynamodb", "cassandra", "couchdb"}),
]

_RELATED_GROUP_BY_TERM: dict[str, frozenset[str]] = {
    term: group for group in RELATED_GROUPS for term in group
}


class MatchType(str, enum.Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    RELATED = "related"
    PARTIAL = "partial"
    MISSING = "missing"
    UNKNOWN = "unknown"


# Fixed, documented confidence value per match type. These are constants
# (not tunable weights) - they express how much a given *kind* of match
# should be trusted, which is a matching-engine concern, whereas the
# scoring *weights* in scorer.py are a business/product concern.
CONFIDENCE_BY_MATCH_TYPE: dict[MatchType, float] = {
    MatchType.EXACT: 1.0,
    MatchType.NORMALIZED: 0.9,
    MatchType.RELATED: 0.6,
    MatchType.PARTIAL: 0.4,
    MatchType.MISSING: 0.0,
    MatchType.UNKNOWN: 0.0,
}


@dataclass(frozen=True)
class SkillRef:
    """A minimal, ORM-independent reference to a resume skill. Keeping
    core/matching free of SQLAlchemy imports is deliberate - it's pure
    business logic, and the service layer is responsible for converting
    ORM rows into these before calling in, and matching results back
    into ORM rows afterward."""

    id: str
    name: str


@dataclass(frozen=True)
class TextRef:
    """A minimal, ORM-independent reference to a piece of resume text
    used for freetext category matching (responsibilities, experience,
    education, domain, keywords, soft skills) - e.g. one experience
    entry's description, one education entry's degree line."""

    id: str
    label: str  # human-readable, e.g. "Experience: Senior Engineer at Acme Corp"
    text: str


@dataclass(frozen=True)
class SkillMatchOutcome:
    match_type: MatchType
    confidence: float
    explanation: str
    matched_skill: SkillRef | None = None
    matched_text: TextRef | None = None


def _best_pairwise_match(requirement_name: str, skill: SkillRef) -> SkillMatchOutcome | None:
    """Classify how well a single resume skill satisfies a requirement
    name. Returns None if there's no match of any kind (caller treats
    that as this particular skill not contributing)."""

    req_raw = requirement_name.strip()
    skill_raw = skill.name.strip()

    if not req_raw or not skill_raw:
        return SkillMatchOutcome(
            match_type=MatchType.UNKNOWN,
            confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.UNKNOWN],
            explanation="Could not compare - one of the names is empty.",
            matched_skill=skill,
        )

    # 1. Exact: identical raw text, case-insensitive.
    if req_raw.casefold() == skill_raw.casefold():
        return SkillMatchOutcome(
            match_type=MatchType.EXACT,
            confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.EXACT],
            explanation=f"Resume skill '{skill.name}' exactly matches the requirement '{requirement_name}'.",
            matched_skill=skill,
        )

    req_norm = normalize_skill_name(req_raw)
    skill_norm = normalize_skill_name(skill_raw)

    # 2. Normalized: equal only after normalization (known formatting
    # variant via the explicit alias table).
    if req_norm == skill_norm:
        return SkillMatchOutcome(
            match_type=MatchType.NORMALIZED,
            confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.NORMALIZED],
            explanation=(
                f"Resume skill '{skill.name}' is a formatting variant of the "
                f"requirement '{requirement_name}' (both normalize to '{req_norm}')."
            ),
            matched_skill=skill,
        )

    # 3. Related: different normalized terms, but both belong to the
    # same explicitly-declared related-terms group.
    req_group = _RELATED_GROUP_BY_TERM.get(req_norm)
    skill_group = _RELATED_GROUP_BY_TERM.get(skill_norm)
    if req_group is not None and req_group is skill_group:
        return SkillMatchOutcome(
            match_type=MatchType.RELATED,
            confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.RELATED],
            explanation=(
                f"Resume skill '{skill.name}' is related to but not identical to "
                f"the requirement '{requirement_name}' (both are '{req_norm}'-family terms)."
            ),
            matched_skill=skill,
        )

    # 4. Partial: meaningful whole-word token overlap, without either
    # term being empty. Token-based (never substring-based) specifically
    # so "java" can never match inside "javascript".
    req_tokens = tokenize(req_raw)
    skill_tokens = tokenize(skill_raw)
    shared = req_tokens & skill_tokens
    if shared and (req_tokens <= skill_tokens or skill_tokens <= req_tokens) and req_tokens != skill_tokens:
        broader, narrower = (
            (skill_raw, req_raw) if len(skill_tokens) > len(req_tokens) else (req_raw, skill_raw)
        )
        return SkillMatchOutcome(
            match_type=MatchType.PARTIAL,
            confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.PARTIAL],
            explanation=(
                f"Resume skill '{skill.name}' partially overlaps with the requirement "
                f"'{requirement_name}' ('{narrower}' is a narrower/broader term within '{broader}')."
            ),
            matched_skill=skill,
        )

    return None


def match_requirement_against_skills(
    requirement_name: str, skills: list[SkillRef]
) -> SkillMatchOutcome:
    """Find the best match for a single JD requirement across all of the
    candidate's verified resume skills.

    Deterministic tie-breaking: candidates are considered in a fixed
    order (sorted by normalized name, then raw name, then id) so the
    result never depends on database row order or insertion order -
    required for the "reproducible" guarantee.
    """
    if not requirement_name.strip():
        return SkillMatchOutcome(
            match_type=MatchType.UNKNOWN,
            confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.UNKNOWN],
            explanation="The requirement has no name to compare against.",
        )

    ordered_skills = sorted(
        skills, key=lambda s: (normalize_skill_name(s.name), s.name.casefold(), s.id)
    )

    best: SkillMatchOutcome | None = None
    rank = {
        MatchType.EXACT: 0,
        MatchType.NORMALIZED: 1,
        MatchType.RELATED: 2,
        MatchType.PARTIAL: 3,
        MatchType.UNKNOWN: 4,
        MatchType.MISSING: 5,
    }

    for skill in ordered_skills:
        outcome = _best_pairwise_match(requirement_name, skill)
        if outcome is None:
            continue
        if best is None or rank[outcome.match_type] < rank[best.match_type]:
            best = outcome
        if best.match_type == MatchType.EXACT:
            break  # can't do better than exact

    if best is not None:
        return best

    return SkillMatchOutcome(
        match_type=MatchType.MISSING,
        confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.MISSING],
        explanation=(
            f"No matching skill for '{requirement_name}' was found in the verified "
            "resume profile."
        ),
    )


# --- Freetext category matching ---------------------------------------------
#
# For requirement types that aren't a flat skill name (responsibilities,
# experience, education, domain, keywords, soft skills), the comparison
# is against prose - a JD requirement like "5+ years of QA automation
# experience" has no single equivalent "skill" on the resume side, only
# passages of text that may or may not cover it. This uses a coarser,
# explicitly-scoped subset of the match taxonomy: normalized (full
# coverage), partial (some coverage), or missing (none) - `exact` and
# `related` aren't meaningful comparisons between prose and prose, so
# they're never produced here.

_FULL_COVERAGE_CONFIDENCE = CONFIDENCE_BY_MATCH_TYPE[MatchType.NORMALIZED]
_PARTIAL_COVERAGE_THRESHOLD = 0.5


def match_requirement_against_text(
    requirement_name: str, candidates: list[TextRef]
) -> SkillMatchOutcome:
    """Classify how well a JD requirement (responsibility, experience,
    education, domain, keyword, or soft-skill) is covered by resume
    freetext, using whole-word token overlap.

    Deterministic tie-breaking: candidates are considered in a fixed
    order (sorted by id) and the single best-covering candidate is kept,
    the same way match_requirement_against_skills is order-independent.
    """
    req_tokens = tokenize(requirement_name)
    if not req_tokens:
        return SkillMatchOutcome(
            match_type=MatchType.UNKNOWN,
            confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.UNKNOWN],
            explanation="The requirement has no meaningful words to compare against.",
        )

    best_ratio = 0.0
    best_candidate: TextRef | None = None
    best_shared: set[str] = set()

    for candidate in sorted(candidates, key=lambda c: c.id):
        candidate_tokens = tokenize(candidate.text)
        shared = req_tokens & candidate_tokens
        ratio = len(shared) / len(req_tokens)
        if ratio > best_ratio:
            best_ratio = ratio
            best_candidate = candidate
            best_shared = shared

    if best_candidate is None or best_ratio <= 0:
        return SkillMatchOutcome(
            match_type=MatchType.MISSING,
            confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.MISSING],
            explanation=(
                f"No part of the verified resume appears to cover '{requirement_name}'."
            ),
        )

    if best_ratio >= 1.0:
        return SkillMatchOutcome(
            match_type=MatchType.NORMALIZED,
            confidence=_FULL_COVERAGE_CONFIDENCE,
            explanation=(
                f"'{best_candidate.label}' covers all the key terms in "
                f"'{requirement_name}' ({', '.join(sorted(best_shared))})."
            ),
            matched_text=best_candidate,
        )

    if best_ratio >= _PARTIAL_COVERAGE_THRESHOLD:
        return SkillMatchOutcome(
            match_type=MatchType.PARTIAL,
            confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.PARTIAL],
            explanation=(
                f"'{best_candidate.label}' partially covers '{requirement_name}' "
                f"(matched: {', '.join(sorted(best_shared))})."
            ),
            matched_text=best_candidate,
        )

    return SkillMatchOutcome(
        match_type=MatchType.MISSING,
        confidence=CONFIDENCE_BY_MATCH_TYPE[MatchType.MISSING],
        explanation=(
            f"No part of the verified resume sufficiently covers '{requirement_name}' "
            f"(best overlap was only {', '.join(sorted(best_shared)) or 'none'})."
        ),
    )


# --- Full-analysis orchestration --------------------------------------------
#
# Ties a JD's requirements to a resume's data one requirement at a time,
# routing each requirement to skill-matching or freetext-matching based
# on its type. This is the single entry point the service layer calls -
# everything above is composable building blocks; this is "run the
# whole analysis."


@dataclass(frozen=True)
class RequirementRef:
    """A minimal, ORM-independent reference to a JD requirement.
    `requirement_type` is a plain string (one of the nine values defined
    on app.models.job_description.RequirementType) - see the note on
    CATEGORY_BY_REQUIREMENT_TYPE in scorer.py for why this module never
    imports the ORM enum directly."""

    id: str
    requirement_type: str
    name: str
    importance: str


@dataclass(frozen=True)
class ResumeProfileForMatching:
    """Everything the matching engine needs from a verified resume,
    already flattened into plain, ORM-independent shapes. Built by the
    service layer from the actual Resume ORM object."""

    skills: list[SkillRef]
    # Candidate text passages per freetext category. Callers decide what
    # belongs in each - typically: responsibilities <- experience
    # descriptions and project descriptions; experience <- experience
    # entries (title/company/description); education <- education
    # entries; keywords (also used for domain and soft_skill
    # requirement types) <- a broad corpus spanning summary, skills,
    # experience, projects, education, and certifications.
    responsibility_candidates: list[TextRef]
    experience_candidates: list[TextRef]
    education_candidates: list[TextRef]
    keyword_candidates: list[TextRef]


@dataclass(frozen=True)
class RequirementMatchResult:
    requirement: RequirementRef
    scoring_category: str
    outcome: SkillMatchOutcome


# requirement_type values that are matched against the resume's Skill
# table rather than freetext.
_SKILL_TABLE_REQUIREMENT_TYPES = frozenset({"required_skill", "preferred_skill", "technology"})


def _freetext_candidates_for(
    requirement_type: str, profile: ResumeProfileForMatching
) -> list[TextRef]:
    if requirement_type == "responsibility":
        return profile.responsibility_candidates
    if requirement_type == "experience":
        return profile.experience_candidates
    if requirement_type == "education":
        return profile.education_candidates
    # keyword, domain, soft_skill all draw from the broad corpus.
    return profile.keyword_candidates


def analyze_requirements(
    requirements: list[RequirementRef], profile: ResumeProfileForMatching
) -> list[RequirementMatchResult]:
    """Match every JD requirement against the verified resume profile.

    Requirements are processed independently and in the order given -
    the result for one requirement never depends on another, which is
    part of what keeps the whole analysis reproducible.
    """
    results: list[RequirementMatchResult] = []

    for requirement in requirements:
        category = CATEGORY_BY_REQUIREMENT_TYPE.get(requirement.requirement_type)

        if requirement.requirement_type in _SKILL_TABLE_REQUIREMENT_TYPES:
            outcome = match_requirement_against_skills(requirement.name, profile.skills)
        else:
            candidates = _freetext_candidates_for(requirement.requirement_type, profile)
            outcome = match_requirement_against_text(requirement.name, candidates)

        results.append(
            RequirementMatchResult(
                requirement=requirement,
                # Fall back to "keywords" for any requirement_type this
                # module doesn't recognize, rather than raising or
                # silently dropping it - keeps analysis total even if
                # the JD domain gains a new type in the future before
                # this mapping is updated.
                scoring_category=category or "keywords",
                outcome=outcome,
            )
        )

    return results
