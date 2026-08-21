import streamlit as st
import re

roman_map = {
    "1": "I", "2": "II", "3": "III", "4": "IV", "5": "V",
    "6": "VI", "7": "VII", "8": "VIII", "9": "IX", "10": "X"
}

def answer_structure_query(q: str) -> str:
    """
    Answers structure-based queries directly using the document_structure.
    No embeddings, no LLM.
    """
    structure = st.session_state.get("document_structure", {})
    if not structure:
        return "No document structure available. Please upload a PDF first."
        
    q_lower = q.lower()
    
    unit_match = re.search(r'unit\s*([ivxlcdm0-9]+)', q_lower)
    if unit_match:
        unit_val = unit_match.group(1).upper()
        roman_val = roman_map.get(unit_val, unit_val)
        
        target_unit_numeric = f"UNIT {unit_val}"
        target_unit_roman = f"UNIT {roman_val}"
        
        found_unit = None
        for key in structure.keys():
            key_upper = key.upper()
            if key_upper == target_unit_numeric or key_upper == target_unit_roman:
                found_unit = key
                break
                
        if found_unit:
            topics = structure[found_unit]
            topics_str = "\n".join([f"- {t}" for t in topics])
            return f"Here are the topics from **{found_unit}**:\n\n{topics_str}"
        else:
            return f"Could not find **Unit {unit_val}** in the document structure."
            
    res = "Here is the structure of the document:\n\n"
    for unit, topics in structure.items():
        topics_str = ", ".join(topics)
        res += f"### {unit}\n{topics_str}\n\n"
    return res
