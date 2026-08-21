import os
import csv
import numpy as np
from PIL import Image

def clean_and_binarize(img_crop, threshold=230):
    gray = img_crop.convert("L")
    arr = np.array(gray)
    
    binary_arr = np.where(arr > threshold, 255, 0).astype(np.uint8)
    
    h, w = binary_arr.shape
    border = 2
    if h > 2 * border and w > 2 * border:
        binary_arr[:border, :] = 255
        binary_arr[-border:, :] = 255
        binary_arr[:, :border] = 255
        binary_arr[:, -border:] = 255
        
    return Image.fromarray(binary_arr)

def find_reference_cards(image_path, log_file):
    img = Image.open(image_path)
    W, H = img.size
    gray = img.convert("L")
    arr = np.array(gray)
    binary = (arr > 200).astype(np.uint8)
    
    start_y = int(H * 0.5)
    binary_bottom = binary[start_y:, :]
    row_sums = np.sum(binary_bottom, axis=1)
    
    row_thresh = W * 0.05
    active_rows = row_sums > row_thresh
    
    row_blocks = []
    in_block = False
    start = 0
    for y in range(len(active_rows)):
        if active_rows[y] and not in_block:
            start = y
            in_block = True
        elif not active_rows[y] and in_block:
            end = y
            if end - start > 20:
                row_blocks.append((start + start_y, end + start_y))
            in_block = False
    if in_block:
        end = len(active_rows)
        if end - start > 20:
            row_blocks.append((start + start_y, end + start_y))
            
    if len(row_blocks) != 2:
        row_blocks = sorted(row_blocks, key=lambda x: x[1] - x[0], reverse=True)[:2]
        row_blocks = sorted(row_blocks, key=lambda x: x[0])
        
    cards = []
    for r_idx, (y_start, y_end) in enumerate(row_blocks):
        row_binary = binary[y_start:y_end, :]
        col_sums = np.sum(row_binary, axis=0)
        col_thresh = (y_end - y_start) * 0.1
        active_cols = col_sums > col_thresh
        
        col_blocks = []
        in_block = False
        start = 0
        for x in range(len(active_cols)):
            if active_cols[x] and not in_block:
                start = x
                in_block = True
            elif not active_cols[x] and in_block:
                end = x
                if end - start > 20:
                    col_blocks.append((start, end))
                in_block = False
        if in_block:
            end = len(active_cols)
            if end - start > 20:
                col_blocks.append((start, end))
                
        if len(col_blocks) != 10:
            col_blocks = sorted(col_blocks, key=lambda x: x[1] - x[0], reverse=True)[:10]
            col_blocks = sorted(col_blocks, key=lambda x: x[0])
            
        for c_idx, (x_start, x_end) in enumerate(col_blocks):
            cards.append({
                "row": r_idx,
                "col": c_idx,
                "bbox": (x_start, y_start, x_end, y_end)
            })
            
    return img, cards

def main():
    workspace_dir = r"d:\intern\verum intern3"
    brain_dir = r"C:\Users\sheka\.gemini\antigravity-ide\brain\5352febb-a93e-48bf-b63e-a445ab0b45fa"
    log_path = os.path.join(workspace_dir, "create_dataset_log.txt")
    
    ref_classes = [
        "ct", "pt_cvt", "breaker", "isolator", "surge_arrester", "transformer", "busbar", "meter", "relay", "fuse",
        "earthing", "light", "motor", "panel", "contactor", "push_button", "indicator", "mccb", "vcb", "others"
    ]
    
    sld_row_classes = {
        2: "transformer",
        3: "ct",
        4: "pt_cvt",
        5: "breaker",
        6: "isolator",
        7: "earthing",
        8: "surge_arrester",
        9: "others",
        10: "others",
        11: "others",
        12: "busbar",
        13: "others",
        14: "others"
    }
    
    substation_row_classes = {
        2: "surge_arrester",
        3: "others",
        4: "pt_cvt",
        5: "others",
        6: "isolator",
        7: "others",
        8: "breaker",
        9: "ct",
        12: "others",
        13: "isolator",
        14: "others",
        15: "others",
        16: "breaker",
        17: "others",
        18: "ct"
    }
    
    dataset_dir = os.path.join(workspace_dir, "dataset")
    symbols_dir = os.path.join(dataset_dir, "electrical_symbols")
    os.makedirs(symbols_dir, exist_ok=True)
    
    all_classes = set(ref_classes)
    for c in all_classes:
        os.makedirs(os.path.join(symbols_dir, c), exist_ok=True)
        
    csv_data = []
    rotation_angles = [0, 90, 180, 270, 15]
    
    class_counters = {c: 0 for c in all_classes}
    
    def save_symbol_variants(img_crop, cls_name, log_file, source_name):
        cleaned = clean_and_binarize(img_crop)
        
        for angle in rotation_angles:
            rotated = cleaned.rotate(angle, fillcolor=255)
            resized = rotated.resize((256, 256), Image.Resampling.LANCZOS)
            
            class_counters[cls_name] += 1
            idx = class_counters[cls_name]
            
            filename = f"{cls_name}_{idx:03d}.png"
            relative_path = f"electrical_symbols/{cls_name}/{filename}"
            save_path = os.path.join(dataset_dir, relative_path.replace("/", os.sep))
            
            resized.save(save_path)
            csv_data.append([relative_path, cls_name])
            
        log_file.write(f"  Extracted symbol class '{cls_name}' from {source_name} (saved {len(rotation_angles)} files)\n")

    with open(log_path, "w") as log:
        log.write("Electrical Symbol Dataset Extraction Log (Version 2)\n")
        log.write("===================================================\n\n")
        
        ref_path = os.path.join(brain_dir, "media__1782282939119.jpg")
        if os.path.exists(ref_path):
            log.write("Processing original reference cards image...\n")
            try:
                img, cards = find_reference_cards(ref_path, log)
                for idx, card in enumerate(cards):
                    cls_name = ref_classes[idx]
                    x_start, y_start, x_end, y_end = card["bbox"]
                    
                    w = x_end - x_start
                    h = y_end - y_start
                    shave_w = int(w * 0.05)
                    shave_h = int(h * 0.05)
                    
                    crop_box = (x_start + shave_w, y_start + shave_h, x_end - shave_w, y_end - shave_h)
                    cropped = img.crop(crop_box)
                    
                    save_symbol_variants(cropped, cls_name, log, f"Reference Card {idx+1}")
            except Exception as e:
                log.write(f"  Error processing reference cards: {str(e)}\n")
        else:
            log.write("Reference cards image not found. Skipping.\n")
            
        sld1_path = os.path.join(brain_dir, "media__1782283747946.png")
        if os.path.exists(sld1_path):
            log.write("\nProcessing Single Line Diagram 1...\n")
            try:
                img1 = Image.open(sld1_path)
                y_start, y_end = 137, 637
                h_total = y_end - y_start
                num_rows = 14
                row_h = h_total / num_rows
                
                x_start, x_end = 122, 172
                
                for row_idx, cls_name in sld_row_classes.items():
                    i = row_idx - 1
                    ry_start = int(y_start + i * row_h) + 2
                    ry_end = int(y_start + (i + 1) * row_h) - 2
                    
                    cropped = img1.crop((x_start, ry_start, x_end, ry_end))
                    save_symbol_variants(cropped, cls_name, log, f"SLD1 Row {row_idx}")
            except Exception as e:
                log.write(f"  Error processing SLD1: {str(e)}\n")
                
        sld2_path = os.path.join(brain_dir, "media__1782283747969.png")
        if os.path.exists(sld2_path):
            log.write("\nProcessing Single Line Diagram 2...\n")
            try:
                img2 = Image.open(sld2_path)
                y_start, y_end = 80, 583
                h_total = y_end - y_start
                num_rows = 14
                row_h = h_total / num_rows
                
                x_start, x_end = 120, 170
                
                for row_idx, cls_name in sld_row_classes.items():
                    i = row_idx - 1
                    ry_start = int(y_start + i * row_h) + 2
                    ry_end = int(y_start + (i + 1) * row_h) - 2
                    
                    cropped = img2.crop((x_start, ry_start, x_end, ry_end))
                    save_symbol_variants(cropped, cls_name, log, f"SLD2 Row {row_idx}")
            except Exception as e:
                log.write(f"  Error processing SLD2: {str(e)}\n")
                
        sub_path = os.path.join(brain_dir, "media__1782283748024.png")
        if os.path.exists(sub_path):
            log.write("\nProcessing Substation Layout Legend...\n")
            try:
                img3 = Image.open(sub_path)
                y_start, y_end = 100, 900
                h_total = y_end - y_start
                num_rows = 20
                row_h = h_total / num_rows
                
                x_start, x_end = 804, 846
                
                for row_idx, cls_name in substation_row_classes.items():
                    i = row_idx - 1
                    ry_start = int(y_start + i * row_h) + 2
                    ry_end = int(y_start + (i + 1) * row_h) - 2
                    
                    cropped = img3.crop((x_start, ry_start, x_end, ry_end))
                    save_symbol_variants(cropped, cls_name, log, f"Substation Row {row_idx}")
            except Exception as e:
                log.write(f"  Error processing Substation: {str(e)}\n")
                
        csv_path = os.path.join(dataset_dir, "labels.csv")
        with open(csv_path, "w", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["filename", "label"])
            writer.writerows(csv_data)
            
        log.write("\nDataset creation finished successfully!\n")
        log.write(f"Total labeled images generated: {len(csv_data)}\n")
        for cls_name, count in class_counters.items():
            log.write(f"  Class '{cls_name}': {count} images\n")
            
        print(f"Dataset successfully created with {len(csv_data)} images!")
        print("Log file saved to create_dataset_log.txt")

if __name__ == "__main__":
    main()
