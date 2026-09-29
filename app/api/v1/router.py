from fastapi import APIRouter
from app.api.v1.endpoints import generate_team_insight, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(generate_team_insight.router, tags=["Team Insights"])
