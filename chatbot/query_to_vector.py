import groq_client

def generate_dynamic_quick_questions(chunks_db):
    """
    Asks Groq to suggest five concise engineering questions based on the document excerpt.
    """
    if not chunks_db:
        return [
            ("Summary", "Give me a summary of the document"),
            ("Key Concepts", "What are the key concepts in this document?"),
            ("Key Details", "What are the most important details in this document?")
        ]

    try:
        excerpt = " ".join([c["content"] for c in chunks_db[:5]])
        system_msg = (
            "You are a helpful assistant. Based on the given document excerpt, suggest five concise, "
            "relevant engineering questions a user might ask. Return each question on a separate line "
            "without numbering, prefixes, or extra formatting. Keep them under 60 characters."
        )
        user_msg = f"Excerpt:\n{excerpt}"
        
        response = groq_client.generate_groq_response(system_msg, user_msg)
        qs = []
        for line in response.splitlines():
            q = line.strip()
            if q and not q.startswith(("[", "Here", "Sure")):
                import re
                q_clean = re.sub(r'^\d+[\.\)\s\-]+', '', q).strip()
                if q_clean:
                    qs.append((q_clean[:25] + "..." if len(q_clean) > 25 else q_clean, q_clean))
        
        if qs:
            return qs[:5]
    except Exception as e:
        print(f"[query_to_vector] Error generating dynamic questions: {e}")

    return [
        ("Summary", "Give me a summary of the document"),
        ("Key Concepts", "What are the key concepts and terms in this document?"),
        ("Structure", "Can you explain the structure and organization of this document?"),
        ("Key Details", "What are the most important details and findings in this document?"),
        ("Takeaways", "What are the main takeaways from this document?")
    ]

def generate_suggestions(chunks_db):
    """
    Generates autocomplete suggestions for search query.
    """
    suggestions = []
    
    qs = generate_dynamic_quick_questions(chunks_db)
    for label, question in qs:
        if question not in suggestions:
            suggestions.append(question)
            
    extracted = set()
    for chunk in chunks_db:
        content = chunk.get("content", "")
        for part in content.split("."):
            part_str = part.strip()
            if part_str.endswith("?") and 15 < len(part_str) < 120:
                clean_q = part_str.replace("\n", " ").strip()
                if clean_q.startswith(("- ", "* ", "1. ", "2. ", "3. ", "4. ", "5. ")):
                    parts = clean_q.split(" ", 1)
                    if len(parts) > 1:
                        clean_q = parts[1]
                extracted.add(clean_q)
                if len(extracted) >= 12:
                    break
        if len(extracted) >= 12:
            break
            
    for q in extracted:
        if q not in suggestions:
            suggestions.append(q)
            
    std_questions = [
        "What is the summary of this document?",
        "What are the key formulas or equations mentioned?",
        "What are the safety margins, limits, or parameters?",
        "List all standards, testing methods, or references.",
        "What are the main takeaways from this document?"
    ]
    for q in std_questions:
        if q not in suggestions:
            suggestions.append(q)
            
    return suggestions
