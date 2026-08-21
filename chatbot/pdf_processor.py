import os
import hashlib
import json
import pickle
import numpy as np
import fitz  # PyMuPDF
import faiss
import re
from PIL import Image
import io
from langchain_text_splitters import RecursiveCharacterTextSplitter

import groq_client
import config

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

def extract_pdf_pages_fitz(pdf_path: str) -> list:
    """
    Extracts text page-by-page from a PDF using PyMuPDF.
    Returns a list of tuples: (page_number, text_content).
    """
    doc = fitz.open(pdf_path)
    pages = []
    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        text = page.get_text()
        pages.append((page_idx + 1, text or ""))
    return pages

def extract_document_structure(pdf_pages) -> dict:
    """
    Parses the PDF text to extract Unit titles and topics.
    """
    full_text = "\n".join([text for _, text in pdf_pages])
    pattern = re.compile(r'(?i)\b(UNIT\s+[IVXLCDM0-9]+|\bUNIT\s+\d+)\b')
    matches = list(pattern.finditer(full_text))
    
    structure = {}
    if not matches:
        return {}
        
    for i, match in enumerate(matches):
        unit_name = match.group(1).upper()
        start_idx = match.end()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(full_text)
        
        section_text = full_text[start_idx:end_idx].strip()
        lines = [line.strip() for line in section_text.split('\n') if line.strip()]
        
        topics = []
        for line in lines[:15]:
            cleaned = re.sub(r'^[-*•\d\.\s]+', '', line).strip()
            if cleaned and 5 < len(cleaned) < 150:
                topics.append(cleaned)
                
        if not topics and section_text:
            parts = [p.strip() for p in section_text.split(',') if p.strip()]
            for p in parts[:15]:
                cleaned = re.sub(r'^[-*•\d\.\s]+', '', p).strip()
                if cleaned and 5 < len(cleaned) < 100:
                    topics.append(cleaned)
                    
        if not topics:
            topics = ["General Unit content and topics"]
            
        structure[unit_name] = topics
        
    return structure

def df_to_markdown(df) -> str:
    """
    Converts a pandas DataFrame to a markdown table without needing the tabulate package.
    """
    if df is None or df.empty:
        return ""
    headers = [str(col) for col in df.columns]
    underline = ["---"] * len(headers)
    
    rows = []
    rows.append("| " + " | ".join(headers) + " |")
    rows.append("| " + " | ".join(underline) + " |")
    
    for _, row in df.iterrows():
        row_str = [str(val).replace("\n", " ") for val in row]
        rows.append("| " + " | ".join(row_str) + " |")
        
    return "\n".join(rows)

def extract_pdf_tables(pdf_path: str, file_name: str) -> list:
    """
    Extracts tables from a PDF using Camelot with Tabula and PyMuPDF as fallbacks.
    Converts tables into markdown content and returns Table chunks.
    """
    table_chunks = []
    
    try:
        print("[pdf_processor] Extracting tables with Camelot...")
        import camelot
        tables = camelot.read_pdf(pdf_path, pages='all')
        for idx, table in enumerate(tables):
            table_md = df_to_markdown(table.df)
            page_num = table.page
            table_chunks.append({
                "page": page_num,
                "content": f"Source Type: TABLE\nPage: {page_num}\nContent:\n{table_md}",
                "source": "PDF_Table",
                "file_name": file_name,
                "chunk_id": f"#table_{idx}"
            })
        if table_chunks:
            print(f"[pdf_processor] Camelot successfully extracted {len(table_chunks)} tables.")
            return table_chunks
    except Exception as e:
        print(f"[pdf_processor] Camelot table extraction failed: {e}. Trying Tabula...")
        
    try:
        import tabula
        dfs = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
        for idx, df in enumerate(dfs):
            table_md = df_to_markdown(df)
            table_chunks.append({
                "page": 1,  # Default fallback page
                "content": f"Source Type: TABLE\nPage: 1\nContent:\n{table_md}",
                "source": "PDF_Table",
                "file_name": file_name,
                "chunk_id": f"#table_{idx}"
            })
        if table_chunks:
            print(f"[pdf_processor] Tabula successfully extracted {len(table_chunks)} tables.")
            return table_chunks
    except Exception as e:
        print(f"[pdf_processor] Tabula table extraction failed: {e}. Trying PyMuPDF native TableFinder...")
        
    try:
        doc = fitz.open(pdf_path)
        for page_idx in range(len(doc)):
            page = doc.load_page(page_idx)
            tables = page.find_tables()
            for t_idx, table in enumerate(tables):
                df = table.to_pandas()
                table_md = df_to_markdown(df)
                page_num = page_idx + 1
                table_chunks.append({
                    "page": page_num,
                    "content": f"Source Type: TABLE\nPage: {page_num}\nContent:\n{table_md}",
                    "source": "PDF_Table",
                    "file_name": file_name,
                    "chunk_id": f"#table_{page_num}_{t_idx}"
                })
        print(f"[pdf_processor] PyMuPDF TableFinder extracted {len(table_chunks)} tables.")
    except Exception as e:
        print(f"[pdf_processor] PyMuPDF table extraction failed: {e}")
        
    return table_chunks

def extract_formulas(text: str, page_num: int, file_name: str) -> list:
    """
    Detects engineering equations using regex and returns Formula chunks.
    Generates explanations via Gemini Vision/Text dynamically if not predefined.
    """
    formula_chunks = []
    
    formula_pattern = re.compile(r'\b([A-Za-z_α-ωθσΔ]{1,5}\s*=\s*[A-Za-z_α-ωθσΔ\d\s\/\*\-\+\^\\\(\)]+)\b')
    
    lines = text.split("\n")
    for line in lines:
        match = formula_pattern.search(line)
        if match:
            formula_str = match.group(1).strip()
            
            if len(formula_str) < 5 or not any(op in formula_str for op in ["=", "+", "-", "*", "/", "^"]):
                continue
                
            if any(c["formula"] == formula_str for c in formula_chunks):
                continue
                
            explanation = COMMON_FORMULAS.get(formula_str)
            if not explanation:
                try:
                    print(f"[pdf_processor] Asking Gemini to explain engineering formula: {formula_str}...")
                    sys_prompt = "You are an expert engineering assistant."
                    prompt = (
                        f"Explain this engineering formula in one simple sentence: '{formula_str}'. "
                        f"E.g. 'P = VI' -> 'Power equals voltage multiplied by current'. "
                        f"Return ONLY the plain sentence explanation."
                    )
                    explanation = groq_client.generate_groq_response(sys_prompt, prompt).strip()
                    COMMON_FORMULAS[formula_str] = explanation
                except Exception:
                    explanation = "Engineering equation"

            formula_chunks.append({
                "type": "formula",
                "page": page_num,
                "formula": formula_str,
                "content": f"Formula: {formula_str}\nExplanation: {explanation}",
                "source": "PDF_Formula",
                "file_name": file_name,
                "chunk_id": f"#formula_{page_num}_{len(formula_chunks)}"
            })
            
    return formula_chunks

def extract_and_analyze_images(pdf_path: str, pdf_hash: str, file_name: str) -> list:
    """
    Extracts images, calls Gemini for descriptions, and returns Diagram chunks.
    """
    doc = fitz.open(pdf_path)
    output_base_dir = os.path.join(config.EXTRACTED_IMAGES_DIR, pdf_hash)
    os.makedirs(output_base_dir, exist_ok=True)
    
    diagram_chunks = []
    page_to_images = {}
    seen_hashes = set()
    
    for page_idx in range(len(doc)):
        page_num = page_idx + 1
        page_to_images[page_num] = []
        page = doc.load_page(page_idx)
        
        images_on_page = page.get_images(full=True)
        for img_idx, img_info in enumerate(images_on_page):
            try:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                img_bytes = base_image["image"]
                img_ext = base_image["ext"]
                
                img_hash = hashlib.md5(img_bytes).hexdigest()
                if img_hash in seen_hashes:
                    continue
                
                pil_img = Image.open(io.BytesIO(img_bytes))
                w, h = pil_img.size
                if w < 150 or h < 150:
                    continue
                    
                seen_hashes.add(img_hash)
                
                img_name = f"page_{page_num}_img_{img_idx}.{img_ext}"
                img_path = os.path.join(output_base_dir, img_name)
                with open(img_path, "wb") as f:
                    f.write(img_bytes)
                    
                page_to_images[page_num].append(img_path)
                
                print(f"[pdf_processor] Generating local Qwen2.5-VL explanation for page {page_num} diagram...")
                prompt = (
                    f"You are an expert engineering assistant. Analyze this diagram/image extracted from page {page_num} "
                    f"of the engineering document. Describe the engineering components, schematics, connections, values, "
                    f"and flow shown in the image. Generate a detailed, professional engineering explanation."
                )
                import vision_analyzer
                explanation = vision_analyzer.analyze_image_local(img_bytes, prompt)
                
                content_str = f"[Diagram from Page {page_num} - {img_name}]: {explanation}"
                diagram_chunks.append({
                    "page": page_num,
                    "content": content_str,
                    "image_path": img_path,
                    "source": "PDF_Diagram",
                    "file_name": file_name,
                    "chunk_id": f"#diagram_{page_num}_{img_idx}"
                })
            except Exception as e:
                print(f"[pdf_processor] Image extraction error on page {page_num}: {e}")
                
    return diagram_chunks, page_to_images

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

def process_and_cache_pdf(uploaded_file, embed_model):
    """
    Processes a PDF file into separate FAISS indices (Text, Diagrams, Formulas, Tables)
    and caches them using MD5 file hashing.
    """
    config.ensure_directories()
    
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    file_hash = hashlib.md5(file_bytes).hexdigest()
    uploaded_file.seek(0)
    
    pdf_dir = os.path.join(config.PDF_STORAGE_DIR, file_hash)
    os.makedirs(pdf_dir, exist_ok=True)
    
    cache_files = {
        "text_index": os.path.join(pdf_dir, "text.index"),
        "text_chunks": os.path.join(pdf_dir, "text_chunks.pkl"),
        "diagram_index": os.path.join(pdf_dir, "diagram.index"),
        "diagram_chunks": os.path.join(pdf_dir, "diagram_chunks.pkl"),
        "formula_index": os.path.join(pdf_dir, "formula.index"),
        "formula_chunks": os.path.join(pdf_dir, "formula_chunks.pkl"),
        "table_index": os.path.join(pdf_dir, "table.index"),
        "table_chunks": os.path.join(pdf_dir, "table_chunks.pkl"),
        "structure": os.path.join(pdf_dir, "structure.json"),
        "images": os.path.join(pdf_dir, "pdf_images.json"),
        "scanned": os.path.join(pdf_dir, "scanned_pages.json")
    }
    
    cache_hit = all(os.path.exists(path) for path in cache_files.values())
    
    if cache_hit:
        print(f"[pdf_processor] Loading cached PDF indexes for {uploaded_file.name}...")
        try:
            with open(cache_files["text_chunks"], "rb") as f:
                text_chunks = pickle.load(f)
            with open(cache_files["diagram_chunks"], "rb") as f:
                diagram_chunks = pickle.load(f)
            with open(cache_files["formula_chunks"], "rb") as f:
                formula_chunks = pickle.load(f)
            with open(cache_files["table_chunks"], "rb") as f:
                table_chunks = pickle.load(f)
                
            text_index = faiss.read_index(cache_files["text_index"]) if os.path.getsize(cache_files["text_index"]) > 0 else None
            diagram_index = faiss.read_index(cache_files["diagram_index"]) if os.path.getsize(cache_files["diagram_index"]) > 0 else None
            formula_index = faiss.read_index(cache_files["formula_index"]) if os.path.getsize(cache_files["formula_index"]) > 0 else None
            table_index = faiss.read_index(cache_files["table_index"]) if os.path.getsize(cache_files["table_index"]) > 0 else None
            
            with open(cache_files["structure"], "r") as f:
                document_structure = json.load(f)
            with open(cache_files["images"], "r") as f:
                pdf_images = json.load(f)
            with open(cache_files["scanned"], "r") as f:
                scanned_pages = json.load(f)
                
            is_scanned = len(scanned_pages) > 0
            
            return {
                "text_index": text_index, "text_chunks": text_chunks,
                "diagram_index": diagram_index, "diagram_chunks": diagram_chunks,
                "formula_index": formula_index, "formula_chunks": formula_chunks,
                "table_index": table_index, "table_chunks": table_chunks,
                "document_structure": document_structure, "pdf_images": pdf_images,
                "is_scanned": is_scanned, "scanned_pages": scanned_pages,
                "file_hash": file_hash
            }
        except Exception as e:
            print(f"[pdf_processor] Cache load failed: {e}. Re-processing...")

    pdf_path = os.path.join(pdf_dir, "document.pdf")
    with open(pdf_path, "wb") as f:
        f.write(file_bytes)
        
    pdf_pages = extract_pdf_pages_fitz(pdf_path)
    
    ocr_pages_text = {}
    doc = fitz.open(pdf_path)
    scanned_pages = []
    is_scanned = False
    
    total_text_len = sum(len(text) for _, text in pdf_pages)
    if total_text_len < 100 * len(pdf_pages):
        is_scanned = True
        print(f"[pdf_processor] Document appears to be a scanned PDF. Rendering all pages as images for OCR...")
        scanned_dir = os.path.join(pdf_dir, "scanned_pages")
        os.makedirs(scanned_dir, exist_ok=True)
        
        for idx in range(len(doc)):
            page_num = idx + 1
            page = doc.load_page(idx)
            pix = page.get_pixmap(dpi=150)
            img_path = os.path.join(scanned_dir, f"page_{page_num}.png")
            pix.save(img_path)
            scanned_pages.append(img_path)
            
            ocr_prompt = (
                "You are an expert OCR and document transcription engine. Extract and transcribe all readable text "
                "from this engineering document page image. Maintain the original layout and structure as much as possible. "
                "Do not add explanations or meta-commentary."
            )
            with open(img_path, "rb") as im_file:
                page_bytes = im_file.read()
            import vision_analyzer
            ocr_text = vision_analyzer.analyze_image_local(page_bytes, ocr_prompt)
            ocr_pages_text[page_num] = ocr_text or ""
    else:
        for page_num, text in pdf_pages:
            cleaned = text.strip()
            page = doc.load_page(page_num - 1)
            has_visuals = len(page.get_images()) > 0 or len(page.get_drawings()) > 0
            if len(cleaned) < 50 and has_visuals:
                print(f"[pdf_processor] Running OCR on visual-only page {page_num}...")
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
                ocr_prompt = (
                    "You are an expert OCR and document transcription engine. Extract and transcribe all readable text "
                    "from this engineering document page image. Maintain the original layout and structure as much as possible. "
                    "Do not add explanations or meta-commentary."
                )
                import vision_analyzer
                ocr_text = vision_analyzer.analyze_image_local(img_bytes, ocr_prompt)
                ocr_pages_text[page_num] = ocr_text or ""
                
    final_pdf_pages = []
    for page_num, text in pdf_pages:
        merged_text = text
        if page_num in ocr_pages_text:
            merged_text = (merged_text + "\n" + ocr_pages_text[page_num]).strip()
        final_pdf_pages.append((page_num, merged_text))

    document_structure = extract_document_structure(final_pdf_pages)
    
    diagram_chunks, pdf_images = extract_and_analyze_images(pdf_path, file_hash, uploaded_file.name)
    table_chunks = extract_pdf_tables(pdf_path, uploaded_file.name)
    
    formula_chunks = []
    for page_num, text in final_pdf_pages:
        f_chunks = extract_formulas(text, page_num, uploaded_file.name)
        formula_chunks.extend(f_chunks)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        length_function=len
    )
    
    text_chunks = []
    if is_scanned:
        for page_num, text in ocr_pages_text.items():
            split_texts = text_splitter.split_text(text)
            for s_idx, chunk_text in enumerate(split_texts):
                text_chunks.append({
                    "page": page_num,
                    "content": chunk_text,
                    "source": "PDF_OCR",
                    "file_name": uploaded_file.name,
                    "chunk_id": f"#ocr_{page_num}_{s_idx}"
                })
    else:
        for page_num, text in final_pdf_pages:
            split_texts = text_splitter.split_text(text)
            for s_idx, chunk_text in enumerate(split_texts):
                text_chunks.append({
                    "page": page_num,
                    "content": chunk_text,
                    "source": "PDF_Text",
                    "file_name": uploaded_file.name,
                    "chunk_id": f"#text_{page_num}_{s_idx}"
                })

    print("[pdf_processor] Building separate FAISS indexes...")
    text_index = build_faiss_index(text_chunks, embed_model)
    diagram_index = build_faiss_index(diagram_chunks, embed_model)
    formula_index = build_faiss_index(formula_chunks, embed_model)
    table_index = build_faiss_index(table_chunks, embed_model)
    
    for index_key, index_obj in [("text_index", text_index), ("diagram_index", diagram_index), 
                                  ("formula_index", formula_index), ("table_index", table_index)]:
        path = cache_files[index_key]
        if index_obj is not None:
            faiss.write_index(index_obj, path)
        else:
            open(path, 'wb').close() # Create empty file
            
    with open(cache_files["text_chunks"], "wb") as f:
        pickle.dump(text_chunks, f)
    with open(cache_files["diagram_chunks"], "wb") as f:
        pickle.dump(diagram_chunks, f)
    with open(cache_files["formula_chunks"], "wb") as f:
        pickle.dump(formula_chunks, f)
    with open(cache_files["table_chunks"], "wb") as f:
        pickle.dump(table_chunks, f)
    with open(cache_files["structure"], "w") as f:
        json.dump(document_structure, f, indent=4)
    with open(cache_files["images"], "w") as f:
        json.dump(pdf_images, f, indent=4)
    with open(cache_files["scanned"], "w") as f:
        json.dump(scanned_pages, f, indent=4)
        
    return {
        "text_index": text_index, "text_chunks": text_chunks,
        "diagram_index": diagram_index, "diagram_chunks": diagram_chunks,
        "formula_index": formula_index, "formula_chunks": formula_chunks,
        "table_index": table_index, "table_chunks": table_chunks,
        "document_structure": document_structure, "pdf_images": pdf_images,
        "is_scanned": is_scanned, "scanned_pages": scanned_pages,
        "file_hash": file_hash
    }
