from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.generate_team_insight import (
    generate_team_insight as core_generate_team_insight,
    EventValidationError,
    LLMClientError,
    LLMResponseValidationError,
)

router = APIRouter()


class TeamInsightRequest(BaseModel):
    team_id: str = Field(..., description="Identificador único do time de engenharia", examples=["platform"])
    events: List[Dict[str, Any]] = Field(..., description="Lista de eventos de engenharia com timestamp ISO-8601")


class MetricsResponse(BaseModel):
    merged_prs: int = Field(..., description="Quantidade total de pull requests mergeados")
    average_pr_cycle_time_hours: float = Field(..., description="Tempo médio de ciclo dos PRs pareados em horas")
    deployments: int = Field(..., description="Quantidade total de deployments")
    incidents: int = Field(..., description="Quantidade total de incidentes")


class InsightContent(BaseModel):
    summary: str = Field(..., description="Resumo do desempenho e produtividade gerado pelo LLM")
    recommendations: List[str] = Field(..., description="Lista de recomendações acionáveis geradas pelo LLM")


class TeamInsightResponse(BaseModel):
    team_id: str
    metrics: MetricsResponse
    insight: InsightContent


import json


class DefaultDevLLMClient:
    """Cliente LLM padrão para testes e desenvolvimento local sem chamadas externas."""
    def complete(self, prompt: str, timeout_seconds: int = 10) -> str:
        return json.dumps({
            "summary": "The team merged one pull request with an average cycle time of 24 hours.",
            "recommendations": [
                "Continue monitoring pull request cycle time.",
                "Maintain deployment frequency and monitor production incidents."
            ]
        })


def get_llm_client() -> Any:
    """
    Provedor de dependência para o cliente LLM.
    Retorna um cliente simulado por padrão e pode ser sobrescrito em produção via app.dependency_overrides.
    """
    return DefaultDevLLMClient()


@router.post(
    "/generate_team_insight",
    response_model=TeamInsightResponse,
    status_code=status.HTTP_200_OK,
    summary="Gera métricas agregadas e insights de time via LLM",
)
def create_team_insight(
    payload: TeamInsightRequest,
    llm_client: Any = Depends(get_llm_client),
):
    try:
        result = core_generate_team_insight(
            team_id=payload.team_id,
            events=payload.events,
            llm_client=llm_client,
        )
        return result
    except EventValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except (LLMClientError, LLMResponseValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha no processamento pelo serviço LLM: {exc}",
        )