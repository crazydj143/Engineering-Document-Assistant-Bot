import streamlit as st
import re
import os
import io
import csv
from datetime import datetime
import pandas as pd
import fitz

def update_boq_in_session_state():
    """
    Computes the BOQ from st.session_state.layout_inventory, st.session_state.symbol_inventory,
    and st.session_state.fixed_inventory, and stores it in st.session_state.boq.
    """
    layout_inv = st.session_state.get("layout_inventory", [])
    symbol_inv = st.session_state.get("symbol_inventory")
    fixed_inv = st.session_state.get("fixed_inventory")

    layout_counts = {}
    fixed_counts = {}
    symbol_counts = {}

    category_map = {}
    unit_map = {}

    def normalize_item(raw_name):
        name_lower = raw_name.lower().strip()
        item_name = raw_name.strip()
        category = "General"
        unit = "Nos"

        if "transformer" in name_lower or "xmer" in name_lower or "xfmr" in name_lower:
            item_name = "Power Transformer"
            category = "Electrical"
        elif "circuit breaker" in name_lower or name_lower == "cb" or name_lower == "breaker" or "vcb" in name_lower:
            item_name = "Circuit Breaker"
            category = "Electrical"
        elif "current transformer" in name_lower or name_lower == "ct" or "current xfmr" in name_lower:
            item_name = "Current Transformer"
            category = "Electrical"
        elif "voltage transformer" in name_lower or name_lower in ("vt", "pt", "cvt") or "potential transformer" in name_lower or "voltage xfmr" in name_lower:
            item_name = "Voltage Transformer"
            category = "Electrical"
        elif "generator" in name_lower or "genset" in name_lower or "dg" in name_lower or "alternator" in name_lower:
            item_name = "Generator"
            category = "Electrical"
        elif "busbar" in name_lower or "bus bar" in name_lower or name_lower in ("bb", "bus"):
            item_name = "Busbar"
            category = "Electrical"
        elif "isolator" in name_lower or "disconnect" in name_lower:
            item_name = "Isolator"
            category = "Electrical"
        elif "lightning arrester" in name_lower or name_lower == "la" or "surge arrester" in name_lower:
            item_name = "Lightning Arrester"
            category = "Electrical"
        elif "wave trap" in name_lower or name_lower == "wt":
            item_name = "Wave Trap"
            category = "Electrical"
        elif "reactor" in name_lower:
            item_name = "Bus Reactor"
            category = "Electrical"
        elif "bay" in name_lower:
            item_name = "Feeder Bay"
            category = "Electrical"
        elif "earthing" in name_lower or "earth pit" in name_lower or "grounding" in name_lower or "earth rod" in name_lower:
            item_name = "Earthing Component"
            category = "Electrical"

        elif "foundation" in name_lower or "fdn" in name_lower or "footing" in name_lower or "plinth" in name_lower:
            item_name = "Foundation"
            category = "Civil"
        elif "road" in name_lower:
            item_name = "Road"
            category = "Civil"
        elif "building" in name_lower or "control room" in name_lower:
            item_name = "Building"
            category = "Civil"
        elif "drain" in name_lower or "drainage" in name_lower:
            item_name = "Drain"
            category = "Civil"
        elif "water tank" in name_lower or "tank" in name_lower:
            item_name = "Water Tank"
            category = "Civil"
        elif "fence" in name_lower or "wall" in name_lower or "gate" in name_lower:
            item_name = "Fencing/Gate"
            category = "Civil"

        elif "gantry" in name_lower or "tower" in name_lower or "mast" in name_lower or "structure" in name_lower or "frame" in name_lower:
            item_name = "Gantry Structure"
            category = "Structural"

        elif any(k in name_lower for k in ["pump", "valve", "fan", "hvac", "chiller", "compressor", "engine", "turbine"]):
            item_name = raw_name.title()
            category = "Mechanical"
        
        else:
            if len(item_name) <= 3:
                item_name = item_name.upper()
            else:
                item_name = item_name.title()

        return item_name, category, unit

    if isinstance(layout_inv, list):
        for item in layout_inv:
            name = item.get("name") or item.get("equipment_name") or item.get("label")
            if name:
                norm_name, cat, unit = normalize_item(name)
                layout_counts[norm_name] = layout_counts.get(norm_name, 0) + 1
                category_map[norm_name] = cat
                unit_map[norm_name] = unit

    if fixed_inv:
        for eq_key, val in fixed_inv.items():
            if isinstance(val, (int, float)) and val > 0 and eq_key not in ("bay_count", "main_bus_sections", "ict_foundations", "bus_reactor_foundation"):
                raw_name = eq_key.replace("_", " ").title()
                norm_name, cat, unit = normalize_item(raw_name)
                fixed_counts[norm_name] = fixed_counts.get(norm_name, 0) + val
                category_map[norm_name] = cat
                unit_map[norm_name] = unit
            elif eq_key == "equipment_inventory" and isinstance(val, dict):
                for sub_key, sub_val in val.items():
                    if isinstance(sub_val, (int, float)) and sub_val > 0:
                        raw_name = sub_key.replace("_", " ").title()
                        norm_name, cat, unit = normalize_item(raw_name)
                        fixed_counts[norm_name] = fixed_counts.get(norm_name, 0) + sub_val
                        category_map[norm_name] = cat
                        unit_map[norm_name] = unit
        
        if fixed_inv.get("ict_foundations"):
            norm_name, cat, unit = normalize_item("Transformer Foundation")
            fixed_counts[norm_name] = fixed_counts.get(norm_name, 0) + fixed_inv["ict_foundations"]
            category_map[norm_name] = cat
            unit_map[norm_name] = unit
        if fixed_inv.get("bus_reactor_foundation"):
            norm_name, cat, unit = normalize_item("Reactor Foundation")
            fixed_counts[norm_name] = fixed_counts.get(norm_name, 0) + fixed_inv["bus_reactor_foundation"]
            category_map[norm_name] = cat
            unit_map[norm_name] = unit

    if symbol_inv and isinstance(symbol_inv, dict):
        for sym_name, count in symbol_inv.items():
            if isinstance(count, (int, float)) and count > 0:
                raw_name = sym_name.replace("_", " ").title()
                norm_name, cat, unit = normalize_item(raw_name)
                symbol_counts[norm_name] = symbol_counts.get(norm_name, 0) + count
                category_map[norm_name] = cat
                unit_map[norm_name] = unit

    all_items = set(list(layout_counts.keys()) + list(fixed_counts.keys()) + list(symbol_counts.keys()))
    boq_list = []

    for item in all_items:
        l_qty = layout_counts.get(item, 0)
        f_qty = fixed_counts.get(item, 0)
        s_qty = symbol_counts.get(item, 0)

        combined_qty = max(l_qty, f_qty)
        if combined_qty == 0:
            combined_qty = s_qty
        else:
            combined_qty = max(combined_qty, s_qty)

        if combined_qty > 0:
            boq_list.append({
                "category": category_map.get(item, "General"),
                "item": item,
                "quantity": int(combined_qty),
                "unit": unit_map.get(item, "Nos")
            })

    boq_list.sort(key=lambda x: (x["category"], x["item"]))
    st.session_state.boq = boq_list


def handle_boq_chat_query(query: str) -> dict | None:
    """
    Routes and responds to BOQ questions. Returns None if query does not match BOQ keywords.
    """
    q_clean = re.sub(r'[^\w\s]', ' ', query.lower()).strip()
    words = q_clean.split()
    
    is_boq_q = any(kw in q_clean for kw in ["boq", "bill of quantities", "bill of quantity"])
    is_list_quantities = "list quantities" in q_clean or "list quantity" in q_clean or ("list" in words and "quantities" in words)
    is_total_electrical = "total electrical" in q_clean or ("total" in words and "electrical" in words)
    is_total_foundations = "total foundation" in q_clean or "total foundations" in q_clean or ("total" in words and ("foundation" in words or "foundations" in words))
    is_total_generators = "total generator" in q_clean or "total generators" in q_clean or ("total" in words and ("generator" in words or "generators" in words))

    if not (is_boq_q or is_list_quantities or is_total_electrical or is_total_foundations or is_total_generators):
        return None

    if not st.session_state.get("active_doc"):
        return {
            "content": "⚠️ No document or drawing has been uploaded. Please upload a DWG, DXF, or PDF engineering drawing to generate a BOQ.",
            "accuracy": 100.0
        }

    update_boq_in_session_state()
    boq = st.session_state.get("boq", [])

    if not boq:
        return {
            "content": f"📋 **Bill of Quantities (BOQ)**\n\nNo components were extracted from `{st.session_state.active_doc}`. Therefore, a BOQ cannot be generated.",
            "accuracy": 100.0
        }

    if is_total_generators:
        generators = [b for b in boq if b["item"].lower() == "generator"]
        total_qty = sum(item["quantity"] for item in generators)
        if total_qty > 0:
            content = f"📊 **Generator Count**\n\nThe total number of generators detected in `{st.session_state.active_doc}` is **{total_qty} Nos**.\n"
            for item in generators:
                content += f"\n- **{item['item']}**: {item['quantity']} {item['unit']} ({item['category']})"
        else:
            content = f"📊 **Generator Count**\n\nNo generators were detected in the drawing `{st.session_state.active_doc}`."
        return {"content": content, "accuracy": 95.0}

    if is_total_foundations:
        foundations = [b for b in boq if "foundation" in b["item"].lower() or b["item"].lower() == "foundation"]
        total_qty = sum(item["quantity"] for item in foundations)
        if total_qty > 0:
            content = f"📊 **Foundation Count**\n\nThe total number of foundations detected in `{st.session_state.active_doc}` is **{total_qty} Nos**.\n"
            for item in foundations:
                content += f"\n- **{item['item']}**: {item['quantity']} {item['unit']} ({item['category']})"
        else:
            content = f"📊 **Foundation Count**\n\nNo foundations were detected in the drawing `{st.session_state.active_doc}`."
        return {"content": content, "accuracy": 95.0}

    if is_total_electrical:
        electrical = [b for b in boq if b["category"].lower() == "electrical"]
        total_qty = sum(item["quantity"] for item in electrical)
        if total_qty > 0:
            content = f"⚡ **Electrical Equipment Inventory**\n\nThe total quantity of electrical equipment detected in `{st.session_state.active_doc}` is **{total_qty} Nos**.\n\nHere is the breakdown:"
            for item in electrical:
                content += f"\n- **{item['item']}**: {item['quantity']} {item['unit']}"
        else:
            content = f"⚡ **Electrical Equipment Inventory**\n\nNo electrical equipment was detected in the drawing `{st.session_state.active_doc}`."
        return {"content": content, "accuracy": 95.0}

    total_items = len(boq)
    total_qty = sum(item["quantity"] for item in boq)

    table_md = "| Category | Item Description | Quantity | Unit |\n| :--- | :--- | :--- | :--- |\n"
    for item in boq:
        table_md += f"| {item['category']} | {item['item']} | {item['quantity']} | {item['unit']} |\n"

    content = f"""📋 **Bill of Quantities (BOQ)**

Here is the automatically generated Bill of Quantities for: **`{st.session_state.active_doc}`**

{table_md}

**Total Equipment Types**: {total_items}
**Total Component Quantity**: {total_qty} Nos

You can search, sort, filter, and download this BOQ in **CSV, Excel, or PDF** formats from the new sidebar section, or download it directly using the buttons below.
"""
    return {
        "content": content,
        "accuracy": 95.0,
        "is_boq": True
    }


def generate_csv_bytes(boq_list):
    """Generates UTF-8 encoded CSV bytes from a BOQ list."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Item Description", "Quantity", "Unit"])
    for row in boq_list:
        writer.writerow([row["category"], row["item"], row["quantity"], row["unit"]])
    return output.getvalue().encode('utf-8')


def generate_excel_bytes(boq_list):
    """Generates Excel workbook bytes from a BOQ list, falls back to CSV on error."""
    df = pd.DataFrame(boq_list)
    df.columns = ["Category", "Item Description", "Quantity", "Unit"]
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Engineering BOQ")
        return output.getvalue()
    except Exception as e:
        print(f"[boq_generator] openpyxl writing failed: {e}. Falling back to CSV.")
        return df.to_csv(index=False).encode('utf-8')


def generate_pdf_bytes(boq_list, drawing_name, drawing_type):
    """Generates a styled PDF report containing the BOQ table and metadata using fitz."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # A4: 595 x 842 points
    
    x_margin = 50
    y_start = 50
    
    page.insert_text((x_margin, y_start), "L&T CONSTRUCTION", fontsize=16, fontname="hebo", color=(0.1, 0.3, 0.6))
    y_start += 20
    page.draw_line((x_margin, y_start), (545, y_start), color=(0.1, 0.3, 0.6), width=1.5)
    y_start += 25
    
    page.insert_text((x_margin, y_start), "Project Name:", fontsize=10, fontname="hebo")
    page.insert_text((x_margin + 100, y_start), "Engineering Document Assistant", fontsize=10, fontname="helv")
    y_start += 16
    
    page.insert_text((x_margin, y_start), "Drawing Name:", fontsize=10, fontname="hebo")
    page.insert_text((x_margin + 100, y_start), str(drawing_name), fontsize=10, fontname="helv")
    y_start += 16
    
    page.insert_text((x_margin, y_start), "Drawing Type:", fontsize=10, fontname="hebo")
    page.insert_text((x_margin + 100, y_start), str(drawing_type), fontsize=10, fontname="helv")
    y_start += 16
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    page.insert_text((x_margin, y_start), "Generated Date:", fontsize=10, fontname="hebo")
    page.insert_text((x_margin + 100, y_start), current_date, fontsize=10, fontname="helv")
    y_start += 25
    
    page.insert_text((x_margin, y_start), "BOQ Executive Summary", fontsize=11, fontname="hebo", color=(0.1, 0.3, 0.6))
    y_start += 15
    
    total_items = len(boq_list)
    total_qty = sum(item["quantity"] for item in boq_list)
    summary_text = (
        f"This Bill of Quantities (BOQ) reports the structured inventory extracted from the engineering "
        f"drawing '{drawing_name}' (classified as {drawing_type}). A total of {total_items} distinct categories of "
        f"equipment and components were identified with a total quantity of {total_qty} units. The extraction covers "
        f"Electrical equipment, Civil layouts, Structural components, and Mechanical systems where detected."
    )
    rect = fitz.Rect(x_margin, y_start, 545, y_start + 50)
    page.insert_textbox(rect, summary_text, fontsize=9, fontname="helv", align=fitz.TEXT_ALIGN_LEFT)
    y_start += 60
    
    page.draw_rect((x_margin, y_start, 545, y_start + 20), color=(0.1, 0.3, 0.6), fill=(0.9, 0.92, 0.96))
    page.insert_text((x_margin + 10, y_start + 14), "Category", fontsize=9, fontname="hebo", color=(0.1, 0.3, 0.6))
    page.insert_text((x_margin + 150, y_start + 14), "Item Description", fontsize=9, fontname="hebo", color=(0.1, 0.3, 0.6))
    page.insert_text((x_margin + 350, y_start + 14), "Quantity", fontsize=9, fontname="hebo", color=(0.1, 0.3, 0.6))
    page.insert_text((x_margin + 440, y_start + 14), "Unit", fontsize=9, fontname="hebo", color=(0.1, 0.3, 0.6))
    y_start += 20
    
    for row in boq_list:
        if y_start > 780:
            page = doc.new_page(width=595, height=842)
            y_start = 50
            page.draw_rect((x_margin, y_start, 545, y_start + 20), color=(0.1, 0.3, 0.6), fill=(0.9, 0.92, 0.96))
            page.insert_text((x_margin + 10, y_start + 14), "Category", fontsize=9, fontname="hebo", color=(0.1, 0.3, 0.6))
            page.insert_text((x_margin + 150, y_start + 14), "Item Description", fontsize=9, fontname="hebo", color=(0.1, 0.3, 0.6))
            page.insert_text((x_margin + 350, y_start + 14), "Quantity", fontsize=9, fontname="hebo", color=(0.1, 0.3, 0.6))
            page.insert_text((x_margin + 440, y_start + 14), "Unit", fontsize=9, fontname="hebo", color=(0.1, 0.3, 0.6))
            y_start += 20
            
        page.draw_line((x_margin, y_start), (545, y_start), color=(0.8, 0.8, 0.8), width=0.5)
        page.insert_text((x_margin + 10, y_start + 14), str(row["category"]), fontsize=8, fontname="helv")
        page.insert_text((x_margin + 150, y_start + 14), str(row["item"]), fontsize=8, fontname="helv")
        page.insert_text((x_margin + 350, y_start + 14), str(row["quantity"]), fontsize=8, fontname="helv")
        page.insert_text((x_margin + 440, y_start + 14), str(row["unit"]), fontsize=8, fontname="helv")
        y_start += 20
        
    page.draw_line((x_margin, y_start), (545, y_start), color=(0.1, 0.3, 0.6), width=1)
    y_start += 15
    
    page.insert_text((x_margin, y_start), f"Total Equipment Count: {len(boq_list)} items (Total Quantity: {total_qty})", fontsize=10, fontname="hebo", color=(0.1, 0.3, 0.6))
    
    return doc.write()
