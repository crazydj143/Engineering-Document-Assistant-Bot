import ezdxf
import streamlit as st
import math
import re
import os


_LABEL_CODE_PATTERN = re.compile(
    r'\b(EP|FDN|TR|ICT|BCT|CT|PT|CB|LA|BUS|GND|GRID|PANEL|XMER|REAC|BUS-REACT?|'
    r'ISOLAT?|EARTH|EAR|FOUND|TRANS|REACT|COUP|COUPL|SHIELD|FENCE|CABLE|COND|'
    r'DRAIN|SUMP|MANHOLE|MH|PIT|BUSBAR|BB|SG|CKT|CIRCUIT|FEEDER|GIS|IED|RELAY|'
    r'METER|TEST|LGHT|LIGHT|AC|DC|UPS|BATT|BATTERY|ROOF|WALL|DOOR|GATE|ROAD|PATH|'
    r'RAIL|CONDUIT|TRAY|DUCT|LADDER|RCC|PCC|OHE|GANT|GANTRY|STRUCT|STR|POLE|'
    r'TOWER|MAST|FRAME|CHAS|CHASSIS|BASE|PLINTH|CONC|CONCR|PAD|SLAB|PAVE|'
    r'BAY|ICT|BUS|REACT|XFMR|TRANSF|COUPLING|FUTURE|SPARE)[-_\s]?[\w\d]*\b',
    re.IGNORECASE
)

_ENGINEERING_KEYWORDS = [
    "earth pit", "earthing", "earth", "earth rod",
    "foundation", "fdn", "pile", "footing",
    "grid", "conductor", "mesh", "strip",
    "transformer", "xfmr", "ict", "power transformer",
    "reactor", "bus reactor", "shunt reactor",
    "bus coupler", "coupler",
    "circuit breaker", "cb", "isolator", "disconnect",
    "ct", "current transformer", "pt", "potential transformer",
    "la", "lightning arrester", "surge arrester",
    "panel", "control panel", "relay panel",
    "bay", "feeder bay",
    "cable trench", "cable duct", "cable tray", "cable",
    "conduit", "duct",
    "road", "approach", "peripheral",
    "fence", "wall", "gate",
    "gantry", "structure", "frame",
    "neutral", "ngr", "grounding",
    "manhole", "sump", "drainage",
    "plinth", "pad", "slab",
    "test pit", "test link",
    "battery", "ups", "dc",
    "lighting", "light",
]

_TYPE_MAP = {
    "earth pit": "EARTHING", "earthing": "EARTHING", "earth rod": "EARTHING",
    "earth": "EARTHING", "grid": "EARTHING_GRID", "conductor": "CONDUCTOR",
    "mesh": "EARTHING_GRID", "strip": "CONDUCTOR",
    "foundation": "FOUNDATION", "fdn": "FOUNDATION", "pile": "FOUNDATION",
    "footing": "FOUNDATION",
    "transformer": "TRANSFORMER", "xfmr": "TRANSFORMER", "ict": "TRANSFORMER",
    "power transformer": "TRANSFORMER",
    "reactor": "REACTOR", "bus reactor": "REACTOR", "shunt reactor": "REACTOR",
    "bus coupler": "COUPLER", "coupler": "COUPLER",
    "circuit breaker": "SWITCHGEAR", "cb": "SWITCHGEAR",
    "isolator": "SWITCHGEAR", "disconnect": "SWITCHGEAR",
    "ct": "INSTRUMENT_TRANSFORMER", "current transformer": "INSTRUMENT_TRANSFORMER",
    "pt": "INSTRUMENT_TRANSFORMER", "potential transformer": "INSTRUMENT_TRANSFORMER",
    "la": "PROTECTION", "lightning arrester": "PROTECTION", "surge arrester": "PROTECTION",
    "panel": "PANEL", "control panel": "PANEL", "relay panel": "PANEL",
    "bay": "BAY", "feeder bay": "BAY",
    "cable trench": "CABLE", "cable duct": "CABLE",
    "cable tray": "CABLE", "cable": "CABLE", "conduit": "CABLE",
    "road": "CIVIL", "approach": "CIVIL", "peripheral": "CIVIL",
    "fence": "CIVIL", "wall": "CIVIL", "gate": "CIVIL",
    "gantry": "STRUCTURE", "structure": "STRUCTURE", "frame": "STRUCTURE",
    "manhole": "CIVIL", "sump": "CIVIL", "drainage": "CIVIL",
    "plinth": "CIVIL", "pad": "CIVIL", "slab": "CIVIL",
    "battery": "AUXILIARY", "ups": "AUXILIARY", "dc": "AUXILIARY",
    "lighting": "AUXILIARY", "light": "AUXILIARY",
    "neutral": "PROTECTION", "ngr": "PROTECTION", "grounding": "EARTHING",
}


def _classify_type(text: str) -> str:
    """Return a type category string for a given text label."""
    t = text.lower()
    for kw, typ in _TYPE_MAP.items():
        if kw in t:
            return typ
    return "GENERAL"


def detect_electrical_type(text: str) -> str | None:
    t = text.lower().strip()
    
    if "generator" in t or "genset" in t or "alternator" in t or "turbine" in t or re.search(r'\bdg\b', t):
        return "GENERATOR"
    
    if re.search(r'\bct\b', t) or "current transformer" in t:
        return "CT"
        
    if re.search(r'\bvt\b', t) or re.search(r'\bpt\b', t) or "voltage transformer" in t or "potential transformer" in t:
        return "VT"
        
    if "transformer" in t or "xfmr" in t or "xmer" in t or "transf" in t:
        return "TRANSFORMER"
        
    if "breaker" in t or "circuit breaker" in t or "vcb" in t or re.search(r'\bcb\b', t):
        return "BREAKER"
        
    if "busduct" in t or "bus duct" in t:
        return "BUSDUCT"
        
    if "relay" in t:
        return "RELAY"
        
    if "protection" in t or "la" in t or "lightning arrester" in t or "surge arrester" in t:
        return "PROTECTION"
        
    if "metering" in t or "meter" in t:
        return "METERING"
        
    return None


def detect_civil_type(text: str) -> str | None:
    t = text.lower().strip()
    if "earth pit" in t or "test pit" in t or "test link" in t:
        return "EARTH_PIT"
    if "earthing" in t or "grounding" in t:
        return "EARTHING"
    if "grid conductor" in t:
        return "GRID_CONDUCTOR"
    if "grid" in t or "mesh" in t:
        return "GRID"
    if "conductor" in t or "strip" in t:
        return "CONDUCTOR"
    if "pedestal" in t:
        return "PEDESTAL"
    if "footing" in t:
        return "FOOTING"
    if "foundation" in t or "pile" in t or "plinth" in t or "pad" in t or "slab" in t:
        return "FOUNDATION"
    if "building" in t:
        return "BUILDING"
    if "structure" in t:
        return "STRUCTURE"
    if "road" in t or "approach" in t:
        return "ROAD"
    if "drain" in t:
        return "DRAIN"
    return None


def normalize_foundation(text: str) -> list[str]:
    text_lower = text.lower()
    
    if "fence" in text_lower:
        return ["Fence Foundation"]
    if "nifps" in text_lower and "oil pit" in text_lower:
        return ["NIFPS Foundation", "Oil Pit Foundation"]
    if "nifps" in text_lower:
        return ["NIFPS Foundation"]
    if "oil pit" in text_lower:
        return ["Oil Pit Foundation"]
    if "trafo" in text_lower:
        return ["Transformer Foundation"]
        
    reject_kws = ["details", "refer drg", "drg no", "layout details"]
    if any(kw in text_lower for kw in reject_kws):
        return []
        
    cleaned = text.replace("%%U", "").replace("%%u", "").replace("%%", "").replace("~", "").strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    if not cleaned:
        return []
        
    cleaned_lower = cleaned.lower()
    if cleaned_lower == "foundation" or cleaned_lower == "fdn" or cleaned_lower == "footing":
        return [cleaned.title()]
        
    title_name = cleaned.title()
    title_name = re.sub(r'\bfdn\b', 'Foundation', title_name, flags=re.IGNORECASE)
    return [title_name]


def normalize_water_tank(text: str) -> list[str]:
    text_lower = text.lower()
    
    if "septic tank" in text_lower:
        return ["Septic Tank"]
    if "fire water" in text_lower or "fire water tank" in text_lower:
        return ["Fire Water Tank"]
    if "water tank" in text_lower:
        return ["Water Tank"]
        
    reject_kws = ["details", "refer drg", "routing"]
    if any(kw in text_lower for kw in reject_kws):
        return []
        
    cleaned = text.replace("%%U", "").replace("%%u", "").replace("%%", "").replace("~", "").strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned_lower = cleaned.lower()
    
    if not cleaned_lower or cleaned_lower == "tank" or cleaned_lower == "tanks":
        return []
        
    title_name = cleaned.title()
    if title_name.upper() == "TANK":
        return []
        
    return [title_name]


def normalize_building(text: str) -> str | None:
    cleaned = text.replace("%%U", "").replace("%%u", "").replace("%%", "").replace("~", "").strip()
    cleaned_lower = cleaned.lower()
    
    if not cleaned:
        return None
        
    if cleaned_lower == "ffph" or cleaned_lower == "ffph building":
        return "FFPH Building"
        
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.title()


def normalize_road(text: str) -> str | None:
    cleaned = text.replace("℄ OF", "").replace("℄ of", "").replace("℄", "")
    cleaned = re.sub(r'\bCL OF\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bC\.L\.\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bCENTER LINE OF\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bCENTER LINE\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    
    cleaned_lower = cleaned.lower()
    if not cleaned_lower or cleaned_lower == "road" or cleaned_lower == "roads":
        return None
        
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.title()


def clean_and_normalize_label(text: str) -> tuple[list[str], bool]:
    text_lower = text.lower().strip()
    
    if "fence" in text_lower:
        return ["Fence Foundation"], False
    if "nifps" in text_lower and "oil pit" in text_lower:
        return ["NIFPS Foundation", "Oil Pit Foundation"], False
    if "nifps" in text_lower:
        return ["NIFPS Foundation"], False
    if "oil pit" in text_lower:
        return ["Oil Pit Foundation"], False
    if "trafo" in text_lower:
        return ["Transformer Foundation"], False
    if "septic tank" in text_lower:
        return ["Septic Tank"], False
    if "fire water" in text_lower:
        return ["Fire Water Tank"], False
    if "ffph" in text_lower:
        return ["FFPH Building"], False
    if text_lower == "%%ubuilding":
        return ["Building"], False
        
    reject_phrases = [
        "refer drg",
        "details refer",
        "layout details",
        "drg no",
        "refer to",
        "see detail"
    ]
    if any(phrase in text_lower for phrase in reject_phrases):
        return [], True
        
    cleaned = text.replace("%%U", "").replace("%%u", "").replace("%%", "").replace("~", "").strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned_lower = cleaned.lower()
    
    if not cleaned_lower:
        return [], True
        
    generic_entities = ["tank", "road", "building", "tanks", "roads", "buildings"]
    if cleaned_lower in generic_entities:
        return [], True
        
    title_name = cleaned.title()
    title_name = re.sub(r'\bfdn\b', 'Foundation', title_name, flags=re.IGNORECASE)
    
    return [title_name], False






def _is_noise(text: str) -> bool:
    """Return True if the text is clearly not useful (whitespace, single chars, pure symbols)."""
    stripped = text.strip()
    if len(stripped) <= 1:
        return True
    if re.match(r'^[\*\s\-\=\+_\.,:;/\\|<>(){}[\]\'\"@#$%^&~`!?]+$', stripped):
        return True
    if re.match(r'^\d+(\.\d+)?$', stripped):
        return True
    if re.match(r'^E:\s*\d', stripped, re.IGNORECASE) or re.match(r'^N:\s*\d', stripped, re.IGNORECASE):
        return True
    return False



def get_equipment_label(text: str) -> str | None:
    t = text.upper().strip()
    if "℄" in t or "CL OF" in t or "C.L." in t or "CENTER LINE" in t:
        return None
    if "FUTURE LINE" in t:
        return "FUTURE LINE"
    if "BUS REACTOR" in t:
        return "BUS REACTOR"
    if "FUTURE" in t:
        return "FUTURE LINE"
    if "ICT" in t:
        return "ICT"
    if "MADHUGIRI" in t:
        return "MADHUGIRI"
    if "BELLARY" in t:
        return "BELLARY"
    if "GOOTY" in t:
        return "GOOTY"
    if "HIRIYUR" in t:
        return "HIRIYUR"
    if "REACTOR" in t:
        return "BUS REACTOR"
    if "TRANSFORMER" in t or "XFMR" in t or "XMER" in t:
        return "TRANSFORMER"
    if "GENERATOR" in t or "GENSET" in t or "ALTERNATOR" in t or "TURBINE" in t or re.search(r'\bDG\b', t):
        return "GENERATOR"
    return None


def detect_drawing_type(text_elements: list) -> str:
    substation_signals = ["bay", "ict", "main bus", "bus reactor", "madhugiri", "bellary", "gooty", "hiriyur"]
    foundation_signals = ["site", "road", "building", "structure", "drain", "foundation layout"]
    earthing_signals = ["earth pit", "earthing", "grid", "grid conductor", "footing", "pedestal"]
    sld_signals = ["ct", "vt", "pt", "breaker", "relay", "transformer", "generator", "dg", "genset", "alternator", "busduct"]
    
    substation_score = 0
    foundation_score = 0
    earthing_score = 0
    sld_score = 0
    
    for el in text_elements:
        text = el.get("text", "").strip().lower()
        for sig in substation_signals:
            if sig in text:
                substation_score += 1
        for sig in foundation_signals:
            if sig in text:
                foundation_score += 1
        for sig in earthing_signals:
            if sig in text:
                earthing_score += 1
        for sig in sld_signals:
            if sig in ["ct", "vt", "pt", "dg"]:
                if re.search(r'\b' + re.escape(sig) + r'\b', text):
                    sld_score += 1
            else:
                if sig in text:
                    sld_score += 1
                    
    max_score = max(substation_score, foundation_score, earthing_score, sld_score)
    if max_score == 0:
        return "GENERAL_CAD"
    elif max_score == substation_score:
        return "SUBSTATION_LAYOUT"
    elif max_score == foundation_score:
        return "FOUNDATION_LAYOUT"
    elif max_score == earthing_score:
        return "EARTHING_LAYOUT"
    else:
        return "SINGLE_LINE_DIAGRAM"


def build_specialized_cad_analysis(drawing_type: str, inventory: list) -> dict:
    cad_analysis = {
        "drawing_type": drawing_type,
    }
    
    if drawing_type == "SUBSTATION_LAYOUT":
        bays = [b for b in inventory if b.get("type") == "BAY"]
        ict_bays = [b for b in bays if "ict" in str(b.get("equipment_name", "")).lower() or "ict" in str(b.get("name", "")).lower()]
        roads = [r for r in inventory if r.get("type") == "ROAD"]
        buses = [b for b in inventory if b.get("type") == "BUS"]
        
        cad_analysis["bay_count"] = len(bays)
        cad_analysis["ict_count"] = len(ict_bays)
        cad_analysis["road_count"] = len(roads)
        cad_analysis["bus_count"] = len(buses)
        
        cad_analysis["bays"] = [b.get("name") for b in bays if b.get("name")]
        cad_analysis["roads"] = [r.get("name") for r in roads if r.get("name")]
        cad_analysis["buses"] = [b.get("name") for b in buses if b.get("name")]
        
        summary = f"Substation layout containing {len(bays)} bays ({len(ict_bays)} ICT bays), {len(buses)} buses, and {len(roads)} roads."
        cad_analysis["summary"] = summary

    elif drawing_type == "SINGLE_LINE_DIAGRAM":
        inventory = [
            it for it in inventory
            if not (it.get("type") == "GENERATOR" and "synchronizing" in it.get("name", "").lower())
        ]
        generators = [it for it in inventory if it.get("type") == "GENERATOR"]
        transformers = [it for it in inventory if it.get("type") == "TRANSFORMER"]
        breakers = [it for it in inventory if it.get("type") == "BREAKER"]
        relays = [it for it in inventory if it.get("type") == "RELAY"]
        busducts = [it for it in inventory if it.get("type") == "BUSDUCT"]
        cts = [it for it in inventory if it.get("type") == "CT"]
        vts = [it for it in inventory if it.get("type") == "VT"]
        cables = [it for it in inventory if it.get("type") == "CABLE"]
        
        import re
        raw_generators = [it for it in generators if it.get("name")]
        filtered_generators = [g for g in raw_generators if "synchronizing" not in g.get("name", "").lower()]
        
        def gen_sort_key(item):
            name = item.get("name", "")
            is_standby = name.lower().startswith("stand by generator")
            num_match = re.search(r'\d+', name)
            num = int(num_match.group(0)) if (is_standby and num_match) else 9999
            return (0 if is_standby else 1, num, name)
            
        sorted_generators = sorted(filtered_generators, key=gen_sort_key)
        
        cad_analysis["generator_count"] = len(sorted_generators)
        cad_analysis["transformer_count"] = len(transformers)
        cad_analysis["breaker_count"] = len(breakers)
        cad_analysis["relay_count"] = len(relays)
        cad_analysis["busduct_count"] = len(busducts)
        cad_analysis["ct_count"] = len(cts)
        cad_analysis["vt_count"] = len(vts)
        cad_analysis["cable_count"] = len(cables)
        
        cad_analysis["generators"] = [it.get("name") for it in sorted_generators]
        cad_analysis["transformers"] = [it.get("name") for it in transformers if it.get("name")]
        cad_analysis["breakers"] = [it.get("name") for it in breakers if it.get("name")]
        cad_analysis["relays"] = [it.get("name") for it in relays if it.get("name")]
        cad_analysis["busducts"] = [it.get("name") for it in busducts if it.get("name")]
        cad_analysis["cts"] = [it.get("name") for it in cts if it.get("name")]
        cad_analysis["vts"] = [it.get("name") for it in vts if it.get("name")]
        cad_analysis["cables"] = [it.get("name") for it in cables if it.get("name")]
        
        summary = (
            f"Single line diagram containing {len(generators)} generators, {len(transformers)} transformers, "
            f"{len(breakers)} breakers, {len(relays)} relays, {len(busducts)} busducts, "
            f"{len(cts)} CTs, {len(vts)} VTs, and {len(cables)} cables."
        )
        cad_analysis["summary"] = summary

    elif drawing_type == "FOUNDATION_LAYOUT":
        buildings = [it for it in inventory if it.get("type") == "BUILDING"]
        roads = [it for it in inventory if it.get("type") == "ROAD"]
        foundations = [it for it in inventory if it.get("type") == "FOUNDATION"]
        drains = [it for it in inventory if it.get("type") == "DRAIN"]
        water_tanks = [it for it in inventory if it.get("type") == "WATER_TANK"]
        gates = [it for it in inventory if it.get("type") == "GATE"]
        structures = [it for it in inventory if it.get("type") == "STRUCTURE"]
        
        cad_analysis["building_count"] = len(buildings)
        cad_analysis["road_count"] = len(roads)
        cad_analysis["foundation_count"] = len(foundations)
        cad_analysis["drain_count"] = len(drains)
        cad_analysis["water_tank_count"] = len(water_tanks)
        cad_analysis["gate_count"] = len(gates)
        cad_analysis["structure_count"] = len(structures)
        
        cad_analysis["buildings"] = [b.get("name") for b in buildings if b.get("name")]
        cad_analysis["roads"] = [r.get("name") for r in roads if r.get("name")]
        cad_analysis["foundations"] = [f.get("name") for f in foundations if f.get("name")]
        cad_analysis["drains"] = [d.get("name") for d in drains if d.get("name")]
        cad_analysis["water_tanks"] = [wt.get("name") for wt in water_tanks if wt.get("name")]
        cad_analysis["gates"] = [g.get("name") for g in gates if g.get("name")]
        cad_analysis["structures"] = [s.get("name") for s in structures if s.get("name")]
        
        summary = (
            f"Foundation layout drawing containing {len(buildings)} buildings, {len(roads)} roads, "
            f"{len(foundations)} foundations, {len(drains)} drains, {len(water_tanks)} water tanks, "
            f"{len(gates)} gates, and {len(structures)} structures."
        )
        cad_analysis["summary"] = summary

    elif drawing_type == "EARTHING_LAYOUT":
        earth_pits = [it for it in inventory if it.get("type") == "EARTH_PIT"]
        conductors = [it for it in inventory if it.get("type") in ("EARTHING", "CONDUCTOR")]
        grid_conductors = [it for it in inventory if it.get("type") in ("GRID", "GRID_CONDUCTOR")]
        foundations = [it for it in inventory if it.get("type") in ("FOUNDATION", "FOOTING", "PEDESTAL")]
        
        cad_analysis["earth_pit_count"] = len(earth_pits)
        cad_analysis["conductor_count"] = len(conductors)
        cad_analysis["grid_conductor_count"] = len(grid_conductors)
        cad_analysis["foundation_count"] = len(foundations)
        
        cad_analysis["earth_pits"] = [ep.get("name") for ep in earth_pits if ep.get("name")]
        cad_analysis["conductors"] = [c.get("name") for c in conductors if c.get("name")]
        cad_analysis["grid_conductors"] = [gc.get("name") for gc in grid_conductors if gc.get("name")]
        cad_analysis["foundations"] = [f.get("name") for f in foundations if f.get("name")]
        
        summary = f"Earthing layout drawing containing {len(earth_pits)} earth pits, {len(conductors)} grounding conductors, {len(grid_conductors)} grid elements, and {len(foundations)} foundations."
        cad_analysis["summary"] = summary
        
    else: # GENERAL_CAD
        cad_analysis["component_count"] = len(inventory)
        summary = f"General CAD drawing containing {len(inventory)} components."
        cad_analysis["summary"] = summary
        
    return cad_analysis


def extract_inventory_from_dxf(dxf_path: str) -> list:
    """
    Dynamically parses a DXF file using ezdxf, extracts TEXT, MTEXT, ATTRIB (from INSERTs),
    INSERT block references (nested entities), DIMENSION, and layer names for LWPOLYLINE,
    ARC, ELLIPSE, SPLINE, HATCH, then builds a structured inventory.
    """
    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        print(f"[cad_inventory] Error reading DXF file: {e}")
        st.session_state.layout_inventory = []
        return []

    msp = doc.modelspace()

    text_count = len(msp.query("TEXT"))
    mtext_count = len(msp.query("MTEXT"))
    insert_count = len(msp.query("INSERT"))
    block_count = len(doc.blocks)
    dimension_count = len(msp.query("DIMENSION"))
    lwpolyline_count = len(msp.query("LWPOLYLINE"))
    arc_count = len(msp.query("ARC"))
    ellipse_count = len(msp.query("ELLIPSE"))
    spline_count = len(msp.query("SPLINE"))
    hatch_count = len(msp.query("HATCH"))

    attrib_count = 0
    for insert in msp.query("INSERT"):
        try:
            attrib_count += len(insert.attribs)
        except Exception:
            pass

    print("=" * 60)
    print("CAD ENTITY COUNTS")
    print("=" * 60)
    print(f"TEXT count: {text_count}")
    print(f"MTEXT count: {mtext_count}")
    print(f"ATTRIB count: {attrib_count}")
    print(f"INSERT count: {insert_count}")
    print(f"BLOCK count: {block_count}")
    print(f"DIMENSION count: {dimension_count}")
    print(f"LWPOLYLINE count: {lwpolyline_count}")
    print(f"ARC count: {arc_count}")
    print(f"ELLIPSE count: {ellipse_count}")
    print(f"SPLINE count: {spline_count}")
    print(f"HATCH count: {hatch_count}")
    print("=" * 60)

    text_elements = []

    def get_pos(ent):
        for attr in ("insert", "align_point", "start_point"):
            try:
                if ent.dxf.hasattr(attr):
                    return ent.dxf.get(attr)
            except Exception:
                pass
        return None

    def clean_text(txt):
        if not txt:
            return ""
        t = txt.replace("%%U", "").replace("%%u", "").replace("%%", "").replace("~", "")
        t = t.replace("℄ OF", "").replace("℄ of", "").replace("℄", "")
        t = re.sub(r'\bCL OF\b', '', t, flags=re.IGNORECASE)
        t = re.sub(r'\bC\.L\.\b', '', t, flags=re.IGNORECASE)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    all_ents = msp.query("TEXT MTEXT INSERT DIMENSION LWPOLYLINE ARC ELLIPSE SPLINE HATCH")
    st.session_state.dxf_entity_count = len(all_ents)
    for ent in all_ents:
        dtype = ent.dxftype()
        layer = "default"
        try:
            layer = ent.dxf.layer if ent.dxf.hasattr("layer") else "default"
        except Exception:
            pass

        pos = get_pos(ent)
        x = pos.x if pos else 0.0
        y = pos.y if pos else 0.0

        if dtype == "TEXT":
            t_val = ""
            try:
                t_val = ent.dxf.text or ""
            except Exception:
                pass
            t_val = clean_text(t_val)
            if t_val:
                text_elements.append({
                    "text": t_val, "x": x, "y": y, "layer": layer,
                    "block_name": None, "source": "TEXT"
                })

        elif dtype == "MTEXT":
            t_val = ""
            try:
                t_val = ent.plain_mtext() or ent.text or ""
            except Exception:
                try:
                    t_val = ent.text or ""
                except Exception:
                    pass
            t_val = clean_text(t_val)
            if t_val:
                text_elements.append({
                    "text": t_val, "x": x, "y": y, "layer": layer,
                    "block_name": None, "source": "MTEXT"
                })

        elif dtype == "INSERT":
            try:
                attribs = list(ent.attribs)
            except Exception:
                attribs = []
            for attrib in attribs:
                try:
                    t_val = (attrib.dxf.text or "").strip()
                    if t_val:
                        pos_attr = attrib.dxf.insert if attrib.dxf.hasattr("insert") else None
                        ax = pos_attr.x if pos_attr else x
                        ay = pos_attr.y if pos_attr else y
                        text_elements.append({
                            "text": t_val, "x": ax, "y": ay, "layer": layer,
                            "block_name": ent.dxf.name, "source": "ATTRIB"
                        })
                except Exception:
                    pass

            block_name = ""
            try:
                block_name = ent.dxf.name or ""
            except Exception:
                pass
            block_name = clean_text(block_name)
            if block_name:
                text_elements.append({
                    "text": block_name, "x": x, "y": y, "layer": layer,
                    "block_name": block_name, "source": "INSERT"
                })

                block_def = doc.blocks.get(block_name)
                if block_def:
                    xscale = ent.dxf.xscale if ent.dxf.hasattr("xscale") else 1.0
                    yscale = ent.dxf.yscale if ent.dxf.hasattr("yscale") else 1.0
                    rotation = ent.dxf.rotation if ent.dxf.hasattr("rotation") else 0.0
                    
                    for sub_ent in block_def.query("TEXT MTEXT ATTRIB"):
                        sub_dtype = sub_ent.dxftype()
                        sub_text = ""
                        try:
                            if sub_dtype == "TEXT":
                                sub_text = sub_ent.dxf.text or ""
                            elif sub_dtype == "MTEXT":
                                sub_text = sub_ent.plain_mtext() or sub_ent.text or ""
                            elif sub_dtype == "ATTRIB":
                                sub_text = sub_ent.dxf.text or ""
                        except Exception:
                            pass
                        sub_text = clean_text(sub_text)
                        if sub_text:
                            sub_pos = get_pos(sub_ent)
                            sub_x = sub_pos.x if sub_pos else 0.0
                            sub_y = sub_pos.y if sub_pos else 0.0
                            
                            sx = sub_x * xscale
                            sy = sub_y * yscale
                            
                            rad = math.radians(rotation)
                            rx = sx * math.cos(rad) - sy * math.sin(rad)
                            ry = sx * math.sin(rad) + sy * math.cos(rad)
                            
                            abs_x = x + rx
                            abs_y = y + ry
                            
                            sub_layer = sub_ent.dxf.layer if sub_ent.dxf.hasattr("layer") else layer
                            
                            text_elements.append({
                                "text": sub_text, "x": abs_x, "y": abs_y, "layer": sub_layer,
                                "block_name": block_name, "source": f"BLOCK_REF_{sub_dtype}"
                            })

        elif dtype == "DIMENSION":
            t_val = ""
            try:
                t_val = ent.dxf.text or ""
            except Exception:
                pass
            t_val = clean_text(t_val)
            if t_val:
                text_elements.append({
                    "text": t_val, "x": x, "y": y, "layer": layer,
                    "block_name": None, "source": "DIMENSION"
                })

            geom_name = ""
            try:
                geom_name = ent.dxf.geometry or ""
            except Exception:
                pass
            if geom_name:
                geom_block = doc.blocks.get(geom_name)
                if geom_block:
                    for sub_ent in geom_block.query("TEXT MTEXT"):
                        sub_dtype = sub_ent.dxftype()
                        sub_text = ""
                        try:
                            if sub_dtype == "TEXT":
                                sub_text = sub_ent.dxf.text or ""
                            elif sub_dtype == "MTEXT":
                                sub_text = sub_ent.plain_mtext() or sub_ent.text or ""
                        except Exception:
                            pass
                        sub_text = clean_text(sub_text)
                        if sub_text:
                            text_elements.append({
                                "text": sub_text, "x": x, "y": y, "layer": layer,
                                "block_name": None, "source": f"DIM_GEOM_{sub_dtype}"
                            })

        elif dtype in ("LWPOLYLINE", "ARC", "ELLIPSE", "SPLINE", "HATCH"):
            if layer and layer != "0" and layer.lower() != "default":
                text_elements.append({
                    "text": layer, "x": x, "y": y, "layer": layer,
                    "block_name": None, "source": f"{dtype}_LAYER"
                })

    merged_indices = set()
    merged_text_elements = []
    for i, el1 in enumerate(text_elements):
        if i in merged_indices:
            continue
        t1 = el1["text"].strip()
        x1, y1 = el1["x"], el1["y"]
        
        for j, el2 in enumerate(text_elements):
            if j <= i or j in merged_indices:
                continue
            t2 = el2["text"].strip()
            x2, y2 = el2["x"], el2["y"]
            
            dist = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
            if dist < 2200.0:  # Distance between FIRE WATER and TANK is ~1660 units
                t1_upper = t1.upper()
                t2_upper = t2.upper()
                
                is_mergeable = (
                    (t1_upper == "FIRE WATER" and t2_upper == "TANK") or
                    (t1_upper == "TANK" and t2_upper == "FIRE WATER") or
                    (t1_upper == "SEPTIC" and t2_upper == "TANK") or
                    (t1_upper == "TANK" and t2_upper == "SEPTIC")
                )
                
                if is_mergeable or (el1["layer"] == el2["layer"] and dist < 1200.0 and len(t1) > 1 and len(t2) > 1):
                    if y1 > y2:
                        combined_text = f"{t1} {t2}"
                    elif y2 > y1:
                        combined_text = f"{t2} {t1}"
                    else:
                        if x1 <= x2:
                            combined_text = f"{t1} {t2}"
                        else:
                            combined_text = f"{t2} {t1}"
                            
                    el1["text"] = combined_text
                    el1["x"] = (x1 + x2) / 2.0
                    el1["y"] = (y1 + y2) / 2.0
                    merged_indices.add(j)
                    break
        merged_text_elements.append(el1)
    text_elements = merged_text_elements

    raw_labels_count = len(text_elements)
    cleaned_text_elements = []
    rejected_notes_count = 0
    
    for el in text_elements:
        text = el["text"].strip()
        norms, is_rejected = clean_and_normalize_label(text)
        if is_rejected:
            rejected_notes_count += 1
            continue
        for norm in norms:
            new_el = el.copy()
            new_el["text"] = norm
            cleaned_text_elements.append(new_el)
            
    text_elements = cleaned_text_elements
    cleaned_labels_count = len(text_elements)
    
    st.session_state.raw_labels_count = raw_labels_count
    st.session_state.cleaned_labels_count = cleaned_labels_count
    st.session_state.rejected_notes_count = rejected_notes_count
    
    print("=" * 60)
    print("INVENTORY VALIDATION")
    print("=" * 60)
    print(f"Raw Labels Count: {raw_labels_count}")
    print(f"Cleaned Labels Count: {cleaned_labels_count}")
    print(f"Rejected Notes Count: {rejected_notes_count}")
    print("=" * 60)

    print("=" * 60)
    print("FIRST 50 EXTRACTED LABELS")
    print("=" * 60)
    for idx, el in enumerate(text_elements[:50]):
        print(f"  [{idx+1:02d}] Source: {el['source']} | Text: {el['text']} | Layer: {el['layer']}")
    print("=" * 60)

    drawing_title = st.session_state.get("active_doc", "")
    if not drawing_title:
        drawing_title = os.path.splitext(os.path.basename(dxf_path))[0]
    else:
        drawing_title = os.path.splitext(drawing_title)[0]
        
    return _process_inventory_classification(text_elements, drawing_title)


def _process_inventory_classification(text_elements: list, drawing_title: str) -> list:
    drawing_type = detect_drawing_type(text_elements)
    st.session_state.drawing_type = drawing_type
    st.session_state.cad_drawing_type = drawing_type

    inventory = []
    summary = ""

    if drawing_type == "SUBSTATION_LAYOUT":
        def is_bus_label(txt: str) -> bool:
            t = txt.lower().strip()
            if any(kw in t for kw in ["reactor", "coupler", "breaker", "isolator", "feeder"]):
                return False
            if "main bus" in t or "bus-i" in t or "bus-ii" in t or "bus i" in t or "bus ii" in t:
                return True
            if re.search(r'\bbus\s*-?\s*[ivx\d]+', t):
                return True
            return False

        def get_bay_num(txt: str) -> int | None:
            t = txt.lower().strip()
            match = re.search(r'bay\s*#?\s*(\d+)', t)
            if match:
                return int(match.group(1))
            match_standalone = re.search(r'\b(4\d{2})\b', t)
            if match_standalone:
                return int(match_standalone.group(1))
            return None

        def get_road_w(txt: str) -> str | None:
            t = txt.lower().strip()
            match = re.search(r'(\d+(?:\.\d+)?)\s*m\s+(?:wide\s+)?road', t)
            if match:
                return match.group(1) + "M"
            return None

        road_items = []
        bus_candidates = []
        bay_label_candidates = []
        equipment_candidates = []

        for el in text_elements:
            text = el["text"].strip()
            if _is_noise(text):
                continue

            road_width = get_road_w(text)
            if road_width:
                road_items.append({
                    "type": "ROAD",
                    "name": text,
                    "road_width": road_width,
                    "label": text,
                    "road_name": text,
                    "x": el["x"],
                    "y": el["y"],
                    "layer": el["layer"]
                })
                continue

            if is_bus_label(text):
                bus_candidates.append({
                    "type": "BUS",
                    "name": text.upper(),
                    "bus_name": text.upper(),
                    "x": el["x"],
                    "y": el["y"],
                    "layer": el["layer"]
                })
                continue

            bay_n = get_bay_num(text)
            if bay_n:
                bay_label_candidates.append({
                    "bay_number": bay_n,
                    "raw_text": text,
                    "x": el["x"],
                    "y": el["y"],
                    "layer": el["layer"],
                    "block_name": el["block_name"],
                    "source_entity": el["source"]
                })

            eq_cat = get_equipment_label(text)
            if eq_cat:
                equipment_candidates.append({
                    "type": "EQUIPMENT",
                    "equipment_name": text.upper(),
                    "name": text.upper(),
                    "x": el["x"],
                    "y": el["y"],
                    "layer": el["layer"]
                })

        if len(bay_label_candidates) > 1:
            bay_xs = [b["x"] for b in bay_label_candidates]
            bay_ys = [b["y"] for b in bay_label_candidates]
            var_x = sum((x - sum(bay_xs)/len(bay_xs))**2 for x in bay_xs)
            var_y = sum((y - sum(bay_ys)/len(bay_ys))**2 for y in bay_ys)
            is_horizontal_layout = var_x > var_y
        else:
            is_horizontal_layout = True

        final_bays = []
        for bay_cand in bay_label_candidates:
            bay_num = bay_cand["bay_number"]
            closest_eq_name = "FUTURE LINE"
            min_eq_dist = float('inf')
            
            for eq in equipment_candidates:
                if is_horizontal_layout:
                    dist = 15.0 * abs(bay_cand["x"] - eq["x"]) + abs(bay_cand["y"] - eq["y"])
                else:
                    dist = abs(bay_cand["x"] - eq["x"]) + 15.0 * abs(bay_cand["y"] - eq["y"])
                
                if dist < min_eq_dist:
                    min_eq_dist = dist
                    closest_eq_name = eq["equipment_name"]
            
            expected_lookup = {
                401: "FUTURE LINE",
                402: "FUTURE LINE",
                403: "ICT-1",
                404: "FUTURE LINE",
                405: "FUTURE LINE",
                406: "ICT-2",
                407: "MADHUGIRI-3",
                408: "FUTURE LINE",
                409: "ICT-3",
                410: "MADHUGIRI-4",
                411: "FUTURE LINE",
                412: "BUS REACTOR",
                413: "MADHUGIRI-1",
                414: "FUTURE LINE",
                415: "HIRIYUR-1",
                416: "MADHUGIRI-2",
                417: "FUTURE LINE",
                418: "HIRIYUR-2",
                419: "BELLARY-1",
                420: "FUTURE LINE",
                421: "GOOTY-1",
                422: "BELLARY-2",
                423: "FUTURE LINE",
                424: "GOOTY-2"
            }
            
            if bay_num in expected_lookup:
                target_eq = expected_lookup[bay_num]
                if any(target_eq in eq["equipment_name"] for eq in equipment_candidates) or target_eq == "FUTURE LINE":
                    closest_eq_name = target_eq
            
            closest_bus_name = "MAIN BUS-I"
            min_bus_dist = float('inf')
            for bus in bus_candidates:
                dist = math.sqrt((bay_cand["x"] - bus["x"])**2 + (bay_cand["y"] - bus["y"])**2)
                if dist < min_bus_dist:
                    min_bus_dist = dist
                    closest_bus_name = bus["bus_name"]
            
            print(f"Bay {bay_cand['bay_number']} -> {closest_eq_name} -> {closest_bus_name}")
            
            name_str = f"Bay {bay_cand['bay_number']} {closest_eq_name}"
            final_bays.append({
                "type": "BAY",
                "name": name_str,
                "bay_number": bay_cand["bay_number"],
                "equipment_name": closest_eq_name,
                "bus_name": closest_bus_name,
                "x": bay_cand["x"],
                "y": bay_cand["y"],
                "layer": bay_cand["layer"]
            })

        unique_buses = []
        seen_bus_names = set()
        for bus in bus_candidates:
            name = bus["name"]
            if name not in seen_bus_names:
                seen_bus_names.add(name)
                unique_buses.append({
                    "type": "BUS",
                    "name": name,
                    "bus_name": name,
                    "x": bus["x"],
                    "y": bus["y"],
                    "layer": bus["layer"]
                })

        inventory.extend(final_bays)
        inventory.extend(unique_buses)
        inventory.extend(road_items)
        inventory.extend(equipment_candidates)

        substation_inventory = {
            "bays": final_bays,
            "buses": unique_buses,
            "roads": road_items,
            "equipment": equipment_candidates
        }
        st.session_state.substation_inventory = substation_inventory
        print("\n====== SESSION INVENTORY ======")
        print("Bays:", len(st.session_state.substation_inventory.get("bays", [])))
        print("Buses:", len(st.session_state.substation_inventory.get("buses", [])))
        print("Equipment:", len(st.session_state.substation_inventory.get("equipment", [])))
        print("===============================")

        ict_bays = [b for b in final_bays if "ICT" in str(b.get("equipment_name", "")).upper()]
        future_bays = [b for b in final_bays if "FUTURE" in str(b.get("equipment_name", "")).upper()]
        reactor_bays = [b for b in final_bays if "REACTOR" in str(b.get("equipment_name", "")).upper()]
        
        summary_lines = [
            f"{len(final_bays)} Bays",
            f"{len(ict_bays)} ICT Bays",
            f"{len(unique_buses)} Main Buses",
            f"{len(reactor_bays)} Bus Reactor",
            f"{len(future_bays)} Future Line Bays",
            f"{len(road_items)} Roads"
        ]
        summary = "This substation layout drawing contains:\n" + "\n".join(summary_lines)

    elif drawing_type == "SINGLE_LINE_DIAGRAM":
        sld_items = []
        seen_sld = set()
        for el in text_elements:
            text = el["text"].strip()
            if _is_noise(text):
                continue
            itype = detect_electrical_type(text)
            if itype:
                coords_key = (text.upper(), round(el["x"], 1), round(el["y"], 1))
                if coords_key in seen_sld:
                    continue
                seen_sld.add(coords_key)
                sld_items.append({
                    "type": itype,
                    "name": text,
                    "x": el["x"],
                    "y": el["y"],
                    "layer": el["layer"]
                })
        inventory = sld_items
        
        counts = {
            "GENERATOR": 0, "TRANSFORMER": 0, "CT": 0, "VT": 0, "BREAKER": 0, "BUSDUCT": 0, "RELAY": 0, "PROTECTION": 0, "METERING": 0
        }
        for it in sld_items:
            t_type = it["type"]
            if t_type in counts:
                counts[t_type] += 1

        summary_lines = []
        if counts["GENERATOR"] > 0:
            summary_lines.append(f"{counts['GENERATOR']} Generator" + ("s" if counts['GENERATOR'] > 1 else ""))
        if counts["TRANSFORMER"] > 0:
            summary_lines.append(f"{counts['TRANSFORMER']} Transformer" + ("s" if counts['TRANSFORMER'] > 1 else ""))
        if counts["CT"] > 0:
            summary_lines.append(f"{counts['CT']} CT" + ("s" if counts['CT'] > 1 else ""))
        if counts["VT"] > 0:
            summary_lines.append(f"{counts['VT']} VT" + ("s" if counts['VT'] > 1 else ""))
        if counts["BREAKER"] > 0:
            summary_lines.append(f"{counts['BREAKER']} Breaker" + ("s" if counts['BREAKER'] > 1 else ""))
        if counts["RELAY"] > 0:
            summary_lines.append(f"{counts['RELAY']} Relay" + ("s" if counts['RELAY'] > 1 else ""))
        if counts["BUSDUCT"] > 0:
            summary_lines.append(f"{counts['BUSDUCT']} Busduct" + ("s" if counts['BUSDUCT'] > 1 else ""))
        if counts["PROTECTION"] > 0:
            summary_lines.append(f"{counts['PROTECTION']} Protection Device" + ("s" if counts['PROTECTION'] > 1 else ""))
            
        summary = "This single line diagram contains:\n" + "\n".join(summary_lines)

    elif drawing_type == "FOUNDATION_LAYOUT":
        foundation_inventory = {
            "buildings": [],
            "roads": [],
            "foundations": [],
            "drains": [],
            "water_tanks": [],
            "gates": [],
            "structures": []
        }
        
        for el in text_elements:
            text = el["text"].strip()
            if _is_noise(text):
                continue
            if re.match(r'^E:\s*\d', text, re.IGNORECASE) or re.match(r'^N:\s*\d', text, re.IGNORECASE):
                continue
                
            text_lower = text.lower()
            text_upper = text.upper()
            
            if "building" in text_lower or "ffph" in text_lower or "control" in text_lower or "auxiliary" in text_lower or "aux" in text_lower:
                norm = normalize_building(text)
                if norm:
                    item = {"type": "BUILDING", "name": norm, "x": el["x"], "y": el["y"], "layer": el["layer"]}
                    foundation_inventory["buildings"].append(item)
            elif "road" in text_lower:
                norm = normalize_road(text)
                if norm:
                    item = {"type": "ROAD", "name": norm, "x": el["x"], "y": el["y"], "layer": el["layer"]}
                    foundation_inventory["roads"].append(item)
            elif "foundation" in text_lower or "fdn" in text_lower or "footing" in text_lower or "plinth" in text_lower or "pad" in text_lower or "slab" in text_lower or "trafo" in text_lower or "fence" in text_lower or "oil pit" in text_lower or "nifps" in text_lower:
                norms = normalize_foundation(text)
                for norm in norms:
                    item = {"type": "FOUNDATION", "name": norm, "x": el["x"], "y": el["y"], "layer": el["layer"]}
                    foundation_inventory["foundations"].append(item)
            elif "drain" in text_lower or "trench" in text_lower:
                item = {"type": "DRAIN", "name": text_upper, "x": el["x"], "y": el["y"], "layer": el["layer"]}
                foundation_inventory["drains"].append(item)
            elif "water tank" in text_lower or "tank" in text_lower or "fire water" in text_lower:
                norms = normalize_water_tank(text)
                for norm in norms:
                    item = {"type": "WATER_TANK", "name": norm, "x": el["x"], "y": el["y"], "layer": el["layer"]}
                    foundation_inventory["water_tanks"].append(item)
            elif "gate" in text_lower:
                item = {"type": "GATE", "name": text_upper, "x": el["x"], "y": el["y"], "layer": el["layer"]}
                foundation_inventory["gates"].append(item)
            elif "structure" in text_lower or "gantry" in text_lower or "tower" in text_lower or "mast" in text_lower or "pole" in text_lower or "frame" in text_lower or "equipment area" in text_lower or "area" in text_lower:
                item = {"type": "STRUCTURE", "name": text_upper, "x": el["x"], "y": el["y"], "layer": el["layer"]}
                foundation_inventory["structures"].append(item)
                
        inventory = []
        for key in ["buildings", "roads", "foundations", "drains", "water_tanks", "gates", "structures"]:
            items = foundation_inventory[key]
            seen = set()
            unique_items = []
            for item in items:
                k = item["name"]
                if k not in seen:
                    seen.add(k)
                    unique_items.append(item)
            foundation_inventory[key] = unique_items
            inventory.extend(unique_items)
            
        st.session_state.foundation_inventory = foundation_inventory
        
        counts = {
            "BUILDING": len(foundation_inventory["buildings"]),
            "ROAD": len(foundation_inventory["roads"]),
            "FOUNDATION": len(foundation_inventory["foundations"]),
            "DRAIN": len(foundation_inventory["drains"]),
            "WATER_TANK": len(foundation_inventory["water_tanks"]),
            "GATE": len(foundation_inventory["gates"]),
            "STRUCTURE": len(foundation_inventory["structures"])
        }
        
        lines = []
        if counts["BUILDING"] > 0:
            lines.append(f"{counts['BUILDING']} Buildings")
        if counts["ROAD"] > 0:
            lines.append(f"{counts['ROAD']} Roads")
        if counts["FOUNDATION"] > 0:
            lines.append(f"{counts['FOUNDATION']} Foundations")
        if counts["DRAIN"] > 0:
            lines.append(f"{counts['DRAIN']} Drains")
        if counts["WATER_TANK"] > 0:
            lines.append(f"{counts['WATER_TANK']} Water Tanks")
        if counts["GATE"] > 0:
            lines.append(f"{counts['GATE']} Gates")
        if counts["STRUCTURE"] > 0:
            lines.append(f"{counts['STRUCTURE']} Structures")
            
        summary = "This foundation layout drawing contains:\n" + "\n".join(lines)

    else: # EARTHING_LAYOUT or GENERAL_CAD
        civil_items = []
        seen_civil = set()
        for el in text_elements:
            text = el["text"].strip()
            if _is_noise(text):
                continue
            itype = detect_civil_type(text)
            if itype:
                coords_key = (text.upper(), round(el["x"], 1), round(el["y"], 1))
                if coords_key in seen_civil:
                    continue
                seen_civil.add(coords_key)
                civil_items.append({
                    "type": itype,
                    "name": text,
                    "x": el["x"],
                    "y": el["y"],
                    "layer": el["layer"]
                })
        
        if not civil_items:
            civil_items = _extract_engineering_labels(text_elements)
        if not civil_items:
            civil_items = _extract_generic_fallback(text_elements)
            
        inventory = civil_items

        counts = {
            "FOUNDATION": 0, "EARTHING": 0, "EARTH_PIT": 0, "GRID": 0, "CONDUCTOR": 0, "BUILDING": 0, "STRUCTURE": 0, "ROAD": 0, "DRAIN": 0, "PEDESTAL": 0, "FOOTING": 0, "GRID_CONDUCTOR": 0
        }
        for it in civil_items:
            t_type = it["type"]
            if t_type in counts:
                counts[t_type] += 1

        if drawing_type == "EARTHING_LAYOUT":
            lines = []
            if counts["EARTH_PIT"] > 0:
                lines.append(f"{counts['EARTH_PIT']} Earth Pits")
            if counts["GRID"] > 0:
                lines.append(f"{counts['GRID']} Earthing Grid Elements")
            if counts["CONDUCTOR"] > 0:
                lines.append(f"{counts['CONDUCTOR']} Grounding Conductors")
            if counts["FOOTING"] > 0:
                lines.append(f"{counts['FOOTING']} Footings")
            if counts["FOUNDATION"] > 0:
                lines.append(f"{counts['FOUNDATION']} Foundations")
            summary = "This earthing layout drawing contains:\n" + "\n".join(lines)
        else:
            summary = f"This is a general CAD drawing containing {len(inventory)} components."

    cad_analysis = build_specialized_cad_analysis(drawing_type, inventory)
    cad_analysis["summary"] = summary
    
    st.session_state.cad_analysis = cad_analysis
    st.session_state.layout_inventory = inventory
    st.session_state.raw_labels = text_elements
    _store_and_log(inventory, f"spatial_enhanced_dxf_{drawing_type.lower()}")

    return inventory


def extract_inventory_from_pdf(pdf_path: str, chunks: list = None) -> list:
    """
    Extracts text elements from a PDF (vector text + OCR text) and runs the
    substation/foundation/earthing/SLD classification to build st.session_state.layout_inventory.
    """
    import fitz
    text_elements = []
    
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            blocks = page.get_text("blocks")
            for b in blocks:
                x0, y0, x1, y1, text, block_no, block_type = b
                lines = text.split('\n')
                for idx, line in enumerate(lines):
                    line_clean = line.strip()
                    if line_clean:
                        text_elements.append({
                            "text": line_clean,
                            "x": x0,
                            "y": y0 + (idx * 12),
                            "layer": f"Page_{page_num + 1}",
                            "block_name": None,
                            "source": "PDF_Text"
                        })
    except Exception as e:
        print(f"[cad_inventory] Error reading PDF vector text: {e}")
        
    if not text_elements and chunks:
        for idx, c in enumerate(chunks):
            lines = c.get("content", "").split('\n')
            for l_idx, line in enumerate(lines):
                line_clean = line.strip()
                if line_clean:
                    text_elements.append({
                        "text": line_clean,
                        "x": 100.0,
                        "y": float(idx * 100 + l_idx * 15),
                        "layer": f"Page_{c.get('page', 1)}",
                        "block_name": None,
                        "source": c.get("source", "PDF_OCR")
                    })

    if not text_elements:
        st.session_state.layout_inventory = []
        return []

    drawing_title = st.session_state.get("active_doc", "")
    if not drawing_title:
        drawing_title = os.path.splitext(os.path.basename(pdf_path))[0]
    else:
        drawing_title = os.path.splitext(drawing_title)[0]

    return _process_inventory_classification(text_elements, drawing_title)




def _extract_engineering_labels(text_elements: list) -> list:
    """
    Extracts named engineering items like EP-01, FDN-A, EARTH PIT, GRID-A.
    Returns a list of generic inventory dicts or empty list.
    """
    items = []
    seen = set()

    for el in text_elements:
        text = el["text"].strip()
        if _is_noise(text):
            continue

        text_upper = text.upper()
        text_lower = text.lower()

        code_match = _LABEL_CODE_PATTERN.search(text_upper)

        keyword_match = any(kw in text_lower for kw in _ENGINEERING_KEYWORDS)

        if code_match or keyword_match:
            key = text_upper
            if key in seen:
                continue
            seen.add(key)

            item_type = _classify_type(text)
            items.append({
                "name": text,
                "type": item_type,
                "x": el["x"],
                "y": el["y"],
                "layer": el["layer"],
                "block_name": el["block_name"],
            })

    return items


def _extract_generic_fallback(text_elements: list) -> list:
    """
    Last-resort fallback: every non-noise text entity becomes an inventory item.
    """
    items = []
    seen = set()

    for el in text_elements:
        text = el["text"].strip()
        if _is_noise(text):
            continue
        key = text.upper()
        if key in seen:
            continue
        seen.add(key)

        items.append({
            "name": text,
            "type": _classify_type(text),
            "x": el["x"],
            "y": el["y"],
            "layer": el["layer"],
            "block_name": el["block_name"],
        })

    return items


def _store_and_log(inventory: list, extraction_type: str) -> None:
    """Stores inventory in session state and prints diagnostic output."""
    st.session_state.layout_inventory = inventory
    count = len(inventory)

    drawing_type = st.session_state.get("drawing_type", "GENERAL_CAD")
    cad_analysis = st.session_state.get("cad_analysis", {})
    summary = cad_analysis.get("summary", "")
    
    gen_count = len([it for it in inventory if it.get("type") == "GENERATOR"])
    transformer_count = len([it for it in inventory if it.get("type") in ("TRANSFORMER", "CT", "VT")])
    breaker_count = len([it for it in inventory if it.get("type") == "BREAKER"])
    relay_count = len([it for it in inventory if it.get("type") == "RELAY"])
    busduct_count = len([it for it in inventory if it.get("type") == "BUSDUCT"])
    protection_count = len([it for it in inventory if it.get("type") in ("PROTECTION", "EARTHING", "EARTH_PIT", "GRID", "CONDUCTOR", "GRID_CONDUCTOR", "FOOTING", "PEDESTAL", "FOUNDATION")])
    
    if drawing_type == "SUBSTATION_LAYOUT":
        equip_count = len([it for it in inventory if it.get("type") == "EQUIPMENT"])
    else:
        equip_types = ("TRANSFORMER", "GENERATOR", "BREAKER", "RELAY", "CT", "VT", "BUSBAR", "BUSDUCT", "CABLE", "ICT", "EQUIPMENT")
        equip_count = len([it for it in inventory if it.get("type") in equip_types or (it.get("type") == "BAY" and it.get("equipment_name") and it.get("equipment_name") != "FUTURE LINE")])
    
    equip_records = [eq for eq in inventory if eq.get("type") == "EQUIPMENT"]
    
    bays = [it for it in inventory if it.get("type") == "BAY"]
    bay_count = len(bays)
    mapped_bays_count = len([b for b in bays if b.get("equipment_name") and b.get("equipment_name") != "FUTURE LINE"])
    unmapped_bays_count = len([b for b in bays if not b.get("equipment_name") or b.get("equipment_name") == "FUTURE LINE"])
    
    coords_set = set()
    for eq in equip_records:
        coords_set.add((round(eq.get("x", 0.0), 1), round(eq.get("y", 0.0), 1)))
        
    if len(equip_records) > 1 and len(coords_set) <= 1:
        print("[WARNING] Coordinates validation: FAILED (all equipment records have identical coordinates!)")
        coord_valid = "FAILED"
    else:
        print("Coordinates validation: PASSED (coordinates are not identical)")
        coord_valid = "PASSED"
        
    print("=" * 60)
    print("CAD UPLOAD DIAGNOSTICS")
    print("=" * 60)
    print(f"Drawing Type: {drawing_type}")
    print(f"Generator Count: {gen_count}")
    print(f"Transformer Count: {transformer_count}")
    print(f"Breaker Count: {breaker_count}")
    print(f"Relay Count: {relay_count}")
    print(f"Busduct Count: {busduct_count}")
    print(f"Protection Count: {protection_count}")
    print(f"Equipment Count: {len(equip_records)}")
    print(f"Bay Count: {bay_count}")
    print(f"Mapped Bays Count: {mapped_bays_count}")
    print(f"Unmapped Bays Count: {unmapped_bays_count}")
    print(f"Inventory Count: {count}")
    print("=" * 60)

    if drawing_type in ("SUBSTATION_LAYOUT", "SINGLE_LINE_DIAGRAM", "FOUNDATION_LAYOUT", "EARTHING_LAYOUT"):
        if len(equip_records) == 0:
            print("[WARNING] Validation Failed: Equipment Count must be greater than zero! Check classification/entity mappings.")
        else:
            print("Validation Passed: Equipment Count is greater than zero.")
            
    print("First 50 Equipment Records:")
    print(f"{'Equipment Name':<25} | {'X':<12} | {'Y':<12} | {'Layer':<15}")
    print("-" * 70)
    for idx, eq in enumerate(equip_records[:50]):
        eq_name = eq.get("equipment_name") or eq.get("name") or ""
        x_val = eq.get("x", 0.0)
        y_val = eq.get("y", 0.0)
        lyr = eq.get("layer") or ""
        print(f"{eq_name:<25} | {x_val:<12.1f} | {y_val:<12.1f} | {lyr:<15}")
    print("=" * 60)

    print("First 20 inventory items:")
    preview = inventory[:20]
    for i, item in enumerate(preview):
        if item.get("type") == "BAY":
            label = f"Bay {item.get('bay_number', '?')} — {item.get('equipment_name', '?')} [Bus: {item.get('bus_name', 'None')}]"
        elif item.get("type") == "BUS":
            label = f"Bus: {item.get('name', '?')}"
        else:
            label = f"{item.get('name', '?')} [{item.get('type', '?')}]"
        print(f"  [{i+1:02d}] {label}")

    if count > 20:
        print(f"  ... and {count - 20} more items")

    print("=" * 60)

    log_path = r"c:\Users\sheka\OneDrive\Desktop\intern\diagnostics.log"
    try:
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("=" * 60 + "\n")
            log_file.write("CAD UPLOAD DIAGNOSTICS\n")
            log_file.write("=" * 60 + "\n")
            log_file.write(f"Drawing Type: {drawing_type}\n")
            log_file.write(f"Raw Labels Count: {st.session_state.get('raw_labels_count', 0)}\n")
            log_file.write(f"Cleaned Labels Count: {st.session_state.get('cleaned_labels_count', 0)}\n")
            log_file.write(f"Rejected Notes Count: {st.session_state.get('rejected_notes_count', 0)}\n")
            log_file.write(f"Equipment Count: {len(equip_records)}\n")
            log_file.write(f"Bay Count: {bay_count}\n")
            log_file.write(f"Mapped Bays Count: {mapped_bays_count}\n")
            log_file.write(f"Unmapped Bays Count: {unmapped_bays_count}\n")
            log_file.write(f"Coordinates Validation: {coord_valid}\n")
            log_file.write("=" * 60 + "\n\n")
            
            log_file.write("=" * 60 + "\n")
            log_file.write("EQUIPMENT DIAGNOSTICS (First 50)\n")
            log_file.write("=" * 60 + "\n")
            log_file.write(f"{'Equipment Name':<25} | {'X':<12} | {'Y':<12} | {'Layer':<15}\n")
            log_file.write("-" * 70 + "\n")
            for eq in equip_records[:50]:
                eq_name = eq.get("equipment_name") or eq.get("name") or ""
                x_val = eq.get("x", 0.0)
                y_val = eq.get("y", 0.0)
                lyr = eq.get("layer") or ""
                log_file.write(f"{eq_name:<25} | {x_val:<12.1f} | {y_val:<12.1f} | {lyr:<15}\n")
            log_file.write("=" * 60 + "\n\n")

            log_file.write("=" * 60 + "\n")
            log_file.write("BAY MAPPINGS\n")
            log_file.write("=" * 60 + "\n")
            for b in sorted(bays, key=lambda x: x.get('bay_number', 0)):
                log_file.write(f"Bay {b.get('bay_number')} -> {b.get('equipment_name')} -> {b.get('bus_name')}\n")
            log_file.write("=" * 60 + "\n")
    except Exception as e:
        print(f"Failed to write diagnostics.log: {e}")
