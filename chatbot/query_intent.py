def determine_query_intent(q: str) -> str:
    """
    Determines if the query is a STRUCTURE question or a RAG question.
    """
    q_lower = q.lower()
    if "topics" in q_lower or "units" in q_lower or "unit" in q_lower or "topic" in q_lower:
        return "STRUCTURE"
    return "RAG"
