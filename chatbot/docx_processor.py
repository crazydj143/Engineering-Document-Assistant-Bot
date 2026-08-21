import os
import hashlib
import json
import pickle
import numpy as np
import faiss
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    import docx
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-docx"])
    import docx

from docx.document import Document
from docx.oxml import CT_P, CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph

import groq_client

COMMON_FORMULAS = {
    "P = VI": "Power equals voltage multiplied by current",
    "σ = F/A": "Stress equals force divided by cross-sectional area",
    "Isc = V/Z": "Short circuit current equals voltage divided by impedance",
    "V = IR": "Voltage equals current multiplied by resistance",
    "I = V/R": "Current equals voltage divided by resistance",
    "P = I^2R": "Power equals squared current multiplied by resistance",
    "F = ma": "Force equals mass multiplied by acceleration",
    "R = ρL/A": "Resistance equals resistivity multiplied by length divided by cross-sectional area"
}

def _iter_docx_elements(parent):
    """
    Yield each paragraph and table child within a parent element, in document order.
    """
    if isinstance(parent, Document):
        parent_elm = parent.element.body
    else:
        parent_elm = parent._element

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

def _format_markdown_table(table) -> str:
    """Formats a python-docx table as a Markdown table string."""
    rows_data = []
    max_cols = 0
    for row in table.rows:
        row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows_data.append(row_cells)
        max_cols = max(max_cols, len(row_cells))
        
    if not rows_data:
        return ""
        
    markdown_lines = []
    headers = rows_data[0]
    if len(headers) < max_cols:
        headers.extend([""] * (max_cols - len(headers)))
    markdown_lines.append("| " + " | ".join(headers) + " |")
    markdown_lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    
    for cells in rows_data[1:]:
        if len(cells) < max_cols:
            cells.extend([""] * (max_cols - len(cells)))
        markdown_lines.append("| " + " | ".join(cells) + " |")
        
    return "\n".join(markdown_lines)

def build_faiss_index(chunks, embed_model):
    """Generates embeddings and builds a FAISS search index for a chunk list."""
    if not chunks:
        return None
    raw_texts = [c["content"] for c in chunks]
    embeddings = embed_model.encode(raw_texts, show_progress_bar=False)
    embeddings = np.array(embeddings).astype("float32")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index

def process_and_cache_docx(uploaded_file, embed_model):
    """
    Loads, parses, chunks, embeds, and indexes a DOCX file.
    Utilizes MD5 hash-based caching to avoid re-indexing.
    Returns a dictionary of separate indices (Text, Diagrams, Formulas, Tables).
    """
    storage_dir = os.path.join(os.getcwd(), "docx_storage")
    os.makedirs(storage_dir, exist_ok=True)
    
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    file_hash = hashlib.md5(file_bytes).hexdigest()
    uploaded_file.seek(0)
    
    cache_dir = os.path.join(storage_dir, file_hash)
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_files = {
        "text_index": os.path.join(cache_dir, "text.index"),
        "text_chunks": os.path.join(cache_dir, "text_chunks.pkl"),
        "formula_index": os.path.join(cache_dir, "formula.index"),
        "formula_chunks": os.path.join(cache_dir, "formula_chunks.pkl"),
        "table_index": os.path.join(cache_dir, "table.index"),
        "table_chunks": os.path.join(cache_dir, "table_chunks.pkl")
    }
    
    cache_hit = all(os.path.exists(path) for path in cache_files.values())
    if cache_hit:
        print(f"[docx_processor] Loading cached DOCX indexes (hash: {file_hash})...")
        try:
            with open(cache_files["text_chunks"], "rb") as f:
                text_chunks = pickle.load(f)
            with open(cache_files["formula_chunks"], "rb") as f:
                formula_chunks = pickle.load(f)
            with open(cache_files["table_chunks"], "rb") as f:
                table_chunks = pickle.load(f)
                
            text_index = faiss.read_index(cache_files["text_index"]) if os.path.getsize(cache_files["text_index"]) > 0 else None
            formula_index = faiss.read_index(cache_files["formula_index"]) if os.path.getsize(cache_files["formula_index"]) > 0 else None
            table_index = faiss.read_index(cache_files["table_index"]) if os.path.getsize(cache_files["table_index"]) > 0 else None
            
            return {
                "text_index": text_index, "text_chunks": text_chunks,
                "diagram_index": None, "diagram_chunks": [],
                "formula_index": formula_index, "formula_chunks": formula_chunks,
                "table_index": table_index, "table_chunks": table_chunks
            }
        except Exception as e:
            print(f"[docx_processor] Cache load failed: {e}. Re-processing...")

    print(f"[docx_processor] Parsing new DOCX file...")
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    doc = docx.Document(uploaded_file)
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
        
    extracted_text_parts = []
    table_chunks = []
    formula_chunks = []
    
    formula_pattern = re.compile(r'\b([A-Za-z_α-ωθσΔ]{1,5}\s*=\s*[A-Za-z_α-ωθσΔ\d\s\/\*\-\+\^\\\(\)]+)\b')
    
    for element in _iter_docx_elements(doc):
        if isinstance(element, Paragraph):
            text = element.text.strip()
            if not text:
                continue
                
            style_name = element.style.name.lower()
            
            match = formula_pattern.search(text)
            if match:
                formula_str = match.group(1).strip()
                if len(formula_str) >= 5 and any(op in formula_str for op in ["=", "+", "-", "*", "/", "^"]):
                    explanation = COMMON_FORMULAS.get(formula_str)
                    if not explanation:
                        try:
                            sys_prompt = "You are an expert engineering assistant."
                            prompt = (
                                f"Explain this engineering formula in one simple sentence: '{formula_str}'. "
                                f"Return ONLY the plain sentence explanation."
                            )
                            explanation = groq_client.generate_groq_response(sys_prompt, prompt).strip()
                            COMMON_FORMULAS[formula_str] = explanation
                        except Exception:
                            explanation = "Engineering equation"
                            
                    formula_chunks.append({
                        "type": "formula",
                        "page": "Word Document",
                        "formula": formula_str,
                        "content": f"Formula: {formula_str}\nExplanation: {explanation}",
                        "source": "DOCX_Formula",
                        "file_name": uploaded_file.name,
                        "chunk_id": f"#formula_{len(formula_chunks)}"
                    })
            
            if "heading" in style_name:
                try:
                    level = int(style_name.replace("heading", "").strip())
                    heading_prefix = "#" * level + " "
                except ValueError:
                    heading_prefix = "### "
                extracted_text_parts.append(f"\n{heading_prefix}{text}\n")
            else:
                extracted_text_parts.append(text)
                
        elif isinstance(element, Table):
            table_md = _format_markdown_table(element)
            if table_md:
                table_chunks.append({
                    "page": "Word Document",
                    "content": f"Source Type: TABLE\nPage: Word Document\nContent:\n{table_md}",
                    "source": "DOCX_Table",
                    "file_name": uploaded_file.name,
                    "chunk_id": f"#table_{len(table_chunks)}"
                })
                
    full_text = "\n\n".join(extracted_text_parts)
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        length_function=len
    )
    split_texts = text_splitter.split_text(full_text)
    
    text_chunks = []
    for idx, split_text in enumerate(split_texts):
        text_chunks.append({
            "page": "Word Document",
            "content": split_text,
            "source": "DOCX_Text",
            "file_name": uploaded_file.name,
            "chunk_id": f"#text_{idx}"
        })
        
    if not text_chunks:
        text_chunks = [{
            "page": "Word Document",
            "content": "Empty DOCX file content.",
            "source": "DOCX_Text",
            "file_name": uploaded_file.name,
            "chunk_id": "#text_0"
        }]

    text_index = build_faiss_index(text_chunks, embed_model)
    formula_index = build_faiss_index(formula_chunks, embed_model)
    table_index = build_faiss_index(table_chunks, embed_model)
    
    for index_key, index_obj in [("text_index", text_index), ("formula_index", formula_index), ("table_index", table_index)]:
        path = cache_files[index_key]
        if index_obj is not None:
            faiss.write_index(index_obj, path)
        else:
            open(path, 'wb').close()
            
    with open(cache_files["text_chunks"], "wb") as f:
        pickle.dump(text_chunks, f)
    with open(cache_files["formula_chunks"], "wb") as f:
        pickle.dump(formula_chunks, f)
    with open(cache_files["table_chunks"], "wb") as f:
        pickle.dump(table_chunks, f)
        
    return {
        "text_index": text_index, "text_chunks": text_chunks,
        "diagram_index": None, "diagram_chunks": [],
        "formula_index": formula_index, "formula_chunks": formula_chunks,
        "table_index": table_index, "table_chunks": table_chunks
    }
