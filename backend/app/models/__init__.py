"""
SQLAlchemy models package.

Importing this package registers all ORM models on `Base.metadata`,
which is required for Alembic autogenerate and for `init_db()` to create
tables. Every new model module must be imported here.
"""

from app.models.resume import (  # noqa: F401
    Certification,
    Education,
    Experience,
    Project,
    Resume,
    ResumeSection,
    ResumeStatus,
    Skill,
    SourceType,
)
from app.models.job_description import (  # noqa: F401
    Importance,
    JDRequirement,
    JobDescription,
    JobDescriptionStatus,
    RequirementType,
)
from app.models.analysis import (  # noqa: F401
    Analysis,
    MatchType,
    SkillMatch,
)
