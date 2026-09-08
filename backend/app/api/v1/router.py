from fastapi import APIRouter

from app.api.v1 import analyses, health, job_descriptions, resumes

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(resumes.router)
api_router.include_router(job_descriptions.router)
api_router.include_router(analyses.router)
