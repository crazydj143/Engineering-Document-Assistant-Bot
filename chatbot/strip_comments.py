import os
import io
import tokenize

def get_whole_line_comment_indices(content):
    try:
        tokens = tokenize.generate_tokens(io.StringIO(content).readline)
        comment_lines = set()
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                # Keep shebangs or encoding declarations
                if tok.string.startswith("#!") or "coding:" in tok.string:
                    continue
                # Check if it's a whole-line comment
                line_str = tok.line
                start_col = tok.start[1]
                if line_str[:start_col].strip() == "":
                    comment_lines.add(tok.start[0])
        return comment_lines
    except tokenize.TokenError:
        return set()

def strip_comments_from_file(filepath):
    print(f"Processing: {filepath}")
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    comment_lines = get_whole_line_comment_indices(content)
    if not comment_lines:
        print(f"  No whole-line comments found.")
        return
        
    lines = content.splitlines(keepends=True)
    clean_lines = []
    removed_count = 0
    for idx, line in enumerate(lines, 1):
        if idx in comment_lines:
            removed_count += 1
            continue
        clean_lines.append(line)
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("".join(clean_lines))
        
    print(f"  Removed {removed_count} comment lines.")

def main():
    workspace = os.path.dirname(os.path.abspath(__file__))
    exclude_dirs = {"__pycache__", ".venv", ".git", ".agents", "extracted_images", "cad_storage", "pdf_storage", "docx_storage", "temp_drawings", "data"}
    
    processed_files = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                # Skip the strip script itself
                if file == "strip_comments.py":
                    continue
                processed_files.append(filepath)
                
    for filepath in processed_files:
        try:
            strip_comments_from_file(filepath)
        except Exception as e:
            print(f"  Error processing {filepath}: {e}")

if __name__ == "__main__":
    main()
