import re

file_path = r"c:\Users\sheka\OneDrive\Desktop\verum intern\cad_processor.py"

with open(file_path, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

content = re.sub(r'# ──+\s*# 2\. Check if cache exists', '# ─────────────────────────────────────────────────────────────────────────────\n    # 2. Check if cache exists', content)

target_str = 'return index, chunks("float32")'
idx = content.find(target_str)
if idx != -1:
    print("Found duplicate target. Truncating and writing correct ending...")
    content = content[:idx] + "return index, chunks\n"
else:
    print("Target not found. Let's check for other potential targets.")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Finished fixing cad_processor.py!")
