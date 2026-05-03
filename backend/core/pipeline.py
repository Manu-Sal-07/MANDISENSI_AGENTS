from mandisense_ai.orchestrator.query_intelligence import handle_query as ml_handle_query


def handle_query(user_query: str) -> dict:
    return ml_handle_query(user_query)
