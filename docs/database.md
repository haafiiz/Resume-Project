# Database

SQLite for V1 (`DATABASE_URL`, default `sqlite:///./storage/app.db`),
accessed through SQLAlchemy (`app/database.py`) with schema managed by
Alembic (`backend/alembic/`).

## Schema overview (as of Sprint 3)

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

## Relationships (SQLAlchemy)

Defined in `app/models/resume.py` and `app/models/job_description.py`.
`Resume` and `JobDescription` are each the parent side of their
relationships, with `cascade="all, delete-orphan"` so that replacing a
resume's skills/experiences/etc. or a job description's requirements (as
happens on every parse/extraction and every `PUT` update) cleanly
removes the old rows rather than leaving orphans.

```python
resume.sections            # list[ResumeSection]
resume.skills                # list[Skill]
resume.experiences             # list[Experience], ordered by sort_order
resume.projects                  # list[Project], ordered by sort_order
resume.education_entries           # list[Education], ordered by sort_order
resume.certifications                # list[Certification]

job_description.requirements   # list[JDRequirement], ordered by sort_order
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
