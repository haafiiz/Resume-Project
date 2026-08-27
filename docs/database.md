# Database

SQLite for V1 (`DATABASE_URL`, default `sqlite:///./storage/app.db`),
accessed through SQLAlchemy (`app/database.py`) with schema managed by
Alembic (`backend/alembic/`).

## Schema overview (as of Sprint 2)

```
resumes
├── resume_sections   (1 resume -> many sections)
├── skills             (1 resume -> many skills)
├── experiences         (1 resume -> many experiences)
├── projects              (1 resume -> many projects)
├── education             (1 resume -> many education entries)
└── certifications          (1 resume -> many certifications)
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

## Relationships (SQLAlchemy)

Defined in `app/models/resume.py`. `Resume` is the parent side of every
relationship, with `cascade="all, delete-orphan"` so that replacing a
resume's skills/experiences/etc. (as happens on every parse and every
`PUT` update) cleanly removes the old rows rather than leaving orphans.

```python
resume.sections            # list[ResumeSection]
resume.skills                # list[Skill]
resume.experiences             # list[Experience], ordered by sort_order
resume.projects                  # list[Project], ordered by sort_order
resume.education_entries           # list[Education], ordered by sort_order
resume.certifications                # list[Certification]
```

## Migrations

Alembic is configured in `backend/alembic/`, with `env.py` reading the
database URL from the same `Settings` object the app uses (not a
hardcoded value in `alembic.ini`) and importing `app.models` so
`autogenerate` can see every model.

Current migrations:

1. `add resume domain tables` — creates `resumes`, `resume_sections`,
   `skills`, `experiences`, `projects`, `education`, `certifications`.

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
