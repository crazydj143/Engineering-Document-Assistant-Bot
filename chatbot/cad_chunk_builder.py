"""
cad_chunk_builder.py
─────────────────────────────────────────────────────────────────────────────
Converts CAD inventory items (structured data) into rich, embeddings-friendly 
text chunks for RAG retrieval.

USAGE:
------
from cad_chunk_builder import convert_inventory_to_chunks
from sentence_transformers import SentenceTransformer
import faiss

# After loading CAD drawing
chunks = convert_inventory_to_chunks(
    inventory=st.session_state.layout_inventory,
    drawing_type=st.session_state.cad_drawing_type,
    cad_analysis=st.session_state.cad_analysis
)

# Build FAISS index
embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
embeddings = embedder.encode([c["content"] for c in chunks])
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

st.session_state.cad_chunks = chunks
st.session_state.cad_index = index
"""

import re


def _get_type_description(item_type: str) -> str:
    """Return contextual description based on equipment type."""
    descriptions = {
        "TRANSFORMER": "a power transformer used for voltage transformation",
        "CT": "a current transformer for metering and protection",
        "VT": "a voltage/potential transformer for metering",
        "BREAKER": "a circuit breaker for switching and protection",
        "BUSDUCT": "a busduct for power distribution",
        "RELAY": "a protective relay for circuit protection",
        "PROTECTION": "a protection device (lightning arrester/surge arrester)",
        "METERING": "a metering device for electrical measurement",
        "GENERATOR": "a power generator or genset",
        
        "BAY": "a feeder bay with associated equipment",
        "BUS": "an electrical bus bar",
        "BUSBAR": "a busbar for power distribution",
        "EQUIPMENT": "electrical equipment",
        "ICT": "an instrument current transformer",
        "COUPLER": "a bus coupler for connecting different buses",
        "BUSREACTOR": "a bus reactor for limiting fault currents",
        "BUSDUCTOR": "a busductor for power distribution",
        
        "EARTHING": "part of the earthing/grounding system",
        "EARTH_PIT": "an earth pit or grounding electrode pit",
        "EARTHING_GRID": "an earthing grid for grounding",
        "GRID_CONDUCTOR": "a conductor in the earthing grid",
        "CONDUCTOR": "a grounding conductor or strip",
        
        "FOUNDATION": "a foundation structure",
        "FOOTING": "a footing or foundation pad",
        "PEDESTAL": "a pedestal foundation",
        
        "BUILDING": "a building structure",
        "STRUCTURE": "a structural element or frame",
        "ROAD": "a road or approach way",
        "DRAIN": "a drainage system or drain",
        "WALL": "a wall structure",
        "GATE": "a gate or entrance",
        "GANTRY": "a gantry structure for equipment support",
        "CABLE": "a cable tray, conduit, or cable routing element",
        
        "AUXILIARY": "an auxiliary system (battery, UPS, lighting)",
        "BATTERY": "a battery system",
        "UPS": "an uninterruptible power supply",
        "LIGHTING": "a lighting installation",
        
        "GENERAL": "a general CAD element",
    }
    
    return descriptions.get(item_type, f"a {item_type.lower().replace('_', ' ')} element")


def convert_inventory_to_chunks(inventory: list, drawing_type: str = "GENERAL", cad_analysis: dict = None) -> list:
    """
    Convert CAD inventory items into rich, embeddings-friendly text chunks.
    
    Args:
        inventory: List of inventory items from cad_inventory.py extraction
        drawing_type: Type of drawing (e.g., "SUBSTATION_LAYOUT", "EARTHING_LAYOUT")
        cad_analysis: CAD analysis dict with summary, counts, etc.
    
    Returns:
        List of chunk dicts with "content", "source", "item_name", etc.
    """
    if not inventory:
        return []
    
    cad_analysis = cad_analysis or {}
    chunks = []
    
    for item in inventory:
        name = item.get("name", "Unknown").strip()
        itype = item.get("type", "GENERAL").strip().upper()
        x = item.get("x", 0)
        y = item.get("y", 0)
        layer = item.get("layer", "default").strip()
        
        if not name or name.lower() in ["", "none", "-", "."]:
            continue
        
        type_desc = _get_type_description(itype)
        
        content = f"Element: {name}. Type: {itype.replace('_', ' ').lower()}. "
        content += f"This is {type_desc}. "
        content += f"Location: coordinates ({x:.1f}, {y:.1f}) on layer '{layer}'. "
        
        if drawing_type:
            content += f"Found in {drawing_type.replace('_', ' ').lower()} drawing. "
        
        if x > 0 and y > 0:
            content += f"Positioned at ({x}, {y}) in drawing space. "
        
        chunk = {
            "content": content,
            "source": "CAD_INVENTORY",
            "item_name": name,
            "item_type": itype,
            "coordinates": (x, y),
            "layer": layer,
            "page": 1,
            "file_name": cad_analysis.get("drawing_title", "CAD Drawing"),
            "chunk_id": f"CAD_{itype}_{name.replace(' ', '_')}",
        }
        chunks.append(chunk)
    
    by_type = {}
    for item in inventory:
        itype = item.get("type", "GENERAL").upper()
        if itype not in by_type:
            by_type[itype] = []
        by_type[itype].append(item.get("name", "Unknown"))
    
    for itype, names in by_type.items():
        if not names:
            continue
        
        count = len(names)
        type_desc = itype.replace("_", " ").lower()
        name_list = ", ".join(sorted(set([n for n in names if n])))
        
        content = f"The drawing contains {count} {type_desc} element(s): {name_list}. "
        
        chunk = {
            "content": content,
            "source": "CAD_SUMMARY",
            "item_type": itype,
            "page": 1,
            "file_name": cad_analysis.get("drawing_title", "CAD Drawing"),
            "chunk_id": f"CAD_SUMMARY_{itype}",
        }
        chunks.append(chunk)
    
    if cad_analysis:
        summary = cad_analysis.get("summary", "")
        if summary:
            chunk = {
                "content": f"Drawing Summary: {summary}",
                "source": "CAD_ANALYSIS",
                "page": 1,
                "file_name": cad_analysis.get("drawing_title", "CAD Drawing"),
                "chunk_id": "CAD_ANALYSIS_SUMMARY",
            }
            chunks.append(chunk)
        
        drawing_title = cad_analysis.get("drawing_title", "CAD Drawing")
        drawing_type_val = cad_analysis.get("drawing_type", "Unknown")
        
        content = f"Drawing: {drawing_title}. Type: {drawing_type_val}. "
        
        if cad_analysis.get("transformers"):
            trans = ", ".join([str(t) for t in cad_analysis.get("transformers", [])])
            content += f"Transformers: {trans}. "
        
        if cad_analysis.get("generators"):
            gens = ", ".join([str(g) for g in cad_analysis.get("generators", [])])
            content += f"Generators: {gens}. "
        
        if cad_analysis.get("breakers"):
            brkrs = ", ".join([str(b) for b in cad_analysis.get("breakers", [])])
            content += f"Circuit Breakers: {brkrs}. "
        
        if cad_analysis.get("foundations"):
            fdns = ", ".join([str(f) for f in cad_analysis.get("foundations", [])])
            content += f"Foundations: {fdns}. "
        
        if cad_analysis.get("earth_pits"):
            eps = ", ".join([str(e) for e in cad_analysis.get("earth_pits", [])])
            content += f"Earth Pits: {eps}. "
        
        if cad_analysis.get("roads"):
            roads = ", ".join([str(r) for r in cad_analysis.get("roads", [])])
            content += f"Roads/Approaches: {roads}. "
        
        if cad_analysis.get("buildings"):
            bldgs = ", ".join([str(b) for b in cad_analysis.get("buildings", [])])
            content += f"Buildings: {bldgs}. "
        
        if len(content) > len(f"Drawing: {drawing_title}. "):
            chunk = {
                "content": content,
                "source": "CAD_METADATA",
                "page": 1,
                "file_name": drawing_title,
                "chunk_id": "CAD_METADATA_COUNTS",
            }
            chunks.append(chunk)
    
    return chunks


def build_cad_chunks_with_relationships(inventory: list, cad_analysis: dict = None) -> list:
    """
    Advanced version: Creates chunks with spatial/logical relationships between items.
    
    Example: "Bay-1 contains Transformer TR-01, Circuit Breaker CB-01, and Current Transformer CT-01"
    
    Args:
        inventory: Inventory items
        cad_analysis: CAD analysis with bay/bus groupings
    
    Returns:
        List of chunks
    """
    chunks = convert_inventory_to_chunks(inventory, cad_analysis.get("drawing_type") if cad_analysis else "GENERAL", cad_analysis)
    
    if not cad_analysis:
        return chunks
    
    bays = cad_analysis.get("bays", [])
    if isinstance(bays, list):
        for bay_name in bays:
            bay_equipment = []
            for item in inventory:
                if "bay" in item.get("name", "").lower() and bay_name.lower() in item.get("name", "").lower():
                    bay_equipment.append(item.get("name"))
            
            if bay_equipment:
                equipment_str = ", ".join(bay_equipment)
                content = f"{bay_name} contains the following equipment: {equipment_str}. "
                
                chunk = {
                    "content": content,
                    "source": "CAD_BAY_COMPOSITION",
                    "bay_name": bay_name,
                    "page": 1,
                    "file_name": cad_analysis.get("drawing_title", "CAD Drawing"),
                    "chunk_id": f"CAD_BAY_{bay_name.replace(' ', '_')}",
                }
                chunks.append(chunk)
    
    return chunks



def integrate_with_rag(inventory, drawing_type, cad_analysis, embed_model, use_relationships=False):
    """
    Complete integration: Convert inventory → chunks → embeddings → FAISS index
    
    Args:
        inventory: CAD inventory items
        drawing_type: Drawing type string
        cad_analysis: CAD analysis dict
        embed_model: SentenceTransformer model
        use_relationships: If True, use advanced chunking with relationships
    
    Returns:
        (chunks, faiss_index) tuple ready to store in session state
    """
    import numpy as np
    
    if use_relationships:
        chunks = build_cad_chunks_with_relationships(inventory, cad_analysis)
    else:
        chunks = convert_inventory_to_chunks(inventory, drawing_type, cad_analysis)
    
    if not chunks:
        print("[WARNING] No CAD chunks generated!")
        return [], None
    
    chunk_texts = [c["content"] for c in chunks]
    embeddings = embed_model.encode(chunk_texts, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype=np.float32)
    
    import faiss
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    print(f"[CAD RAG] Created {len(chunks)} chunks, indexed in FAISS")
    
    return chunks, index
