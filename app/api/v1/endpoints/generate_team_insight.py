from fastapi import APIRouter
from core.generate_team_insight import generate_team_insight

router = APIRouter()


@router.get("/generate_team_insight", summary="generate_team_insight")
async def get_team_insight(team_id, events, llm_client):
    return generate_team_insight(team_id, events, llm_client)