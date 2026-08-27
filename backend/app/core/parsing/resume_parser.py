"""
Deterministic resume parsing: text -> structured data.

This module never uses an LLM and never invents anything - it only
extracts what is literally present in the document text, using regex and
heuristics for section detection and field extraction. Where the
structure of a resume can't be confidently determined (unusual layout,
missing sections, etc.), extraction is simply left empty rather than
guessed at; the caller (resume_service) is responsible for routing a
thin result to the `needs_review` status so a human confirms it.

Supported layouts are common, single-column resume formats. Highly
unusual layouts (multi-column, heavily graphical, table-based) may
extract poorly - that is an accepted, intentional trade-off in favor of
never fabricating structure that isn't really there.
"""

import re
from dataclasses import dataclass, field

# --- Section detection -------------------------------------------------

SECTION_HEADERS: dict[str, list[str]] = {
    "summary": ["summary", "professional summary", "profile", "objective"],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
    ],
    "education": ["education", "academic background", "academics"],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
        "skills & tools",
    ],
    "projects": ["projects", "personal projects", "key projects"],
    "certifications": [
        "certifications",
        "certificates",
        "licenses",
        "licenses & certifications",
    ],
}

_HEADER_LOOKUP: dict[str, str] = {
    alias: section_type
    for section_type, aliases in SECTION_HEADERS.items()
    for alias in aliases
}


def _normalize_header(line: str) -> str | None:
    """Return the canonical section type if `line` looks like a section
    header, else None."""
    candidate = line.strip().strip(":").strip().lower()
    if not candidate or len(candidate) > 40:
        return None
    return _HEADER_LOOKUP.get(candidate)


@dataclass
class ParsedSection:
    section_type: str
    heading: str
    content: str
    sort_order: int


@dataclass
class ParsedSkill:
    name: str


@dataclass
class ParsedExperience:
    job_title: str | None = None
    company: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    description: str | None = None


@dataclass
class ParsedProject:
    name: str | None = None
    description: str | None = None
    technologies: str | None = None


@dataclass
class ParsedEducation:
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@dataclass
class ParsedCertification:
    name: str
    issuer: str | None = None
    issue_date: str | None = None


@dataclass
class ParsedResume:
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    sections: list[ParsedSection] = field(default_factory=list)
    skills: list[ParsedSkill] = field(default_factory=list)
    experiences: list[ParsedExperience] = field(default_factory=list)
    projects: list[ParsedProject] = field(default_factory=list)
    education: list[ParsedEducation] = field(default_factory=list)
    certifications: list[ParsedCertification] = field(default_factory=list)

    @property
    def has_meaningful_content(self) -> bool:
        """Whether parsing produced enough structured data to consider
        the resume usefully parsed, vs. needing manual review."""
        return bool(
            self.skills or self.experiences or self.education or self.projects
        )


def split_into_sections(text: str) -> tuple[str, list[ParsedSection]]:
    """Split resume text into a leading "header block" (everything before
    the first recognized section) and a list of detected sections.
    """
    lines = [line for line in text.split("\n") if line.strip()]

    header_lines: list[str] = []
    sections: list[ParsedSection] = []

    current_type: str | None = None
    current_heading: str = ""
    current_lines: list[str] = []
    sort_order = 0

    def flush() -> None:
        nonlocal current_type, current_heading, current_lines, sort_order
        if current_type is not None:
            sections.append(
                ParsedSection(
                    section_type=current_type,
                    heading=current_heading,
                    content="\n".join(current_lines).strip(),
                    sort_order=sort_order,
                )
            )
            sort_order += 1
        current_type = None
        current_heading = ""
        current_lines = []

    for line in lines:
        section_type = _normalize_header(line)
        if section_type is not None:
            flush()
            current_type = section_type
            current_heading = line.strip()
            continue

        if current_type is None:
            header_lines.append(line)
        else:
            current_lines.append(line)

    flush()

    return "\n".join(header_lines), sections


# --- Contact info extraction --------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(
    r"(\+?\d{1,3}[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}"
)
_LOCATION_RE = re.compile(r"\b[A-Z][a-zA-Z.\-]+(?:\s[A-Z][a-zA-Z.\-]+)*,\s?[A-Z]{2}\b")


def extract_contact_info(
    header_text: str,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Extract (full_name, email, phone, location) from the header block
    (the text preceding the first detected section, which conventionally
    holds the candidate's name and contact details)."""
    lines = [line.strip() for line in header_text.split("\n") if line.strip()]

    email_match = _EMAIL_RE.search(header_text)
    email = email_match.group(0) if email_match else None

    phone_match = _PHONE_RE.search(header_text)
    phone = phone_match.group(0).strip() if phone_match else None

    location_match = _LOCATION_RE.search(header_text)
    location = location_match.group(0) if location_match else None

    full_name = None
    for line in lines:
        # The name is conventionally the first line that isn't itself an
        # email, phone number, or location fragment.
        if _EMAIL_RE.search(line) or _PHONE_RE.search(line):
            continue
        if location and line.strip() == location:
            continue
        full_name = line
        break

    return full_name, email, phone, location


# --- Skills extraction ---------------------------------------------------

_SKILL_SPLIT_RE = re.compile(r"[,;•|\u2022\n]")


def extract_skills(section_content: str) -> list[ParsedSkill]:
    if not section_content.strip():
        return []

    raw_items = _SKILL_SPLIT_RE.split(section_content)

    skills: list[ParsedSkill] = []
    seen: set[str] = set()

    for raw in raw_items:
        name = raw.strip(" \t-:")
        if not name or len(name) > 60:
            continue
        # Drop sub-headers like "Languages:" that sometimes appear inline
        # within a skills section.
        if name.endswith(":"):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        skills.append(ParsedSkill(name=name))

    return skills


# --- Date range detection (shared by experience/education) ---------------

_MONTH = (
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
    r"[a-z]*\.?"
)
_DATE_TOKEN = rf"(?:{_MONTH}\.?\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}})"
_PRESENT_TOKEN = r"(?:Present|Current|Now)"

_DATE_RANGE_RE = re.compile(
    rf"(?P<start>{_DATE_TOKEN})\s*(?:-|–|—|to)\s*(?P<end>{_DATE_TOKEN}|{_PRESENT_TOKEN})",
    re.IGNORECASE,
)


def _find_date_range(line: str) -> tuple[str | None, str | None, bool]:
    match = _DATE_RANGE_RE.search(line)
    if not match:
        return None, None, False

    start = match.group("start")
    end = match.group("end")
    is_current = bool(re.match(_PRESENT_TOKEN, end, re.IGNORECASE))
    return start, (None if is_current else end), is_current


def _split_title_company(line: str) -> tuple[str | None, str | None]:
    """Best-effort split of a 'Job Title, Company' / 'Job Title | Company'
    / 'Job Title at Company' / 'Job Title - Company' line."""
    for separator in ("|", " at ", " - ", " – ", ","):
        if separator in line:
            left, right = line.split(separator, 1)
            left, right = left.strip(), right.strip()
            if left and right:
                return left, right
    return line.strip() or None, None


# --- Experience extraction ------------------------------------------------


def extract_experience(section_content: str) -> list[ParsedExperience]:
    lines = [line.strip() for line in section_content.split("\n") if line.strip()]
    if not lines:
        return []

    # Find every line that contains a date range - these anchor the start
    # of each entry (the line immediately before an anchor is
    # conventionally the job title/company header for that entry).
    anchors: list[tuple[int, str, str | None, bool, str]] = []
    for idx, line in enumerate(lines):
        start, end, is_current = _find_date_range(line)
        if start is not None:
            remainder = _DATE_RANGE_RE.sub("", line).strip(" |,-–—")
            anchors.append((idx, start, end, is_current, remainder))

    if not anchors:
        # No dates detected anywhere - can't confidently split into
        # entries. Return everything as a single, low-confidence entry
        # for the user to correct rather than guessing at a split.
        return [ParsedExperience(description="\n".join(lines).strip() or None)]

    entries: list[ParsedExperience] = []

    for i, (idx, start, end, is_current, remainder) in enumerate(anchors):
        header_idx = idx - 1
        header_lines: list[str] = []
        if header_idx >= 0 and not any(a[0] == header_idx for a in anchors):
            header_lines.append(lines[header_idx])
        if remainder:
            header_lines.append(remainder)

        if i + 1 < len(anchors):
            next_header_idx = anchors[i + 1][0] - 1
            description_end = next_header_idx if next_header_idx > idx else anchors[i + 1][0]
        else:
            description_end = len(lines)

        description_lines = [
            line.lstrip("-*•\u2022 \t") for line in lines[idx + 1 : description_end]
        ]

        title, company = (None, None)
        location = None
        if header_lines:
            title, company = _split_title_company(header_lines[0])
            if len(header_lines) > 1:
                location = header_lines[1]

        entries.append(
            ParsedExperience(
                job_title=title,
                company=company,
                location=location,
                start_date=start,
                end_date=end,
                is_current=is_current,
                description="\n".join(description_lines).strip() or None,
            )
        )

    return entries


# --- Education extraction -------------------------------------------------

_DEGREE_KEYWORDS = [
    "bachelor",
    "master",
    "b.s.",
    "b.a.",
    "m.s.",
    "m.a.",
    "ph.d",
    "phd",
    "mba",
    "associate",
    "diploma",
    "b.sc",
    "m.sc",
]


def extract_education(section_content: str) -> list[ParsedEducation]:
    lines = [line.strip() for line in section_content.split("\n") if line.strip()]
    if not lines:
        return []

    anchors: list[tuple[int, str, str | None, str]] = []
    for idx, line in enumerate(lines):
        start, end, _ = _find_date_range(line)
        if start is not None:
            remainder = _DATE_RANGE_RE.sub("", line).strip(" |,-–—")
            anchors.append((idx, start, end, remainder))

    def _split_degree(header_lines: list[str]) -> tuple[str | None, str | None, str | None]:
        degree_line = next(
            (
                line
                for line in header_lines
                if any(keyword in line.lower() for keyword in _DEGREE_KEYWORDS)
            ),
            None,
        )
        non_degree_lines = [line for line in header_lines if line != degree_line]
        institution = non_degree_lines[0] if non_degree_lines else None

        degree, field_of_study = None, None
        if degree_line:
            parts = re.split(r",|\bin\b", degree_line, maxsplit=1)
            degree = parts[0].strip()
            if len(parts) > 1:
                field_of_study = parts[1].strip()

        return institution, degree, field_of_study

    if not anchors:
        # No dates detected - can't confidently split multiple entries,
        # so treat the whole block as a single low-confidence entry.
        institution, degree, field_of_study = _split_degree(lines)
        return [
            ParsedEducation(
                institution=institution, degree=degree, field_of_study=field_of_study
            )
        ]

    entries: list[ParsedEducation] = []
    previous_idx = -1

    for idx, start, end, remainder in anchors:
        header_lines = list(lines[previous_idx + 1 : idx])
        if remainder:
            header_lines.append(remainder)

        institution, degree, field_of_study = _split_degree(header_lines)

        entries.append(
            ParsedEducation(
                institution=institution,
                degree=degree,
                field_of_study=field_of_study,
                start_date=start,
                end_date=end,
            )
        )
        previous_idx = idx

    return entries


# --- Projects extraction ---------------------------------------------------

_TECH_LINE_RE = re.compile(r"^(technologies|tech stack|tools|stack)\s*:\s*(.+)$", re.IGNORECASE)


def extract_projects(section_content: str) -> list[ParsedProject]:
    lines = [line.strip() for line in section_content.split("\n") if line.strip()]
    if not lines:
        return []

    entries: list[ParsedProject] = []
    current_name: str | None = None
    current_description: list[str] = []
    current_tech: str | None = None
    just_saw_tech = False

    def flush() -> None:
        nonlocal current_name, current_description, current_tech
        if current_name is None and not current_description:
            return
        entries.append(
            ParsedProject(
                name=current_name,
                description="\n".join(current_description).strip() or None,
                technologies=current_tech,
            )
        )
        current_name = None
        current_description = []
        current_tech = None

    for line in lines:
        tech_match = _TECH_LINE_RE.match(line)
        if tech_match:
            current_tech = tech_match.group(2).strip()
            just_saw_tech = True
            continue

        is_bullet = line.lstrip().startswith(("-", "*", "•", "\u2022"))
        # A short line with no sentence-ending punctuation reads as a
        # title; a line ending in '.', '!' or '?' reads as prose
        # (description), regardless of length.
        looks_like_title = (
            not is_bullet and len(line) <= 80 and not line.endswith((".", "!", "?"))
        )

        if current_name is None:
            # First line of a fresh block is always the project name.
            current_name = line
            just_saw_tech = False
            continue

        if looks_like_title and not just_saw_tech and current_description:
            # Only treat a later title-like line as the *next* project
            # once the current one has already gathered some description
            # - otherwise a two-line "name, then tech line" block would
            # be mistaken for two separate projects.
            flush()
            current_name = line
            just_saw_tech = False
            continue

        current_description.append(line.lstrip("-*•\u2022 \t"))
        just_saw_tech = False

    flush()

    return entries


# --- Certifications extraction ----------------------------------------------


def extract_certifications(section_content: str) -> list[ParsedCertification]:
    lines = [line.strip() for line in section_content.split("\n") if line.strip()]
    certifications: list[ParsedCertification] = []

    for line in lines:
        clean = line.lstrip("-*•\u2022 \t")
        if not clean:
            continue

        year_match = re.search(r"\b(19|20)\d{2}\b", clean)
        issue_date = year_match.group(0) if year_match else None

        parts = re.split(r",|\||-(?!\d)", clean, maxsplit=1)
        name = parts[0].strip()
        issuer = parts[1].strip() if len(parts) > 1 else None
        if issuer:
            issuer = re.sub(r"\b(19|20)\d{2}\b", "", issuer).strip(" ,-")

        if name:
            certifications.append(
                ParsedCertification(name=name, issuer=issuer or None, issue_date=issue_date)
            )

    return certifications


# --- Top-level orchestration ------------------------------------------------


def parse_resume_text(text: str) -> ParsedResume:
    """Parse raw resume text into a ParsedResume.

    This is the single entry point resume_service should call - it
    coordinates section detection and per-section field extraction, but
    performs no I/O and knows nothing about file formats.
    """
    header_text, sections = split_into_sections(text)
    full_name, email, phone, location = extract_contact_info(header_text)

    result = ParsedResume(
        full_name=full_name,
        email=email,
        phone=phone,
        location=location,
        sections=sections,
    )

    for section in sections:
        if section.section_type == "summary" and not result.summary:
            result.summary = section.content
        elif section.section_type == "skills":
            result.skills.extend(extract_skills(section.content))
        elif section.section_type == "experience":
            result.experiences.extend(extract_experience(section.content))
        elif section.section_type == "education":
            result.education.extend(extract_education(section.content))
        elif section.section_type == "projects":
            result.projects.extend(extract_projects(section.content))
        elif section.section_type == "certifications":
            result.certifications.extend(extract_certifications(section.content))

    return result
