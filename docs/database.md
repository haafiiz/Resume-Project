# Database

SQLite for V1 (`DATABASE_URL`, default `sqlite:///./storage/app.db`),
accessed through SQLAlchemy (`app/database.py`) with schema managed by
Alembic (`backend/alembic/`).

## Schema overview (as of Sprint 4)

```
resumes
├── resume_sections   (1 resume -> many sections)
├── skills             (1 resume -> many skills)
├── experiences         (1 resume -> many experiences)
├── projects              (1 resume -> many projects)
├── education             (1 resume -> many education entries)
└── certifications          (1 resume -> many certifications)

job_descriptions
└── jd_requirements    (1 job description -> many requirements)

analyses                (references a resume + a job description)
└── skill_matches         (1 analysis -> many per-requirement match results)
```

Every child table has a `resume_id` foreign key with
`ON DELETE CASCADE` — deleting a `Resume` row removes all of its
sections/skills/experiences/projects/education/certifications
automatically. There is no resume deletion endpoint yet in this sprint,
but the cascade is in place for when one is added.

### `resumes`

The top-level record for an uploaded resume and its extracted profile.

| Column | Type | Notes |
|---|---|---|
| `id` | string (UUID) | primary key |
| `original_filename` | string | as provided by the client; display-only, never used for storage paths |
| `stored_filename` | string | unique; the actual filename under `storage/uploads/` |
| `file_extension` | string | `.pdf` or `.docx` |
| `content_type` | string | validated declared MIME type |
| `file_size_bytes` | int | |
| `status` | enum | `uploaded` \| `parsed` \| `needs_review` \| `verified` — see [docs/resume-processing.md](./resume-processing.md#verification-flow-and-states) |
| `full_name`, `email`, `phone`, `location`, `summary` | string, nullable | extracted (or user-corrected) contact info |
| `raw_text` | text, nullable | full extracted document text, kept for debugging/re-parsing |
| `parse_error` | text, nullable | human-readable explanation when status is `needs_review` |
| `verified_at` | datetime, nullable | set when the resume transitions to `verified` |
| `created_at`, `updated_at` | datetime | |

### `resume_sections`

The raw section text detected during parsing (e.g. everything under an
"Experience" heading), kept independently of the structured tables below
so the original section text is always available even if structured
extraction within it was incomplete.

| Column | Notes |
|---|---|
| `resume_id` | FK -> `resumes.id` |
| `section_type` | canonical type: `summary`, `experience`, `education`, `skills`, `projects`, `certifications` |
| `heading` | the literal heading line as it appeared in the document |
| `content` | the section's raw text |
| `sort_order` | position within the document |

### `skills`, `experiences`, `projects`, `education`, `certifications`

Each row represents one structured, factual claim extracted from (or
entered for) the resume. All five share the same source-of-truth
pattern:

| Column | Notes |
|---|---|
| `resume_id` | FK -> `resumes.id` |
| `source` | `resume` (extracted by the parser) or `user` (entered/edited by the person) |
| `verified` | `false` until the user confirms the item |

Type-specific fields:

- **`skills`**: `name`, `category` (nullable, unused by the parser yet -
  reserved for future skill categorization)
- **`experiences`**: `job_title`, `company`, `location`, `start_date`,
  `end_date` (free-text strings, not parsed dates - resumes use too many
  date formats to normalize reliably), `is_current` (bool), `description`,
  `sort_order`
- **`projects`**: `name`, `description`, `technologies` (free-text,
  comma-separated), `sort_order`
- **`education`**: `institution`, `degree`, `field_of_study`,
  `start_date`, `end_date`, `sort_order`
- **`certifications`**: `name`, `issuer`, `issue_date`

`start_date`/`end_date` are stored as free-text strings rather than
`Date` columns deliberately: resumes express dates in wildly
inconsistent formats ("Jan 2020", "01/2020", "2020"), and coercing them
into a strict date type risks silently corrupting or discarding
information the user actually wrote - which would conflict with the
project's truth-constrained principle.

## Job description tables

### `job_descriptions`

The top-level record for a saved job description. Unlike resumes, there
is no file storage involved — the description is pasted text saved
directly.

| Column | Type | Notes |
|---|---|---|
| `id` | string (UUID) | primary key |
| `title` | string, nullable | optional, as entered by the user |
| `company` | string, nullable | optional, as entered by the user |
| `description` | text | required — the full pasted job posting text |
| `status` | enum | `created` \| `extracted` \| `needs_review` \| `verified` — see [docs/ai-architecture.md](./ai-architecture.md#failure-handling) |
| `raw_ai_response` | text, nullable | reserved for storing the AI's raw response for debugging (not currently populated - `extraction_error` covers the user-facing case) |
| `extraction_error` | text, nullable | human-readable explanation when status is `needs_review` |
| `verified_at` | datetime, nullable | set when the JD transitions to `verified` |
| `created_at`, `updated_at` | datetime | |

### `jd_requirements`

Each row is one structured requirement extracted from (or manually added
to) a job description, following the same source-of-truth-style pattern
as the resume domain's per-item tables.

| Column | Notes |
|---|---|
| `job_description_id` | FK -> `job_descriptions.id`, `ON DELETE CASCADE` |
| `requirement_type` | one of 9 values: `required_skill`, `preferred_skill`, `technology`, `responsibility`, `education`, `experience`, `domain`, `keyword`, `soft_skill` |
| `name` | as extracted or entered, e.g. `"Python"` |
| `normalized_name` | lowercased/trimmed/whitespace-collapsed version of `name`, computed deterministically in `app/utils/text_normalization.py` — never by the AI |
| `importance` | `required` \| `preferred` \| `nice_to_have` — independent of `requirement_type`, so e.g. a `technology` can still be marked `nice_to_have` |
| `description` | text, nullable | optional elaboration |
| `source_text` | text, nullable | the literal excerpt from the job description this requirement was derived from, for traceability |
| `sort_order` | int | position as extracted |
| `verified` | bool | `false` until the user confirms the item, mirroring the resume domain's per-item `verified` flag |

Note there's no `source` column here (unlike the resume domain's
`Skill`/`Experience`/etc., which distinguish `resume` vs `user`) — every
`JDRequirement` either comes from AI extraction or manual entry, and
since a job description isn't a claim about a candidate that needs a
provenance audit trail in the same way, tracking `verified` alone was
judged sufficient for this domain. This can be revisited if a future
sprint needs the distinction.

## Matching engine tables

See [docs/matching-engine.md](./matching-engine.md) for the scoring
algorithm these tables store the results of.

### `analyses`

One matching-engine run comparing a verified resume against a verified
job description.

| Column | Type | Notes |
|---|---|---|
| `id` | string (UUID) | primary key |
| `resume_id` | string (UUID) | FK -> `resumes.id`, `ON DELETE CASCADE` |
| `job_description_id` | string (UUID) | FK -> `job_descriptions.id`, `ON DELETE CASCADE` |
| `overall_score` | float | 0-100, the final weighted score |
| `required_skills_score`, `responsibilities_score`, `experience_score`, `education_score`, `preferred_skills_score`, `keywords_score` | float | 0-100 each, the six category scores that feed into `overall_score` |
| `weights_snapshot` | text (JSON) | the weights and full per-category breakdown (weight, requirement count, score, weighted contribution) used to produce this analysis, captured at analysis time |
| `created_at` | datetime | |

`weights_snapshot` exists because weights are configurable (see
`app/config.py`) and may change after an analysis is created - storing
the snapshot is what keeps a past analysis reproducible/explainable even
if the configured defaults are later changed. There's intentionally no
`updated_at`: an analysis is a point-in-time record, not something a
user edits - if the underlying resume or JD changes, a fresh analysis
should be created rather than mutating an old one.

### `skill_matches`

One row per JD requirement evaluated as part of an `Analysis` -
including requirements that ended up `missing`, so "nothing matched" is
just as visible and traceable as a match.

| Column | Notes |
|---|---|
| `analysis_id` | FK -> `analyses.id`, `ON DELETE CASCADE` |
| `jd_requirement_id` | FK -> `jd_requirements.id`, `ON DELETE CASCADE` — the requirement this row evaluates |
| `resume_skill_id` | FK -> `skills.id`, `ON DELETE SET NULL`, nullable — populated only when the match came from the resume's `Skill` table (`required_skill` / `preferred_skill` / `technology` categories); null for freetext-category matches and for `missing` |
| `matched_resume_label` | nullable — for freetext-category matches (responsibility/experience/education/domain/keyword/soft_skill), a human-readable label for the resume passage that satisfied the requirement (e.g. `"Experience: Senior Engineer at Acme Corp"`), since there's no single-table FK equivalent to `Skill.id` for prose |
| `matched_resume_text` | nullable — the actual text snapshot behind `matched_resume_label`, for transparency |
| `match_type` | enum: `exact` \| `normalized` \| `related` \| `partial` \| `missing` \| `unknown` |
| `confidence` | float, 0.0-1.0 |
| `explanation` | text — human-readable reason for the classification |
| `requirement_type`, `requirement_name`, `scoring_category` | denormalized copies of the requirement's category-relevant fields, captured at analysis time so a `SkillMatch` remains fully meaningful even if the underlying `JDRequirement` is later edited or deleted |
| `sort_order` | int |

**Why more columns than the spec's literal five?** The spec names
"analysis ID, JD requirement, resume skill, match type, confidence,
explanation" - this table has all five (`analysis_id`,
`jd_requirement_id`, `resume_skill_id`, `match_type`, `confidence`,
`explanation`) plus the freetext-match fields
(`matched_resume_label`/`matched_resume_text`) and the denormalized
requirement fields, both added because a real analysis covers all nine
`requirement_type` values, not just resume-table skill matches - see
[docs/matching-engine.md](./matching-engine.md#freetext-categories) for
why responsibilities/experience/education/domain/keywords/soft-skills
need a text reference instead of a `Skill` row.

## Relationships (SQLAlchemy)

Defined in `app/models/resume.py`, `app/models/job_description.py`, and
`app/models/analysis.py`. `Resume`, `JobDescription`, and `Analysis` are
each the parent side of their relationships, with
`cascade="all, delete-orphan"` so that replacing a resume's
skills/experiences/etc., a job description's requirements, or an
analysis's matches cleanly removes the old rows rather than leaving
orphans.

```python
resume.sections            # list[ResumeSection]
resume.skills                # list[Skill]
resume.experiences             # list[Experience], ordered by sort_order
resume.projects                  # list[Project], ordered by sort_order
resume.education_entries           # list[Education], ordered by sort_order
resume.certifications                # list[Certification]

job_description.requirements   # list[JDRequirement], ordered by sort_order

analysis.matches   # list[SkillMatch], ordered by sort_order
```

## Migrations

Alembic is configured in `backend/alembic/`, with `env.py` reading the
database URL from the same `Settings` object the app uses (not a
hardcoded value in `alembic.ini`) and importing `app.models` so
`autogenerate` can see every model.

Current migrations:

1. `add resume domain tables` — creates `resumes`, `resume_sections`,
   `skills`, `experiences`, `projects`, `education`, `certifications`.
2. `add job description domain tables` — creates `job_descriptions`,
   `jd_requirements`.
3. `add analysis and skill match tables` — creates `analyses`,
   `skill_matches`.

To generate a new migration after changing a model:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Always review an autogenerated migration before committing it - Alembic
is good but not infallible, particularly around SQLite's limited
`ALTER TABLE` support (some changes on SQLite require Alembic's "batch
mode," which the generated migration will use automatically for
column-level alterations).
