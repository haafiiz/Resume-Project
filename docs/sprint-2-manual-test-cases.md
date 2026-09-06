# Sprint 2 — Manual Test Cases

**Scope:** Resume upload, storage, parsing, structured extraction, review/edit, and verification. Covers the `POST/GET/PUT /resumes` API and the `/resumes`, `/resumes/new`, `/resumes/:id` frontend pages.

**Prerequisites:**
- Backend running (`uvicorn app.main:app --reload`) with a clean database (`alembic upgrade head` on an empty `storage/app.db`)
- Frontend running (`npm run dev`), pointed at the backend
- Sample files ready: a valid `.docx` resume with all sections populated, a valid `.pdf` resume with all sections populated, an empty `.docx`, a non-resume file with a `.pdf`/`.docx` extension (e.g. a renamed `.txt`), a genuinely unsupported type (`.txt`, `.jpg`), and an oversized file (>10 MB, or whatever `MAX_UPLOAD_SIZE_MB` is configured to)

Each test case lists **Preconditions**, **Steps**, and **Expected Result**. A "(API)" case can be run with curl/Postman/the `/docs` Swagger UI; a "(UI)" case is run in the browser. Most flows are covered both ways since the UI is a thin layer over the API — the API case verifies the contract, the UI case verifies the app wires it up correctly.

---

## 1. Upload

### TC-1.1 — Upload a valid DOCX resume (API)
**Preconditions:** Backend running, empty database.
**Steps:** `POST /api/v1/resumes` with a valid `.docx` file, `Content-Type: multipart/form-data`.
**Expected:** `201 Created`. Response contains `id`, `original_filename` matching the uploaded file, `status` is `"parsed"` (assuming the sample resume has extractable sections), `parse_error` is `null`.

### TC-1.2 — Upload a valid PDF resume (API)
**Steps:** `POST /api/v1/resumes` with a valid `.pdf` file.
**Expected:** Same as TC-1.1, for the PDF path.

### TC-1.3 — Upload a valid resume (UI)
**Steps:** Navigate to `/resumes/new`. Drag a valid resume file onto the drop zone, or click and browse to select it.
**Expected:** "Uploading and parsing…" message shown while in flight. On success, browser navigates to `/resumes/:id` and the profile page loads with extracted data visible.

### TC-1.4 — Upload via drag-and-drop vs. click-to-browse (UI)
**Steps:** Repeat TC-1.3 once using drag-and-drop and once using click-to-browse.
**Expected:** Both paths succeed identically. Drop zone highlights (visual state change) while a file is dragged over it.

### TC-1.5 — Reject unsupported file type (API)
**Steps:** `POST /api/v1/resumes` with a `.txt` or `.jpg` file.
**Expected:** `400 Bad Request`. `detail` message names the rejected extension and lists allowed types (`.pdf, .docx`). No resume record created (confirm via `GET /resumes` — count unchanged).

### TC-1.6 — Reject unsupported file type (UI)
**Steps:** On `/resumes/new`, select a `.txt` file (native file picker may pre-filter by `accept=".pdf,.docx"` — if so, use "All files" to bypass, or drag-and-drop the file instead).
**Expected:** Inline error message shown on the page (red banner). Page remains on `/resumes/new` — no navigation occurs.

### TC-1.7 — Reject oversized file (API)
**Steps:** `POST /api/v1/resumes` with a file larger than `MAX_UPLOAD_SIZE_MB`.
**Expected:** `400 Bad Request`, `detail` states the file size and the maximum allowed.

### TC-1.8 — Reject oversized file (UI)
**Steps:** Same as TC-1.7 via the upload UI.
**Expected:** Inline error message with the size/limit detail.

### TC-1.9 — Reject empty (zero-byte) file (API)
**Steps:** `POST /api/v1/resumes` with a 0-byte file named `resume.pdf`.
**Expected:** `400 Bad Request`, `detail` states the file is empty.

### TC-1.10 — Accept a structurally valid but content-empty document (API)
**Steps:** `POST /api/v1/resumes` with a valid `.docx` that has no paragraphs/text (e.g. a blank Word doc saved as-is).
**Expected:** `201 Created` (the file itself is valid, just contentless). `status` is `"needs_review"`, `parse_error` explains no readable text was found. Resume record is created and appears in `GET /resumes`.

### TC-1.11 — Reject file whose content doesn't match its extension (API)
**Steps:** Rename a `.txt` file to `resume.pdf` (or `resume.docx`) and upload it.
**Expected:** `400 Bad Request`, `detail` mentions the content doesn't match the extension (magic-byte signature check).

### TC-1.12 — Reject unsafe/path-like filename (API)
**Steps:** Upload with a filename like `../../etc/passwd.pdf` (most HTTP clients will need this set explicitly in the multipart `filename` field).
**Expected:** `400 Bad Request`, `detail` mentions invalid filename characters.

### TC-1.13 — Reject missing file field (API)
**Steps:** `POST /api/v1/resumes` with no `file` field in the multipart body.
**Expected:** `422 Unprocessable Entity` (FastAPI's standard validation error for a missing required field).

### TC-1.14 — Upload a scanned/image-only PDF (no text layer) (API/UI)
**Steps:** Upload a PDF that is a scanned image with no embedded text.
**Expected:** `201 Created`, `status` is `"needs_review"`, `parse_error` explains no readable text was found (mentions the possibility of an image-based scan).

### TC-1.15 — Uploaded file is never overwritten (API)
**Steps:** Upload the same file (same original filename and content) twice.
**Expected:** Two separate resume records are created, each with a distinct `id`. `GET /resumes` shows two entries. (Confirms UUID-based storage never collides/overwrites.)

### TC-1.16 — Filesystem path is never exposed (API)
**Steps:** Inspect every field of the response from TC-1.1 and from `GET /resumes/{id}/profile`.
**Expected:** No field contains a filesystem path (e.g. no `storage/uploads/...` string anywhere in any response body).

---

## 2. Parsing accuracy

Use a resume with a **realistic, well-structured layout**: name/email/phone/location header, a Summary section, 2+ Experience entries with date ranges, an Education section, a Skills list, at least one Project, and a Certification.

### TC-2.1 — Contact info extraction
**Steps:** Upload the sample resume. `GET /resumes/{id}/profile`.
**Expected:** `full_name`, `email`, `phone`, `location` all correctly populated and match the source document.

### TC-2.2 — Skills extraction
**Expected:** `skills` array contains every skill listed in the Skills section, with no duplicates (case-insensitive), each with `source: "resume"` and `verified: false`.

### TC-2.3 — Multiple experience entries do not bleed into each other
**Steps:** Use a resume with 2+ experience entries back-to-back (no blank-line separation in the source, mimicking common DOCX/PDF export behavior).
**Expected:** Each experience entry in the response has the correct `job_title`, `company`, `start_date`, `end_date`, and `description` — no entry's description contains the next entry's title/company text.

### TC-2.4 — Currently-held position detection
**Steps:** Include an experience entry with an end date of "Present" (e.g. "Jan 2022 - Present").
**Expected:** That entry's `is_current` is `true` and `end_date` is `null`.

### TC-2.5 — Education extraction with multiple entries
**Steps:** Use a resume with 2 education entries.
**Expected:** Both entries extracted separately with correct `institution`, `degree`, `field_of_study`, `start_date`, `end_date` — no bleed between entries.

### TC-2.6 — Project extraction with a "Technologies:" line
**Steps:** Include a project with a name, a `Technologies: X, Y, Z` line, and a description sentence ending in a period.
**Expected:** `name`, `technologies`, and `description` all populated correctly. The description sentence is **not** mistaken for a second project's name (regression check).

### TC-2.7 — Certification extraction with issuer and year
**Steps:** Include a certification formatted as `"Name - Issuer, Year"`.
**Expected:** `name`, `issuer`, and `issue_date` (the year) all correctly split out.

### TC-2.8 — Unusual/unparseable layout routes to needs_review
**Steps:** Upload a resume with no recognizable section headers (e.g. a single unstructured paragraph).
**Expected:** `201 Created`, `status` is `"needs_review"`, `parse_error` explains no structured sections were identified. Fields that couldn't be found remain `null`/empty rather than containing guessed values.

---

## 3. Profile retrieval

### TC-3.1 — Get profile for an existing resume (API)
**Steps:** `GET /resumes/{id}/profile` for a resume uploaded in TC-1.1.
**Expected:** `200 OK`. Full profile returned including `sections`, `skills`, `experiences`, `projects`, `education_entries`, `certifications`, each item carrying `source` and `verified`.

### TC-3.2 — Get profile for a nonexistent resume (API)
**Steps:** `GET /resumes/does-not-exist/profile`.
**Expected:** `404 Not Found`.

### TC-3.3 — View profile in the UI (UI)
**Steps:** Navigate to `/resumes/:id` for an uploaded resume.
**Expected:** Page shows the resume's name/filename, status badge, contact fields pre-filled, and every section (Skills, Experience, Projects, Education, Certifications) pre-filled with extracted data.

### TC-3.4 — List all resumes (API)
**Steps:** Upload 2–3 resumes, then `GET /resumes`.
**Expected:** `200 OK`, array with one summary entry per resume (id, filename, status, full_name, timestamps) — no nested section data (lightweight list).

### TC-3.5 — List resumes in the UI (UI)
**Steps:** Navigate to `/resumes` after uploading a few resumes.
**Expected:** All uploaded resumes listed with name/filename and a status badge; clicking a row navigates to its detail page. With zero resumes uploaded, an empty-state message is shown instead.

---

## 4. Corrections (update)

### TC-4.1 — Correct a scalar field (API)
**Steps:** `PUT /resumes/{id}` with `{"full_name": "Corrected Name"}` on an unverified resume.
**Expected:** `200 OK`. `full_name` updated in the response; all other fields (skills, experiences, etc.) unchanged from before the request.

### TC-4.2 — Replace the skills list (API)
**Steps:** `PUT /resumes/{id}` with a `skills` array different from the current one (some removed, some added, `verified: true` on each).
**Expected:** `200 OK`. Returned `skills` array exactly matches what was submitted — old skills not in the payload are gone, new ones present, each with `source: "user"` and `verified: true`.

### TC-4.3 — Replace experience/projects/education/certifications (API)
**Steps:** Repeat TC-4.2 for each of `experiences`, `projects`, `education_entries`, `certifications`.
**Expected:** Same full-replace behavior for each section independently; sections not included in the payload are left untouched.

### TC-4.4 — Partial payload leaves other sections untouched (API)
**Steps:** `PUT /resumes/{id}` with only `{"phone": "555-0000"}` (no `skills`, `experiences`, etc. keys at all).
**Expected:** `phone` updated; `skills`, `experiences`, `projects`, `education_entries`, `certifications` all unchanged.

### TC-4.5 — Update a nonexistent resume (API)
**Steps:** `PUT /resumes/does-not-exist` with any valid payload.
**Expected:** `404 Not Found`.

### TC-4.6 — Editing needs_review resume with real data promotes status (API)
**Steps:** Upload an empty/unparseable document (→ `needs_review`), then `PUT` with a `full_name` and at least one skill.
**Expected:** Resume's `status` becomes `"parsed"`.

### TC-4.7 — Edit fields in the UI (UI)
**Steps:** On `/resumes/:id`, edit the Full Name field, add/remove a skill via the Skills editor, edit an experience entry's description, click **Save changes**.
**Expected:** "Changes saved." confirmation shown. Reloading the page (re-fetching the profile) shows the edits persisted.

### TC-4.8 — Add and remove items via each section editor (UI)
**Steps:** For each of Skills, Experience, Projects, Education, Certifications: click "+ Add …", fill in fields, save; then remove an existing item, save.
**Expected:** Each editor correctly adds a new blank row, accepts input, and removes rows on click. Saved state reflects the additions/removals after reload.

### TC-4.9 — "Verified" checkbox per item (UI)
**Steps:** Toggle the "Verified" checkbox on a skill or experience entry, save, then re-fetch the profile via `GET /resumes/{id}/profile` (API) to confirm.
**Expected:** The item's `verified` value in the backend matches what was set in the UI.

---

## 5. Verification

### TC-5.1 — Verify a parsed resume (API)
**Steps:** `POST /resumes/{id}/verify` on a resume with `status: "parsed"`.
**Expected:** `200 OK`. `status` becomes `"verified"`, `verified_at` is set to a non-null timestamp.

### TC-5.2 — Verify a needs_review resume (API)
**Steps:** `POST /resumes/{id}/verify` on a resume with `status: "needs_review"`.
**Expected:** `200 OK`, transitions to `"verified"` (needs_review is allowed to be verified — the user has presumably reviewed/filled in the data manually first).

### TC-5.3 — Cannot verify a freshly uploaded, unparsed resume (API)
**Steps:** This is difficult to trigger normally since parsing runs synchronously on upload — if there's any code path that can leave a resume in `status: "uploaded"`, attempt to verify it there.
**Expected:** `409 Conflict` with a message explaining the resume hasn't been parsed yet. (If no such resume can exist in practice, note this as "not reproducible under current upload flow" rather than skipping — flag for review.)

### TC-5.4 — Verifying twice is idempotent (API)
**Steps:** `POST /resumes/{id}/verify` twice in a row.
**Expected:** Both calls return `200 OK` with `status: "verified"`. No error on the second call.

### TC-5.5 — Verify a nonexistent resume (API)
**Steps:** `POST /resumes/does-not-exist/verify`.
**Expected:** `404 Not Found`.

### TC-5.6 — Cannot edit a verified resume (API)
**Steps:** Verify a resume (TC-5.1), then `PUT /resumes/{id}` with any payload.
**Expected:** `409 Conflict`, message explains the resume is already verified and corrections are no longer accepted.

### TC-5.7 — Verify in the UI (UI)
**Steps:** On `/resumes/:id`, click **"Mark Resume as Verified"**.
**Expected:** Confirmation message shown ("Resume verified..."). Status badge updates to "Verified". All form fields become disabled/read-only. Save/Verify buttons disappear, replaced by a message that further corrections require uploading a new resume.

### TC-5.8 — Verified resume UI state persists across reload (UI)
**Steps:** After TC-5.7, reload the page.
**Expected:** Resume still shows as Verified, form still disabled — state is correctly re-fetched from the backend, not just a client-side flag.

---

## 6. Cross-cutting / integration

### TC-6.1 — CORS allows the frontend origin (API)
**Steps:** Send an `OPTIONS` preflight to `POST /resumes` with `Origin: http://localhost:5173`.
**Expected:** `200 OK`, `Access-Control-Allow-Origin` header present and matches the frontend origin.

### TC-6.2 — Source-of-truth metadata is visible and correct throughout
**Steps:** Upload a resume, inspect all extracted items (`source: "resume"`, `verified: false`); edit one section and re-inspect (`source: "user"`, `verified` per what was submitted).
**Expected:** Metadata transitions correctly and is never silently dropped or defaulted incorrectly.

### TC-6.3 — Full happy-path flow end-to-end (UI)
**Steps:** Upload a resume → review the auto-populated profile → correct at least one field in each section → save → click Mark Resume as Verified → confirm the resume shows as Verified in the `/resumes` list.
**Expected:** Every step succeeds without error; final state is consistent between the list page, detail page, and a direct `GET /resumes/{id}/profile` call.

### TC-6.4 — Two resumes uploaded for the same user do not interfere
**Steps:** Upload two different resumes back-to-back. Edit one; verify the other. Reload both detail pages.
**Expected:** Each resume's data, status, and verification state are independent — no cross-contamination.

### TC-6.5 — Backend restart preserves data
**Steps:** Upload and verify a resume. Restart the backend process. `GET /resumes/{id}/profile` again.
**Expected:** Data persisted (SQLite file-based storage) — profile identical to before restart.

---

## Test summary template

| TC ID | Result (Pass/Fail) | Notes |
|---|---|---|
| TC-1.1 | | |
| TC-1.2 | | |
| … | | |

Log any failure with: the exact request/steps used, actual vs. expected response, and whether it reproduces consistently.
