def generate_team_insight(team_id, events, llm_client):
    events = agregate_metrics(events)

    prompt = generate_prompt(team_id, events)

    response = llm_client(prompt)

    return response

def agregate_metrics(events):
    pass

def generate_prompt(team_id, events):
    pass