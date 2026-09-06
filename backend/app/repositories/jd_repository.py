"""
Job description repository.

Mirrors app/repositories/resume_repository.py's pattern: the only layer
allowed to issue SQLAlchemy queries for JD data.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.job_description import JDRequirement, JobDescription


class JDRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, job_description_id: str) -> JobDescription | None:
        query = (
            select(JobDescription)
            .where(JobDescription.id == job_description_id)
            .options(selectinload(JobDescription.requirements))
        )
        return self.db.execute(query).scalar_one_or_none()

    def list_all(self) -> list[JobDescription]:
        query = select(JobDescription).order_by(JobDescription.created_at.desc())
        return list(self.db.execute(query).scalars().all())

    def create(self, job_description: JobDescription) -> JobDescription:
        self.db.add(job_description)
        self.db.commit()
        self.db.refresh(job_description)
        return job_description

    def save(self, job_description: JobDescription) -> JobDescription:
        self.db.add(job_description)
        self.db.commit()
        self.db.refresh(job_description)
        return job_description

    def replace_requirements(
        self, job_description: JobDescription, requirements: list[JDRequirement]
    ) -> None:
        job_description.requirements.clear()
        job_description.requirements.extend(requirements)
