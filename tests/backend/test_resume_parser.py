from app.core.parsing.resume_parser import (
    extract_certifications,
    extract_education,
    extract_experience,
    extract_projects,
    extract_skills,
    parse_resume_text,
)

SAMPLE_RESUME_TEXT = """Jane Doe
jane.doe@example.com
(512) 555-1234
Austin, TX

Summary
Experienced software engineer with a passion for backend systems.

Experience
Senior Software Engineer, Acme Corp
Austin, TX | Jan 2020 - Present
- Built scalable APIs using Python and FastAPI
- Led a team of 4 engineers

Software Engineer, Beta Inc
Jun 2017 - Dec 2019
- Developed internal tooling in Django

Education
University of Texas at Austin
Bachelor of Science in Computer Science
Aug 2013 - May 2017

Skills
Python, FastAPI, Django, SQL, Docker, AWS

Projects
Resume Parser
Technologies: Python, regex
A tool that parses resumes into structured data.

Certifications
AWS Certified Solutions Architect - Amazon, 2021
"""


class TestSkillExtraction:
    def test_extracts_comma_separated_skills(self):
        skills = extract_skills("Python, FastAPI, Django, SQL")

        assert [s.name for s in skills] == ["Python", "FastAPI", "Django", "SQL"]

    def test_deduplicates_case_insensitively(self):
        skills = extract_skills("Python, python, PYTHON, SQL")

        assert [s.name for s in skills] == ["Python", "SQL"]

    def test_handles_bulleted_lines(self):
        skills = extract_skills("• Python\n• SQL\n• Docker")

        assert [s.name for s in skills] == ["Python", "SQL", "Docker"]

    def test_empty_section_yields_no_skills(self):
        assert extract_skills("") == []
        assert extract_skills("   \n  ") == []


class TestExperienceExtraction:
    def test_extracts_single_entry(self):
        entries = extract_experience(
            "Software Engineer, Beta Inc\nJun 2017 - Dec 2019\n- Developed internal tooling"
        )

        assert len(entries) == 1
        entry = entries[0]
        assert entry.job_title == "Software Engineer"
        assert entry.company == "Beta Inc"
        assert entry.start_date == "Jun 2017"
        assert entry.end_date == "Dec 2019"
        assert entry.is_current is False
        assert "Developed internal tooling" in entry.description

    def test_extracts_multiple_entries_without_bleed(self):
        content = (
            "Senior Software Engineer, Acme Corp\n"
            "Austin, TX | Jan 2020 - Present\n"
            "- Built scalable APIs\n"
            "- Led a team of 4 engineers\n"
            "Software Engineer, Beta Inc\n"
            "Jun 2017 - Dec 2019\n"
            "- Developed internal tooling in Django"
        )

        entries = extract_experience(content)

        assert len(entries) == 2
        first, second = entries

        assert first.job_title == "Senior Software Engineer"
        assert first.company == "Acme Corp"
        assert first.is_current is True
        assert "Built scalable APIs" in first.description
        # The second entry's header must not leak into the first entry's
        # description - this was a real bug caught during manual testing.
        assert "Beta Inc" not in first.description

        assert second.job_title == "Software Engineer"
        assert second.company == "Beta Inc"
        assert second.start_date == "Jun 2017"
        assert second.end_date == "Dec 2019"
        assert "Developed internal tooling in Django" in second.description

    def test_no_dates_returns_single_low_confidence_entry(self):
        entries = extract_experience("Some unstructured text with no dates at all")

        assert len(entries) == 1
        assert entries[0].start_date is None

    def test_empty_section_yields_no_entries(self):
        assert extract_experience("") == []


class TestEducationExtraction:
    def test_extracts_institution_degree_and_field(self):
        content = (
            "University of Texas at Austin\n"
            "Bachelor of Science in Computer Science\n"
            "Aug 2013 - May 2017"
        )

        entries = extract_education(content)

        assert len(entries) == 1
        entry = entries[0]
        assert entry.institution == "University of Texas at Austin"
        assert entry.degree == "Bachelor of Science"
        assert entry.field_of_study == "Computer Science"
        assert entry.start_date == "Aug 2013"
        assert entry.end_date == "May 2017"

    def test_extracts_multiple_entries(self):
        content = (
            "Seattle University\n"
            "Master of Science in Software Engineering\n"
            "2016 - 2018\n"
            "State College\n"
            "Bachelor of Arts in Mathematics\n"
            "2010 - 2014"
        )

        entries = extract_education(content)

        assert len(entries) == 2
        assert entries[0].institution == "Seattle University"
        assert entries[1].institution == "State College"
        assert entries[1].field_of_study == "Mathematics"


class TestProjectExtraction:
    def test_extracts_name_technologies_and_description(self):
        content = (
            "Resume Parser\n"
            "Technologies: Python, regex\n"
            "A tool that parses resumes into structured data."
        )

        entries = extract_projects(content)

        assert len(entries) == 1
        entry = entries[0]
        assert entry.name == "Resume Parser"
        assert entry.technologies == "Python, regex"
        assert entry.description == "A tool that parses resumes into structured data."

    def test_does_not_split_description_sentence_into_new_project(self):
        # Regression test for a real bug: a description sentence ending
        # in a period must never be mistaken for the next project's name.
        content = "My Project\nTechnologies: Go\nThis sentence describes what it does."

        entries = extract_projects(content)

        assert len(entries) == 1


class TestCertificationExtraction:
    def test_extracts_name_issuer_and_year(self):
        entries = extract_certifications("AWS Certified Solutions Architect - Amazon, 2021")

        assert len(entries) == 1
        entry = entries[0]
        assert entry.name == "AWS Certified Solutions Architect"
        assert entry.issuer == "Amazon"
        assert entry.issue_date == "2021"

    def test_extracts_multiple_lines(self):
        entries = extract_certifications(
            "AWS Certified Solutions Architect - Amazon, 2021\n"
            "Certified Kubernetes Administrator - CNCF, 2022"
        )

        assert len(entries) == 2


class TestFullResumeParse:
    def test_parses_all_sections_from_full_resume(self):
        result = parse_resume_text(SAMPLE_RESUME_TEXT)

        assert result.full_name == "Jane Doe"
        assert result.email == "jane.doe@example.com"
        assert result.phone == "(512) 555-1234"
        assert result.location == "Austin, TX"
        assert "backend systems" in result.summary

        assert {s.name for s in result.skills} == {
            "Python",
            "FastAPI",
            "Django",
            "SQL",
            "Docker",
            "AWS",
        }
        assert len(result.experiences) == 2
        assert len(result.education) == 1
        assert len(result.projects) == 1
        assert len(result.certifications) == 1
        assert result.has_meaningful_content is True

    def test_resume_with_no_recognizable_sections_has_no_meaningful_content(self):
        result = parse_resume_text("Just some random text with no headers at all.")

        assert result.has_meaningful_content is False
