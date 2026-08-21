import json
import os
import sys

SYSTEM_DESCRIPTION = (
    "Trained using a custom engineering symbol knowledge base, equipment taxonomy, "
    "alias mappings, and drawing-label datasets to recognize electrical and civil "
    "engineering components from CAD drawings and engineering documents."
)

def train_symbol_database():
    """
    Compiles and builds:
    - Symbol Index
    - Alias Index
    - Family Index
    - Label Index
    This index is used by the chatbot during CAD analysis.
    """
    print("[Symbol Trainer] Starting symbol training compilation pipeline...")
    print(f"[Symbol Trainer] System Description: {SYSTEM_DESCRIPTION}")
    
    dir_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(dir_path)
    
    try:
        import train_symbol_knowledge
        train_symbol_knowledge.main()
    except ImportError:
        print("[Symbol Trainer] Could not import train_symbol_knowledge module, executing manually...")
        
    db_path = os.path.join(dir_path, "symbol_knowledge_base.json")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Trained knowledge base not found at {db_path}")
        
    with open(db_path, "r") as f:
        db = json.load(f)
        
    symbol_index = db["symbols"]
    alias_index = db["aliases"]
    family_index = db["families"]
    label_index = db["labels"]
    
    print("[Symbol Trainer] Compiled memory lookup indices:")
    print(f"  - Symbol Index: {len(symbol_index)} entries")
    print(f"  - Alias Index: {len(alias_index)} entries")
    print(f"  - Family Index: {len(family_index)} entries")
    print(f"  - Label Index: {len(label_index)} entries")
    
    return {
        "symbol_index": symbol_index,
        "alias_index": alias_index,
        "family_index": family_index,
        "label_index": label_index,
        "description": SYSTEM_DESCRIPTION
    }

if __name__ == "__main__":
    train_symbol_database()
