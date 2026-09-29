import pytest
from tests.core import fixtures
from app.core.generate_team_insight import (
    aggregate_metrics,
    agregate_metrics,
    validate_events,
    EventValidationError,
)


# --- 1. Testes de Agregação de Métricas ---

def test_aggregate_metrics_happy_path():
    """Valida o cálculo exato com os eventos fornecidos no fixture."""
    result = aggregate_metrics(fixtures.test_events)
    assert result == fixtures.expected_metrics


def test_agregate_metrics_alias():
    """Garante compatibilidade com o typo 'agregate_metrics' do teste original."""
    result = agregate_metrics(fixtures.test_events)
    assert result == fixtures.expected_metrics


def test_aggregate_metrics_with_unmatched_prs():
    """
    Eventos de PR não-pareados devem ser ignorados no cálculo de cycle time:
    - pr-1: aberto e mergeado após 24h
    - pr-2: aberto mas nunca mergeado (ignorado no cycle time e merged_prs)
    - pr-3: mergeado sem abertura registrada (contado em merged_prs, ignorado no cycle time)
    """
    events = [
        {"type": "pr_opened", "id": "pr-1", "timestamp": "2026-01-01T00:00:00Z"},
        {"type": "pr_merged", "id": "pr-1", "timestamp": "2026-01-02T00:00:00Z"},  # 24h
        {"type": "pr_opened", "id": "pr-2", "timestamp": "2026-01-02T00:00:00Z"},  # sem merge
        {"type": "pr_merged", "id": "pr-3", "timestamp": "2026-01-03T00:00:00Z"},  # sem open
        {"type": "deployment", "timestamp": "2026-01-03T10:00:00Z"},
        {"type": "deployment", "timestamp": "2026-01-03T11:00:00Z"},
        {"type": "incident", "timestamp": "2026-01-04T00:00:00Z"},
    ]
    result = aggregate_metrics(events)
    assert result == {
        "merged_prs": 2,  # pr-1 e pr-3
        "average_pr_cycle_time_hours": 24.0,  # apenas pr-1 tem abertura e merge
        "deployments": 2,
        "incidents": 1,
    }


def test_aggregate_metrics_multiple_paired_prs_average():
    """Valida o cálculo da média com múltiplos PRs pareados."""
    events = [
        {"type": "pr_opened", "id": "pr-1", "timestamp": "2026-01-01T00:00:00Z"},
        {"type": "pr_merged", "id": "pr-1", "timestamp": "2026-01-01T10:00:00Z"},  # 10h
        {"type": "pr_opened", "id": "pr-2", "timestamp": "2026-01-01T00:00:00Z"},
        {"type": "pr_merged", "id": "pr-2", "timestamp": "2026-01-01T20:00:00Z"},  # 20h
    ]
    result = aggregate_metrics(events)
    assert result["merged_prs"] == 2
    assert result["average_pr_cycle_time_hours"] == 15.0  # (10 + 20) / 2


def test_aggregate_metrics_empty_events():
    """Lista vazia de eventos deve retornar contadores zerados e média 0.0."""
    result = aggregate_metrics([])
    assert result == {
        "merged_prs": 0,
        "average_pr_cycle_time_hours": 0.0,
        "deployments": 0,
        "incidents": 0,
    }


# --- 2. Testes de Validação de Eventos ---

def test_validate_events_success():
    """Eventos válidos passam sem levantar exceção."""
    validate_events(fixtures.test_events)


@pytest.mark.parametrize("invalid_events", [
    None,
    "not-a-list",
    [{"type": "deployment"}],  # falta timestamp
    [{"timestamp": "2026-01-01T09:00:00Z"}],  # falta type
    [{"type": "pr_opened", "timestamp": "2026-01-01T09:00:00Z"}],  # PR sem id
    [{"type": "unknown_event", "timestamp": "2026-01-01T09:00:00Z"}],  # tipo desconhecido
    [{"type": "deployment", "timestamp": "2026-01-01 09:00:00"}],  # sem Z e formato inválido
    [{"type": "deployment", "timestamp": "2026-01-01T09:00:00+02:00"}],  # não termina em Z
    [{"type": "deployment", "timestamp": "not-a-dateZ"}],  # data malformada
])
def test_validate_events_raises_for_malformed_input(invalid_events):
    """Eventos malformados devem levantar EventValidationError."""
    with pytest.raises(EventValidationError):
        validate_events(invalid_events)


# --- 3. Testes de Construção do Prompt ---

def test_generate_prompt_structure_and_metrics():
    """O prompt deve conter o team_id, as métricas agregadas e a instrução de saída JSON."""
    from app.core.generate_team_insight import generate_prompt

    prompt = generate_prompt(fixtures.team_id, fixtures.expected_metrics)

    assert isinstance(prompt, str)
    assert fixtures.team_id in prompt
    assert "merged_prs" in prompt
    assert "average_pr_cycle_time_hours" in prompt
    assert "deployments" in prompt
    assert "incidents" in prompt
    # Deve exigir o formato JSON esperado
    assert "summary" in prompt
    assert "recommendations" in prompt


def test_generate_prompt_never_contains_raw_events():
    """Garante que nenhum dado de evento bruto (timestamps ou IDs de PR) vaze no prompt."""
    from app.core.generate_team_insight import generate_prompt

    prompt = generate_prompt(fixtures.team_id, fixtures.expected_metrics)

    for event in fixtures.test_events:
        if "id" in event:
            assert event["id"] not in prompt
        assert event["timestamp"] not in prompt


# --- 4. Testes de Integração LLM, Bounded Retries & Orquestrador ---

class MockLLMClient:
    def __init__(self, side_effects):
        self.side_effects = list(side_effects)
        self.call_count = 0
        self.recorded_calls = []

    def complete(self, prompt, timeout_seconds=10):
        self.call_count += 1
        self.recorded_calls.append({"prompt": prompt, "timeout_seconds": timeout_seconds})
        if not self.side_effects:
            raise RuntimeError("Nenhum retorno mockado restante.")
        effect = self.side_effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect


def test_generate_team_insight_happy_path():
    """Valida o fluxo completo de ponta a ponta com sucesso na 1ª tentativa do LLM."""
    import json
    from app.core.generate_team_insight import generate_team_insight

    mock_llm_response = json.dumps({
        "summary": "The team merged one pull request with an average cycle time of 24 hours.",
        "recommendations": [
            "Continue monitoring pull request cycle time."
        ]
    })
    client = MockLLMClient([mock_llm_response])

    result = generate_team_insight(fixtures.team_id, fixtures.test_events, client)

    assert result == fixtures.expected_complete_result
    assert client.call_count == 1
    assert client.recorded_calls[0]["timeout_seconds"] == 10


def test_generate_team_insight_retry_success_after_transient_error():
    """Recuperação com retry na 2ª tentativa após erro transitório na 1ª."""
    import json
    from app.core.generate_team_insight import generate_team_insight

    valid_response = json.dumps({
        "summary": "The team merged one pull request with an average cycle time of 24 hours.",
        "recommendations": [
            "Continue monitoring pull request cycle time."
        ]
    })
    # 1ª tentativa: Exceção transitória de timeout / rede
    # 2ª tentativa: Sucesso
    client = MockLLMClient([TimeoutError("Transient timeout"), valid_response])

    result = generate_team_insight(fixtures.team_id, fixtures.test_events, client)

    assert result == fixtures.expected_complete_result
    assert client.call_count == 2  # 1 tentativa inicial + 1 retry


def test_generate_team_insight_retry_success_after_invalid_json():
    """Recuperação com retry após a 1ª resposta retornar JSON inválido."""
    import json
    from app.core.generate_team_insight import generate_team_insight

    valid_response = json.dumps({
        "summary": "The team merged one pull request with an average cycle time of 24 hours.",
        "recommendations": ["Continue monitoring pull request cycle time."]
    })
    # 1ª tentativa: JSON quebrado
    # 2ª tentativa: Sucesso
    client = MockLLMClient(["Invalid non-json response", valid_response])

    result = generate_team_insight(fixtures.team_id, fixtures.test_events, client)

    assert result == fixtures.expected_complete_result
    assert client.call_count == 2


def test_generate_team_insight_fails_after_max_one_retry():
    """Garante que o serviço falha após no máximo 1 retry (total de 2 tentativas)."""
    from app.core.generate_team_insight import generate_team_insight, LLMClientError

    # Ambas as tentativas falham
    client = MockLLMClient([
        ConnectionError("First failure"),
        ConnectionError("Second failure"),
        # Se tentasse uma 3ª vez, não deveria acontecer
        ConnectionError("Third failure"),
    ])

    with pytest.raises(LLMClientError):
        generate_team_insight(fixtures.team_id, fixtures.test_events, client)

    assert client.call_count == 2  # Exatamente 2 tentativas (1 inicial + 1 retry)


@pytest.mark.parametrize("invalid_response", [
    "not-json",
    '{"summary": "missing recommendations"}',
    '{"recommendations": ["missing summary"]}',
    '{"summary": 123, "recommendations": ["invalid summary type"]}',
    '{"summary": "valid", "recommendations": "not a list"}',
    '{"summary": "valid", "recommendations": [123, 456]}',  # itens não-string
])
def test_generate_team_insight_rejects_malformed_llm_schema(invalid_response):
    """Rejeita payloads que não respeitam o contrato de tipos {summary: str, recommendations: list[str]}."""
    from app.core.generate_team_insight import generate_team_insight, LLMResponseValidationError

    client = MockLLMClient([invalid_response, invalid_response])

    with pytest.raises(LLMResponseValidationError):
        generate_team_insight(fixtures.team_id, fixtures.test_events, client)

    assert client.call_count == 2


def test_validate_events_item_not_dict():
    """Valida que itens que não sejam dicionários na lista de eventos disparam EventValidationError."""
    with pytest.raises(EventValidationError, match="deve ser um dicionário"):
        validate_events(["not-a-dict"])


def test_validate_llm_response_not_string():
    """Valida que respostas do LLM que não são strings disparam LLMResponseValidationError."""
    from app.core.generate_team_insight import validate_llm_response, LLMResponseValidationError

    with pytest.raises(LLMResponseValidationError, match="deve ser uma string"):
        validate_llm_response(None)


def test_validate_llm_response_json_not_dict():
    """Valida que JSON que é uma lista dispara LLMResponseValidationError."""
    from app.core.generate_team_insight import validate_llm_response, LLMResponseValidationError

    with pytest.raises(LLMResponseValidationError, match="deve ser um objeto/dicionário"):
        validate_llm_response("[]")
