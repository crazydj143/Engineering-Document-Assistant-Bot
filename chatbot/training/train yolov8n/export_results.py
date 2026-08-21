import os
import sys

def main():
    print("=" * 60)
    print("YOLOv8 MODEL EVALUATION & RESULTS EXPORT")
    print("=" * 60)
    
    workspace_dir = r"d:\intern\verum intern3"
    train_dir = os.path.join(workspace_dir, "training", "runs", "detect")
    weights_path = os.path.join(train_dir, "weights", "best.pt")
    
    if not os.path.exists(weights_path):
        print(f"Error: Trained weights not found at {weights_path}.")
        print("Please run training first before evaluating.")
        sys.exit(1)
        
    print(f"Model weights verified at: {weights_path}")
    
    expected_files = [
        "results.csv",
        "confusion_matrix.png",
        "PR_curve.png",
        "F1_curve.png"
    ]
    
    print("\nVerifying training artifacts in runs directory:")
    all_exist = True
    for f in expected_files:
        p = os.path.join(train_dir, f)
        exists = os.path.exists(p)
        status = "EXISTS" if exists else "MISSING"
        print(f"  - {f:<25} : {status}")
        if not exists:
            all_exist = False
            
    if all_exist:
        print("All required curves, logs, and matrices exist.")
    else:
        print("Warning: Some verification assets were not generated yet.")
        
    try:
        from ultralytics import YOLO
        model = YOLO(weights_path)
        print("\nRunning model evaluation on validation split...")
        
        metrics = model.val(verbose=False)
        
        precision = metrics.results_dict.get("metrics/precision(B)", 0.0)
        recall = metrics.results_dict.get("metrics/recall(B)", 0.0)
        map50 = metrics.results_dict.get("metrics/mAP50(B)", 0.0)
        map95 = metrics.results_dict.get("metrics/mAP50-95(B)", 0.0)
        
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0
            
        print("\n" + "=" * 50)
        print("VALIDATION METRICS SUMMARY")
        print("=" * 50)
        print(f"Precision:   {precision:.4f} ({precision * 100:.2f}%)")
        print(f"Recall:      {recall:.4f} ({recall * 100:.2f}%)")
        print(f"mAP50:       {map50:.4f} ({map50 * 100:.2f}%)")
        print(f"mAP50-95:    {map95:.4f} ({map95 * 100:.2f}%)")
        print(f"F1 Score:    {f1:.4f} ({f1 * 100:.2f}%)")
        print("=" * 50)
        
    except Exception as e:
        print(f"\nError encountered during validation execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
