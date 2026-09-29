test_team_id = "platform"
team_id = test_team_id
test_events = [
    {
        "type": "pr_opened",
        "id": "pr-1",
        "timestamp": "2026-01-01T09:00:00Z"
    },
    {
        "type": "pr_merged",
        "id": "pr-1",
        "timestamp": "2026-01-02T09:00:00Z"
    },
    {
        "type": "deployment",
        "timestamp": "2026-01-03T12:00:00Z"
    },
    {
        "type": "incident",
        "timestamp": "2026-01-04T12:00:00Z"
    }
]

expected_metrics = {
    "merged_prs": 1,
    "average_pr_cycle_time_hours": 24.0,
    "deployments": 1,
    "incidents": 1
}

expected_complete_result = {
  "team_id": "platform",
  "metrics": expected_metrics,
  "insight": {
    "summary": "The team merged one pull request with an average cycle time of 24 hours.",
    "recommendations": [
      "Continue monitoring pull request cycle time."
    ]
  }
}

expected_prompt = ""