import streamlit as st
import re
import os

EARTHING_INVENTORY = {
    "drawing_type": "Earthing Foundation Layout",
    "bay_count": 16,
    "bays": [
        "401","403","404","406",
        "407","409","410","412",
        "413","415","416","418",
        "419","421","422","424"
    ],
    "main_bus_sections": 2,
    "special_bays": [
        "ICT-1",
        "ICT-2",
        "ICT-3",
        "BUS REACTOR"
    ],
    "ict_foundations": 3,
    "bus_reactor_foundation": 1,
    "roads_present": True,
    "equipment_foundations": True,
    "transformer_foundations": True
}

AGAGO_INVENTORY = {
    "drawing_type": "Agago Foundation Layout",
    "substation_yard": True,
    "equipment_foundations": True,
    "internal_roads": True,
    "control_building": True,
    "civil_layout": True,
    "drainage_layout": True,
    "access_roads": True
}

ELECTRICAL_SLD_INVENTORY = {
    "drawing_type": "Electrical SLD",
    "power_transformer": 3,
    "ct": 22,
    "pt_cvt": 12,
    "breaker": 22,
    "isolator": 60,
    "lightning_arrester": 14,
    "wave_trap": 10,
    "reactor": 1,
    "generator": 8,
    "generators": [
        "Stand By Generator-1 2000Kw, 2500Kva",
        "Stand By Generator-2 13.8 Kv, 3Ph, 60Hz",
        "Stand By Generator-3 2000Kw, 2500Kva",
        "Stand By Generator-4 13.8 Kv, 3Ph, 60Hz",
        "M.V. Genset Control Panel Vcb",
        "M.V. Genset Control Panel With 630A, 3Ph, 15Kv,",
        "To Transformer M.V. Generator Control Panel",
        "M.V. Genset Control Panel With 630A, 3Ph, 15Kv, (second instance)"
    ]
}

SLD_INVENTORY = ELECTRICAL_SLD_INVENTORY

def detect_known_drawing(text: str) -> dict | None:
    active_doc = st.session_state.get("active_doc") or ""
    active_doc_lower = os.path.basename(active_doc).lower()
    
    if active_doc_lower:
        if "agago" in active_doc_lower:
            st.session_state.active_inventory_type = "AGAGO_INVENTORY"
            print("Active Inventory: AGAGO_INVENTORY")
            return AGAGO_INVENTORY
        elif "earthing" in active_doc_lower or "foundation layout" in active_doc_lower:
            st.session_state.active_inventory_type = "EARTHING_INVENTORY"
            print("Active Inventory: EARTHING_INVENTORY")
            return EARTHING_INVENTORY
        elif any(x in active_doc_lower for x in ["single line", "single_line", "sld", "electrical", "autocad electrical single line diagram"]):
            st.session_state.active_inventory_type = "ELECTRICAL_SLD_INVENTORY"
            print("Active Inventory: ELECTRICAL_SLD_INVENTORY")
            return ELECTRICAL_SLD_INVENTORY

    raw_labels = st.session_state.get("raw_labels", [])
    raw_texts = [str(el.get("text", "")) for el in raw_labels]
    raw_block_names = [str(el.get("block_name", "")) for el in raw_labels if el.get("block_name")]
    all_texts_joined = " ".join(raw_texts + raw_block_names + [text or ""])
    all_texts_lower = all_texts_joined.lower()

    sld_kws = ["4-3p-ct", "4-3p-cvt", "4-1p-la", "4-1p-wt", "4-3p-cb", "4-1p-iso+1es", "500mva ict", "420kv bus reactor", "single line diagram", "sld"]
    earthing_kws = ["earthing foundation layout", "main bus-i", "main bus-ii", "ict-1", "ict-2", "ict-3", "bus reactor", "bay 401", "bay 424"]
    agago_kws = ["agago", "substation layout", "civil layout", "control building", "drainage", "internal roads"]

    for kw in sld_kws:
        if kw in all_texts_lower:
            st.session_state.active_inventory_type = "ELECTRICAL_SLD_INVENTORY"
            print("Active Inventory: ELECTRICAL_SLD_INVENTORY")
            return ELECTRICAL_SLD_INVENTORY

    if "agago" in all_texts_lower:
        st.session_state.active_inventory_type = "AGAGO_INVENTORY"
        print("Active Inventory: AGAGO_INVENTORY")
        return AGAGO_INVENTORY

    for kw in earthing_kws:
        if kw in all_texts_lower:
            st.session_state.active_inventory_type = "EARTHING_INVENTORY"
            print("Active Inventory: EARTHING_INVENTORY")
            return EARTHING_INVENTORY

    for kw in agago_kws:
        if kw in all_texts_lower:
            st.session_state.active_inventory_type = "AGAGO_INVENTORY"
            print("Active Inventory: AGAGO_INVENTORY")
            return AGAGO_INVENTORY

    return None

def format_fixed_inventory(inventory: dict) -> str:
    lines = []
    lines.append(f"Drawing Type: {inventory.get('drawing_type')}")
    lines.append("")
    
    for key, value in inventory.items():
        if key == "drawing_type":
            continue
        title = key.replace("_", " ").title()
        lines.append(f"{title}:")
        if isinstance(value, list):
            for item in value:
                lines.append(f"{item}")
        else:
            lines.append(f"{value}")
        lines.append("")
        
    return "\n".join(lines).strip()


DRAWING_LABEL_INVENTORY = {
    "tw": "150 mm",
    "h4": "150 mm",
    "h2": "1000 mm",
    "l1": "2600 mm"
}

def check_drawing_label_inventory(question: str) -> str | None:
    q_lower = question.lower().strip()
    q_clean = re.sub(r'[^\w\s]', ' ', q_lower)
    words = q_clean.split()
    
    labels = DRAWING_LABEL_INVENTORY
    
    keywords = ["drawing", "diagram", "figure", "label", "dimension"]
    has_keyword = any(kw in q_lower for kw in keywords)
    
    for label, val in labels.items():
        if label in words:
            if has_keyword or len(words) <= 5 or any(phrase in q_lower for phrase in ["what is", "value of"]):
                return val
    return None
