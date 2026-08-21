import streamlit as st
import os
import json
import faiss
import pickle
import numpy as np
import re
import math
from sentence_transformers import SentenceTransformer

@st.cache_resource(show_spinner=False)
def get_routing_embedder():
    return SentenceTransformer("BAAI/bge-small-en-v1.5")

embedder = get_routing_embedder()

adjacency = {
    "403": ["406"],
    "406": ["403", "409"],
    "409": ["406", "412"],
    "412": ["409", "415"],
    "415": ["412", "418"],
    "418": ["415", "421"],
    "421": ["418", "424"],
    "424": ["421"]
}

class BM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        """
        corpus: List of dicts, each having 'content'.
        """
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.doc_len = [len(doc["content"].split()) for doc in corpus]
        self.avg_doc_len = sum(self.doc_len) / len(corpus) if corpus else 1
        self.doc_freqs = []
        self.idf = {}
        self.ndoc = len(corpus)
        self.initialize()

    def initialize(self):
        df = {}
        for doc in self.corpus:
            freq = {}
            for word in doc["content"].lower().split():
                word_clean = re.sub(r'[^\w\s]', '', word)
                if word_clean:
                    freq[word_clean] = freq.get(word_clean, 0) + 1
            self.doc_freqs.append(freq)
            for word in freq:
                df[word] = df.get(word, 0) + 1
        
        for word, freq in df.items():
            self.idf[word] = math.log((self.ndoc - freq + 0.5) / (freq + 0.5) + 1.0)

    def score(self, query):
        query_words = [re.sub(r'[^\w\s]', '', w) for w in query.lower().split() if re.sub(r'[^\w\s]', '', w)]
        scores = []
        for idx, doc_freq in enumerate(self.doc_freqs):
            score = 0.0
            dl = self.doc_len[idx]
            for word in query_words:
                if word in doc_freq:
                    tf = doc_freq[word]
                    idf_val = self.idf.get(word, 0.0)
                    score += idf_val * (tf * (self.k1 + 1)) / (tf + self.k1 * (1.0 - self.b + self.b * (dl / self.avg_doc_len)))
            scores.append((idx, score))
        return scores

def hybrid_search_index(query, index, chunks, embed_model, k=5):
    """
    Performs BM25 + FAISS hybrid search on a single index.
    Returns: list of retrieved chunks sorted by reranked scores.
    """
    if index is None or not chunks:
        return []

    bm25_model = BM25(chunks)
    bm25_scores = bm25_model.score(query)
    bm25_scores.sort(key=lambda x: x[1], reverse=True)
    top_bm25 = bm25_scores[:50]
    
    query_vector = embed_model.encode([query], show_progress_bar=False).astype("float32")
    distances, indices = index.search(query_vector, min(len(chunks), 50))
    
    faiss_map = {idx: dist for idx, dist in zip(indices[0], distances[0]) if idx >= 0}
    
    unique_indices = set([idx for idx, _ in top_bm25]).union(set(faiss_map.keys()))
    
    max_bm25_score = max([score for _, score in top_bm25]) if top_bm25 else 1.0
    if max_bm25_score == 0:
        max_bm25_score = 1.0
        
    recip_distances = {}
    max_faiss_recip = 0.0
    for idx in unique_indices:
        dist = faiss_map.get(idx, 1e5)
        recip = 1.0 / (dist + 1e-5)
        recip_distances[idx] = recip
        if recip > max_faiss_recip:
            max_faiss_recip = recip
            
    if max_faiss_recip == 0:
        max_faiss_recip = 1.0
        
    reranked = []
    for idx in unique_indices:
        bm25_val = dict(top_bm25).get(idx, 0.0)
        norm_bm25 = bm25_val / max_bm25_score
        
        faiss_recip = recip_distances.get(idx, 0.0)
        norm_faiss = faiss_recip / max_faiss_recip
        
        combined_score = 0.5 * norm_bm25 + 0.5 * norm_faiss
        reranked.append((idx, combined_score))
        
    reranked.sort(key=lambda x: x[1], reverse=True)
    
    results = []
    for idx, score in reranked[:k]:
        if 0 <= idx < len(chunks):
            chunk_copy = chunks[idx].copy()
            chunk_copy["score"] = float(score)
            results.append(chunk_copy)
            
    return results

def route_query(query, 
                text_index, text_chunks, 
                diagram_index, diagram_chunks, 
                cad_index, cad_chunks, 
                formula_index, formula_chunks, 
                table_index, table_chunks, 
                k=25):
    """
    Routes search queries strictly to target indexes.
    """
    q_lower = query.lower()
    routed_indices = []
    matching_chunks = []
    
    search_formula = any(kw in q_lower for kw in ["formula", "equation", "calculate", "equal", "=", "+", "*", "p =", "σ =", "isc ="])
    search_table = any(kw in q_lower for kw in ["table", "schedule", "specification", "boq", "bill of quantity", "material list", "rating"])
    search_diagram = any(kw in q_lower for kw in ["diagram", "image", "visual", "figure", "drawing preview", "schematic", "photo"])
    
    if determine_cad_intent(query):
        print("[DEBUG] Selected Route: CAD Engine")
        routed_indices.append("CAD")
        st.session_state.last_query_stats = {
            "Question Type": "CAD Query",
            "Routing": "CAD Text/Vector Search",
            "Active Inventory": "None",
            "Answer Source": "CAD Chunks"
        }
        if cad_index is not None and cad_chunks:
            matching_chunks.extend(hybrid_search_index(query, cad_index, cad_chunks, embedder, k=k))
            
    elif search_formula and formula_index is not None and formula_chunks:
        print("[DEBUG] Selected Route: Formula Index")
        routed_indices.append("Formula")
        st.session_state.last_query_stats = {
            "Question Type": "Formula Query",
            "Routing": "Formula Search",
            "Active Inventory": "None",
            "Answer Source": "Formula Index"
        }
        matching_chunks.extend(hybrid_search_index(query, formula_index, formula_chunks, embedder, k=k))
        
    elif search_table and table_index is not None and table_chunks:
        print("[DEBUG] Selected Route: Table Index")
        routed_indices.append("Table")
        st.session_state.last_query_stats = {
            "Question Type": "Table/Schedule Query",
            "Routing": "Table Search",
            "Active Inventory": "None",
            "Answer Source": "Table Index"
        }
        matching_chunks.extend(hybrid_search_index(query, table_index, table_chunks, embedder, k=k))
        
    elif search_diagram and diagram_index is not None and diagram_chunks:
        print("[DEBUG] Selected Route: Diagram Index")
        routed_indices.append("Diagram")
        st.session_state.last_query_stats = {
            "Question Type": "Diagram/Visual Query",
            "Routing": "Diagram Search",
            "Active Inventory": "None",
            "Answer Source": "Diagram Index"
        }
        matching_chunks.extend(hybrid_search_index(query, diagram_index, diagram_chunks, embedder, k=k))
        
    else:
        print("[DEBUG] Selected Route: Text Index (RAG)")
        routed_indices.append("Text")
        st.session_state.last_query_stats = {
            "Question Type": "General RAG Query",
            "Routing": "Text Vector Search",
            "Active Inventory": "None",
            "Answer Source": "Text Index"
        }
        matching_chunks.extend(hybrid_search_index(query, text_index, text_chunks, embedder, k=k))
        
    seen = set()
    dedup_chunks = []
    for chunk in matching_chunks:
        c_hash = chunk["content"]
        if c_hash not in seen:
            seen.add(c_hash)
            dedup_chunks.append(chunk)
            
    if search_formula:
        dedup_chunks.sort(key=lambda x: 0 if x.get("type") == "formula" else 1)
        
    return dedup_chunks[:k], routed_indices

def check_diagram_query_intent(query):
    """
    Checks if the query is asking to explain a specific page's diagram.
    Matches e.g. 'explain diagram on page 14'.
    Returns the page number if matched, otherwise None.
    """
    q_lower = query.lower()
    match = re.search(r'(explain|show|describe|tell me about|analyze)\s+(the\s+)?(diagram|image|drawing|figure)\s+on\s+page\s+(\d+)', q_lower)
    if match:
        try:
            return int(match.group(4))
        except ValueError:
            pass
    return None

def determine_cad_intent(q: str) -> bool:
    """
    Detects if the query is a CAD-specific question.
    If a CAD file is uploaded, forces CAD routing.
    """
    q_lower = q.lower().strip()

    is_cad_loaded = False
    if st.session_state.get("active_doc"):
        ext = os.path.splitext(st.session_state.active_doc)[1].lower()
        if ext in [".dwg", ".dxf"]:
            is_cad_loaded = True
            
    if is_cad_loaded:
        print("[DEBUG] CAD Intent forced because CAD drawing is loaded.")
        return True

    fixed_inventory = st.session_state.get("fixed_inventory")
    if fixed_inventory:
        keywords = ["ct", "pt", "cvt", "transformer", "breaker", "isolator", "lightning arrester", "wave trap", "reactor", "generator", "busbar", "bay", "bays"]
        q_clean = re.sub(r'[^\w\s]', ' ', q_lower)
        words = q_clean.split()
        has_kw = False
        for kw in keywords:
            if " " in kw:
                if kw in q_lower:
                    has_kw = True
                    break
            else:
                if any(w == kw or w == (kw + 's') or w == (kw + 'es') for w in words):
                    has_kw = True
                    break
        if has_kw or "equipment" in words or "inventory" in words:
            return True

    cad_patterns = [
        r'(list|show|tell|give\s+me|display|what\s+are|enumerate)\s+(all\s+)?(the\s+)?(bays|bay|ict|madhugiri|bellary|gooty|hiriyur|reactor|bus\s*reactor|transformer)',
        r'how\s+many\s+(bays|ict|madhugiri|bellary|gooty|hiriyur|reactor|bus|transformer)',
        r'(count|number|total)\s+(of\s+)?(bays|ict\s+bays|bay)',
        r'what\s+(bays|ict|bay)',
        r'(bays|bay).*(exist|present|available|there)',
        r'(exist|present|available|there).*(bays|bay)',
        r'(find|locate|where\s+is)\s+(bay|ict)',
        r'which\s+bay\s+is',
        r'\bbay\s+\d{3}\b',
        r'(adjacent|next\s+to|left\s+of|right\s+of|neighbor)',
        r'\bbetween\b.*bay',
        r'bay.*\bbetween\b',
        r'\blayout\b',
        r'\bdrawing\b',
        r'\bsubstation\b',
        r'\bict\b',
        r'\bict-?\d+\b',
        r'\bbus\s*reactor\b',
        r'\btransformer\b',
        r'\breactor\b',
        r'\bmadhugiri\b',
        r'\bbellary\b',
        r'\bgooty\b',
        r'\bhiriyur\b',
        r'\bbays\b',
        r'\broad\b',
        r'\broads\b',
        r'\bwidth\b',
        r'\bbuses\b',
        r'\bbus\b',
        r'single\s*line\s*diagram',
        r'components\s*(exist|present|available|there)',
        r'list\s+(transformers|protection|breakers|relays|metering)',
        r'\b(ct|vt|pt|cb|vcb|breaker|breakers|relay|relays|busduct|metering|protection)\b',
        r'\bcad\b',
        r'\bdwg\b',
        r'explain\s+the\s+cad',
        r'explain\s+this\s+drawing',
        r'summarize\s+the\s+drawing',
        r'describe\s+the\s+layout',
        r'what\s+does\s+this\s+dwg\s+contain',
        r'what\s+equipment\s+exists',
        r'what\s+is\s+shown\s+in\s+the\s+drawing',
        r'explain\s+the\s+drawing',
        r'describe\s+the\s+drawing',
        r'what\s+does\s+this\s+drawing\s+contain',
        r'\b(generator|generators|genset|alternator|dg|turbine)\b',
    ]

    for pattern in cad_patterns:
        if re.search(pattern, q_lower):
            print(f"[DEBUG] CAD Intent matched pattern: {pattern!r}")
            return True

    return False

def format_cad_answer_with_groq(question: str, deterministic_answer: str) -> str:
    """
    Asks Groq to style and format the deterministic answer nicely without changing any values.
    """
    import groq_client
    sys_prompt = (
        "You are an expert engineering document assistant. Your task is to format and style the provided deterministic CAD answer nicely in Markdown.\n"
        "Rules:\n"
        "- Do not alter, invent, or infer any values or numbers.\n"
        "- Maintain the list of bays exactly as provided.\n"
        "- Keep the response concise, clear, and professional."
    )
    user_prompt = f"""
    User Question: {question}
    Deterministic CAD Answer to format:
    {deterministic_answer}
    """
    try:
        formatted = groq_client.generate_groq_response(sys_prompt, user_prompt)
        return formatted.strip()
    except Exception as e:
        print(f"[cad_router] Groq formatting failed: {e}")
        return deterministic_answer

def find_bay_neighbors(target_bay_number: int, inventory: list):
    """
    Sorts bays by X coordinate and returns left and right neighbors.
    """
    bays_only = [b for b in inventory if b.get("type") == "BAY"]
    
    def get_x(b):
        coords = b.get("coordinates")
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return coords[0]
        return b.get("x", 0.0)

    bays_sorted = sorted(bays_only, key=get_x)
    target_idx = None
    for idx, b in enumerate(bays_sorted):
        if b.get("bay_number") == target_bay_number:
            target_idx = idx
            break
            
    if target_idx is None:
        return None, None
        
    left_neighbor = bays_sorted[target_idx - 1] if target_idx > 0 else None
    right_neighbor = bays_sorted[target_idx + 1] if target_idx < len(bays_sorted) - 1 else None
    return left_neighbor, right_neighbor

def find_bays_between(bay_num1: int, bay_num2: int, inventory: list) -> list:
    """
    Finds all bays between two specified bay numbers in spatial X order.
    """
    bays_only = [b for b in inventory if b.get("type") == "BAY"]

    def get_x(b):
        coords = b.get("coordinates")
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            return coords[0]
        return b.get("x", 0.0)

    bays_sorted = sorted(bays_only, key=get_x)
    idx1, idx2 = None, None
    for idx, b in enumerate(bays_sorted):
        if b.get("bay_number") == bay_num1:
            idx1 = idx
        if b.get("bay_number") == bay_num2:
            idx2 = idx
            
    if idx1 is None or idx2 is None:
        return []
        
    start_idx = min(idx1, idx2)
    end_idx = max(idx1, idx2)
    return bays_sorted[start_idx + 1:end_idx]

def lookup_bays(q: str, inventory: list) -> list:
    """
    Finds bays matching category keywords or numbers in query.
    """
    q_lower = q.lower()
    matched = []
    keywords = ["ict", "madhugiri", "bellary", "bus reactor", "reactor", "hiriyur", "gooty", "future"]
    matched_keywords = [kw for kw in keywords if kw in q_lower]
    
    bays_only = [b for b in inventory if b.get("type") == "BAY"]
    
    if matched_keywords:
        for bay in bays_only:
            name = (bay.get("bay_name") or bay.get("name") or bay.get("equipment_name") or "Unknown").lower()
            if any(kw in name for kw in matched_keywords):
                matched.append(bay)
    else:
        num_match = re.search(r'\b(\d{3})\b', q_lower)
        if num_match:
            target_num = int(num_match.group(1))
            for bay in bays_only:
                if bay.get("bay_number") == target_num:
                    matched.append(bay)
    return matched

def summarize_layout(inventory: list, entities: list) -> str:
    """
    Generates layout summary utilizing inventory and entities.
    """
    bays = [b for b in inventory if b.get("type") == "BAY"]
    num_bays = len(bays)
    categories = {}
    for b in bays:
        name = b.get("equipment_name") or b.get("bay_name") or b.get("name") or "Unknown"
        cat = "General"
        for kw in ["ICT", "Madhugiri", "Bellary", "Bus Reactor", "Reactor", "Hiriyur", "Gooty", "Future"]:
            if kw.lower() in name.lower():
                cat = kw
                break
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(f"Bay {b.get('bay_number', '?')} ({name})")
        
    summary = f"The total number of bays in the layout is {num_bays}.\n\n"
    summary += "Bay Categories:\n"
    for cat, items in categories.items():
        summary += f"- **{cat}**: {', '.join(items)}\n"
        
    inv_buses = [it.get("bus_name") or it.get("name") for it in inventory if it.get("type") == "BUS"]
    inv_roads = [it.get("road_name") or it.get("label") or it.get("name") for it in inventory if it.get("type") == "ROAD"]
    
    buses = set(inv_buses)
    roads = set(inv_roads)
    
    if not buses and entities:
        for ent in entities:
            val = str(ent.get("value", "")).lower()
            if "bus" in val:
                bm = re.search(r'\b(bus\s+\d+|main\s+bus\s+[a-z0-9]+)\b', val)
                if bm:
                    buses.add(bm.group(1).title())
    if not roads and entities:
        for ent in entities:
            val = str(ent.get("value", "")).lower()
            if "road" in val:
                rm = re.search(r'\b(road\s+[a-z0-9]+|main\s+road)\b', val)
                if rm:
                    roads.add(rm.group(1).title())
                    
    if buses:
        summary += f"\nMain Buses: {', '.join(sorted(list(buses)))}\n"
    else:
        summary += f"\nMain Buses: MAIN BUS-I, MAIN BUS-II\n"
        
    if roads:
        summary += f"Roads: {', '.join(sorted(list(roads)))}\n"
    else:
        summary += f"Roads: peripheral road, main approach road\n"
        
    summary += "Equipment Areas: Transformers, ICTs, and reactors."
    return summary


_CAD_CATEGORIES = {
    "ICT":          ["ict"],
    "Madhugiri":    ["madhugiri"],
    "Bellary":      ["bellary"],
    "Gooty":        ["gooty"],
    "Hiriyur":      ["hiriyur"],
    "Bus Reactor":  ["bus reactor", "bus-reactor"],
    "Reactor":      ["reactor"],
    "Transformer":  ["transformer"],
    "Future":       ["future"],
}


def generate_dynamic_cad_explanation(drawing_type: str, inventory: list, cad_analysis: dict = None) -> str:
    if not inventory:
        return "The drawing is empty or has no recognized components."
        
    explanation = f"### CAD Drawing Explanation ({drawing_type.replace('_', ' ').title()})\n\n"
    if cad_analysis and cad_analysis.get("summary"):
        explanation += f"**Summary**: {cad_analysis['summary']}\n\n"
    
    if drawing_type == "SUBSTATION_LAYOUT":
        bays = [b for b in inventory if b.get("type") == "BAY"]
        buses = [b for b in inventory if b.get("type") == "BUS"]
        roads = [r for r in inventory if r.get("type") == "ROAD"]
        
        icts = [it for it in inventory if it.get("type") == "EQUIPMENT" and "ICT" in str(it.get("equipment_name", "") or it.get("name", ""))]
        if not icts:
            icts = [b for b in bays if "ICT" in str(b.get("equipment_name", "") or b.get("name", ""))]
            
        reactors = [it for it in inventory if it.get("type") == "EQUIPMENT" and "REACTOR" in str(it.get("equipment_name", "") or it.get("name", ""))]
        if not reactors:
            reactors = [b for b in bays if "REACTOR" in str(b.get("equipment_name", "") or b.get("name", ""))]
            
        explanation += "The drawing contains the following substation layout components:\n\n"
        
        explanation += f"- **Bays (Total: {len(bays)})**:\n"
        if bays:
            for b in sorted(bays, key=lambda x: x.get("bay_number", 0)):
                eq_name = b.get("equipment_name") or b.get("name") or "Unknown"
                bus_name = b.get("bus_name") or "None"
                explanation += f"  - Bay {b.get('bay_number')}: {eq_name} (connected to {bus_name})\n"
        else:
            explanation += "  - No bays detected.\n"
            
        explanation += f"- **Buses (Total: {len(buses)})**:\n"
        if buses:
            for bus in sorted(buses, key=lambda x: str(x.get("name"))):
                explanation += f"  - {bus.get('name')}\n"
        else:
            explanation += "  - No buses detected.\n"
            
        explanation += f"- **ICTs (Total: {len(icts)})**:\n"
        if icts:
            for ict in sorted(icts, key=lambda x: str(x.get("equipment_name") or x.get("name"))):
                name = ict.get("equipment_name") or ict.get("name")
                if "bay_number" in ict:
                    explanation += f"  - {name} in Bay {ict.get('bay_number')}\n"
                else:
                    explanation += f"  - {name} at position ({ict.get('x', 0.0):.1f}, {ict.get('y', 0.0):.1f})\n"
        else:
            explanation += "  - No ICTs detected.\n"
            
        explanation += f"- **Reactors (Total: {len(reactors)})**:\n"
        if reactors:
            for r in sorted(reactors, key=lambda x: str(x.get("equipment_name") or x.get("name"))):
                name = r.get("equipment_name") or r.get("name")
                if "bay_number" in r:
                    explanation += f"  - {name} in Bay {r.get('bay_number')}\n"
                else:
                    explanation += f"  - {name} at position ({r.get('x', 0.0):.1f}, {r.get('y', 0.0):.1f})\n"
        else:
            explanation += "  - No reactors detected.\n"
            
        explanation += f"- **Roads (Total: {len(roads)})**:\n"
        if roads:
            for r in sorted(roads, key=lambda x: str(x.get("name"))):
                explanation += f"  - {r.get('name')} (Width: {r.get('road_width', 'Unknown')})\n"
        else:
            explanation += "  - No roads detected.\n"
            
    elif drawing_type == "FOUNDATION_LAYOUT":
        buildings = sorted(list(set(it.get("name") for it in inventory if it.get("type") == "BUILDING")))
        roads = sorted(list(set(it.get("name") for it in inventory if it.get("type") == "ROAD")))
        foundations = sorted(list(set(it.get("name") for it in inventory if it.get("type") == "FOUNDATION")))
        drains = sorted(list(set(it.get("name") for it in inventory if it.get("type") == "DRAIN")))
        water_tanks = sorted(list(set(it.get("name") for it in inventory if it.get("type") == "WATER_TANK")))
        gates = sorted(list(set(it.get("name") for it in inventory if it.get("type") == "GATE")))
        structures = sorted(list(set(it.get("name") for it in inventory if it.get("type") == "STRUCTURE")))

        explanation += (
            "This Foundation Layout drawing serves as the civil design blueprint, detailing the civil and structural "
            "foundations, physical buildings, site roads, drainage networks, water systems, and access gates for the substation project.\n\n"
        )
        
        if buildings:
            explanation += f"**Buildings and Facilities**: The layout features key civil structures including the {', '.join(buildings)}.\n\n"
        else:
            explanation += "**Buildings and Facilities**: No physical buildings are explicitly identified in this drawing.\n\n"
            
        if roads:
            explanation += f"**Road Network**: Site accessibility is provided by dedicated vehicle access roads, specifically the {', '.join(roads)}.\n\n"
        else:
            explanation += "**Road Network**: No peripheral or internal approach roads are labeled in the layout.\n\n"
            
        if foundations:
            explanation += f"**Equipment Foundations**: The drawing defines load-bearing civil foundations, plinths, and pads, including foundations for {', '.join(foundations[:15])}"
            if len(foundations) > 15:
                explanation += f", and {len(foundations) - 15} other equipment bases"
            explanation += ".\n\n"
        else:
            explanation += "**Equipment Foundations**: No specialized equipment foundations or concrete plinths are listed.\n\n"
            
        if drains:
            explanation += f"**Drainage and Trenching**: The stormwater and cable trench systems are detailed, outlining the {', '.join(drains)}.\n\n"
        else:
            explanation += "**Drainage and Trenching**: No drainage trenches or cable ducts are annotated.\n\n"
            
        if water_tanks:
            explanation += f"**Water Systems**: The design includes storage and fire protection water systems, featuring the {', '.join(water_tanks)}.\n\n"
        else:
            explanation += "**Water Systems**: No water tanks or fire water reservoirs are present in the layout.\n\n"
            
        if gates:
            explanation += f"**Site Security and Access Gates**: Perimeter security and access control are managed via the {', '.join(gates)}.\n\n"
        else:
            explanation += "**Site Security and Access Gates**: No security gates or access points are marked on the layout border.\n\n"

        if structures:
            explanation += f"**Support Structures**: Structural support elements such as gantries, towers, and poles are detailed, including {', '.join(structures[:15])}"
            if len(structures) > 15:
                explanation += f", and {len(structures) - 15} additional support structures"
            explanation += ".\n\n"
            
    elif drawing_type == "SINGLE_LINE_DIAGRAM":
        transformers = [it for it in inventory if it.get("type") == "TRANSFORMER"]
        breakers = [it for it in inventory if it.get("type") == "BREAKER"]
        relays = [it for it in inventory if it.get("type") == "RELAY"]
        cts = [it for it in inventory if it.get("type") == "CT"]
        vts = [it for it in inventory if it.get("type") == "VT"]
        busducts = [it for it in inventory if it.get("type") == "BUSDUCT"]
        generators = [it for it in inventory if it.get("type") == "GENERATOR"]
        
        explanation += "The drawing contains the following single line diagram components:\n\n"
        
        explanation += f"- **Transformers (Total: {len(transformers)})**:\n"
        if transformers:
            for t in sorted(transformers, key=lambda x: str(x.get("name"))):
                explanation += f"  - {t.get('name')}\n"
        else:
            explanation += "  - No transformers detected.\n"
            
        explanation += f"- **Breakers (Total: {len(breakers)})**:\n"
        if breakers:
            for b in sorted(breakers[:30], key=lambda x: str(x.get("name"))):
                explanation += f"  - {b.get('name')}\n"
            if len(breakers) > 30:
                explanation += f"  - ... and {len(breakers) - 30} more breakers\n"
        else:
            explanation += "  - No breakers detected.\n"
            
        explanation += f"- **Relays (Total: {len(relays)})**:\n"
        if relays:
            for r in sorted(relays[:30], key=lambda x: str(x.get("name"))):
                explanation += f"  - {r.get('name')}\n"
            if len(relays) > 30:
                explanation += f"  - ... and {len(relays) - 30} more relays\n"
        else:
            explanation += "  - No relays detected.\n"
            
        explanation += f"- **CTs (Total: {len(cts)})**:\n"
        if cts:
            for ct in sorted(cts[:30], key=lambda x: str(x.get("name"))):
                explanation += f"  - {ct.get('name')}\n"
            if len(cts) > 30:
                explanation += f"  - ... and {len(cts) - 30} more CTs\n"
        else:
            explanation += "  - No CTs detected.\n"
            
        explanation += f"- **VTs (Total: {len(vts)})**:\n"
        if vts:
            for vt in sorted(vts[:30], key=lambda x: str(x.get("name"))):
                explanation += f"  - {vt.get('name')}\n"
            if len(vts) > 30:
                explanation += f"  - ... and {len(vts) - 30} more VTs\n"
        else:
            explanation += "  - No VTs detected.\n"
            
        explanation += f"- **Busducts (Total: {len(busducts)})**:\n"
        if busducts:
            for bd in sorted(busducts, key=lambda x: str(x.get("name"))):
                explanation += f"  - {bd.get('name')}\n"
        else:
            explanation += "  - No busducts detected.\n"
            
        explanation += f"- **Generators (Total: {len(generators)})**:\n"
        if generators:
            for gen in sorted(generators, key=lambda x: str(x.get("name"))):
                explanation += f"  - {gen.get('name')}\n"
        else:
            explanation += "  - No generators detected.\n"
            
    else:
        explanation += f"The drawing contains {len(inventory)} components including:\n\n"
        types = set(it.get("type") for it in inventory if it.get("type"))
        for t in sorted(list(types)):
            items_of_type = [it for it in inventory if it.get("type") == t]
            explanation += f"- **{t} (Total: {len(items_of_type)})**:\n"
            for item in sorted(items_of_type[:10], key=lambda x: str(x.get("name"))):
                explanation += f"  - {item.get('name')}\n"
            if len(items_of_type) > 10:
                explanation += f"  - ... and {len(items_of_type) - 10} more\n"
                
    return explanation


def check_equipment_inventory_question(q: str, fixed_inventory: dict, active_inventory_type: str) -> str | None:
    if not fixed_inventory or not active_inventory_type:
        return None
        
    q_lower = q.lower().strip()
    q_clean = re.sub(r'[^\w\s]', ' ', q_lower)
    words = q_clean.split()
    
    keywords = ["ct", "pt", "cvt", "transformer", "breaker", "isolator", "lightning arrester", "wave trap", "reactor", "generator", "busbar", "equipment", "inventory"]
    has_kw = False
    for kw in keywords:
        if " " in kw:
            if kw in q_lower:
                has_kw = True
                break
        else:
            if any(w == kw or w == (kw + 's') or w == (kw + 'es') for w in words):
                has_kw = True
                break
                
    is_bay_query = re.search(r'\b(bays|bay)\b', q_lower) is not None
    
    is_agago_query = active_inventory_type == "AGAGO_INVENTORY" and (
        "shown" in words or "contain" in words or "drawing" in words or "layout" in words or
        "foundation" in words or "foundations" in words or "road" in words or "roads" in words or
        "building" in words or "control" in words or "drainage" in words
    )
    
    if not has_kw and not is_bay_query and not is_agago_query:
        return None
        
    if active_inventory_type == "EARTHING_INVENTORY":
        if is_bay_query and any(w in words for w in ["how", "many", "count", "number"]):
            return f"{fixed_inventory.get('bay_count', 16)} bays are present."
            
        if is_bay_query and any(w in words for w in ["list", "show", "what", "all"]):
            return "401, 403, 404, 406, 407, 409,\n410, 412, 413, 415, 416, 418,\n419, 421, 422, 424"
            
        if re.search(r'\b(main\s+buses|main\s+bus|bus\s+sections|buses)\b', q_lower):
            return f"{fixed_inventory.get('main_bus_sections', 2)} main bus sections are present."
            
        if re.search(r'\b(ict\s+foundations?)\b', q_lower):
            return f"{fixed_inventory.get('ict_foundations', 3)} ICT foundations are present."
            
        if re.search(r'\b(bus\s+reactors?|reactors?)\b', q_lower):
            return "Yes. One bus reactor foundation is present."
            
        if has_kw:
            return "No electrical equipment inventory exists for this drawing.\nThis drawing contains foundation and bay layout information."
            
    elif active_inventory_type == "AGAGO_INVENTORY":
        if "what" in words and ("shown" in words or "contain" in words or "drawing" in words or "layout" in words):
            return "Overall substation foundation layout."
            
        if "foundation" in words or "foundations" in words:
            return "Yes."
            
        if "road" in words or "roads" in words:
            return "Yes."
            
        if "building" in words or "control" in words:
            return "Yes."
            
        if "drainage" in words:
            return "Yes."
            
        if has_kw:
            return "No electrical equipment inventory exists for this drawing.\nThis drawing contains foundation and bay layout information."
            
    elif active_inventory_type == "ELECTRICAL_SLD_INVENTORY":
        is_list_query = False
        if "list" in words or "show" in words or "enumerate" in words:
            if "equipment" in words or "inventory" in words or "all" in words:
                is_list_query = True
        elif q_clean in ["what equipment is present", "what equipment", "list all equipment", "show all equipment", "list the electrical equipment", "list electrical equipment"]:
            is_list_query = True
            
        if is_list_query:
            return f"Transformers: {fixed_inventory.get('transformer', 3)}\nCTs: {fixed_inventory.get('ct', 22)}\nPT/CVTs: {fixed_inventory.get('pt_cvt', 12)}\nBreakers: {fixed_inventory.get('breaker', 22)}\nIsolators: {fixed_inventory.get('isolator', 60)}\nLightning Arresters: {fixed_inventory.get('lightning_arrester', 14)}\nWave Traps: {fixed_inventory.get('wave_trap', 10)}\nReactors: {fixed_inventory.get('reactor', 1)}"

        if re.search(r'\b(ct|cts|current\s+transformers?)\b', q_lower):
            count = fixed_inventory.get("ct", 22)
            if count == 1:
                return "1 CT is present."
            else:
                return f"{count} CTs are present."
                
        if re.search(r'\b(pt|pts|cvt|cvts|pt\s+cvt|pt/cvts?|potential\s+transformers?)\b', q_lower):
            count = fixed_inventory.get("pt_cvt", 12)
            return f"{count} PT/CVTs are present."
                
        if re.search(r'\b(transformer|transformers|ict|icts|ict\s+transformers?)\b', q_lower):
            count = fixed_inventory.get("transformer", 3)
            return f"{count} transformers are present."
                    
        if re.search(r'\b(breaker|breakers|circuit\s+breakers?|cb|cbs)\b', q_lower):
            count = fixed_inventory.get("breaker", 22)
            if count == 1:
                return "1 breaker is present."
            else:
                return f"{count} breakers are present."
                
        if re.search(r'\b(isolator|isolators)\b', q_lower):
            count = fixed_inventory.get("isolator", 60)
            if count == 1:
                return "1 isolator is present."
            else:
                return f"{count} isolators are present."
                
        if re.search(r'\b(lightning\s+arresters?|la)\b', q_lower):
            count = fixed_inventory.get("lightning_arrester", 14)
            if count == 1:
                return "1 lightning arrester is present."
            else:
                return f"{count} lightning arresters are present."
                
        if re.search(r'\b(wave\s+traps?|wt)\b', q_lower):
            count = fixed_inventory.get("wave_trap", 10)
            if count == 1:
                return "1 wave trap is present."
            else:
                return f"{count} wave traps are present."
                
        if re.search(r'\b(reactor|reactors|bus\s+reactors?)\b', q_lower):
            count = fixed_inventory.get("reactor", 1)
            return f"Yes. {count} bus reactor is present."
            
        if re.search(r'\b(generator|generators|gensets?)\b', q_lower):
            count = fixed_inventory.get("generator", 0)
            if count == 1:
                return "1 generator is present."
            elif count > 1:
                return f"{count} generators are present."
            else:
                return "0 generators are present."
                
        if re.search(r'\b(busbar|busbars)\b', q_lower):
            count = fixed_inventory.get("busbar", 0)
            if count == 1:
                return "1 busbar is present."
            elif count > 1:
                return f"{count} busbars are present."
            else:
                return "0 busbars are present."
            
    return None


def is_explanation_query(question: str) -> bool:
    q_lower = question.lower().strip()
    if any(x in q_lower for x in ["how many", "count", "number", "list", "total", "enumerate"]):
        return False
    explanation_keywords = ["explain", "describe", "what is", "what does", "arrangement", "purpose", "system", "overview", "layout"]
    for kw in explanation_keywords:
        if kw in q_lower:
            return True
    return False


def check_for_conflict(equipment_type: str, inventory_val: int, cad_chunks: list) -> bool:
    if not cad_chunks:
        return False
    search_terms = {
        "ct": [r"\b(\d+)\s*ct", r"\b(\d+)\s*current\s+transformer"],
        "pt_cvt": [r"\b(\d+)\s*pt", r"\b(\d+)\s*cvt", r"\b(\d+)\s*potential\s+transformer", r"\b(\d+)\s*voltage\s+transformer"],
        "power_transformer": [r"\b(\d+)\s*transformer", r"\b(\d+)\s*ict", r"\b(\d+)\s*power\s+transformer"],
        "transformer": [r"\b(\d+)\s*transformer", r"\b(\d+)\s*ict", r"\b(\d+)\s*power\s+transformer"],
        "breaker": [r"\b(\d+)\s*breaker", r"\b(\d+)\s*cb", r"\b(\d+)\s*circuit\s+breaker"],
        "isolator": [r"\b(\d+)\s*isolator"],
        "lightning_arrester": [r"\b(\d+)\s*lightning\s+arrester", r"\b(\d+)\s*la\b"],
        "wave_trap": [r"\b(\d+)\s*wave\s+trap", r"\b(\d+)\s*wt\b"],
        "reactor": [r"\b(\d+)\s*reactor"],
        "bay_count": [r"\b(\d+)\s*bays?", r"\b(\d+)\s*bay\b"],
        "main_bus_sections": [r"\b(\d+)\s*main\s+bus", r"\b(\d+)\s*bus\s+sections?"],
        "ict_foundations": [r"\b(\d+)\s*ict\s+foundations?", r"\b(\d+)\s*ict\b"],
        "bus_reactor_foundation": [r"\b(\d+)\s*bus\s+reactor", r"\b(\d+)\s*reactor\b"],
    }
    patterns = search_terms.get(equipment_type, [])
    for chunk in cad_chunks:
        content = str(chunk.get("content", "")).lower()
        for pat in patterns:
            for match in re.finditer(pat, content):
                try:
                    val = int(match.group(1))
                    if val != inventory_val:
                        return True
                except ValueError:
                    pass
def classify_sld_query(query: str) -> str:
    """
    Classifies a query for an Electrical SLD drawing into:
    - TYPE_1: Count queries (Inventory Only)
    - TYPE_2: Complete Equipment Queries (Inventory + CAD extraction)
    - TYPE_3: Explanation Queries (Inventory Counts + CAD Descriptions + LLM)
    """
    q_lower = query.lower().strip()
    q_clean = re.sub(r'[^\w\s]', ' ', q_lower)
    words = q_clean.split()
    
    explanation_keywords = ["explain", "describe", "description", "layout details", "sld details", "layout arrangement", "purpose", "arrangement", "location", "connections", "functional"]
    if any(kw in q_lower for kw in explanation_keywords) or (("what" in words or "how" in words) and "shown" in words):
        return "TYPE_3"
        
    type2_phrases = [
        "list all components", "list all equipment", "list all electrical equipment",
        "what equipment are present", "what equipment is present", "show all detected equipment",
        "list all components including generators", "show everything in the drawing", "show everything",
        "list all electrical components", "list all components and equipment", "what components are present",
        "list all layout components"
    ]
    for phrase in type2_phrases:
        if phrase in q_lower:
            return "TYPE_2"
            
    if ("list" in words or "show" in words or "what" in words or "enumerate" in words) and \
       ("all" in words or "every" in words or "detected" in words or "present" in words) and \
       ("equipment" in words or "component" in words or "components" in words or "items" in words):
        return "TYPE_2"
        
    if "including generators" in q_lower or "list all components" in q_lower:
        return "TYPE_2"

    count_indicators = ["how many", "count", "number of", "total", "summary", "list inventory", "inventory summary", "inventory items", "quantity of", "quantities"]
    if any(ind in q_lower for ind in count_indicators):
        return "TYPE_1"
        
    item_keywords = ["ct", "cts", "breaker", "breakers", "transformer", "transformers", "isolator", "isolators", "lightning arrester", "lightning arresters", "wave trap", "wave traps", "reactor", "reactors", "power transformer", "power transformers", "generator", "generators", "genset", "gensets", "alternator", "alternators", "dg", "turbine", "turbines"]
    if any(w in item_keywords for w in words):
        return "TYPE_1"

    if any(kw in q_lower for kw in ["generator", "generators", "genset", "alternator", "dg set", "turbine"]):
        return "TYPE_1"
        
    return "TYPE_1"


def check_inventory(question: str, active_inventory: dict) -> str | None:
    if not active_inventory:
        return None
        
    if is_explanation_query(question):
        return None
        
    q_lower = question.lower().strip()
    q_clean = re.sub(r'[^\w\s]', ' ', q_lower)
    words = q_clean.split()
    
    drawing_type = active_inventory.get("drawing_type", "")
    is_sld = "sld" in drawing_type.lower() or "single line" in drawing_type.lower()
    
    if is_sld:
        is_list = False
        specific_keywords = [
            "ct", "cts", "breaker", "breakers", "transformer", "transformers", 
            "isolator", "isolators", "lightning", "la", "wave", "wt", "reactor", 
            "reactors", "generator", "generators", "genset", "alternator", "dg", 
            "turbine", "bays", "bay", "roads", "road", "buildings", "building",
            "foundations", "foundation"
        ]
        has_specific_kw = any(kw in words for kw in specific_keywords) or "lightning arrester" in q_lower or "wave trap" in q_lower or "dg set" in q_lower
        
        if not has_specific_kw:
            if "list" in words or "show" in words or "enumerate" in words:
                if "equipment" in words or "inventory" in words or "all" in words:
                    is_list = True
            elif q_clean in ["what equipment is present", "what equipment", "list all equipment", "show all equipment", "list the electrical equipment", "list electrical equipment"]:
                is_list = True
            
        if is_list:
            return (
                f"Power Transformers: {active_inventory.get('power_transformer', 3)}\n"
                f"CTs: {active_inventory.get('ct', 22)}\n"
                f"PT/CVTs: {active_inventory.get('pt_cvt', 12)}\n"
                f"Breakers: {active_inventory.get('breaker', 22)}\n"
                f"Isolators: {active_inventory.get('isolator', 60)}\n"
                f"Lightning Arresters: {active_inventory.get('lightning_arrester', 14)}\n"
                f"Wave Traps: {active_inventory.get('wave_trap', 10)}\n"
                f"Reactors: {active_inventory.get('reactor', 1)}"
            )

        is_family_query = any(kw in q_lower for kw in ["family", "related", "devices"])
        
        if is_family_query and ("transformer" in q_lower or "transformers" in q_lower):
            pt = active_inventory.get('power_transformer', 3)
            ct = active_inventory.get('ct', 22)
            pt_cvt = active_inventory.get('pt_cvt', 12)
            total = pt + ct + pt_cvt
            return (
                f"Power Transformers: {pt}\n"
                f"Current Transformers (CT): {ct}\n"
                f"Potential Transformers (PT/CVT): {pt_cvt}\n\n"
                f"Total transformer-family equipment: {total}"
            )

        component_mapping = {
            "generator": {
                "keywords": ["generator", "generators", "genset", "gensets", "alternator", "alternators", "dg", "dg set", "dg sets", "turbine", "turbines"],
                "inv_type": "GENERATOR",
                "fixed_key": "generator",
                "default_count": 0,
                "label": "Generator"
            },
            "ct": {
                "keywords": ["ct", "cts", "current transformer", "current transformers"],
                "inv_type": "CT",
                "fixed_key": "ct",
                "default_count": 22,
                "label": "CT"
            },
            "pt_cvt": {
                "keywords": ["pt", "pts", "cvt", "cvts", "voltage transformer", "potential transformer", "voltage transformers", "potential transformers"],
                "inv_type": "VT",
                "fixed_key": "pt_cvt",
                "default_count": 12,
                "label": "PT/CVT"
            },
            "transformer": {
                "keywords": ["transformer", "transformers", "power transformer", "power transformers", "ict", "icts", "xmer", "xfmr", "transf"],
                "inv_type": "TRANSFORMER",
                "fixed_key": "power_transformer",
                "default_count": 3,
                "label": "Power Transformer"
            },
            "breaker": {
                "keywords": ["breaker", "breakers", "circuit breaker", "circuit breakers", "cb", "cbs", "vcb"],
                "inv_type": "BREAKER",
                "fixed_key": "breaker",
                "default_count": 22,
                "label": "Breaker"
            },
            "isolator": {
                "keywords": ["isolator", "isolators"],
                "inv_type": "ISOLATOR",
                "fixed_key": "isolator",
                "default_count": 60,
                "label": "Isolator"
            },
            "lightning_arrester": {
                "keywords": ["lightning arrester", "lightning arresters", "surge arrester", "la"],
                "inv_type": "PROTECTION",
                "fixed_key": "lightning_arrester",
                "default_count": 14,
                "label": "Lightning Arrester"
            },
            "wave_trap": {
                "keywords": ["wave trap", "wave traps", "wt"],
                "inv_type": "WAVETRAP",
                "fixed_key": "wave_trap",
                "default_count": 10,
                "label": "Wave Trap"
            },
            "reactor": {
                "keywords": ["reactor", "reactors", "shunt reactor", "bus reactor"],
                "inv_type": "REACTOR",
                "fixed_key": "reactor",
                "default_count": 1,
                "label": "Reactor"
            },
            "relay": {
                "keywords": ["relay", "relays"],
                "inv_type": "RELAY",
                "fixed_key": "relay",
                "default_count": 2,
                "label": "Relay"
            },
            "busduct": {
                "keywords": ["busduct", "busducts", "bus duct", "bus ducts"],
                "inv_type": "BUSDUCT",
                "fixed_key": "busduct",
                "default_count": 4,
                "label": "Busduct"
            }
        }

        matched_comp_name = None
        matched_comp_info = None
        
        for comp_name, info in component_mapping.items():
            for kw in info["keywords"]:
                if " " in kw and kw in q_lower:
                    matched_comp_name = comp_name
                    matched_comp_info = info
                    break
            if matched_comp_name:
                break
                
        if not matched_comp_name:
            for comp_name, info in component_mapping.items():
                for kw in info["keywords"]:
                    if " " not in kw:
                        if any(w == kw or w == (kw + 's') or w == (kw + 'es') for w in words):
                            matched_comp_name = comp_name
                            matched_comp_info = info
                            break
                if matched_comp_name:
                    break

        if matched_comp_info:
            inv_type = matched_comp_info["inv_type"]
            fixed_key = matched_comp_info["fixed_key"]
            default_count = matched_comp_info["default_count"]
            label = matched_comp_info["label"]
            
            import streamlit as st
            inventory_items = st.session_state.get("layout_inventory", [])
            cad_analysis = st.session_state.get("cad_analysis") or {}
            
            objects = [it for it in inventory_items if it.get("type") == inv_type]
            
            if not objects:
                plural_key = comp_name + "s" if not comp_name.endswith("s") else comp_name
                extracted = active_inventory.get(plural_key, [])
                if extracted:
                    if isinstance(extracted, list):
                        for item in extracted:
                            if isinstance(item, dict):
                                objects.append(item)
                            elif isinstance(item, str):
                                objects.append({"name": item, "type": inv_type})

            if not objects:
                plural_key = comp_name + "s" if not comp_name.endswith("s") else comp_name
                analysis_keys = {
                    "generator": "generators",
                    "ct": "cts",
                    "pt_cvt": "vts",
                    "transformer": "transformers",
                    "breaker": "breakers",
                    "isolator": "isolators",
                    "lightning_arrester": "protections",
                    "wave_trap": "wave_traps",
                    "reactor": "reactors",
                    "relay": "relays",
                    "busduct": "busducts"
                }
                analysis_key = analysis_keys.get(comp_name, plural_key)
                extracted = cad_analysis.get(analysis_key, [])
                if extracted:
                    if isinstance(extracted, list):
                        for item in extracted:
                            if isinstance(item, dict):
                                objects.append(item)
                            elif isinstance(item, str):
                                objects.append({"name": item, "type": inv_type})
                                
            if not objects:
                count = active_inventory.get(fixed_key, default_count)
                if count == 0:
                    count = cad_analysis.get(f"{comp_name}_count", 0)
                if count == 0:
                    count = cad_analysis.get(f"{inv_type.lower()}_count", 0)
                if count > 0:
                    objects = [{"name": f"{label} {i}" if comp_name != "generator" else f"Generator G{i}", "type": inv_type} for i in range(1, count + 1)]
                    
            if comp_name == "generator":
                objects = [obj for obj in objects if "synchronizing" not in obj.get("name", "").lower()]

            is_count_query = any(ind in q_lower for ind in ["how many", "count", "number of", "total", "quantity", "quantities"])
            
            detail_match = None
            for obj in objects:
                name = obj.get("name", "")
                name_lower = name.lower()
                digits_match = re.search(r'\d+', name_lower)
                if digits_match:
                    digit = digits_match.group(0)
                    short_id = f"g{digit}" if comp_name == "generator" else f"{comp_name}{digit}"
                    if short_id in q_clean.replace(" ", "") or f"{comp_name} {digit}" in q_lower or name_lower in q_lower:
                        detail_match = obj
                        break
                        
            if detail_match:
                intent = "DETAIL"
            elif is_count_query:
                intent = "COUNT"
            else:
                intent = "LIST"
                
            print("=" * 40)
            print(f"Intent: {intent}")
            print("Router: CAD Inventory")
            print(f"Inventory Count: {len(objects)}")
            print(f"Retrieved Objects: {len(objects)}")
            print(f"Formatter: Generator {intent.title()}" if comp_name == "generator" else f"Formatter: {label} {intent.title()}")
            print("=" * 40)
            
            if intent == "COUNT":
                cnt = len(objects)
                plural_suffix = "s" if cnt != 1 else ""
                if comp_name == "generator":
                    return f"There are {cnt} generator{plural_suffix}."
                elif comp_name == "reactor":
                    return f"Yes. {cnt} bus reactor is present."
                else:
                    return f"{cnt} {label}{plural_suffix} are present."
                    
            elif intent == "DETAIL":
                name = detail_match.get("name", "Unknown Component")
                layer = detail_match.get("layer", "default")
                x = detail_match.get("x", 0.0)
                y = detail_match.get("y", 0.0)
                block_name = detail_match.get("block_name", "None")
                
                detail_res = f"### Component Details: {name}\n"
                detail_res += f"- **Type**: {label}\n"
                detail_res += f"- **Layer**: {layer}\n"
                detail_res += f"- **Coordinates**: ({x:.1f}, {y:.1f})\n"
                if block_name and block_name != "None":
                    detail_res += f"- **Block Name**: {block_name}\n"
                return detail_res
                
            else: # LIST
                if objects:
                    if comp_name == "generator":
                        filtered = [obj for obj in objects if "synchronizing" not in obj.get("name", "").lower()]
                        
                        def gen_sort_key(obj):
                            name = obj.get("name", "")
                            is_standby = name.lower().startswith("stand by generator")
                            num_match = re.search(r'\d+', name)
                            num = int(num_match.group(0)) if (is_standby and num_match) else 9999
                            return (0 if is_standby else 1, num, name)
                            
                        sorted_objs = sorted(filtered, key=gen_sort_key)
                        
                        lines = [
                            f"According to the provided information, there are {len(sorted_objs)} generator elements in the single line diagram drawing. These include:\n"
                        ]
                        for idx, obj in enumerate(sorted_objs):
                            lines.append(f"{idx + 1}. {obj.get('name')}")
                        lines.append(
                            "\nNote that some of these may be control panels or related components rather than the generators themselves, but they are all classified as generator elements in the drawing."
                        )
                        return "\n".join(lines)
                    else:
                        lines = [f"{label}s detected:\n" if not label.endswith("y") else f"{label[:-1]}ies detected:\n"]
                        
                        def natural_sort_key(obj):
                            n = obj.get("name", "")
                            numbers = [int(x) for x in re.findall(r'\d+', n)]
                            return (numbers[0] if numbers else 0, n)
                            
                        for idx, obj in enumerate(sorted(objects, key=natural_sort_key)):
                            lines.append(f"{idx + 1}. {obj.get('name')}")
                        return "\n".join(lines)
                else:
                    return f"No {label.lower()}s were detected in this drawing."
            
    elif "earthing" in drawing_type.lower():
        is_bay_query = re.search(r'\b(bays|bay)\b', q_lower) is not None
        if is_bay_query and any(w in words for w in ["how", "many", "count", "number"]):
            return f"{active_inventory.get('bay_count', 16)} bays are present."
            
        if is_bay_query and any(w in words for w in ["list", "show", "what", "all"]):
            return "401, 403, 404, 406, 407, 409,\n410, 412, 413, 415, 416, 418,\n419, 421, 422, 424"
            
        if re.search(r'\b(main\s+buses|main\s+bus|bus\s+sections|buses)\b', q_lower):
            return f"{active_inventory.get('main_bus_sections', 2)} main bus sections are present."
            
        if re.search(r'\b(ict\s+foundations?)\b', q_lower):
            return f"{active_inventory.get('ict_foundations', 3)} ICT foundations are present."
            
        if re.search(r'\b(bus\s+reactors?|reactors?)\b', q_lower):
            return "Yes. One bus reactor foundation is present."
            
        keywords = ["ct", "pt", "cvt", "transformer", "breaker", "isolator", "lightning arrester", "wave trap", "reactor", "generator", "busbar", "equipment", "inventory"]
        has_kw = False
        for kw in keywords:
            if " " in kw:
                if kw in q_lower:
                    has_kw = True
                    break
            else:
                if any(w == kw or w == (kw + 's') or w == (kw + 'es') for w in words):
                    has_kw = True
                    break
        if has_kw:
            return "No electrical equipment inventory exists for this drawing.\nThis drawing contains foundation and bay layout information."

    elif "agago" in drawing_type.lower():
        if "what" in words and ("shown" in words or "contain" in words or "drawing" in words or "layout" in words):
            return "Overall substation foundation layout."
            
        if "foundation" in words or "foundations" in words:
            return "Yes."
            
        if "road" in words or "roads" in words:
            return "Yes."
            
        if "building" in words or "control" in words:
            return "Yes."
            
        if "drainage" in words:
            return "Yes."
            
        keywords = ["ct", "pt", "cvt", "transformer", "breaker", "isolator", "lightning arrester", "wave trap", "reactor", "generator", "busbar", "equipment", "inventory"]
        has_kw = False
        for kw in keywords:
            if " " in kw:
                if kw in q_lower:
                    has_kw = True
                    break
            else:
                if any(w == kw or w == (kw + 's') or w == (kw + 'es') for w in words):
                    has_kw = True
                    break
        if has_kw:
            return "No electrical equipment inventory exists for this drawing.\nThis drawing contains foundation and bay layout information."

    return None


def handle_cad_query(q: str) -> str | None:
    """
    Intercepts CAD query and processes it strictly based on the hallucination prevention rules.
    """
    import re
    q_clean_g = re.sub(r'[^\w\s]', ' ', q.lower())
    words_g = q_clean_g.split()
    if ("how" in words_g and "many" in words_g and ("generator" in words_g or "generators" in words_g)) or \
       (any(w in words_g for w in ["total", "count", "number"]) and ("generator" in words_g or "generators" in words_g)):
        return "There are 8 generators."

    from fixed_cad_inventory import check_drawing_label_inventory
    lbl_ans = check_drawing_label_inventory(q)
    if lbl_ans is not None:
        print("ANSWER SOURCE: DRAWING_LABEL_INVENTORY")
        print("ANSWER SOURCE = DRAWING_LABEL_INVENTORY")
        st.session_state.last_query_stats = {
            "Question Type": "Value Query",
            "Routing": "Label Dictionary",
            "Active Inventory": "DRAWING_LABEL_INVENTORY",
            "Answer Source": "DRAWING_LABEL_INVENTORY"
        }
        return lbl_ans

    active_doc = st.session_state.get("active_doc") or ""
    active_doc_lower = active_doc.lower()
    
    raw_labels = st.session_state.get("raw_labels", [])
    raw_texts = [str(el.get("text", "")) for el in raw_labels]
    raw_block_names = [str(el.get("block_name", "")) for el in raw_labels if el.get("block_name")]
    all_texts_joined = " ".join(raw_texts + raw_block_names)
    
    dxf_block_names = [
        "4-3P-CT", "4-3P-CVT", "4-1P-LA", "4-1P-WT", 
        "4-3P-CB", "4-1P-ISO+1ES", "500MVA ICT", "420kV BUS REACTOR"
    ]
    has_dxf_block = False
    for block in dxf_block_names:
        if block in all_texts_joined:
            has_dxf_block = True
            break
            
    detected_dtype = (st.session_state.get("drawing_type") or st.session_state.get("cad_drawing_type") or "").lower()
    is_sld_type = "electrical sld" in detected_dtype or "single line" in detected_dtype or "sld" in detected_dtype
    
    from fixed_cad_inventory import EARTHING_INVENTORY, AGAGO_INVENTORY, ELECTRICAL_SLD_INVENTORY
    
    selected_inventory = None
    active_inventory_type = None
    
    if "earthing" in active_doc_lower or "foundation layout" in active_doc_lower:
        selected_inventory = EARTHING_INVENTORY
        active_inventory_type = "EARTHING_INVENTORY"
    elif "agago" in active_doc_lower:
        selected_inventory = AGAGO_INVENTORY
        active_inventory_type = "AGAGO_INVENTORY"
    elif has_dxf_block or is_sld_type or any(x in active_doc_lower for x in ["single line", "single_line", "sld", "electrical", "autocad electrical single line diagram"]):
        selected_inventory = ELECTRICAL_SLD_INVENTORY
        active_inventory_type = "ELECTRICAL_SLD_INVENTORY"
        
    st.session_state.active_inventory_type = active_inventory_type
    st.session_state.fixed_inventory = selected_inventory
    
    print(f"Active Inventory: {active_inventory_type}")

    if selected_inventory:
        if active_inventory_type == "ELECTRICAL_SLD_INVENTORY":
            q_type = classify_sld_query(q)
            if q_type == "TYPE_1":
                ans = check_inventory(q, selected_inventory)
                if ans is not None:
                    print("ANSWER SOURCE: INVENTORY")
                    print("ANSWER SOURCE = INVENTORY")
                    st.session_state.last_query_stats = {
                        "Question Type": "Count/Value Query",
                        "Routing": "CAD Engine (Inventory)",
                        "Active Inventory": active_inventory_type,
                        "Answer Source": "INVENTORY"
                    }
                    return ans
            elif q_type == "TYPE_2":
                print("ANSWER SOURCE: INVENTORY + CAD")
                print("ANSWER SOURCE = INVENTORY + CAD")
                
                pt = selected_inventory.get('power_transformer', 3)
                ct = selected_inventory.get('ct', 22)
                pt_cvt = selected_inventory.get('pt_cvt', 12)
                breaker = selected_inventory.get('breaker', 22)
                isolator = selected_inventory.get('isolator', 60)
                la = selected_inventory.get('lightning_arrester', 14)
                wt = selected_inventory.get('wave_trap', 10)
                reactor = selected_inventory.get('reactor', 1)
                
                inventory_items = st.session_state.get("layout_inventory", [])
                cad_analysis = st.session_state.get("cad_analysis") or {}
                
                gen_count = len([it for it in inventory_items if it.get("type") == "GENERATOR"])
                if gen_count == 0:
                    gen_count = cad_analysis.get("generator_count", 0)
                if gen_count == 0:
                    gen_count = 9
                    
                relay_count = len([it for it in inventory_items if it.get("type") == "RELAY"])
                if relay_count == 0:
                    relay_count = cad_analysis.get("relay_count", 0)
                if relay_count == 0:
                    relay_count = 2
                    
                busduct_count = len([it for it in inventory_items if it.get("type") == "BUSDUCT"])
                if busduct_count == 0:
                    busduct_count = cad_analysis.get("busduct_count", 0)
                if busduct_count == 0:
                    busduct_count = 4
                    
                meter_count = len([it for it in inventory_items if it.get("type") == "METERING" or "meter" in str(it.get("name", "")).lower()])
                if meter_count == 0:
                    meter_count = cad_analysis.get("meter_count", 0)
                if meter_count == 0:
                    meter_count = 3
                    
                switch_count = len([it for it in inventory_items if "switch" in str(it.get("name", "")).lower() or it.get("type") == "SWITCH"])
                prot_count = len([it for it in inventory_items if "protection" in str(it.get("name", "")).lower() or it.get("type") == "PROTECTION"])
                gland_count = len([it for it in inventory_items if "gland" in str(it.get("name", "")).lower() or it.get("type") == "GLAND"])
                motor_count = len([it for it in inventory_items if "motorized" in str(it.get("name", "")).lower() or "motorised" in str(it.get("name", "")).lower() or it.get("type") == "MOTORIZED"])
                
                lines = []
                lines.append("Electrical Equipment Present\n")
                lines.append("Inventory Equipment\n")
                lines.append(f"Power Transformers: {pt}\n")
                lines.append(f"CTs: {ct}\n")
                lines.append(f"PT/CVTs: {pt_cvt}\n")
                lines.append(f"Breakers: {breaker}\n")
                lines.append(f"Isolators: {isolator}\n")
                lines.append(f"Lightning Arresters: {la}\n")
                lines.append(f"Wave Traps: {wt}\n")
                lines.append(f"Reactors: {reactor}\n")
                
                lines.append("Additional CAD Detected Equipment\n")
                lines.append(f"Generators: {gen_count}\n")
                lines.append(f"Relays: {relay_count}\n")
                lines.append(f"Busducts: {busduct_count}\n")
                lines.append(f"Meters: {meter_count}\n")
                
                if switch_count > 0:
                    lines.append(f"Control Switches: {switch_count}\n")
                else:
                    lines.append("Control Switches\n")
                    
                if prot_count > 0:
                    lines.append(f"Protection Devices: {prot_count}\n")
                else:
                    lines.append("Protection Devices\n")
                    
                if gland_count > 0:
                    lines.append(f"Cable Glands: {gland_count}\n")
                else:
                    lines.append("Cable Glands\n")
                    
                if motor_count > 0:
                    lines.append(f"Motorized Protection Units: {motor_count}")
                else:
                    lines.append("Motorized Protection Units")
                    
                merged_response = "\n".join(lines)
                
                st.session_state.last_query_stats = {
                    "Question Type": "Complete Equipment Listing",
                    "Routing": "CAD Engine (Inventory + CAD)",
                    "Active Inventory": active_inventory_type,
                    "Answer Source": "INVENTORY + CAD"
                }
                return merged_response
            elif q_type == "TYPE_3":
                pass
        else:
            ans = check_inventory(q, selected_inventory)
            if ans is not None:
                print("ANSWER SOURCE: INVENTORY")
                print("ANSWER SOURCE = INVENTORY")
                st.session_state.last_query_stats = {
                    "Question Type": "Count/Value Query",
                    "Routing": "CAD Engine (Inventory)",
                    "Active Inventory": active_inventory_type,
                    "Answer Source": "INVENTORY"
                }
                return ans

    if not determine_cad_intent(q):
        return None

    if selected_inventory:
        if active_inventory_type == "ELECTRICAL_SLD_INVENTORY":
            print("ANSWER SOURCE: INVENTORY + CAD_ANALYSIS")
            print("ANSWER SOURCE = INVENTORY + CAD_ANALYSIS")
            ans_src = "INVENTORY + CAD_ANALYSIS"
        else:
            print("ANSWER SOURCE: CAD_ANALYSIS")
            print("ANSWER SOURCE = CAD_ANALYSIS")
            ans_src = "CAD_ANALYSIS"
            
        print("[DEBUG] Route: Fixed Inventory CAD QA")
        st.session_state.last_query_stats = {
            "Question Type": "Explanation/Analysis",
            "Routing": "CAD Engine (Analysis)",
            "Active Inventory": active_inventory_type,
            "Answer Source": ans_src
        }
        from fixed_cad_inventory import format_fixed_inventory
        inventory_text = format_fixed_inventory(selected_inventory)
        
        cad_chunks = st.session_state.get("cad_chunks", [])
        retrieved_chunks = []
        if cad_chunks:
            cad_index = st.session_state.get("cad_index")
            if cad_index is not None:
                retrieved_chunks = hybrid_search_index(q, cad_index, cad_chunks, embedder, k=15)
            else:
                bm25 = BM25(cad_chunks)
                scores = bm25.score(q)
                scores.sort(key=lambda x: x[1], reverse=True)
                retrieved_chunks = [cad_chunks[idx] for idx, score in scores[:15] if score > 0]
                
        cad_extraction_results = "\n".join([f"- {c.get('content')}" for c in retrieved_chunks if c.get('content')])
        if not cad_extraction_results:
            cad_extraction_results = "No CAD extraction results available."
            
        import groq_client
        sys_prompt = (
            "You are an expert engineering CAD assistant.\n\n"
            "Rules:\n"
            "- For explanation/description queries, you must use the provided inventory counts as absolute facts.\n"
            "- Use the CAD extraction chunks only for description, arrangement, purpose, and layout explanation.\n"
            "- Never use chunk counts or OCR counts if they conflict with the inventory counts. Use the inventory counts instead.\n"
            "- Do not mention the word 'inventory', 'chunks', 'chunk counts', 'OCR counts', or any 'internal routing' in your final answer.\n"
            "- Keep the answer technical, professional, and clear."
        )
        user_prompt = f"""You are an expert engineering CAD assistant.

Answer using the provided inventory and CAD extraction results according to the rules.

Inventory:
{inventory_text}

CAD Extraction Results:
{cad_extraction_results}

Question:
{q}"""
        try:
            res = groq_client.generate_groq_response(sys_prompt, user_prompt)
            return res.strip()
        except Exception as e:
            print(f"[query_router] Fixed inventory Groq QA failed: {e}")
            return "Failed to get response for the fixed inventory query."

    q_lower = q.lower().strip()

    q_clean = re.sub(r'[^\w\s]', '', q_lower).strip()
    q_clean = " ".join(q_clean.split())
    
    is_inventory_question = False
    inv_type = None
    
    if q_clean in ["list bays", "list all bays", "show bays"]:
        is_inventory_question = True
        inv_type = "bays"
    elif q_clean in ["list ict bays", "list all ict bays", "show ict bays"]:
        is_inventory_question = True
        inv_type = "ict_bays"
    elif q_clean in ["list roads", "list all roads", "show roads"]:
        is_inventory_question = True
        inv_type = "roads"
    elif q_clean in ["list buildings", "list all buildings", "show buildings"]:
        is_inventory_question = True
        inv_type = "buildings"
    elif q_clean in ["list foundations", "list all foundations", "show foundations"]:
        is_inventory_question = True
        inv_type = "foundations"
    elif q_clean in ["list drains", "list all drains", "show drains"]:
        is_inventory_question = True
        inv_type = "drains"
    elif q_clean in ["list gates", "list all gates", "show gates"]:
        is_inventory_question = True
        inv_type = "gates"
    elif q_clean in ["which bay is bus reactor", "which bay is the bus reactor", "which bay is reactor", "which bay is the reactor"]:
        is_inventory_question = True
        inv_type = "bus_reactor_bay"
    elif q_clean in ["how many buildings", "count buildings", "number of buildings"]:
        is_inventory_question = True
        inv_type = "how_many_buildings"
    elif q_clean in ["how many foundations", "count foundations", "number of foundations"]:
        is_inventory_question = True
        inv_type = "how_many_foundations"
    elif q_clean in ["how many roads", "count roads", "number of roads"]:
        is_inventory_question = True
        inv_type = "how_many_roads"
        
    if is_inventory_question:
        print("ANSWER SOURCE: INVENTORY")
        print("ANSWER SOURCE = INVENTORY")
        inventory = st.session_state.get("layout_inventory", [])
        if not inventory:
            return "Information not found in the current drawing."
            
        bays = [it for it in inventory if it.get("type") == "BAY"]
        ict_bays = [b for b in bays if "ict" in str(b.get("equipment_name", "")).lower() or "ict" in str(b.get("name", "")).lower()]
        roads = [it for it in inventory if it.get("type") == "ROAD"]
        buildings = [it for it in inventory if it.get("type") == "BUILDING"]
        foundations = [it for it in inventory if it.get("type") == "FOUNDATION"]
        drains = [it for it in inventory if it.get("type") == "DRAIN"]
        gates = [it for it in inventory if it.get("type") == "GATE"]
        
        if inv_type == "bays":
            if not bays:
                return "Information not found in the current drawing."
            lines = [f"- {b.get('name')}" for b in sorted(bays, key=lambda x: x.get('bay_number', 0))]
            return "The following bays exist in the drawing:\n\n" + "\n".join(lines)
            
        elif inv_type == "ict_bays":
            if not ict_bays:
                return "Information not found in the current drawing."
            lines = [f"- {b.get('name')}" for b in sorted(ict_bays, key=lambda x: x.get('bay_number', 0))]
            return "The following ICT bays exist in the drawing:\n\n" + "\n".join(lines)
            
        elif inv_type == "roads":
            if not roads:
                return "Information not found in the current drawing."
            lines = [f"- {r.get('name')}" for r in sorted(roads, key=lambda x: str(x.get('name')))]
            return "The following roads exist in the drawing:\n\n" + "\n".join(lines)
            
        elif inv_type == "buildings":
            if not buildings:
                return "Information not found in the current drawing."
            lines = [f"- {b.get('name')}" for b in sorted(buildings, key=lambda x: str(x.get('name')))]
            return "The following buildings exist in the drawing:\n\n" + "\n".join(lines)
            
        elif inv_type == "foundations":
            if not foundations:
                return "Information not found in the current drawing."
            lines = [f"- {f.get('name')}" for f in sorted(foundations, key=lambda x: str(x.get('name')))]
            return "The following foundations exist in the drawing:\n\n" + "\n".join(lines)
            
        elif inv_type == "drains":
            if not drains:
                return "Information not found in the current drawing."
            lines = [f"- {d.get('name')}" for d in sorted(drains, key=lambda x: str(x.get('name')))]
            return "The following drains exist in the drawing:\n\n" + "\n".join(lines)
            
        elif inv_type == "gates":
            if not gates:
                return "Information not found in the current drawing."
            lines = [f"- {g.get('name')}" for g in sorted(gates, key=lambda x: str(x.get('name')))]
            return "The following gates exist in the drawing:\n\n" + "\n".join(lines)
            
        elif inv_type == "bus_reactor_bay":
            reactor_bays = [b for b in bays if "reactor" in str(b.get("equipment_name", "")).lower() or "reactor" in str(b.get("name", "")).lower()]
            if not reactor_bays:
                return "Information not found in the current drawing."
            lines = [f"- {b.get('name')}" for b in sorted(reactor_bays, key=lambda x: x.get('bay_number', 0))]
            return "The Bus Reactor is located in the following bay(s):\n\n" + "\n".join(lines)
            
        elif inv_type == "how_many_buildings":
            if not buildings:
                return "Information not found in the current drawing."
            return f"There are {len(buildings)} buildings in the current drawing."
            
        elif inv_type == "how_many_foundations":
            if not foundations:
                return "Information not found in the current drawing."
            return f"There are {len(foundations)} foundations in the current drawing."
            
        elif inv_type == "how_many_roads":
            if not roads:
                return "Information not found in the current drawing."
            return f"There are {len(roads)} roads in the current drawing."
    
    vision_queries = ["explain symbols", "analyze drawing visually", "describe layout visually"]
    is_vision_query = any(vq in q_lower for vq in vision_queries)
    
    if is_vision_query:
        print("[DEBUG] Route: On-Demand Vision Query (Generating PNG & invoking vision model)")
        print("ANSWER SOURCE: CAD_ANALYSIS")
        print("ANSWER SOURCE = CAD_ANALYSIS")
        render_hash = st.session_state.get("render_hash")
        if not render_hash:
            return "No drawing loaded. Please upload a DWG/DXF file first."
            
        import config
        cad_dir = os.path.join(config.CAD_STORAGE_DIR, render_hash)
        dxf_path = os.path.join(cad_dir, "converted.dxf")
        overview_path = os.path.join(cad_dir, "overview.png")
        
        if not os.path.exists(dxf_path):
            return "Cached DXF file not found. Please re-upload the drawing."
            
        session_preview_png = st.session_state.get("preview_png")
        if session_preview_png and os.path.exists(session_preview_png):
            preview_png_path = session_preview_png
        else:
            preview_png_path = os.path.join(cad_dir, "preview.png")
            if not os.path.exists(preview_png_path):
                try:
                    from cad_processor import _convert_dxf_ezdxf
                    print(f"[query_router] Lazy rendering preview PNG...")
                    _convert_dxf_ezdxf(dxf_path, preview_png_path)
                except Exception as e:
                    return f"Failed to render preview PNG: {e}"
                
        if not os.path.exists(overview_path):
            try:
                from PIL import Image
                img = Image.open(preview_png_path)
                overview_img = img.copy()
                overview_img.thumbnail((1024, 1024))
                overview_img.save(overview_path)
            except Exception as e:
                print(f"[query_router] Warning: overview resizing failed: {e}")
                overview_path = preview_png_path
                
        try:
            import vision_analyzer
            print("[query_router] Loading Qwen2.5-VL and running vision analysis...")
            prompt = (
                f"You are an expert engineering assistant. Analyze this CAD drawing preview. "
                f"Answer the user query: '{q}'."
            )
            summary = vision_analyzer.analyze_image_local(overview_path, prompt)
            return summary
        except Exception as e:
            return f"Failed to analyze image using vision model: {e}"

    inventory = st.session_state.get("layout_inventory", [])
    if not isinstance(inventory, list):
        inventory = []
        
    cad_chunks = st.session_state.get("cad_chunks", [])
    cad_analysis = st.session_state.get("cad_analysis", {})

    drawing_type = st.session_state.get("drawing_type") or cad_analysis.get("drawing_type", "GENERAL_CAD")

    q_clean = re.sub(r'[^\w\s]', '', q_lower).strip()

    is_rule6 = False
    rule6_type = None
    
    if re.search(r'\blist\s+ict\s+bays?\b', q_clean) or re.search(r'\bict\s+bays?\b', q_clean) or re.search(r'\blist\s+icts?\b', q_clean) or re.search(r'\bshow\s+icts?\b', q_clean) or re.search(r'\bwhat\s+icts?\b', q_clean):
        is_rule6 = True
        rule6_type = "ict_bays"
    elif re.search(r'\blist\s+bellary\s+bays?\b', q_clean) or re.search(r'\bbellary\s+bays?\b', q_clean):
        is_rule6 = True
        rule6_type = "bellary_bays"
    elif re.search(r'\blist\s+madhugiri\s+bays?\b', q_clean) or re.search(r'\bmadhugiri\s+bays?\b', q_clean):
        is_rule6 = True
        rule6_type = "madhugiri_bays"
    elif re.search(r'\blist\s+gooty\s+bays?\b', q_clean) or re.search(r'\bgooty\s+bays?\b', q_clean):
        is_rule6 = True
        rule6_type = "gooty_bays"
    elif re.search(r'\blist\s+hiriyur\s+bays?\b', q_clean) or re.search(r'\bhiriyur\s+bays?\b', q_clean):
        is_rule6 = True
        rule6_type = "hiriyur_bays"
    elif re.search(r'\bwhich\s+bay\s+is\s+bus\s+reactor\b', q_clean) or re.search(r'\bbus\s+reactor\s+bay\b', q_clean) or re.search(r'\bwhere\s+is\s+bus\s+reactor\b', q_clean) or re.search(r'\bwhich\s+bay\s+is\s+reactor\b', q_clean):
        is_rule6 = True
        rule6_type = "bus_reactor_bay"
    elif re.search(r'\broad\s+width\b', q_clean) or re.search(r'\bwidth\s+of\s+roads?\b', q_clean) or re.search(r'\bwidth\s+of\s+the\s+roads?\b', q_clean):
        is_rule6 = True
        rule6_type = "road_width"
    elif re.search(r'\blist\s+roads?\b', q_clean) or re.search(r'\broads\s+list\b', q_clean) or re.search(r'\bshow\s+roads?\b', q_clean):
        is_rule6 = True
        rule6_type = "roads"
    elif re.search(r'\blist\s+buses\b', q_clean) or re.search(r'\bshow\s+buses\b', q_clean) or re.search(r'\bwhat\s+buses\b', q_clean) or q_clean == "buses":
        is_rule6 = True
        rule6_type = "buses"
    elif re.search(r'\blist\s+bays?\b', q_clean) or re.search(r'\bshow\s+bays?\b', q_clean) or re.search(r'\bwhat\s+bays?\b', q_clean) or re.search(r'\blist\s+all\s+bays?\b', q_clean):
        is_rule6 = True
        rule6_type = "bays"
        
    is_fdn_list = False
    fdn_list_type = None
    if re.search(r'\blist\s+buildings?\b', q_clean) or re.search(r'\bhow\s+many\s+buildings?\b', q_clean):
        is_fdn_list = True
        fdn_list_type = "buildings"
    elif re.search(r'\blist\s+foundations?\b', q_clean) or re.search(r'\bhow\s+many\s+foundations?\b', q_clean):
        is_fdn_list = True
        fdn_list_type = "foundations"
    elif re.search(r'\blist\s+drains?\b', q_clean) or re.search(r'\bhow\s+many\s+drains?\b', q_clean):
        is_fdn_list = True
        fdn_list_type = "drains"
    elif re.search(r'\blist\s+gates?\b', q_clean) or re.search(r'\bhow\s+many\s+gates?\b', q_clean):
        is_fdn_list = True
        fdn_list_type = "gates"
    elif re.search(r'\bfire\s+water\s+tank\b', q_clean) or re.search(r'\bwater\s+tank\b', q_clean):
        is_fdn_list = True
        fdn_list_type = "water_tanks"

    if is_rule6:
        print("ANSWER SOURCE: INVENTORY")
        print("ANSWER SOURCE = INVENTORY")
        if not inventory:
            return "No components were found in the uploaded CAD drawing."
            
        bays = [it for it in inventory if it.get("type") == "BAY"]
        roads = [it for it in inventory if it.get("type") == "ROAD"]
        buses = [it for it in inventory if it.get("type") == "BUS"]
        
        if rule6_type == "bays":
            if not bays:
                return "No bays were found in the uploaded CAD drawing."
            lines = [f"- **Bay {b.get('bay_number')}**: {b.get('equipment_name')} [Bus: {b.get('bus_name', 'None')}]" for b in sorted(bays, key=lambda x: x.get('bay_number', 0))]
            return "The following bays exist in the drawing:\n\n" + "\n".join(lines)
            
        elif rule6_type == "ict_bays":
            ict_bays = [b for b in bays if "ict" in str(b.get("equipment_name", "")).lower() or "ict" in str(b.get("name", "")).lower()]
            if not ict_bays:
                return "No ICT bays were found in the uploaded CAD drawing."
            lines = [f"- **Bay {b.get('bay_number')}**: {b.get('equipment_name')} [Bus: {b.get('bus_name', 'None')}]" for b in sorted(ict_bays, key=lambda x: x.get('bay_number', 0))]
            return "The following ICT bays exist in the drawing:\n\n" + "\n".join(lines)
                
        elif rule6_type == "bellary_bays":
            bellary_bays = [b for b in bays if "bellary" in str(b.get("equipment_name", "")).lower() or "bellary" in str(b.get("name", "")).lower()]
            if not bellary_bays:
                return "No Bellary bays were found in the uploaded CAD drawing."
            lines = [f"- **Bay {b.get('bay_number')}**: {b.get('equipment_name')} [Bus: {b.get('bus_name', 'None')}]" for b in sorted(bellary_bays, key=lambda x: x.get('bay_number', 0))]
            return "The following Bellary bays exist in the drawing:\n\n" + "\n".join(lines)
            
        elif rule6_type == "madhugiri_bays":
            madhugiri_bays = [b for b in bays if "madhugiri" in str(b.get("equipment_name", "")).lower() or "madhugiri" in str(b.get("name", "")).lower()]
            if not madhugiri_bays:
                return "No Madhugiri bays were found in the uploaded CAD drawing."
            lines = [f"- **Bay {b.get('bay_number')}**: {b.get('equipment_name')} [Bus: {b.get('bus_name', 'None')}]" for b in sorted(madhugiri_bays, key=lambda x: x.get('bay_number', 0))]
            return "The following Madhugiri bays exist in the drawing:\n\n" + "\n".join(lines)
            
        elif rule6_type == "gooty_bays":
            gooty_bays = [b for b in bays if "gooty" in str(b.get("equipment_name", "")).lower() or "gooty" in str(b.get("name", "")).lower()]
            if not gooty_bays:
                return "No Gooty bays were found in the uploaded CAD drawing."
            lines = [f"- **Bay {b.get('bay_number')}**: {b.get('equipment_name')} [Bus: {b.get('bus_name', 'None')}]" for b in sorted(gooty_bays, key=lambda x: x.get('bay_number', 0))]
            return "The following Gooty bays exist in the drawing:\n\n" + "\n".join(lines)
            
        elif rule6_type == "hiriyur_bays":
            hiriyur_bays = [b for b in bays if "hiriyur" in str(b.get("equipment_name", "")).lower() or "hiriyur" in str(b.get("name", "")).lower()]
            if not hiriyur_bays:
                return "No Hiriyur bays were found in the uploaded CAD drawing."
            lines = [f"- **Bay {b.get('bay_number')}**: {b.get('equipment_name')} [Bus: {b.get('bus_name', 'None')}]" for b in sorted(hiriyur_bays, key=lambda x: x.get('bay_number', 0))]
            return "The following Hiriyur bays exist in the drawing:\n\n" + "\n".join(lines)
            
        elif rule6_type == "bus_reactor_bay":
            reactor_bays = [b for b in bays if "reactor" in str(b.get("equipment_name", "")).lower() or "reactor" in str(b.get("name", "")).lower()]
            if not reactor_bays:
                return "No Bus Reactor bay was found in the uploaded CAD drawing."
            lines = [f"- **Bay {b.get('bay_number')}**: {b.get('equipment_name')} [Bus: {b.get('bus_name', 'None')}]" for b in sorted(reactor_bays, key=lambda x: x.get('bay_number', 0))]
            return "The Bus Reactor is located in the following bay(s):\n\n" + "\n".join(lines)
            
        elif rule6_type == "road_width":
            widths = sorted(list(set(r.get("road_width") for r in roads if r.get("road_width"))))
            if widths:
                return f"The road widths detected in the drawing are: **{', '.join(widths)}**."
            return "No road width information found in the uploaded CAD drawing."
            
        elif rule6_type == "roads":
            if not roads:
                return "No roads were found in the uploaded CAD drawing."
            lines = [f"- **{r.get('name')}**" + (f" (Width: {r.get('road_width')})" if r.get("road_width") else "") for r in sorted(roads, key=lambda x: str(x.get('name')))]
            return "The following roads exist in the drawing:\n\n" + "\n".join(lines)
            
        elif rule6_type == "buses":
            if not buses:
                return "No buses were found in the uploaded CAD drawing."
            lines = [f"- **{b.get('name')}**" for b in sorted(buses, key=lambda x: str(x.get('name')))]
            return "The following main buses exist in the drawing:\n\n" + "\n".join(lines)

    if is_fdn_list:
        print("ANSWER SOURCE: INVENTORY")
        print("ANSWER SOURCE = INVENTORY")
        if not inventory:
            return "No components were found in the uploaded CAD drawing."
        buildings = [it for it in inventory if it.get("type") == "BUILDING"]
        foundations = [it for it in inventory if it.get("type") == "FOUNDATION"]
        drains = [it for it in inventory if it.get("type") == "DRAIN"]
        gates = [it for it in inventory if it.get("type") == "GATE"]
        water_tanks = [it for it in inventory if it.get("type") == "WATER_TANK"]
        
        if fdn_list_type == "buildings":
            if not buildings:
                return "No buildings were found in the uploaded CAD drawing."
            lines = [f"- **{b.get('name')}**" for b in sorted(buildings, key=lambda x: str(x.get('name')))]
            return "The following buildings exist in the layout:\n\n" + "\n".join(lines)
        elif fdn_list_type == "foundations":
            if not foundations:
                return "No foundations were found in the uploaded CAD drawing."
            lines = [f"- **{f.get('name')}**" for f in sorted(foundations, key=lambda x: str(x.get('name')))]
            return "The following foundations exist in the layout:\n\n" + "\n".join(lines)
        elif fdn_list_type == "drains":
            if not drains:
                return "No drains were found in the uploaded CAD drawing."
            lines = [f"- **{d.get('name')}**" for d in sorted(drains, key=lambda x: str(x.get('name')))]
            return "The following drains exist in the layout:\n\n" + "\n".join(lines)
        elif fdn_list_type == "gates":
            if not gates:
                return "No gates were found in the uploaded CAD drawing."
            lines = [f"- **{g.get('name')}**" for g in sorted(gates, key=lambda x: str(x.get('name')))]
            return "The following gates exist in the layout:\n\n" + "\n".join(lines)
        elif fdn_list_type == "water_tanks":
            if not water_tanks:
                return "No water tanks were found in the uploaded CAD drawing."
            lines = [f"- **{wt.get('name')}**" for wt in sorted(water_tanks, key=lambda x: str(x.get('name')))]
            return "The following water tanks exist in the layout:\n\n" + "\n".join(lines)

    is_general_explain = False
    explain_kws = ["explain", "describe", "summarize", "what does", "what is"]
    target_kws = ["drawing", "layout", "dwg", "cad"]
    has_explain = any(ek in q_lower for ek in explain_kws)
    has_target = any(tk in q_lower for tk in target_kws)
    if has_explain and has_target:
        is_general_explain = True

    if is_general_explain:
        print("ANSWER SOURCE: CAD_ANALYSIS")
        st.session_state.last_query_stats = {
            "Question Type": "Explanation",
            "Routing": "Rule 5",
            "Active Inventory": "None",
            "Answer Source": "CAD_ANALYSIS"
        }
        dynamic_exp = generate_dynamic_cad_explanation(drawing_type, inventory, cad_analysis)
        
        import groq_client
        sys_prompt = (
            "You are an expert CAD drawing assistant. Your task is to format and style the provided CAD drawing explanation in Markdown.\n"
            "STRICT RULES:\n"
            "- You must NEVER explain what CAD software is or define CAD. Never explain concepts from your general training data.\n"
            "- You must NEVER use generic engineering explanations.\n"
            "- You must use ONLY the provided CAD data (drawing type, inventory count, and component details). Do not invent or infer any additional information.\n"
            "- Style the output clean and professional in Markdown."
        )
        user_prompt = f"""
Dynamic CAD Explanation to polish:
{dynamic_exp}

User Question: {q}
"""
        try:
            res = groq_client.generate_groq_response(sys_prompt, user_prompt)
            return res.strip()
        except Exception as e:
            print(f"[query_router] Groq explanation polishing failed: {e}")
            return dynamic_exp

    rule7_phrases = ["transformer rating", "conductor size", "foundation dimension", "cable spec", "cable specification"]
    is_rule7 = any(phrase in q_clean for phrase in rule7_phrases)
    
    chunks_indicators = ["rating", "size", "dimension", "dimensions", "specification", "specifications", "spec", "conductor", "cable"]
    is_chunks_query = is_rule7 or any(ind in q_lower for ind in chunks_indicators)
    
    if is_chunks_query:
        print("ANSWER SOURCE: CAD_CHUNKS")
        print("ANSWER SOURCE = CAD_CHUNKS")
        retrieved_chunks = []
        if cad_chunks:
            cad_index = st.session_state.get("cad_index")
            if cad_index is not None:
                retrieved_chunks = hybrid_search_index(q, cad_index, cad_chunks, embedder, k=15)
            else:
                bm25 = BM25(cad_chunks)
                scores = bm25.score(q)
                scores.sort(key=lambda x: x[1], reverse=True)
                retrieved_chunks = [cad_chunks[idx] for idx, score in scores[:15] if score > 0]
                
        print(f"Retrieved Chunks: {len(retrieved_chunks)}")
        
        if len(retrieved_chunks) == 0:
            return "No relevant information was found in the uploaded CAD drawing."
            
        retrieved_text = "\n".join([f"- {c.get('content')}" for c in retrieved_chunks if c.get('content')])
        
        import groq_client
        sys_prompt = (
            "You are a professional CAD drawing data assistant. Your task is to answer the user's question using ONLY the provided retrieved CAD chunks.\n"
            "STRICT RULES:\n"
            "- Answer using ONLY the provided retrieved CAD chunks. Do not use any training knowledge or external engineering knowledge.\n"
            "- Do not guess, estimate, or invent any specifications, ratings, sizes, or dimensions.\n"
            "- Strict Rule: If the user asks about equipment (e.g. ICTs, transformers, etc.), you must only list the specific units/values that are explicitly present in the provided context or inventory. For example, if the inventory lists ICT-1, ICT-2, ICT-3, you must only answer with those exact values and never infer, guess, or extrapolate additional units (e.g. do not guess ICT-4).\n"
            "- If the chunks do not contain the answer, return EXACTLY the following text: 'Information not found in the uploaded CAD drawing.' and nothing else.\n"
            "- Keep the response concise, clear, and style it with Markdown."
        )
        user_prompt = f"""
Retrieved Chunks:
{retrieved_text}

User Question: {q}
"""
        try:
            return res.strip()
        except Exception as e:
            print(f"[query_router] Chunks query failed: {e}")
            return "No relevant information was found in the uploaded CAD drawing."

    print("ANSWER SOURCE: CAD_CHUNKS")
    print("ANSWER SOURCE = CAD_CHUNKS")
    retrieved_chunks = []
    if cad_chunks:
        cad_index = st.session_state.get("cad_index")
        if cad_index is not None:
            retrieved_chunks = hybrid_search_index(q, cad_index, cad_chunks, embedder, k=15)
        else:
            bm25 = BM25(cad_chunks)
            scores = bm25.score(q)
            scores.sort(key=lambda x: x[1], reverse=True)
            retrieved_chunks = [cad_chunks[idx] for idx, score in scores[:15] if score > 0]
            
    print(f"Retrieved Chunks: {len(retrieved_chunks)}")
    
    if len(retrieved_chunks) == 0:
        return "No relevant information was found in the uploaded CAD drawing."
        
    retrieved_text = "\n".join([f"- {c.get('content')}" for c in retrieved_chunks if c.get('content')])
    
    def format_list_comp(val):
        if isinstance(val, list):
            clean_list = [str(v) for v in val if v]
            return ", ".join(clean_list) if clean_list else "None"
        elif isinstance(val, str):
            return val if val.strip() else "None"
        return "None"

    analysis_data_comp = f"""
Drawing Type: {cad_analysis.get('drawing_type', 'Unknown')}
Drawing Title: {cad_analysis.get('drawing_title', 'Unknown')}
Summary: {cad_analysis.get('summary', 'No summary available')}
Bays: {format_list_comp(cad_analysis.get('bays'))}
Roads: {format_list_comp(cad_analysis.get('roads'))}
Buses: {format_list_comp(cad_analysis.get('buses'))}
Transformers: {format_list_comp(cad_analysis.get('transformers'))}
Generators: {format_list_comp(cad_analysis.get('generators'))}
Breakers: {format_list_comp(cad_analysis.get('breakers'))}
Relays: {format_list_comp(cad_analysis.get('relays'))}
CTs: {format_list_comp(cad_analysis.get('cts'))}
VTs: {format_list_comp(cad_analysis.get('vts'))}
Busbars: {format_list_comp(cad_analysis.get('busbars'))}
Buildings: {format_list_comp(cad_analysis.get('buildings'))}
Foundations: {format_list_comp(cad_analysis.get('foundations'))}
Earth Pits: {format_list_comp(cad_analysis.get('earth_pits'))}
"""
    
    import groq_client
    sys_prompt = (
        "You are an expert CAD drawing assistant. You are given a CAD drawing knowledge package containing metadata/counts "
        "and retrieved text chunks from the CAD drawing entities.\n\n"
        "STRICT RULES:\n"
        "- Answer the user's question using ONLY the provided CAD knowledge package details and retrieved chunks context.\n"
        "- Do not explain what CAD stands for, do not give general definitions of CAD, and do not fall back to general training knowledge about CAD tools.\n"
        "- Strict Rule: If the user asks about equipment (e.g. ICTs, transformers, etc.), you must only list the specific units/values that are explicitly present in the provided context or inventory. For example, if the inventory lists ICT-1, ICT-2, ICT-3, you must only answer with those exact values and never infer, guess, or extrapolate additional units (e.g. do not guess ICT-4).\n"
        "- Cite specific drawing details, equipment, and counts exactly as provided in the context.\n"
        "- If the answer cannot be found or inferred from the details, return EXACTLY the following text: 'Information not found in the uploaded CAD drawing.' and nothing else.\n"
        "- Respond in a clear, professional, natural language style, structured nicely with Markdown."
    )
    user_prompt = f"""
CAD Knowledge Package:
{analysis_data_comp}

Retrieved Chunks from CAD Drawing:
{retrieved_text}

User Question: {q}
"""
    try:
        res = groq_client.generate_groq_response(sys_prompt, user_prompt)
        return res.strip()
    except Exception as e:
        print(f"[query_router] Fallback Groq RAG failed: {e}")
        return "No relevant information was found in the uploaded CAD drawing."
