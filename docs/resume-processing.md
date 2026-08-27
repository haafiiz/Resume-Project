# Resume Processing

This document covers the resume upload → parse → review → verify flow
implemented in Sprint 2: `core/parsing/`, `services/resume_service.py`,
and the `/api/v1/resumes` routes.

## Supported file formats

- **DOCX** (`.docx`) — parsed with `python-docx`
- **PDF** (`.pdf`) — parsed with `pypdf`

Any other extension is rejected at upload time. Scanned/image-only PDFs
(no embedded text layer) are accepted as files but will produce no
extractable text — the resume is still stored, but its status becomes
`needs_review` with an explanatory `parse_error`, since OCR is out of
scope for this sprint.

## Why parsing is deterministic, not LLM-based

Per the project's core business rule, nothing in this system may invent
information. An LLM asked to "extract structured data" from a resume
will, if the input is ambiguous, often paraphrase, infer, or quietly
fill gaps. A regex/heuristic parser either finds a match in the literal
text or it doesn't — there's no room for it to invent a skill or a
company name that isn't there. That's why `core/parsing/resume_parser.py`
uses pattern-based extraction exclusively, with no AI provider call
anywhere in the resume pipeline.

The trade-off: heuristic parsing handles common, single-column resume
layouts well, but unusual layouts (multi-column, heavily graphical,
table-heavy) may extract poorly or not at all. This is an intentional
trade-off in favor of "never fabricate structure that isn't really
there" — a resume that can't be confidently parsed is routed to
`needs_review` so the user fills in the gaps themselves, rather than the
system guessing.

## Upload flow

```
POST /api/v1/resumes  (multipart/form-data, field name "file")
```

1. **Validation** (`app/utils/upload_validation.py`), in order:
   - Filename present, no path separators, reasonable length
   - Extension is `.pdf` or `.docx` (configurable via
     `ALLOWED_UPLOAD_EXTENSIONS`)
   - File is not empty
   - File size is within `MAX_UPLOAD_SIZE_MB` (default 10 MB)
   - File content's **magic bytes** match the extension (`%PDF` for PDF,
     the ZIP signature `PK\x03\x04` for DOCX) — the client-declared
     `Content-Type` is treated as a plausibility check only, never
     trusted on its own, since it's trivial to spoof
   - A failure at any step returns `400` with a human-readable message;
     nothing is written to disk or the database.
2. **Storage** (`app/utils/file_storage.py`): the file is written to
   `storage/uploads/<uuid>.<ext>`. The stored filename is always a
   freshly generated UUID — the original client filename is never used
   to construct a path, and an existing upload is never overwritten. The
   filesystem path is never returned in any API response; the frontend
   only ever sees the resume's database `id`.
3. **Text extraction** (`core/parsing/docx_parser.py` /
   `core/parsing/pdf_parser.py`): raw text is pulled from the file.
4. **Structured parsing** (`core/parsing/resume_parser.py`): the raw
   text is split into sections and each section's fields are extracted
   (see below).
5. **Persistence**: the resume and its structured items are saved. The
   resume's `status` is set based on how much was extracted (see
   "Verification states" below).

## Parsing architecture

```
core/parsing/
├── docx_parser.py     bytes -> plain text (python-docx)
├── pdf_parser.py       bytes -> plain text (pypdf)
└── resume_parser.py     text -> ParsedResume (sections + structured fields)
```

`resume_parser.py` is the only module with knowledge of resume
structure; the format-specific parsers know nothing beyond "extract
readable text from this byte format." This keeps the structural
heuristics in one place regardless of source format.

### Section detection

Lines that match a known header alias (case-insensitive, e.g.
"Experience", "Work History", "Employment History" all map to the
canonical section type `experience`) start a new section; everything
until the next recognized header belongs to that section. Text before
the first recognized header is treated as the "header block" and mined
for contact info (name, email, phone, location).

Canonical section types: `summary`, `experience`, `education`, `skills`,
`projects`, `certifications`. See `SECTION_HEADERS` in
`resume_parser.py` for the full alias list.

### Field extraction per section

- **Contact info**: regex for email and phone anywhere in the header
  block; a `City, ST`-style pattern for location; the first line that
  isn't itself an email/phone/location is taken as the name.
- **Skills**: split on commas, semicolons, bullets, and newlines;
  deduplicated case-insensitively.
- **Experience / Education**: entries are split using **date-range
  lines as anchors** (e.g. "Jan 2020 - Present", "2016 - 2018"). The
  line immediately before a date-range line is treated as that entry's
  header (job title/company, or institution/degree); everything between
  one entry's date line and the next entry's header is that entry's
  description (experience only — education entries don't collect a
  description block, since that content is uncommon and hard to
  distinguish from the next entry's header). If no date range is found
  anywhere in the section, the whole block becomes a single
  low-confidence entry for the user to fill in.
- **Projects**: the first line of a block is the project name; a line
  matching `Technologies:`/`Tech stack:`/etc. is captured separately;
  everything else is description. A later short line with no
  sentence-ending punctuation is treated as the *next* project's name,
  but only once the current project has already gathered a description
  — this avoids a two-line "name, then tech line" block being split
  into two phantom projects.
- **Certifications**: each line is one certification; a 4-digit year is
  pulled out as the issue date; the remainder is split into name and
  issuer on the first comma/pipe/dash.

None of this is claimed to be perfect — see "Why parsing is
deterministic" above for the trade-off this represents.

## Source-of-truth metadata

Every extracted `Skill`, `Experience`, `Project`, `Education`, and
`Certification` row carries:

- `source`: `"resume"` (came from parsing) or `"user"` (entered/edited
  by the person)
- `verified`: `false` until the user confirms it

When a resume is first parsed, every item is `source=resume,
verified=false`. When the user edits a section through
`PUT /resumes/{id}`, every item in that section is rewritten with
`source=user` and whatever `verified` value the client sent — the
frontend editors default new/edited items to `verified: true` since
editing something is itself an act of confirmation, but the API doesn't
assume that on the user's behalf; it uses exactly what's submitted.

This distinction is what a future matching/tailoring engine will use to
tell "the resume says this" apart from "the user has confirmed this" —
neither this sprint nor the two are collapsed into a single flag.

## Verification flow and states

```
uploaded -> parsed | needs_review -> verified
```

| Status | Meaning |
|---|---|
| `uploaded` | File stored, parsing not yet run (transient - parsing happens synchronously as part of upload in this sprint, so a resume should only be observed in this state very briefly, if ever, mid-request) |
| `parsed` | Parsing found meaningful structured content (at least one skill, experience, education, or project entry) |
| `needs_review` | Parsing ran but found little/nothing usable (empty document, unrecognized layout, or a genuine parse failure) - the parser explains why via `parse_error` |
| `verified` | The user has explicitly confirmed the profile via `POST /resumes/{id}/verify` |

Rules:

- `PUT /resumes/{id}` (corrections) is only allowed while the resume is
  **not** verified; once verified, the endpoint returns `409 Conflict`.
  This keeps a verified profile immutable — if something needs to
  change, upload a new resume.
- `POST /resumes/{id}/verify` requires the resume to have been parsed at
  least once (rejects `uploaded`); calling it again on an
  already-verified resume is a no-op that returns `200`.
- Editing a `needs_review` resume with real data (e.g. the user manually
  fills in their name and adds skills) promotes its status to `parsed`,
  since the user has now supplied what the parser couldn't find.
- **No other part of the system may use an unverified resume profile.**
  `ResumeService.assert_verified()` exists specifically for later
  sprints (matching/tailoring) to call before using a resume as an input
  - this sprint doesn't have a matching engine yet, so nothing calls it
  yet, but the guard is in place so the rule can't be silently skipped
  later.

## Frontend flow

```
/resumes          list of uploaded resumes with status badges
/resumes/new       drag-and-drop / click-to-browse upload
/resumes/:id        profile view, section editors, and "Mark Resume as Verified"
```

The detail page (`src/pages/ResumeDetail.tsx`) loads the profile, renders
editable contact-info fields plus one editor component per section
(`SkillsEditor`, `ExperienceEditor`, `ProjectEditor`, `EducationEditor`,
`CertificationEditor`, all under `src/components/resume/`), and offers
two actions: **Save changes** (`PUT /resumes/{id}`) and **Mark Resume as
Verified** (`POST /resumes/{id}/verify`). Once verified, the whole form
is disabled (`<fieldset disabled>`) and the save/verify buttons are
hidden, mirroring the backend's immutability rule.
