import os
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Train YOLOv8n model on electrical engineering symbols.")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--batch", type=str, default="-1", help="Batch size. Use -1 for auto-tuning")
    parser.add_argument("--imgsz", type=int, default=640, help="Image training resolution size")
    args = parser.parse_args()
    
    print("=" * 60)
    print("YOLOv8 ELECTRICAL SYMBOLS MODEL TRAINING")
    print("=" * 60)

    try:
        import torch
        cuda_available = torch.cuda.is_available()
        device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU"
        print(f"CUDA Available: {cuda_available} (Device: {device_name})")
    except ImportError:
        print("Warning: PyTorch not found. Ultralytics will install it automatically during import.")
        cuda_available = False
        device_name = "CPU"
        
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Error: Ultralytics package is not installed. Please run 'pip install ultralytics'.")
        sys.exit(1)
        
    workspace_dir = r"d:\intern\verum intern3"
    yaml_path = os.path.join(workspace_dir, "training", "yolo_dataset", "data.yaml")
    
    if not os.path.exists(yaml_path):
        print(f"Error: dataset configuration file not found at {yaml_path}.")
        print("Please run 'python training/validate_dataset.py' first to build the dataset.")
        sys.exit(1)
        
    print(f"Loading base pretrained model: yolov8n.pt")
    model = YOLO("yolov8n.pt")
    
    project_dir = os.path.join(workspace_dir, "training", "runs")
    
    device = 0 if cuda_available else "cpu"
    batch_size = int(args.batch) if args.batch != "-1" else "auto"
    
    print(f"Starting training:")
    print(f"  - Config Yaml:   {yaml_path}")
    print(f"  - Epochs:        {args.epochs}")
    print(f"  - Batch Size:    {batch_size}")
    print(f"  - Image Size:    {args.imgsz}")
    print(f"  - Device:        {device} ({device_name})")
    print(f"  - Mixed Precision (AMP): {cuda_available}")
    print(f"  - Output Project: {project_dir}")
    print("=" * 60)
    
    try:
        model.train(
            data=yaml_path,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=batch_size,
            device=device,
            amp=cuda_available, # Mixed precision
            project=project_dir,
            name="detect", # Directory will be training/runs/detect
            exist_ok=True, # Overwrite/reuse the directory instead of train1, train2...
            val=True
        )
        print("\nTraining completed successfully!")
        print(f"Weights saved at: {os.path.join(project_dir, 'detect', 'weights', 'best.pt')}")
        print("=" * 60)
    except Exception as e:
        print(f"\nError encountered during training: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
