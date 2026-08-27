"""
Resume repository.

This is the only layer allowed to issue SQLAlchemy queries for resume
data. Services call into here; nothing above this layer should import
sqlalchemy directly for resume-related persistence.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.resume import (
    Certification,
    Education,
    Experience,
    Project,
    Resume,
    ResumeSection,
    Skill,
)


def _with_relationships(query):
    return query.options(
        selectinload(Resume.sections),
        selectinload(Resume.skills),
        selectinload(Resume.experiences),
        selectinload(Resume.projects),
        selectinload(Resume.education_entries),
        selectinload(Resume.certifications),
    )


class ResumeRepository:
    def __init__(self, db: Session):
        self.db = db

    # --- Reads ---

    def get(self, resume_id: str) -> Resume | None:
        query = _with_relationships(select(Resume).where(Resume.id == resume_id))
        return self.db.execute(query).scalar_one_or_none()

    def list_all(self) -> list[Resume]:
        query = select(Resume).order_by(Resume.created_at.desc())
        return list(self.db.execute(query).scalars().all())

    def stored_filename_exists(self, stored_filename: str) -> bool:
        query = select(Resume.id).where(Resume.stored_filename == stored_filename)
        return self.db.execute(query).scalar_one_or_none() is not None

    # --- Writes ---

    def create(self, resume: Resume) -> Resume:
        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)
        return resume

    def save(self, resume: Resume) -> Resume:
        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)
        return resume

    def replace_skills(self, resume: Resume, skills: list[Skill]) -> None:
        resume.skills.clear()
        resume.skills.extend(skills)

    def replace_experiences(self, resume: Resume, experiences: list[Experience]) -> None:
        resume.experiences.clear()
        resume.experiences.extend(experiences)

    def replace_projects(self, resume: Resume, projects: list[Project]) -> None:
        resume.projects.clear()
        resume.projects.extend(projects)

    def replace_education(self, resume: Resume, education_entries: list[Education]) -> None:
        resume.education_entries.clear()
        resume.education_entries.extend(education_entries)

    def replace_certifications(
        self, resume: Resume, certifications: list[Certification]
    ) -> None:
        resume.certifications.clear()
        resume.certifications.extend(certifications)

    def replace_sections(self, resume: Resume, sections: list[ResumeSection]) -> None:
        resume.sections.clear()
        resume.sections.extend(sections)

    def commit(self) -> None:
        self.db.commit()
