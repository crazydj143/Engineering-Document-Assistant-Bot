import os
import argparse
import sys
from PIL import Image

class SymbolDetector:
    def __init__(self, weights_path=None):
        self.is_ready = False
        self.model = None
        self.class_names = {}
        
        workspace_dir = r"d:\intern\verum intern3"
        if not weights_path:
            weights_path = os.path.join(workspace_dir, "training", "runs", "detect", "weights", "best.pt")
            
        print(f"[SymbolDetector] Searching for weights at {weights_path}...")
        if not os.path.exists(weights_path):
            print(f"[SymbolDetector] WARNING: Model weights not found at {weights_path}.")
            print("[SymbolDetector] Run 'python training/train_yolo.py' to train the model first.")
            print("[SymbolDetector] Falling back to silent mock mode (returning empty predictions).")
            return
            
        try:
            from ultralytics import YOLO
            self.model = YOLO(weights_path)
            self.class_names = self.model.names
            self.is_ready = True
            print(f"[SymbolDetector] YOLOv8 symbol detection model loaded successfully.")
        except Exception as e:
            print(f"[SymbolDetector] Failed to load model weights: {e}")
            print("[SymbolDetector] Falling back to silent mock mode.")

    def predict(self, image_path: str, conf_threshold: float = 0.25) -> list:
        """
        Runs YOLO symbol detection on an image.
        Returns a list of detections:
        [
            {"class": class_name, "confidence": confidence, "bbox": [x1, y1, x2, y2]}
        ]
        Where bbox coordinates are pixels on the input image.
        """
        if not self.is_ready or not self.model:
            return []
            
        if not os.path.exists(image_path):
            print(f"[SymbolDetector] Error: Image path {image_path} does not exist.")
            return []
            
        try:
            results = self.model.predict(
                source=image_path,
                conf=conf_threshold,
                verbose=False
            )
            
            detections = []
            if not results:
                return detections
                
            result = results[0]
            boxes = result.boxes
            
            for box in boxes:
                cls_idx = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist() # [x_min, y_min, x_max, y_max] in pixels
                
                class_name = self.class_names.get(cls_idx, f"class_{cls_idx}")
                
                detections.append({
                    "class": class_name,
                    "confidence": conf,
                    "bbox": [int(coord) for coord in xyxy]
                })
                
            return detections
        except Exception as e:
            print(f"[SymbolDetector] Error running model prediction: {e}")
            return []

def main():
    parser = argparse.ArgumentParser(description="Run YOLO symbol inference on drawings.")
    parser.add_argument("--image", type=str, required=True, help="Path to input image (PNG/JPG/JPEG)")
    parser.add_argument("--weights", type=str, default=None, help="Path to best.pt weights")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    args = parser.parse_args()
    
    detector = SymbolDetector(weights_path=args.weights)
    
    if not detector.is_ready:
        print("Detector not ready. Exiting.")
        sys.exit(1)
        
    print(f"Running inference on: {args.image}")
    detections = detector.predict(args.image, conf_threshold=args.conf)
    
    print("\nDetections:")
    print("-" * 50)
    if not detections:
        print("No symbols detected.")
    for idx, d in enumerate(detections):
        bbox = d["bbox"]
        print(f"  [{idx+1:02d}] Class: {d['class']} | Conf: {d['confidence']:.2f} | BBox: {bbox}")
    print("-" * 50)

if __name__ == "__main__":
    main()
