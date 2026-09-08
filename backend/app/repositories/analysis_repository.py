"""
Analysis repository - the only layer that talks SQLAlchemy directly for
analysis/match data.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.analysis import Analysis, SkillMatch


class AnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, analysis_id: str) -> Analysis | None:
        query = (
            select(Analysis)
            .where(Analysis.id == analysis_id)
            .options(selectinload(Analysis.matches))
        )
        return self.db.execute(query).scalar_one_or_none()

    def create(self, analysis: Analysis, matches: list[SkillMatch]) -> Analysis:
        analysis.matches.extend(matches)
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def list_all(self) -> list[Analysis]:
        query = select(Analysis).order_by(Analysis.created_at.desc())
        return list(self.db.execute(query).scalars().all())
