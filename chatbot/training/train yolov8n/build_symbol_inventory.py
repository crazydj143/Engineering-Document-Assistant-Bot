import json
import os

def build_inventory_from_dxf(drawing_name, detected_block_counts):
    """
    Given a list of raw CAD block counts or labels detected in the drawing,
    this function translates them using our trained alias and family taxonomy
    to return a standard, professional component inventory.
    """
    dir_path = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(dir_path, "symbol_knowledge_base.json")
    
    if not os.path.exists(db_path):
        print(f"[Inventory Builder] Knowledge base not found. Running training first...")
        from symbol_trainer import train_symbol_database
        db_indexes = train_symbol_database()
        symbol_index = db_indexes["symbol_index"]
        alias_index = db_indexes["alias_index"]
        family_index = db_indexes["family_index"]
    else:
        with open(db_path, "r") as f:
            db = json.load(f)
        symbol_index = db["symbols"]
        alias_index = db["aliases"]
        family_index = db["families"]
        
    print(f"[Inventory Builder] Analyzing drawing '{drawing_name}' block counts against trained mappings...")
    
    standardized_inventory = {}
    
    for block_name, count in detected_block_counts.items():
        standard_key = None
        if block_name in symbol_index:
            standard_key = block_name
        elif block_name in alias_index:
            standard_key = alias_index[block_name]
        else:
            for alias, target_key in alias_index.items():
                if alias.lower() == block_name.lower():
                    standard_key = target_key
                    break
                    
        if standard_key:
            sym_info = symbol_index.get(standard_key, {"name": standard_key.upper(), "category": "unknown"})
            sym_name = sym_info["name"]
            standardized_inventory[sym_name] = standardized_inventory.get(sym_name, 0) + count
            print(f"  - Matched '{block_name}' -> '{sym_name}' ({count} units)")
        else:
            standardized_inventory[block_name.upper()] = standardized_inventory.get(block_name.upper(), 0) + count
            print(f"  - Unrecognized element '{block_name}', added as raw component ({count} units)")
            
    return standardized_inventory

def run_sample_verification():
    """
    Run sample verification mode.
    Input: ["CT", "Current Transformer", "ICT", "Breaker"]
    Expected Output:
    {
      "ct": 2,
      "power_transformer": 1,
      "breaker": 1
    }
    """
    sample_input = ["CT", "Current Transformer", "ICT", "Breaker"]
    
    dir_path = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(dir_path, "symbol_knowledge_base.json")
    
    if not os.path.exists(db_path):
        from symbol_trainer import train_symbol_database
        db_indexes = train_symbol_database()
        symbol_index = db_indexes["symbol_index"]
        alias_index = db_indexes["alias_index"]
    else:
        with open(db_path, "r") as f:
            db = json.load(f)
        symbol_index = db["symbols"]
        alias_index = db["aliases"]
        
    print("="*60)
    print("        ENGINEERING SYMBOL INVENTORY BUILD VERIFICATION")
    print("="*60)
    print(f"Sample Input: {sample_input}")
    
    inventory = {}
    
    for item in sample_input:
        standard_key = None
        if item.lower() in symbol_index:
            standard_key = item.lower()
        elif item in alias_index:
            standard_key = alias_index[item]
        else:
            for alias, key in alias_index.items():
                if alias.lower() == item.lower():
                    standard_key = key
                    break
                    
        if standard_key:
            inventory[standard_key] = inventory.get(standard_key, 0) + 1
            print(f"  Matched: '{item}' -> '{standard_key}'")
        else:
            inventory[item.lower()] = inventory.get(item.lower(), 0) + 1
            print(f"  Unmatched: '{item}' added as raw standard key '{item.lower()}'")
            
    print("\nInventory Summary Output:")
    print(json.dumps(inventory, indent=2))
    print("="*60)
    
    return inventory

if __name__ == "__main__":
    run_sample_verification()
