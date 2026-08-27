from fastapi import APIRouter

from app.api.v1 import health, resumes

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(resumes.router)

# Future sprints will register additional routers here, e.g.:
# api_router.include_router(job_descriptions.router)
# api_router.include_router(analysis.router)
