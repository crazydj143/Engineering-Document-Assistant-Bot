import os
import csv
import numpy as np
import shutil
from PIL import Image

def get_symbol_bbox(image_path, threshold=240):
    """
    Loads an image, converts it to grayscale, and finds the bounding box of
    non-white pixels (symbol lines) to create a tight YOLO annotation.
    """
    try:
        img = Image.open(image_path).convert("L")
        arr = np.array(img)
        
        y_indices, x_indices = np.where(arr < threshold)
        
        if len(x_indices) == 0 or len(y_indices) == 0:
            return 0.5, 0.5, 0.9, 0.9
            
        h, w = arr.shape
        min_x, max_x = float(np.min(x_indices)), float(np.max(x_indices))
        min_y, max_y = float(np.min(y_indices)), float(np.max(y_indices))
        
        box_w = (max_x - min_x) / w
        box_h = (max_y - min_y) / h
        x_center = (min_x + max_x) / (2.0 * w)
        y_center = (min_y + max_y) / (2.0 * h)
        
        x_center = max(0.01, min(0.99, x_center))
        y_center = max(0.01, min(0.99, y_center))
        box_w = max(0.01, min(0.99, box_w))
        box_h = max(0.01, min(0.99, box_h))
        
        return x_center, y_center, box_w, box_h
    except Exception as e:
        print(f"Warning: Failed to compute bounding box for {image_path}: {e}")
        return 0.5, 0.5, 0.9, 0.9

def main():
    print("=" * 60)
    print("YOLO DATASET VALIDATOR & CONVERTER")
    print("=" * 60)
    
    workspace_dir = r"d:\intern\verum intern3"
    dataset_dir = os.path.join(workspace_dir, "training", "dataset")
    csv_path = os.path.join(dataset_dir, "labels.csv")
    
    if not os.path.exists(csv_path):
        print(f"Error: labels.csv not found at {csv_path}")
        return
        
    entries = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(row)
            
    print(f"Found {len(entries)} entries in labels.csv")
    
    valid_entries = []
    classes = set()
    corrupt_count = 0
    missing_count = 0
    
    for entry in entries:
        rel_path = entry["filename"]
        label = entry["label"]
        abs_path = os.path.join(dataset_dir, rel_path.replace("/", os.sep))
        
        if not os.path.exists(abs_path):
            print(f"  [Missing File] {abs_path}")
            missing_count += 1
            continue
            
        try:
            with Image.open(abs_path) as img:
                img.verify() # Verify image integrity
            valid_entries.append((abs_path, label))
            classes.add(label)
        except Exception as e:
            print(f"  [Corrupt File] {abs_path}: {e}")
            corrupt_count += 1
            
    print(f"\nVerification Results:")
    print(f"  - Valid images:   {len(valid_entries)}")
    print(f"  - Missing images: {missing_count}")
    print(f"  - Corrupt images: {corrupt_count}")
    print(f"  - Unique classes: {len(classes)} ({sorted(list(classes))})")
    
    class_list = sorted(list(classes))
    class_map = {name: idx for idx, name in enumerate(class_list)}
    
    class_counts = {}
    for _, label in valid_entries:
        class_counts[label] = class_counts.get(label, 0) + 1
        
    print("\nClass Statistics:")
    for cls in class_list:
        print(f"  - {cls}: {class_counts.get(cls, 0)} images")
        
    np.random.seed(42)
    shuffled_indices = np.random.permutation(len(valid_entries))
    split_idx = int(len(valid_entries) * 0.8)
    
    train_indices = shuffled_indices[:split_idx]
    val_indices = shuffled_indices[split_idx:]
    
    yolo_dir = os.path.join(workspace_dir, "training", "yolo_dataset")
    shutil.rmtree(yolo_dir, ignore_errors=True)
    
    dirs = {
        "train_img": os.path.join(yolo_dir, "train", "images"),
        "train_lbl": os.path.join(yolo_dir, "train", "labels"),
        "val_img": os.path.join(yolo_dir, "val", "images"),
        "val_lbl": os.path.join(yolo_dir, "val", "labels")
    }
    
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
        
    def process_split(indices, img_dest, lbl_dest, name):
        for idx in indices:
            abs_path, label = valid_entries[idx]
            base_name = os.path.basename(abs_path)
            name_no_ext = os.path.splitext(base_name)[0]
            
            dest_img = os.path.join(img_dest, base_name)
            shutil.copy2(abs_path, dest_img)
            
            x_center, y_center, w, h = get_symbol_bbox(abs_path)
            class_idx = class_map[label]
            
            dest_lbl = os.path.join(lbl_dest, f"{name_no_ext}.txt")
            with open(dest_lbl, "w") as lbl_file:
                lbl_file.write(f"{class_idx} {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}\n")
                
        print(f"Processed {len(indices)} images for {name}")

    process_split(train_indices, dirs["train_img"], dirs["train_lbl"], "train")
    process_split(val_indices, dirs["val_img"], dirs["val_lbl"], "val")
    
    yaml_path = os.path.join(yolo_dir, "data.yaml")
    
    yolo_dir_forward = yolo_dir.replace("\\", "/")
    
    with open(yaml_path, "w") as yf:
        yf.write(f"path: {yolo_dir_forward}\n")
        yf.write("train: train/images\n")
        yf.write("val: val/images\n")
        yf.write("\n")
        yf.write("names:\n")
        for cls_name, idx in class_map.items():
            yf.write(f"  {idx}: {cls_name}\n")
            
    print(f"\nGenerated data.yaml at {yaml_path}")
    print("Dataset validation and conversion complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
