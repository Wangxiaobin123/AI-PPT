from fastapi import APIRouter

from src.api.v1.endpoints import files, generate, health, intent, skills, tasks

v1_router = APIRouter()
v1_router.include_router(health.router, tags=["health"])
v1_router.include_router(intent.router, tags=["intent"])
v1_router.include_router(generate.router, tags=["generate"])
v1_router.include_router(files.router, tags=["files"])
v1_router.include_router(skills.router, tags=["skills"])
v1_router.include_router(tasks.router, tags=["tasks"])
