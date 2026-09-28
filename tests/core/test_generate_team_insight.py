from tests.core import fixtures

from app.core.generate_team_insight import generate_team_insight, agregate_metrics, generate_prompt


def test_agregate_metrics():
    result = agregate_metrics(fixtures.test_events)
    assert result == fixtures.expected_metrics


def test_generate_prompt():
    result = generate_prompt(fixtures.team_id, fixtures.expected_metrics)
    assert result == fixtures.expected_prompt

