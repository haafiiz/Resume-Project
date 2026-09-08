# Matching Engine

This document covers `core/matching/` — the deterministic engine that
compares a verified resume against a verified job description and
produces a transparent, reproducible match score. Implemented in
Sprint 4.

## Why deterministic, not AI-scored

The matching engine **never calls an LLM**. Given the same resume and
JD, it always produces the same score, the same matches, and the same
explanations - every run is byte-for-byte reproducible. This is a
direct consequence of the platform's core truth constraint: a score
that could vary between runs, or that came from a model's internal
judgment rather than an inspectable rule, couldn't be trusted as
evidence of anything. Every classification in this document traces back
to an explicit, testable rule.

## Module layout

```
core/matching/
├── normalizer.py    Controlled name normalization (never fuzzy/blind stemming)
├── matcher.py         Per-requirement match classification + full-analysis orchestration
└── scorer.py            Weighted category scoring
```

## Normalization: an allow-list, not an algorithm

`normalizer.py`'s `normalize_skill_name()` is deliberately **not** a
generic stemmer or fuzzy-similarity function. The temptation with a
problem like "REST API" / "REST APIs" / "RESTful API" meaning the same
thing is to reach for an algorithm that measures string similarity - but
similarity algorithms can't distinguish "two spellings of the same
thing" from "two different things that happen to look alike," and the
cost of getting that wrong is a false positive that tells someone
they're qualified for something they aren't.

Instead, `CANONICAL_ALIASES` is a small, explicit, hand-maintained
dictionary. Only pairs listed there are ever treated as equivalent:

```python
CANONICAL_ALIASES = {
    "rest api": "rest api",
    "rest apis": "rest api",
    "restful api": "rest api",
    "restful apis": "rest api",
    "javascript": "javascript",
    "js": "javascript",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    # ... (see the module for the full list)
}
```

Adding a new alias is a deliberate, reviewed code change - never
something the matching run infers on its own. **Genuinely different
technologies are never added here, even if they're commonly confused**
(Java/JavaScript, Selenium/Playwright, AWS/Azure, React/Angular, etc.).

## Match types

Every JD requirement is classified against the resume's skills (or, for
non-skill requirement types, against resume text - see "Freetext
categories" below) using a fixed rule ladder, checked in this order:

| Match type | Rule | Confidence |
|---|---|---|
| `exact` | Raw name strings are identical (case-insensitive) | 1.0 |
| `normalized` | Not identical, but equal after normalization (known formatting variant, e.g. "REST APIs" vs "RESTful API") | 0.9 |
| `related` | Different normalized terms, but both belong to an explicitly-declared related-terms group (e.g. "SQL" and "PostgreSQL") | 0.6 |
| `partial` | Meaningful whole-**word**-token overlap where one term is a subset of the other (e.g. "AWS" vs "AWS Lambda") | 0.4 |
| `missing` | No resume skill satisfies the requirement | 0.0 |
| `unknown` | The requirement or every candidate has no usable name to compare (defensive fallback; shouldn't occur with valid data) | 0.0 |

The ladder stops at the first (best) rule that fires - if a resume skill
matches exactly, weaker rules are never even checked for that
requirement.

### Why `partial` matching is token-based, not substring-based

This is the detail that makes the false-positive guards actually safe.
A naive substring check (`"java" in "javascript"`) would incorrectly
flag Java as present whenever a resume lists JavaScript. Instead,
`partial` matching tokenizes both names into whole words and only
matches when one name's token *set* is a subset of the other's:

- `"aws lambda"` tokenizes to `{"aws", "lambda"}`, `"aws"` tokenizes to
  `{"aws"}` - `{"aws"} ⊂ {"aws", "lambda"}`, so this is a legitimate
  partial match (a broader/narrower relationship).
- `"java"` tokenizes to `{"java"}`, `"javascript"` tokenizes to
  `{"javascript"}` - these are simply two different single-word tokens
  with zero overlap. No rule in the ladder can ever connect them.

This is why the mandatory false-positive pairs work correctly "for
free" from the token-based design, rather than needing special-cased
exclusion rules.

### `related` groups

A small, deliberately conservative set of term families where members
are genuinely connected but not interchangeable:

```python
RELATED_GROUPS = [
    {"sql", "mysql", "postgresql", "sql server", "oracle sql", "sqlite", "mariadb"},
    {"ci cd", "jenkins", "github actions", "gitlab ci", "circleci", "travis ci"},
    {"nosql", "mongodb", "dynamodb", "cassandra", "couchdb"},
]
```

If a JD requires "SQL" and the resume lists "PostgreSQL", that's a
`related` match at reduced confidence (0.6) - the candidate has
demonstrated SQL-adjacent capability, but PostgreSQL specifically wasn't
what was asked for. This groups list is the only other place (besides
`CANONICAL_ALIASES`) where equivalence-like relationships are declared,
and it's just as conservative and explicit.

### Freetext categories

Requirement types `responsibility`, `experience`, `education`, `domain`,
`keyword`, and `soft_skill` aren't flat skill names - a requirement like
"5+ years of QA automation experience" has no single equivalent
"skill" on the resume side, only passages of prose that may or may not
cover it. For these, `matcher.py`'s `match_requirement_against_text()`
uses whole-word token-overlap ratio against candidate resume text
(experience descriptions, education entries, project descriptions, or a
broad corpus spanning the whole profile, depending on the category):

| Coverage | Match type | Confidence |
|---|---|---|
| All requirement tokens found in the resume text | `normalized` | 0.9 |
| ≥50% of requirement tokens found | `partial` | 0.4 |
| <50% (or none) found | `missing` | 0.0 |

`exact` and `related` aren't produced for freetext categories - they
aren't meaningful comparisons between two pieces of prose the way they
are between two skill names.

## Reproducibility

Given the exact same resume skills and JD requirements, the matching
engine always produces the same result:

- Candidate skills are always considered in a fixed sort order
  (normalized name, then raw name, then id) - never database row order
  or insertion order.
- When multiple candidates could match, ties are broken deterministically
  by that same fixed order, not by "whichever came first" in an
  unordered collection.
- No randomness, no model sampling, no external state.

This is directly tested (`tests/backend/test_matching_engine.py::TestReproducibility`):
shuffling the order of candidate skills, or running the same match
multiple times, always yields identical results.

## Scoring

### The six weighted categories

```
Required Skills       50%
Responsibilities      25%
Experience             10%
Education                5%
Preferred Skills          5%
Keywords                    5%
```

Configurable via environment variables (`MATCH_WEIGHT_REQUIRED_SKILLS`,
etc. - see `app/config.py`), read into a `MatchWeights` object that
validates the weights sum to 1.0. Never hardcoded in an API route -
`app/api/v1/analyses.py` only calls `AnalysisService`, which reads
weights from settings.

### Mapping nine requirement types onto six scoring categories

JD requirements are extracted into **nine** `requirement_type` values
(see [docs/ai-architecture.md](./ai-architecture.md)), three more than
the six weighted categories above. This mapping is a deliberate,
documented interpretive choice:

| `requirement_type` | Scoring category | Rationale |
|---|---|---|
| `required_skill` | Required Skills | direct |
| `technology` | Required Skills | a required tool/tech stack item is assessed the same way a required skill is - the spec gives it no separate weight |
| `preferred_skill` | Preferred Skills | direct |
| `responsibility` | Responsibilities | direct |
| `experience` | Experience | direct |
| `education` | Education | direct |
| `keyword` | Keywords | direct |
| `domain` | Keywords | domain expertise is assessed the same contextual way generic keyword coverage is |
| `soft_skill` | Keywords | same reasoning as domain |

### Category score formula

For a category with JD requirements `R`:

```
category_score = (sum of each requirement's best-match confidence) / len(R)
```

This is **confidence-weighted**, not a binary matched/not-matched
count - a `partial` match contributes 0.4 to the average, not a full 1
or a full 0, so the score reflects match *quality*.

### The empty-category rule

**If a category has zero JD requirements, its score is 1.0 (full
marks) - not 0.** This is deliberate: an empty category means the JD
made no ask in that area, so there's nothing for the candidate to be
missing. Scoring it as 0 would punish the candidate for a gap the JD
itself never specified - the opposite of the intended, explainable
behavior. This rule is directly tested
(`test_matching_engine.py::TestScoreCategory::test_empty_category_gets_neutral_score`
and `TestComputeScore::test_completely_empty_jd_scores_100`).

### Overall score

```
overall_score = sum(weight[category] * category_score[category] for category in categories) * 100
```

Expressed as 0-100. Every number that feeds into it - each category's
weight, requirement count, raw score, and weighted contribution - is
retained on the `Analysis` record (`weights_snapshot`, plus the six
per-category score columns), so any score can always be explained by
pointing at exactly which requirements contributed what, even if the
configured default weights change later.

### Worked example: the acceptance criteria scenario

Resume skills: Python, Selenium, Playwright, SQL.
JD required skills: Python, Selenium, Playwright, Cypress, AWS.

| Requirement | Match | Confidence |
|---|---|---|
| Python | exact | 1.0 |
| Selenium | exact | 1.0 |
| Playwright | exact | 1.0 |
| Cypress | missing | 0.0 |
| AWS | missing | 0.0 |

```
required_skills score = (1.0 + 1.0 + 1.0 + 0.0 + 0.0) / 5 = 0.6
required_skills contribution = 0.6 * 0.50 = 0.30

responsibilities, experience, education, preferred_skills, keywords:
  all empty (this JD only specified required skills) -> score 1.0 each
  contribution = 1.0 * (0.25 + 0.10 + 0.05 + 0.05 + 0.05) = 0.50

overall_score = (0.30 + 0.50) * 100 = 80.0
```

`SQL` is on the resume but wasn't requested by the JD anywhere - it
never appears as a fabricated match to any requirement. Instead it's
surfaced separately as an "extra resume skill"
(`GET /analyses/{id}/matches` → `extra_resume_skills`), informational
only and never scored.

This exact scenario is covered end-to-end in
`tests/backend/test_analysis_api.py::TestAcceptanceCriteria`.

## The critical rule

**If a skill appears in the JD but not in the verified resume, it is
always classified `missing` - never fabricated as a match.** This isn't
just documented; it's structural:

- `AnalysisService.create_analysis()` only ever reads the resume and JD
  as already verified by the user (`assert_verified()` on both,
  enforced with a `409` otherwise) - it has no code path that writes to
  or infers additions for the resume.
- `core/matching/matcher.py` has no mechanism to invent a skill - every
  match type resolves to either a specific resume item (`matched_skill`
  / `matched_text`) or `missing`/`unknown` with no reference at all.
- Every requirement that doesn't match anything on the resume produces a
  `SkillMatch` row with `match_type="missing"`, `resume_skill_id=None`,
  and an explanation naming exactly what wasn't found - it's recorded,
  not silently dropped, so "missing" is just as visible and explainable
  as a match.

## Database model

See [docs/database.md](./database.md#matching-engine-tables) for the
full `Analysis`/`SkillMatch` schema.

## API

See [docs/api.md](./api.md#analyses) for the full `POST/GET /analyses`
and `GET /analyses/{id}/matches` reference.
