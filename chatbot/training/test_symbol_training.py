import json
import os

def run_tests():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    
    with open(os.path.join(dir_path, "symbol_knowledge_base.json"), "r") as f:
        db = json.load(f)
        
    symbols = db["symbols"]
    aliases = db["aliases"]
    families = db["families"]
    labels = db["labels"]
    
    print("="*60)
    print("      ENGINEERING SYMBOL TRAINING VALIDATION TEST SUITE")
    print("="*60)
    
    success = True
    
    alias_tests = {
        "CT": "ct",
        "Current Transformer": "ct",
        "ICT": "power_transformer",
        "Voltage Transformer": "pt_cvt"
    }
    
    print("\n[Test Case 1] Verifying Alias Resolutions:")
    for alias, expected in alias_tests.items():
        actual = aliases.get(alias)
        if actual == expected:
            print(f"  PASS: '{alias}' -> '{actual}'")
        else:
            print(f"  FAIL: '{alias}' -> Expected '{expected}', got '{actual}'")
            success = False
            
    label_tests = {
        "tw": "Thickness of Side Wall",
        "h4": "Trench Dimension"
    }
    
    print("\n[Test Case 2] Verifying Label Lookups:")
    for label, expected in label_tests.items():
        actual = labels.get(label)
        if actual == expected:
            print(f"  PASS: '{label}' -> '{actual}'")
        else:
            print(f"  FAIL: '{label}' -> Expected '{expected}', got '{actual}'")
            success = False
            
    family_tests = {
        "transformer_family": ["power_transformer", "ct", "pt_cvt"]
    }
    
    print("\n[Test Case 3] Verifying Family Lookups:")
    for family, expected in family_tests.items():
        actual = families.get(family)
        if actual and set(expected).issubset(set(actual)):
            print(f"  PASS: '{family}' -> {actual}")
        else:
            print(f"  FAIL: '{family}' -> Expected subset {expected}, got {actual}")
            success = False
            
    print("\n" + "="*60)
    if success:
        print("  ALL VALIDATION TESTS PASSED SUCCESSFULLY!")
    else:
        print("  SOME TESTS FAILED. PLEASE VERIFY SYMBOL MAPS.")
    print("="*60)
    
    return success

if __name__ == "__main__":
    run_tests()
