import json
from datetime import datetime
from typing import Any, Dict, List, Optional


class EventValidationError(Exception):
    """Exceção levantada quando um evento ou lista de eventos é inválido."""
    pass


class LLMClientError(Exception):
    """Exceção levantada em falhas de comunicação com o cliente LLM."""
    pass


class LLMResponseValidationError(Exception):
    """Exceção levantada quando a resposta do LLM não respeita o schema esperado."""
    pass


SUPPORTED_EVENT_TYPES = {"pr_opened", "pr_merged", "deployment", "incident"}


def _parse_timestamp(timestamp_str: Any) -> datetime:
    """Valida e converte timestamp ISO-8601 terminado obrigatoriamente em 'Z'."""
    if not isinstance(timestamp_str, str) or not timestamp_str.endswith("Z"):
        raise EventValidationError(
            f"Timestamp inválido: deve ser uma string ISO-8601 terminada em 'Z'. Recebido: {timestamp_str!r}"
        )
    try:
        # Substitui 'Z' por '+00:00' para garantir compatibilidade completa com datetime.fromisoformat
        return datetime.fromisoformat(timestamp_str[:-1] + "+00:00")
    except Exception as exc:
        raise EventValidationError(f"Timestamp malformado: {timestamp_str!r}") from exc


def validate_events(events: Any) -> None:
    """Valida a integridade da lista de eventos recebida."""
    if not isinstance(events, list):
        raise EventValidationError(f"O payload de eventos deve ser uma lista, recebido: {type(events).__name__}")

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise EventValidationError(f"O evento no índice {index} deve ser um dicionário.")

        event_type = event.get("type")
        if not event_type or event_type not in SUPPORTED_EVENT_TYPES:
            raise EventValidationError(
                f"Evento no índice {index} possui tipo inválido ou ausente: {event_type!r}. "
                f"Tipos suportados: {sorted(SUPPORTED_EVENT_TYPES)}"
            )

        if "timestamp" not in event:
            raise EventValidationError(f"Evento no índice {index} não contém o campo obrigatório 'timestamp'.")

        _parse_timestamp(event["timestamp"])

        if event_type in {"pr_opened", "pr_merged"}:
            pr_id = event.get("id")
            if not pr_id or not isinstance(pr_id, str):
                raise EventValidationError(
                    f"Evento do tipo '{event_type}' no índice {index} requer um campo 'id' não-vazio."
                )


def aggregate_metrics(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcula métricas determinísticas a partir dos eventos de engenharia:
    - merged_prs: contagem de PRs mergeados
    - average_pr_cycle_time_hours: média de horas entre abertura e merge de PRs pareados
    - deployments: contagem de eventos de deploy
    - incidents: contagem de eventos de incidente
    """
    validate_events(events)

    opened_prs: Dict[str, datetime] = {}
    merged_prs: Dict[str, datetime] = {}
    merged_prs_count = 0
    deployments_count = 0
    incidents_count = 0

    for event in events:
        event_type = event["type"]
        ts = _parse_timestamp(event["timestamp"])

        if event_type == "pr_opened":
            opened_prs[event["id"]] = ts
        elif event_type == "pr_merged":
            merged_prs_count += 1
            merged_prs[event["id"]] = ts
        elif event_type == "deployment":
            deployments_count += 1
        elif event_type == "incident":
            incidents_count += 1

    # Calcula o tempo de ciclo apenas para PRs que possuem ambos os eventos (abertura e merge)
    cycle_times_hours: List[float] = []
    for pr_id, merge_ts in merged_prs.items():
        if pr_id in opened_prs:
            open_ts = opened_prs[pr_id]
            diff_hours = (merge_ts - open_ts).total_seconds() / 3600.0
            if diff_hours >= 0:
                cycle_times_hours.append(diff_hours)

    avg_cycle_time = (
        round(sum(cycle_times_hours) / len(cycle_times_hours), 2)
        if cycle_times_hours
        else 0.0
    )

    return {
        "merged_prs": merged_prs_count,
        "average_pr_cycle_time_hours": avg_cycle_time,
        "deployments": deployments_count,
        "incidents": incidents_count,
    }


# Alias mantido para compatibilidade com o teste pré-existente
agregate_metrics = aggregate_metrics


def generate_prompt(team_id: str, metrics: Dict[str, Any]) -> str:
    """
    Constrói o prompt contendo exclusivamente o team_id e as métricas agregadas.
    Instrui o modelo a responder estritamente no formato JSON solicitado.
    """
    metrics_json = json.dumps(metrics, indent=2)
    return (
        f"You are an engineering leadership assistant. Analyze the productivity metrics for team '{team_id}'.\n\n"
        f"Aggregated Metrics:\n{metrics_json}\n\n"
        "Instructions:\n"
        "1. Provide a concise summary of the team's engineering productivity based solely on these metrics.\n"
        "2. Provide actionable recommendations for the team.\n"
        "3. Do not rank or compare individual engineers.\n"
        "4. Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "summary": "string",\n'
        '  "recommendations": ["string"]\n'
        "}\n"
    )


def validate_llm_response(raw_response: Any) -> Dict[str, Any]:
    """Valida se a resposta do LLM é um JSON válido com o schema exigido."""
    if not isinstance(raw_response, str):
        raise LLMResponseValidationError(
            f"Resposta do LLM deve ser uma string, recebido: {type(raw_response).__name__}"
        )

    try:
        data = json.loads(raw_response)
    except Exception as exc:
        raise LLMResponseValidationError(f"Resposta do LLM não é um JSON válido: {exc}") from exc

    if not isinstance(data, dict):
        raise LLMResponseValidationError("JSON do LLM deve ser um objeto/dicionário.")

    summary = data.get("summary")
    if not isinstance(summary, str):
        raise LLMResponseValidationError("O campo 'summary' deve ser uma string.")

    recommendations = data.get("recommendations")
    if not isinstance(recommendations, list) or not all(isinstance(rec, str) for rec in recommendations):
        raise LLMResponseValidationError("O campo 'recommendations' deve ser uma lista de strings.")

    return {
        "summary": summary,
        "recommendations": recommendations,
    }


def call_llm_with_retry(llm_client: Any, prompt: str, timeout_seconds: int = 10) -> Dict[str, Any]:
    """
    Executa a chamada ao cliente LLM com estratégia de retry limitado (máximo 1 retry após tentativa inicial).
    """
    last_error: Optional[Exception] = None

    for attempt in range(2):  # Tentativa 1 (inicial) e Tentativa 2 (retry único)
        try:
            raw_response = llm_client.complete(prompt, timeout_seconds=timeout_seconds)
            return validate_llm_response(raw_response)
        except LLMResponseValidationError as exc:
            last_error = exc
        except Exception as exc:
            last_error = LLMClientError(f"Falha na comunicação com o LLM (tentativa {attempt + 1}): {exc}")

    if isinstance(last_error, LLMResponseValidationError):
        raise last_error
    raise last_error or LLMClientError("Falha desconhecida ao invocar o LLM.")


def generate_team_insight(
    team_id: str,
    events: List[Dict[str, Any]],
    llm_client: Any,
) -> Dict[str, Any]:
    """
    Função principal que orquestra o cálculo de métricas e geração de insight via LLM.
    """
    metrics = aggregate_metrics(events)
    prompt = generate_prompt(team_id, metrics)
    insight = call_llm_with_retry(llm_client, prompt, timeout_seconds=10)

    return {
        "team_id": team_id,
        "metrics": metrics,
        "insight": insight,
    }