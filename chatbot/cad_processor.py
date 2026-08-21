import os
import sys
import shutil
import subprocess
import tempfile
import hashlib
import json
import faiss
import pickle
import numpy as np

import config
import streamlit as st

GENERATE_PREVIEW = True
CAD_CACHE_VERSION = "v26"
def _find_oda_converter() -> str | None:
    """
    Searches common installation paths for ODAFileConverter.exe.
    Returns the full path if found, otherwise None.
    """
    import shutil
    
    env_oda_path = os.getenv("ODA_PATH") or os.getenv("ODA_DIR")
    if env_oda_path:
        env_oda_path = env_oda_path.strip('"').strip("'")
        if os.path.isdir(env_oda_path):
            possible_exe = os.path.join(env_oda_path, "ODAFileConverter.exe")
            if os.path.exists(possible_exe):
                return possible_exe
        elif os.path.isfile(env_oda_path) and os.path.basename(env_oda_path).lower() == "odafileconverter.exe":
            return env_oda_path

    in_path = shutil.which("ODAFileConverter") or shutil.which("ODAFileConverter.exe")
    if in_path:
        return in_path

    search_roots = [
        r"D:\intern\oda",
        r"D:\intern",
        r"C:\Program Files\ODA",
        r"C:\Program Files (x86)\ODA",
        r"C:\ODA",
        r"D:\Program Files\ODA",
        r"D:\ODA",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"D:\Program Files",
    ]
    for root_dir in search_roots:
        if not os.path.exists(root_dir):
            continue
        try:
            for entry in os.scandir(root_dir):
                if entry.is_file() and entry.name.lower() == "odafileconverter.exe":
                    return entry.path
                elif entry.is_dir() and not entry.name.startswith("."):
                    try:
                        for sub_entry in os.scandir(entry.path):
                            if sub_entry.is_file() and sub_entry.name.lower() == "odafileconverter.exe":
                                return sub_entry.path
                            elif sub_entry.is_dir() and not sub_entry.name.startswith("."):
                                try:
                                    for sub2_entry in os.scandir(sub_entry.path):
                                        if sub2_entry.is_file() and sub2_entry.name.lower() == "odafileconverter.exe":
                                            return sub2_entry.path
                                except Exception:
                                    pass
                    except Exception:
                        pass
        except Exception:
            pass
    return None

def _convert_dwg_to_dxf_oda(dwg_path: str) -> str:
    """
    Uses ODA File Converter to convert a .dwg file to .dxf.
    """
    oda_exe = _find_oda_converter()
    if not oda_exe:
        raise RuntimeError(
            "ODA File Converter not found.\n"
            "Download and install it from: https://www.opendesign.com/guestfiles/oda_file_converter\n"
            "Expected installation directory: C:\\Program Files\\ODA\\"
        )

    temp_in = tempfile.mkdtemp()
    temp_out = tempfile.mkdtemp()
    try:
        shutil.copy(dwg_path, temp_in)
        base_name = os.path.splitext(os.path.basename(dwg_path))[0]

        cmd = [
            oda_exe,
            temp_in,
            temp_out,
            "ACAD2018",      # output version
            "DXF",           # output format
            "0",             # recurse: 0 = no
            "1",             # audit: 1 = yes
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
        print(f"[cad_processor] ODA returncode: {result.returncode}")
        
        dxf_output = os.path.join(temp_out, base_name + ".dxf")
        if not os.path.exists(dxf_output):
            dxf_output_upper = os.path.join(temp_out, base_name + ".DXF")
            if os.path.exists(dxf_output_upper):
                dxf_output = dxf_output_upper
            else:
                raise RuntimeError(
                    f"ODA File Converter ran but produced no DXF.\n"
                    f"stdout: {result.stdout}\nstderr: {result.stderr}"
                )

        dest_dxf = os.path.splitext(dwg_path)[0] + ".dxf"
        shutil.copy(dxf_output, dest_dxf)
        return dest_dxf

    finally:
        shutil.rmtree(temp_in, ignore_errors=True)
        shutil.rmtree(temp_out, ignore_errors=True)

def _convert_dxf_ezdxf(input_path: str, output_path: str, figsize: tuple = (10, 10), dpi: int = 100) -> str:
    """
    Renders a .dxf file to a PNG image using ezdxf + matplotlib.
    """
    try:
        import ezdxf
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "ezdxf", "matplotlib"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import ezdxf
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

    doc = ezdxf.readfile(input_path)
    msp = doc.modelspace()

    fig = plt.figure(figsize=figsize, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("white")

    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    frontend = Frontend(ctx, out)
    frontend.draw_layout(msp, finalize=True)

    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path

def detect_symbols_yolo(preview_png_path: str) -> dict:
    """
    Placeholder function for YOLO symbol detection.
    Reads a preview PNG and returns a symbol count inventory.
    """
    return {
        "generator": 0,
        "transformer": 0,
        "ct": 0,
        "pt": 0,
        "breaker": 0,
        "isolator": 0,
        "busbar": 0,
        "line": 0,
        "reactor": 0,
        "wave_trap": 0,
        "lightning_arrester": 0
    }

def parse_dxf_entities(dxf_path: str) -> list:
    """
    Parses a DXF file using ezdxf and extracts:
    TEXT, MTEXT, LINE, DIMENSION, LAYER, BLOCK, INSERT, ATTRIB, LWPOLYLINE,
    ARC, ELLIPSE, SPLINE, HATCH, POLYLINE.
    """
    import ezdxf
    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        print(f"[cad_processor] Failed to read DXF file: {e}")
        return []
        
    msp = doc.modelspace()
    parsed_entities = []
    
    for block in doc.blocks:
        is_layout = getattr(block, 'is_layout_block', None)
        if is_layout is None:
            is_block_layout = getattr(block, 'is_block_layout', None)
            if is_block_layout is not None:
                is_layout = not is_block_layout
            else:
                is_layout = block.name.startswith('*')
        if not is_layout:
            parsed_entities.append({
                "label": block.name,
                "value": f"block definition with {len(block)} entities",
                "type": "block"
            })
            
    for entity in msp:
        dtype = entity.dxftype()
        layer = entity.dxf.layer if entity.dxf.hasattr("layer") else "default"
        
        parsed_entities.append({
            "label": f"layer: {layer}",
            "value": f"Entity of type {dtype} on layer {layer}",
            "type": "layer"
        })
        
        if dtype in ("TEXT", "MTEXT"):
            val = entity.text if hasattr(entity, "text") else entity.dxf.text
            parsed_entities.append({
                "label": "text",
                "value": str(val).strip(),
                "type": dtype.lower()
            })
        elif dtype == "DIMENSION":
            label = entity.dxf.text if entity.dxf.hasattr("text") else ""
            try:
                val = str(entity.dxf.actual_measurement)
            except Exception:
                val = ""
            if not label:
                label = "dimension"
            parsed_entities.append({
                "label": str(label).strip(),
                "value": str(val).strip(),
                "type": "dimension"
            })
        elif dtype == "LINE":
            parsed_entities.append({
                "label": "line",
                "value": f"start {entity.dxf.start} to end {entity.dxf.end}",
                "type": "line"
            })
        elif dtype == "CIRCLE":
            parsed_entities.append({
                "label": "circle",
                "value": f"center {entity.dxf.center} radius {entity.dxf.radius}",
                "type": "circle"
            })
        elif dtype == "ARC":
            parsed_entities.append({
                "label": "arc",
                "value": f"center {entity.dxf.center} radius {entity.dxf.radius} start_angle {entity.dxf.start_angle} end_angle {entity.dxf.end_angle}",
                "type": "arc"
            })
        elif dtype == "ELLIPSE":
            parsed_entities.append({
                "label": "ellipse",
                "value": f"center {entity.dxf.center} major_axis {entity.dxf.major_axis} ratio {entity.dxf.ratio}",
                "type": "ellipse"
            })
        elif dtype == "SPLINE":
            parsed_entities.append({
                "label": "spline",
                "value": f"degree {entity.dxf.degree} fit_points {getattr(entity.dxf, 'fit_points', [])} control_points {list(entity.control_points)}",
                "type": "spline"
            })
        elif dtype == "HATCH":
            parsed_entities.append({
                "label": "hatch",
                "value": f"pattern {entity.dxf.pattern_name} associative {entity.dxf.associative}",
                "type": "hatch"
            })
        elif dtype == "INSERT":
            parsed_entities.append({
                "label": "insert",
                "value": f"block reference {entity.dxf.name} at {entity.dxf.insert}",
                "type": "insert"
            })
            for attrib in entity.attribs:
                parsed_entities.append({
                    "label": f"attribute {attrib.dxf.tag}",
                    "value": f"tag {attrib.dxf.tag} text {attrib.dxf.text}",
                    "type": "attrib"
                })
        elif dtype == "ATTRIB":
            parsed_entities.append({
                "label": "attrib",
                "value": f"tag {entity.dxf.tag} text {entity.dxf.text}",
                "type": "attrib"
            })
        elif dtype in ("POLYLINE", "LWPOLYLINE"):
            try:
                points = list(entity.points())
            except Exception:
                points = []
            parsed_entities.append({
                "label": "polyline",
                "value": f"polyline with {len(points)} points",
                "type": "polyline"
            })
            
    unique_ents = []
    seen_layer_ents = set()
    for ent in parsed_entities:
        if ent["type"] == "layer":
            if ent["label"] in seen_layer_ents:
                continue
            seen_layer_ents.add(ent["label"])
        unique_ents.append(ent)
        
    return unique_ents

def _print_diagnostics(final_inventory, drawing_type, file_name, cad_analysis, chunk_count=0):
    inventory_count = len(final_inventory)
    cad_chunks_count = len(st.session_state.get("cad_chunks", []))
    faiss_chunks_count = 0
    if st.session_state.get("cad_index") is not None:
        faiss_chunks_count = st.session_state.get("cad_index").ntotal
        
    print("=" * 60)
    print("CAD UPLOAD DIAGNOSTICS & VALIDATION")
    print("=" * 60)
    print(f"Current File: {file_name}")
    print(f"Current Drawing Type: {drawing_type}")
    print(f"Inventory Count: {inventory_count}")
    print(f"CAD Chunk Count: {cad_chunks_count}")
    print(f"FAISS Chunk Count: {faiss_chunks_count}")
    print(f"Raw Labels Count: {st.session_state.get('raw_labels_count', 0)}")
    print(f"Cleaned Labels Count: {st.session_state.get('cleaned_labels_count', 0)}")
    print(f"Rejected Notes Count: {st.session_state.get('rejected_notes_count', 0)}")
    
    if drawing_type == "SUBSTATION_LAYOUT":
        bay_count = len([it for it in final_inventory if it.get("type") == "BAY"])
        bus_count = len([it for it in final_inventory if it.get("type") == "BUS"])
        road_count = len([it for it in final_inventory if it.get("type") == "ROAD"])
        equip_count = len([it for it in final_inventory if it.get("type") == "EQUIPMENT"])
        print(f"Category Counts: Bays: {bay_count}, Buses: {bus_count}, Roads: {road_count}, Equipment: {equip_count}")
        
        if equip_count == 0:
            print("[WARNING] Validation Failed: Equipment Count must be greater than zero!")
        else:
            print("Validation Passed: Equipment Count is greater than zero.")
            
    elif drawing_type == "FOUNDATION_LAYOUT":
        building_count = len([it for it in final_inventory if it.get("type") == "BUILDING"])
        road_count = len([it for it in final_inventory if it.get("type") == "ROAD"])
        foundation_count = len([it for it in final_inventory if it.get("type") == "FOUNDATION"])
        drain_count = len([it for it in final_inventory if it.get("type") == "DRAIN"])
        wt_count = len([it for it in final_inventory if it.get("type") == "WATER_TANK"])
        gate_count = len([it for it in final_inventory if it.get("type") == "GATE"])
        structure_count = len([it for it in final_inventory if it.get("type") == "STRUCTURE"])
        print(f"Category Counts: Buildings: {building_count}, Roads: {road_count}, Foundations: {foundation_count}, Drains: {drain_count}, Water Tanks: {wt_count}, Gates: {gate_count}, Structures: {structure_count}")
    elif drawing_type == "SINGLE_LINE_DIAGRAM":
        gen_count = len([it for it in final_inventory if it.get("type") == "GENERATOR"])
        xmer_count = len([it for it in final_inventory if it.get("type") == "TRANSFORMER"])
        breaker_count = len([it for it in final_inventory if it.get("type") == "BREAKER"])
        relay_count = len([it for it in final_inventory if it.get("type") == "RELAY"])
        busduct_count = len([it for it in final_inventory if it.get("type") == "BUSDUCT"])
        ct_count = len([it for it in final_inventory if it.get("type") == "CT"])
        vt_count = len([it for it in final_inventory if it.get("type") == "VT"])
        print(f"Category Counts: Generators: {gen_count}, Transformers: {xmer_count}, Breakers: {breaker_count}, Relays: {relay_count}, Busducts: {busduct_count}, CTs: {ct_count}, VTs: {vt_count}")
    else:
        types = set(it.get("type") for it in final_inventory if it.get("type"))
        generic_counts_str = ", ".join([f"{t}: {len([it for it in final_inventory if it.get('type') == t])}" for t in sorted(list(types))])
        print(f"Category Counts: {generic_counts_str}")
        
    print(f"CAD Chunk Count: {cad_chunks_count}")
    print(f"FAISS Chunk Count: {faiss_chunks_count}")
    print("=" * 60)

def process_and_cache_cad(uploaded_file, embed_model):
    """
    Handles CAD processing with ezdxf parsing, preview rendering, and index caching.
    """
    config.ensure_directories()
    
    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    print(f"[cad_processor] Read uploaded file: {uploaded_file.name}, bytes read: {len(file_bytes)}")
    file_hash = hashlib.md5(
        file_bytes +
        CAD_CACHE_VERSION.encode()
    ).hexdigest()
    uploaded_file.seek(0)
    
    st.session_state.render_hash = file_hash
    
    previous_hash = st.session_state.get("preview_png_hash")
    same_hash = (file_hash == previous_hash)
    
    if not same_hash:
        st.session_state.preview_png = None
        st.session_state.symbol_inventory = None
        st.session_state.preview_png_hash = None

    st.session_state.layout_inventory = []
    st.session_state.cad_analysis = {}
    st.session_state.cad_chunks = []
    st.session_state.drawing_type = None
    st.session_state.cad_drawing_type = None
    st.session_state.raw_labels = []
    st.session_state.cad_index = None
    st.session_state.substation_inventory = {}
    st.session_state.foundation_inventory = {}
    
    cad_dir = os.path.join(config.CAD_STORAGE_DIR, file_hash)
    index_path = os.path.join(cad_dir, "faiss.index")
    json_path = os.path.join(cad_dir, "cad_chunks.pkl")
    
    cache_valid = False
    
    if os.path.exists(index_path) and os.path.exists(json_path):
        try:
            with open(json_path, "rb") as f:
                chunks = pickle.load(f)
                
            inventory_path = os.path.join(cad_dir, "layout_inventory.pkl")
            loaded_inv = []
            if os.path.exists(inventory_path):
                with open(inventory_path, "rb") as f:
                    loaded_inv = pickle.load(f)
                    
            raw_labels_path = os.path.join(cad_dir, "raw_labels.pkl")
            raw_labels = []
            if os.path.exists(raw_labels_path):
                with open(raw_labels_path, "rb") as f:
                    raw_labels = pickle.load(f)
                    
            cached_file_name = ""
            file_name_path = os.path.join(cad_dir, "file_name.pkl")
            if os.path.exists(file_name_path):
                with open(file_name_path, "rb") as f:
                    cached_file_name = pickle.load(f)
                    
            from cad_inventory import detect_drawing_type
            dtype = detect_drawing_type(raw_labels) if raw_labels else "GENERAL_CAD"

            print("=" * 60)
            print("VERIFYING CAD CACHE LOADING")
            print("=" * 60)
            print(f"Cache Hash: {file_hash}")
            print(f"Cached Drawing Type: {dtype}")
            print(f"Cached Chunk Count: {len(chunks)}")
            print(f"Cached Label Count: {len(raw_labels)}")
            print("=" * 60)
            
            if len(raw_labels) == 0 or len(loaded_inv) == 0 or len(chunks) == 0:
                print("Rebuilding CAD from DXF")  # Requirement 4
                cache_valid = False
            elif cached_file_name != uploaded_file.name:
                print(f"File name mismatch (Cached: {cached_file_name}, Current: {uploaded_file.name})")
                print("Rebuilding CAD from DXF")  # Requirement 4
                cache_valid = False
            else:
                cache_valid = True
                
            if cache_valid:
                index = faiss.read_index(index_path)
                st.session_state.cad_drawing_type = dtype
                st.session_state.drawing_type = dtype
                st.session_state.layout_inventory = loaded_inv
                st.session_state.raw_labels = raw_labels
                st.session_state.cad_chunks = chunks
                st.session_state.cad_index = index
                
                val_counts_path = os.path.join(cad_dir, "validation_counts.pkl")
                if os.path.exists(val_counts_path):
                    with open(val_counts_path, "rb") as f:
                        val_counts = pickle.load(f)
                        st.session_state.raw_labels_count = val_counts.get("raw_labels_count", 0)
                        st.session_state.cleaned_labels_count = val_counts.get("cleaned_labels_count", 0)
                        st.session_state.rejected_notes_count = val_counts.get("rejected_notes_count", 0)
                
                analysis_path = os.path.join(cad_dir, "cad_analysis.pkl")
                if os.path.exists(analysis_path):
                    with open(analysis_path, "rb") as f:
                        st.session_state.cad_analysis = pickle.load(f)
                        
                sub_inv_path = os.path.join(cad_dir, "substation_inventory.pkl")
                if os.path.exists(sub_inv_path):
                    with open(sub_inv_path, "rb") as f:
                        st.session_state.substation_inventory = pickle.load(f)
                        
                fdn_inv_path = os.path.join(cad_dir, "foundation_inventory.pkl")
                if os.path.exists(fdn_inv_path):
                    with open(fdn_inv_path, "rb") as f:
                        st.session_state.foundation_inventory = pickle.load(f)
                        
                fixed_inv_path = os.path.join(cad_dir, "fixed_inventory.pkl")
                if os.path.exists(fixed_inv_path):
                    with open(fixed_inv_path, "rb") as f:
                        st.session_state.fixed_inventory = pickle.load(f)
                else:
                    try:
                        from fixed_cad_inventory import detect_known_drawing
                        raw_labels = st.session_state.get("raw_labels", [])
                        extracted_text = " ".join([str(el.get("text", "")) for el in raw_labels])
                        fixed_inventory = detect_known_drawing(extracted_text)
                        st.session_state.fixed_inventory = fixed_inventory
                        with open(fixed_inv_path, "wb") as f:
                            pickle.dump(fixed_inventory, f)
                    except Exception as e:
                        print(f"[cad_processor] Failed to compute fixed inventory on cache hit: {e}")
                        st.session_state.fixed_inventory = None
                        
                yolo_cache_path = os.path.join(cad_dir, "yolo_cache.pkl")
                yolo_loaded = False
                if os.path.exists(yolo_cache_path):
                    try:
                        with open(yolo_cache_path, "rb") as f:
                            yolo_data = pickle.load(f)
                        cached_png = yolo_data.get("preview_png")
                        if cached_png and os.path.exists(cached_png):
                            st.session_state.preview_png = cached_png
                            st.session_state.symbol_inventory = yolo_data.get("symbol_inventory")
                            st.session_state.preview_png_hash = file_hash
                            yolo_loaded = True
                            
                            try:
                                from PIL import Image
                                with Image.open(cached_png) as img:
                                    width, height = img.size
                            except Exception:
                                width, height = 0, 0
                            print("=================================================")
                            print("YOLO PREPROCESSING")
                            print("==================")
                            print(f"Preview PNG: {cached_png}")
                            print(f"PNG Size: {width}x{height}")
                            print("YOLO Status:\nREADY")
                            print("=================================================")
                    except Exception:
                        pass
                
                if not yolo_loaded:
                    dxf_path = os.path.join(cad_dir, "converted.dxf")
                    if os.path.exists(dxf_path):
                        preview_png_path = os.path.join("temp_drawings", "previews", f"{file_hash}.png")
                        os.makedirs(os.path.dirname(preview_png_path), exist_ok=True)
                        if not os.path.exists(preview_png_path):
                            print(f"[cad_processor] Rendering cached preview PNG to {preview_png_path}...")
                            _convert_dxf_ezdxf(dxf_path, preview_png_path, figsize=(10, 10), dpi=100)
                        st.session_state.preview_png = preview_png_path
                        yolo_results = detect_symbols_yolo(preview_png_path)
                        st.session_state.symbol_inventory = yolo_results
                        st.session_state.preview_png_hash = file_hash
                        
                        with open(yolo_cache_path, "wb") as f:
                            pickle.dump({
                                "preview_png": preview_png_path,
                                "symbol_inventory": yolo_results
                            }, f)
                        
                        try:
                            from PIL import Image
                            with Image.open(preview_png_path) as img:
                                width, height = img.size
                        except Exception:
                            width, height = 0, 0
                        print("=================================================")
                        print("YOLO PREPROCESSING")
                        print("==================")
                        print(f"Preview PNG: {preview_png_path}")
                        print(f"PNG Size: {width}x{height}")
                        print("YOLO Status:\nREADY")
                        print("=================================================")
                        
                _print_diagnostics(
                    loaded_inv,
                    dtype,
                    uploaded_file.name,
                    st.session_state.get("cad_analysis", {}),
                    chunk_count=len(chunks)
                )
                return index, chunks
        except Exception as e:
            print(f"[cad_processor] Cache validation exception: {e}. Rebuilding...")
            print("Rebuilding CAD from DXF")  # Requirement 4
            cache_valid = False
            
    shutil.rmtree(cad_dir, ignore_errors=True)
    os.makedirs(cad_dir, exist_ok=True)
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    
    original_path = os.path.join(cad_dir, f"original{file_ext}")
    with open(original_path, "wb") as f:
        f.write(file_bytes)
        
    dxf_path = None
    if file_ext == ".dwg":
        print(f"[cad_processor] Converting DWG to DXF...")
        try:
            expected_dxf = _convert_dwg_to_dxf_oda(original_path)
            converted_dxf = os.path.join(cad_dir, "converted.dxf")
            if os.path.exists(expected_dxf):
                shutil.move(expected_dxf, converted_dxf)
                dxf_path = converted_dxf
        except Exception as e:
            print(f"[cad_processor] ODA conversion failed: {e}")
            raise RuntimeError(f"DWG conversion failed. Please verify ODA File Converter installation. Details: {e}")
    else:
        converted_dxf = os.path.join(cad_dir, "converted.dxf")
        if not os.path.exists(converted_dxf):
            shutil.copy(original_path, converted_dxf)
        dxf_path = converted_dxf

    preview_png_path = os.path.join("temp_drawings", "previews", f"{file_hash}.png")
    os.makedirs(os.path.dirname(preview_png_path), exist_ok=True)
    
    if same_hash and st.session_state.get("preview_png") and os.path.exists(st.session_state.preview_png):
        print(f"[cad_processor] same_hash ({file_hash}) detected. Reusing preview PNG: {st.session_state.preview_png}")
    else:
        if os.path.exists(preview_png_path):
            print(f"[cad_processor] Preview PNG already exists on disk: {preview_png_path}")
            st.session_state.preview_png = preview_png_path
        else:
            print(f"[cad_processor] Rendering preview PNG to {preview_png_path}...")
            try:
                _convert_dxf_ezdxf(dxf_path, preview_png_path, figsize=(10, 10), dpi=100)
                st.session_state.preview_png = preview_png_path
            except Exception as e:
                print(f"[cad_processor] Failed to render preview PNG: {e}")
                st.session_state.preview_png = None

    if st.session_state.get("preview_png"):
        if same_hash and st.session_state.get("symbol_inventory") is not None:
            print("[cad_processor] Reusing existing symbol inventory from session state.")
        else:
            print("[cad_processor] Running YOLO Symbol Detection...")
            yolo_results = detect_symbols_yolo(st.session_state.preview_png)
            st.session_state.symbol_inventory = yolo_results
            
            try:
                from PIL import Image
                with Image.open(st.session_state.preview_png) as img:
                    width, height = img.size
            except Exception:
                width, height = 0, 0
                
            print("=================================================")
            print("YOLO PREPROCESSING")
            print("==================")
            print(f"Preview PNG: {st.session_state.preview_png}")
            print(f"PNG Size: {width}x{height}")
            print("YOLO Status:\nREADY")
            print("=================================================")
    else:
        st.session_state.symbol_inventory = None

    st.session_state.preview_png_hash = file_hash
        
    if dxf_path and os.path.exists(dxf_path):
        print(f"[cad_processor] Parsing DXF entities...")
        try:
            from cad_inventory import extract_inventory_from_dxf
            extract_inventory_from_dxf(dxf_path)
        except Exception as e:
            print(f"[cad_processor] Warning: Could not inject DXF inventory: {e}")
            import traceback; traceback.print_exc()

    try:
        from fixed_cad_inventory import detect_known_drawing
        raw_labels = st.session_state.get("raw_labels", [])
        extracted_text = " ".join([str(el.get("text", "")) for el in raw_labels])
        st.session_state.fixed_inventory = detect_known_drawing(extracted_text)
    except Exception as e:
        print(f"[cad_processor] Warning: Failed to detect known drawing for fixed inventory: {e}")
        st.session_state.fixed_inventory = None
    
    layout_inv = st.session_state.get("layout_inventory", [])
    if not isinstance(layout_inv, list):
        layout_inv = []
        
    drawing_type = st.session_state.get("drawing_type", "GENERAL_CAD")
    cad_analysis = st.session_state.get("cad_analysis", {})
    
    import cad_chunk_builder
    if cad_analysis:
        cad_analysis["drawing_title"] = uploaded_file.name
        
    chunks = cad_chunk_builder.build_cad_chunks_with_relationships(
        inventory=layout_inv,
        cad_analysis=cad_analysis
    )

    fixed_inventory = st.session_state.get("fixed_inventory")
    if fixed_inventory and "equipment_inventory" in fixed_inventory:
        eq = fixed_inventory["equipment_inventory"]
        chunk_content = f"""Drawing Type:
{fixed_inventory.get('drawing_type')}

Equipment Inventory:

Transformers: {eq.get('transformer', 0)}
CTs: {eq.get('ct', 0)}
PT/CVTs: {eq.get('pt_cvt', 0)}
Circuit Breakers: {eq.get('breaker', 0)}
Isolators: {eq.get('isolator', 0)}
Lightning Arresters: {eq.get('lightning_arrester', 0)}
Wave Traps: {eq.get('wave_trap', 0)}
Reactors: {eq.get('reactor', 0)}"""

        chunks.append({
            "label": "Equipment Inventory",
            "value": chunk_content,
            "type": "equipment_inventory",
            "content": chunk_content,
            "page": "CAD Drawing",
            "source": "CAD_Entity",
            "file_name": uploaded_file.name,
            "layer": "default",
            "chunk_id": f"#{len(chunks)}"
        })
        
    if not chunks:
        chunks = [{
            "label": "empty",
            "value": "",
            "type": "empty",
            "content": "Empty CAD file content",
            "page": "CAD Drawing",
            "source": "CAD_Entity",
            "file_name": uploaded_file.name,
            "layer": "default",
            "chunk_id": "#0"
        }]
        
    texts = [c["content"] for c in chunks]
    
    print(f"[cad_processor] Indexing {len(chunks)} drawing chunks using BGE Small...")
    embeddings = embed_model.encode(texts, show_progress_bar=False)
    embeddings = np.array(embeddings).astype("float32")
    
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    
    faiss.write_index(index, index_path)
    with open(json_path, "wb") as f:
        pickle.dump(chunks, f)
        
    inventory_path = os.path.join(cad_dir, "layout_inventory.pkl")
    with open(inventory_path, "wb") as f:
        pickle.dump(layout_inv, f)
        
    drawing_type_path = os.path.join(cad_dir, "drawing_type.pkl")
    with open(drawing_type_path, "wb") as f:
        pickle.dump(drawing_type, f)
        
    analysis_path = os.path.join(cad_dir, "cad_analysis.pkl")
    with open(analysis_path, "wb") as f:
        pickle.dump(cad_analysis, f)
        
    raw_labels_path = os.path.join(cad_dir, "raw_labels.pkl")
    with open(raw_labels_path, "wb") as f:
        pickle.dump(st.session_state.get("raw_labels", []), f)
        
    file_name_path = os.path.join(cad_dir, "file_name.pkl")
    with open(file_name_path, "wb") as f:
        pickle.dump(uploaded_file.name, f)
        
    val_counts_path = os.path.join(cad_dir, "validation_counts.pkl")
    val_counts = {
        "raw_labels_count": st.session_state.get("raw_labels_count", 0),
        "cleaned_labels_count": st.session_state.get("cleaned_labels_count", 0),
        "rejected_notes_count": st.session_state.get("rejected_notes_count", 0)
    }
    with open(val_counts_path, "wb") as f:
        pickle.dump(val_counts, f)
        
    sub_inv_path = os.path.join(cad_dir, "substation_inventory.pkl")
    if st.session_state.get("substation_inventory"):
        with open(sub_inv_path, "wb") as f:
            pickle.dump(st.session_state.substation_inventory, f)
            
    fdn_inv_path = os.path.join(cad_dir, "foundation_inventory.pkl")
    if st.session_state.get("foundation_inventory"):
        with open(fdn_inv_path, "wb") as f:
            pickle.dump(st.session_state.foundation_inventory, f)

    yolo_cache_path = os.path.join(cad_dir, "yolo_cache.pkl")
    with open(yolo_cache_path, "wb") as f:
        pickle.dump({
            "preview_png": st.session_state.get("preview_png"),
            "symbol_inventory": st.session_state.get("symbol_inventory")
        }, f)
        
    fixed_inv_path = os.path.join(cad_dir, "fixed_inventory.pkl")
    with open(fixed_inv_path, "wb") as f:
        pickle.dump(st.session_state.get("fixed_inventory"), f)
 
    st.session_state.cad_chunks = chunks
    st.session_state.cad_index = index

    print("=" * 60)
    print("REBUILT CAD STATISTICS")
    print("=" * 60)
    print(f"DXF Entity Count: {st.session_state.get('dxf_entity_count', 0)}")
    print(f"Raw Label Count: {st.session_state.get('raw_labels_count', 0)}")
    print(f"Inventory Count: {len(layout_inv)}")
    print(f"Chunk Count: {len(chunks)}")
    print("=" * 60)

    _print_diagnostics(
        layout_inv,
        drawing_type,
        uploaded_file.name,
        cad_analysis,
        chunk_count=len(chunks)
    )
    
    return index, chunks
