from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()
api_router.include_router(health.router)

# Future sprints will register additional routers here, e.g.:
# api_router.include_router(resumes.router)
# api_router.include_router(job_descriptions.router)
# api_router.include_router(analysis.router)
