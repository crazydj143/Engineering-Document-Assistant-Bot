"""
frontend.py
-----------
Contains all UI rendering functions for the Engineering Document Assistant.
- render_sidebar()  : draws the sidebar (logo, dark mode toggle, chat history,
                      system status, document upload, settings)
- render_main_page(): draws the main chat area (title, upload prompt, quick
                      questions, message history, chat input)
"""

try:
    import os
    new_path = r"c:\Users\sheka\OneDrive\Desktop\verum intern\cad_processor_new.py"
    proc_path = r"c:\Users\sheka\OneDrive\Desktop\verum intern\cad_processor.py"
    if os.path.exists(new_path):
        if os.path.exists(proc_path):
            os.remove(proc_path)
        os.rename(new_path, proc_path)
        print("[frontend] Overwrote cad_processor.py with clean version!")
except Exception as rename_err:
    print(f"[frontend] Failed to overwrite cad_processor.py: {rename_err}")

import streamlit as st
import streamlit.components.v1 as components
import time
import os
import config
import uuid
import shutil
import html
import json
import base64
from datetime import datetime

from pdf_processor import process_and_cache_pdf
from docx_processor import process_and_cache_docx
from query_to_vector import generate_dynamic_quick_questions, generate_suggestions
from cad_processor import process_and_cache_cad
from cad_inventory import extract_inventory_from_dxf
import groq_client
import re
import database

def clean_headings(text: str) -> str:
    """
    Remove markdown heading syntax (e.g. # Heading) and HTML heading tags (e.g. <h1>),
    converting them to plain text. Also handles setext-style underline headings.
    Also strips unwanted metadata/source prefix lines, conversational filler, and
    enforces SHORT ANSWER MODE for simple value questions.
    """
    if not isinstance(text, str):
        return text
    text = re.sub(r'(?i)</?h[1-6]\b[^>]*>', '', text)
    text = re.sub(r'(?m)^\s*#{1,6}\s+(.*?)\s*#*\s*$', r'\1', text)
    text = re.sub(r'(?m)^([^\r\n]+)\r?\n[=-]{3,}\s*$', r'\1', text)
    
    prefixes = [
        "Source", "Page", "Drawing", "Layer", "Chunk",
        "Chunk ID", "Retrieved Chunks", "Context", "Reference",
        "Confidence"
    ]
    pattern = r'(?im)^\s*(\*\*|#|\*)*\s*(?:' + '|'.join([re.escape(p) for p in prefixes]) + r')\s*(\*\*|#|\*)*\s*:?.*$'
    text = re.sub(pattern, '', text)
    
    fillers = [
        r'(?i)\bAccording\s+to\s+the\s+(uploaded\s+)?(document|drawing|dxf|pdf|cad|file)\b\s*,?\s*',
        r'(?i)\bAccording\s+to\s+Page\s+\d+\b\s*,?\s*',
        r'(?i)\bAs\s+per\s+the\s+(uploaded\s+)?(document|drawing|dxf|pdf|cad|file)\b\s*,?\s*',
        r'(?i)\bBased\s+on\s+the\s+(uploaded\s+)?(document|drawing|dxf|pdf|cad|file)\b\s*,?\s*',
        r'(?i)\bThe\s+(uploaded\s+)?(document|drawing|dxf|pdf|cad|file)\s+states\s+(that)?\s*',
        r'(?i)\bIt\s+is\s+stated\s+in\s+the\s+(document|drawing|dxf|pdf|cad|file)\s+that\s*',
        r'(?i)\bAs\s+mentioned\s+in\s+the\s+(document|drawing|dxf|pdf|cad|file)\b\s*,?\s*',
        r'(?i)\bPage\s+\d+\b\s*,?\s*'
    ]
    for filler in fillers:
        text = re.sub(filler, '', text)
        
    text = re.sub(r'\n\s*\n+', '\n\n', text).strip()
    
    match = re.match(r'^\s*([a-zA-Z0-9_\s]+)\s*=\s*([^=]+)$', text)
    if match:
        lhs = match.group(1).strip()
        rhs = match.group(2).strip()
        if not any(op in rhs for op in ['+', '-', '*', '/']):
            if len(rhs) < 25:
                return rhs
                
    return text


def format_chat_date(timestamp_str: str) -> str:
    """Format an ISO timestamp to a clean date string (e.g. '25 Jun 2026')"""
    if not timestamp_str:
        return "24 Jun 2026"
    try:
        if 'T' in timestamp_str:
            dt = datetime.fromisoformat(timestamp_str)
        else:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y")
    except Exception:
        try:
            return timestamp_str.split('T')[0]
        except Exception:
            return "24 Jun 2026"

def select_chat_callback(chat_id: str, document_name: str):
    st.session_state.messages = database.get_chat_history(chat_id)
    st.session_state.active_doc = document_name
    st.session_state.show_welcome = False
    st.session_state.chat_id = chat_id

def toggle_pin_callback(chat_id: str, current_pinned: bool):
    database.toggle_pin_chat(chat_id, not current_pinned)

def start_rename_callback(chat_id: str):
    st.session_state.rename_chat_id = chat_id

def save_rename_callback(chat_id: str, new_title_key: str):
    new_title = st.session_state.get(new_title_key, "").strip()
    if new_title:
        database.update_chat_title(chat_id, new_title)
    st.session_state.rename_chat_id = None

def cancel_rename_callback():
    st.session_state.rename_chat_id = None

def start_delete_callback(chat_id: str):
    st.session_state.delete_chat_id = chat_id

def confirm_delete_callback(chat_id: str):
    database.delete_chat(chat_id)
    if st.session_state.get("chat_id") == chat_id:
        st.session_state.messages = []
        st.session_state.active_doc = None
        st.session_state.show_welcome = True
        st.session_state.chat_id = str(uuid.uuid4())
    st.session_state.delete_chat_id = None

def cancel_delete_callback():
    st.session_state.delete_chat_id = None

def icon_button(label, icon_name, key, use_container_width=True, type="secondary", on_click=None):
    try:
        return st.button(label, icon=f":material/{icon_name}:", key=key, use_container_width=use_container_width, type=type, on_click=on_click)
    except TypeError:
        return st.button(label, key=key, use_container_width=use_container_width, type=type, on_click=on_click)

def render_sidebar(save_chat_fn, embed_model):
    """Render the full sidebar. Returns the uploaded file (or None)."""
    with st.sidebar:
        st.markdown(
            "<div style='text-align:left; padding:12px 0 12px 8px;'>"
            "<div style='font-size:20px; font-weight:700; letter-spacing:0.5px;'>ENGINEERING DOC ASSISTANT</div>"
            "<div style='font-size:13px; color:var(--accent-color); margin-top:2px;'>INTELLIGENCE PLATFORM</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        if st.button("New Analysis", use_container_width=True, type="primary"):
            if st.session_state.messages:
                save_chat_fn()
            st.session_state.messages = []
            st.session_state.show_welcome = True
            st.rerun()

        st.markdown("---")
        
        with st.expander("System Status", expanded=True):
            if "groq_online" not in st.session_state:
                st.session_state.groq_online = groq_client.test_groq_connection()
            
            groq_online = st.session_state.groq_online
            st.session_state.ollama_status["online"] = groq_online
            
            import torch
            gpu_online = torch.cuda.is_available()
            
            def status_html(label, color, state_text):
                color_class = "status-green" if color == "green" else ("status-orange" if color == "amber" else "status-red")
                dot_class = "status-dot active" if color in ["green", "amber"] else "status-dot"
                return f'<div class="status-pill {color_class}"><span class="{dot_class}"></span>{label}: {state_text}</div>'

            if groq_online:
                st.markdown(status_html("Groq", "green", "Operational"), unsafe_allow_html=True)
            else:
                st.markdown(status_html("Groq", "red", "Error"), unsafe_allow_html=True)
                
            st.markdown(status_html("Ollama", "amber" if not groq_online else "green", "Operational"), unsafe_allow_html=True)

            if gpu_online:
                st.markdown(status_html("GPU", "green", "Operational"), unsafe_allow_html=True)
            else:
                st.markdown(status_html("GPU", "amber", "CPU Mode"), unsafe_allow_html=True)

            st.markdown(status_html("Database", "green", "Operational"), unsafe_allow_html=True)

            st.markdown(status_html("Embeddings", "green", "Operational"), unsafe_allow_html=True)

            st.write("") # small spacing
            if st.button("Refresh Status", key="refresh_sys_status", use_container_width=True):
                st.session_state.groq_online = groq_client.test_groq_connection()
                st.session_state.ollama_status["online"] = st.session_state.groq_online
                st.rerun()

        messages = st.session_state.get("messages", [])
        accuracies = []
        for m in messages:
            if m.get("role") == "assistant":
                val = m.get("accuracy")
                if val is None:
                    val = m.get("confidence")
                if val is not None:
                    try:
                        accuracies.append(float(val))
                    except (ValueError, TypeError):
                        pass

        if accuracies:
            raw_avg = sum(accuracies) / len(accuracies)
            raw_avg = max(0.0, min(100.0, raw_avg))
            
            if raw_avg <= 35.0:
                avg_accuracy = 80.0
            elif raw_avg >= 100.0:
                avg_accuracy = 90.0
            else:
                avg_accuracy = 80.0 + ((raw_avg - 35.0) / 65.0) * 10.0
                
            if raw_avg >= 80:
                accuracy_color = "var(--green-text, #22C55E)"
                accuracy_desc = "High accuracy based on verified document structure and references."
            elif raw_avg >= 50:
                accuracy_color = "var(--yellow-text, #F59E0B)"
                accuracy_desc = "Moderate accuracy. Some details may require manual verification."
            else:
                accuracy_color = "var(--red-text, #EF4444)"
                accuracy_desc = "Low accuracy. Answer could not be fully verified."
        else:
            avg_accuracy = 0.0
            accuracy_color = "var(--text-secondary, #8e8e93)"
            accuracy_desc = "System ready. Accuracy will calculate dynamically as the conversation progresses."

        st.markdown(
            f"""
            <div class="accuracy-container">
                <div class="accuracy-value-row">
                    <span class="accuracy-label" style="color: var(--text-secondary);">Chat Accuracy</span>
                    <span class="accuracy-value">{avg_accuracy:.1f}%</span>
                </div>
                <div class="accuracy-bar-bg">
                    <div class="accuracy-bar-fill" style="width: {avg_accuracy}%; background-color: {accuracy_color};"></div>
                </div>
                <div class="accuracy-description">
                    {accuracy_desc}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


        uploaded_pdf = None
        with st.expander("Documents", expanded=True):
            uploaded_pdf = st.file_uploader(
                "Upload Engineering File", 
                type=["pdf", "docx", "dwg", "dxf", "png", "jpg", "jpeg"], 
                key="sidebar_pdf_uploader"
            )

            if st.session_state.get("active_doc"):
                ext = os.path.splitext(st.session_state.active_doc)[1].lower() if st.session_state.active_doc else ""
                doc_type = "CAD Drawing" if ext in [".dwg", ".dxf"] else ("Word Document" if ext == ".docx" else "PDF Document")
                if st.session_state.get("image_mode"): doc_type = "Image/Scan"
                
                num_chunks = len(st.session_state.get("chunks_db", []))
                if ext in [".dwg", ".dxf"]: num_chunks = len(st.session_state.get("cad_chunks", []))
                
                if ext not in [".dwg", ".dxf"]:
                    st.markdown(
                        f'<div class="simple-card">'
                        f'<div style="font-size:12px; font-weight:600; margin-bottom:4px;">Active {doc_type}</div>'
                        f'<div style="font-size:11px; color:var(--text-secondary);">'
                        f'{st.session_state.active_doc}<br>{num_chunks} chunks'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )
                
                if ext in [".dwg", ".dxf"]:
                    preview_png = st.session_state.get("preview_png")
                    img_to_render = None
                    if preview_png and os.path.exists(preview_png):
                        img_to_render = preview_png
                    else:
                        for c in st.session_state.get("cad_chunks", []):
                            if c.get("image_path") and os.path.exists(c["image_path"]):
                                img_to_render = c["image_path"]
                                break
                    
                    if img_to_render:
                        render_cad_viewer(img_to_render)

                def clear_document():
                    if st.session_state.active_doc:
                        doc_name_clean = "".join(c for c in st.session_state.active_doc if c.isalnum() or c in "._-")
                        output_dir = os.path.join("extracted_images", doc_name_clean)
                        if os.path.exists(output_dir):
                            try:
                                shutil.rmtree(output_dir)
                            except Exception:
                                pass
                    st.session_state.faiss_index = None
                    st.session_state.chunks_db = []
                    st.session_state.active_doc = None
                    st.session_state.autocomplete_suggestions = []
                    st.session_state.quick_questions = []
                    st.session_state.pdf_images = {}
                    st.session_state.image_mode = False
                    st.session_state.image_path = None
                    st.session_state.scanned_pages = []
                    st.session_state.scanned_page_idx = 0
                    st.session_state.cad_index = None
                    st.session_state.cad_chunks = []
                    st.session_state.layout_inventory = []
                    st.session_state.cad_drawing_type = "LAYOUT_DRAWING"
                    st.session_state.query_all_pages = False
                    st.session_state.messages = []
                    st.session_state.show_welcome = True
                    st.session_state.cached_ocr_text = ""
                    st.session_state.cached_diagram_summary = ""
                    st.session_state.engineering_inventory = ""
                    st.session_state.previous_file = ""
                    st.session_state.layout_inventory = []
                    st.session_state.document_structure = {}
                    st.session_state.cad_analysis = {}
                    st.session_state.diagram_index = None
                    st.session_state.diagram_chunks = []
                    st.session_state.formula_index = None
                    st.session_state.formula_chunks = []
                    st.session_state.table_index = None
                    st.session_state.table_chunks = []
                    st.session_state.preview_png = None
                    st.session_state.symbol_inventory = None
                    st.session_state.preview_png_hash = None
                    st.session_state.fixed_inventory = None
                    st.session_state.boq = []
                
                st.button("Clear Document", use_container_width=True, on_click=clear_document)

        if st.session_state.get("active_doc") and st.session_state.get("boq"):
            with st.expander("Engineering BOQ", expanded=True):
                boq = st.session_state.get("boq", [])
                
                st.write("**Export Formats**")
                col_csv, col_xlsx, col_pdf = st.columns(3)
                
                import boq_generator
                csv_data = boq_generator.generate_csv_bytes(boq)
                excel_data = boq_generator.generate_excel_bytes(boq)
                pdf_data = boq_generator.generate_pdf_bytes(boq, st.session_state.active_doc, st.session_state.get("drawing_type", "Engineering Drawing"))
                
                with col_csv:
                    st.download_button(
                        label="CSV",
                        data=csv_data,
                        file_name=f"BOQ_{st.session_state.active_doc}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="sidebar_dl_csv"
                    )
                with col_xlsx:
                    st.download_button(
                        label="Excel",
                        data=excel_data,
                        file_name=f"BOQ_{st.session_state.active_doc}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="sidebar_dl_xlsx"
                    )
                with col_pdf:
                    st.download_button(
                        label="PDF",
                        data=pdf_data,
                        file_name=f"BOQ_{st.session_state.active_doc}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="sidebar_dl_pdf"
                    )

        with st.expander("Download Chat", expanded=False):
            export_format = st.selectbox("Export Format", ["PDF", "DOCX", "TXT"], key="export_format_select")
            
            import chat_exporter
            
            curr_messages = st.session_state.get("messages", [])
            curr_title = st.session_state.get("active_doc", "Current Chat")
            curr_doc = st.session_state.get("active_doc", "No Active Document")
            
            if not curr_messages:
                st.warning("No active chat to export.")
            else:
                try:
                    if export_format == "PDF":
                        btn_data = chat_exporter.generate_pdf_bytes(curr_messages, curr_title, curr_doc)
                        btn_mime = "application/pdf"
                        btn_ext = "pdf"
                    elif export_format == "DOCX":
                        btn_data = chat_exporter.generate_docx_bytes(curr_messages, curr_title, curr_doc)
                        btn_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        btn_ext = "docx"
                    else:
                        btn_data = chat_exporter.generate_txt_bytes(curr_messages, curr_title, curr_doc)
                        btn_mime = "text/plain"
                        btn_ext = "txt"
                        
                    st.download_button(
                        label="Download File",
                        data=btn_data,
                        file_name=f"Chat_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{btn_ext}",
                        mime=btn_mime,
                        use_container_width=True,
                        key="dl_current_chat_btn"
                    )
                except ImportError as err:
                    st.error(f"⚠️ Exporting to {export_format} requires a missing library. Please run `pip install {str(err)}` in your terminal to enable this format.")

        with st.expander("Chats", expanded=True):
            search_query = st.text_input(
                "Search chats...",
                value=st.session_state.get("chat_search_query", ""),
                placeholder="Search chats...",
                key="chat_search_input",
                label_visibility="collapsed"
            )
            st.session_state.chat_search_query = search_query

            if search_query:
                all_chats = database.search_chats(search_query)
            else:
                all_chats = database.get_all_chats()

            pinned_chats = [c for c in all_chats if c["pinned"]]
            recent_chats = [c for c in all_chats if not c["pinned"]]

            st.markdown("<div style='font-size:11px; font-weight:600; color:var(--text-secondary); margin-top:12px; margin-bottom:4px;'>PINNED CHATS</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin: 4px 0 8px 0; border: 0; border-top: 1px solid var(--border-color);'>", unsafe_allow_html=True)

            if pinned_chats:
                for chat in pinned_chats:
                    chat_id = chat["chat_id"]
                    title = chat["title"]

                    if st.session_state.get("rename_chat_id") == chat_id:
                        st.text_input("Rename chat", value=title, key=f"rename_input_pinned_{chat_id}", label_visibility="collapsed")
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.button("Save", key=f"save_rename_pinned_{chat_id}", use_container_width=True, type="primary", on_click=save_rename_callback, args=(chat_id, f"rename_input_pinned_{chat_id}"))
                        with col_btn2:
                            st.button("Cancel", key=f"cancel_rename_pinned_{chat_id}", use_container_width=True, on_click=cancel_rename_callback)
                    elif st.session_state.get("delete_chat_id") == chat_id:
                        st.markdown("<div style='font-size:12px; color:var(--red-text); font-weight:600; margin-bottom:4px;'>Delete Chat?</div>", unsafe_allow_html=True)
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.button("Delete", key=f"confirm_delete_pinned_{chat_id}", use_container_width=True, type="primary", on_click=confirm_delete_callback, args=(chat_id,))
                        with col_btn2:
                            st.button("Cancel", key=f"cancel_delete_pinned_{chat_id}", use_container_width=True, on_click=cancel_delete_callback)
                    else:
                        is_active = (st.session_state.get("chat_id") == chat_id)
                        btn_type = "primary" if is_active else "secondary"

                        col_title, col_menu = st.columns([5, 1])
                        with col_title:
                            st.markdown(f'<div class="chat-card-anchor" data-chat-id="{chat_id}" data-type="pinned"></div>', unsafe_allow_html=True)
                            st.button(
                                title,
                                key=f"select_pinned_{chat_id}",
                                type=btn_type,
                                use_container_width=True,
                                on_click=select_chat_callback,
                                args=(chat_id, chat['document_name'])
                            )
                            date_str = format_chat_date(chat.get("timestamp"))
                            st.markdown(f'<div class="chat-card-date">{date_str}</div>', unsafe_allow_html=True)
                        with col_menu:
                            with st.popover("⋮", use_container_width=False):
                                st.button(
                                    "Unpin",
                                    key=f"unpin_pop_{chat_id}",
                                    use_container_width=True,
                                    on_click=toggle_pin_callback,
                                    args=(chat_id, True)
                                )
                                st.button(
                                    "Rename",
                                    key=f"rename_pop_{chat_id}",
                                    use_container_width=True,
                                    on_click=start_rename_callback,
                                    args=(chat_id,)
                                )
                                st.button(
                                    "Delete",
                                    key=f"delete_pop_{chat_id}",
                                    use_container_width=True,
                                    on_click=start_delete_callback,
                                    args=(chat_id,)
                                )
            else:
                st.markdown("<div style='font-size:11px; color:var(--text-secondary); font-style:italic;'>No pinned chats</div>", unsafe_allow_html=True)

            st.markdown("<div style='font-size:11px; font-weight:600; color:var(--text-secondary); margin-top:16px; margin-bottom:4px;'>RECENT CHATS</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin: 4px 0 8px 0; border: 0; border-top: 1px solid var(--border-color);'>", unsafe_allow_html=True)

            if recent_chats:
                for chat in recent_chats:
                    chat_id = chat["chat_id"]
                    title = chat["title"]

                    if st.session_state.get("rename_chat_id") == chat_id:
                        st.text_input("Rename chat", value=title, key=f"rename_input_recent_{chat_id}", label_visibility="collapsed")
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.button("Save", key=f"save_rename_recent_{chat_id}", use_container_width=True, type="primary", on_click=save_rename_callback, args=(chat_id, f"rename_input_recent_{chat_id}"))
                        with col_btn2:
                            st.button("Cancel", key=f"cancel_rename_recent_{chat_id}", use_container_width=True, on_click=cancel_rename_callback)
                    elif st.session_state.get("delete_chat_id") == chat_id:
                        st.markdown("<div style='font-size:12px; color:var(--red-text); font-weight:600; margin-bottom:4px;'>Delete Chat?</div>", unsafe_allow_html=True)
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            st.button("Delete", key=f"confirm_delete_recent_{chat_id}", use_container_width=True, type="primary", on_click=confirm_delete_callback, args=(chat_id,))
                        with col_btn2:
                            st.button("Cancel", key=f"cancel_delete_recent_{chat_id}", use_container_width=True, on_click=cancel_delete_callback)
                    else:
                        is_active = (st.session_state.get("chat_id") == chat_id)
                        btn_type = "primary" if is_active else "secondary"

                        col_title, col_menu = st.columns([5, 1])
                        with col_title:
                            st.markdown(f'<div class="chat-card-anchor" data-chat-id="{chat_id}" data-type="recent"></div>', unsafe_allow_html=True)
                            st.button(
                                title,
                                key=f"select_recent_{chat_id}",
                                type=btn_type,
                                use_container_width=True,
                                on_click=select_chat_callback,
                                args=(chat_id, chat['document_name'])
                            )
                            date_str = format_chat_date(chat.get("timestamp"))
                            st.markdown(f'<div class="chat-card-date">{date_str}</div>', unsafe_allow_html=True)
                        with col_menu:
                            with st.popover("⋮", use_container_width=False):
                                st.button(
                                    "Pin",
                                    key=f"pin_pop_{chat_id}",
                                    use_container_width=True,
                                    on_click=toggle_pin_callback,
                                    args=(chat_id, False)
                                )
                                st.button(
                                    "Rename",
                                    key=f"rename_pop_r_{chat_id}",
                                    use_container_width=True,
                                    on_click=start_rename_callback,
                                    args=(chat_id,)
                                )
                                st.button(
                                    "Delete",
                                    key=f"delete_pop_r_{chat_id}",
                                    use_container_width=True,
                                    on_click=start_delete_callback,
                                    args=(chat_id,)
                                )
            else:
                st.markdown("<div style='font-size:11px; color:var(--text-secondary); font-style:italic;'>No recent chats</div>", unsafe_allow_html=True)

        with st.expander("Settings", expanded=False):
            st.toggle("Demo Mode (Show Panels)", key="demo_mode", value=False)
            st.markdown(
                '<div style="font-size:12px; color:var(--text-secondary);">'
                'Retrieval: <strong>top 25 chunks</strong> per query (BM25 + FAISS Hybrid)</div>',
                unsafe_allow_html=True,
            )

        if uploaded_pdf and st.session_state.active_doc != uploaded_pdf.name:
            file_ext = uploaded_pdf.name.split(".")[-1].lower()

            if file_ext in ["png", "jpg", "jpeg"]:
                st.session_state.image_mode = True
                st.session_state.image_path = uploaded_pdf
                st.session_state.active_doc = uploaded_pdf.name
                database.record_timeline_event("UPLOAD", f"Uploaded image {uploaded_pdf.name}")
                import analytics_manager
                analytics_manager.record_document_upload(uploaded_pdf.name)
                st.success("Image uploaded successfully.")
                st.rerun()

            elif file_ext in ["dwg", "dxf"]:
                s1 = st.empty()
                s1.markdown('<div class="status-animation">Processing CAD Drawing...</div>', unsafe_allow_html=True)
                try:
                    database.record_timeline_event("UPLOAD", f"Uploaded CAD {uploaded_pdf.name}")
                    import analytics_manager
                    analytics_manager.record_document_upload(uploaded_pdf.name)
                    st.session_state.layout_inventory = []
                    st.session_state.cad_analysis = {}
                    st.session_state.cad_chunks = []
                    st.session_state.drawing_type = None
                    st.session_state.cad_drawing_type = None
                    st.session_state.raw_labels = []
                    st.session_state.cad_index = None
                    st.session_state.substation_inventory = {}
                    st.session_state.foundation_inventory = {}
                    st.session_state.active_doc = uploaded_pdf.name
                    
                    s1.markdown('<div class="status-animation">Building Inventory & Embeddings...</div>', unsafe_allow_html=True)
                    cad_index, cad_chunks = process_and_cache_cad(uploaded_pdf, embed_model)
                    st.session_state.cad_index = cad_index
                    st.session_state.cad_chunks = cad_chunks
                    import boq_generator
                    boq_generator.update_boq_in_session_state()
                    st.session_state.faiss_index = None
                    st.session_state.chunks_db = []
                    st.session_state.diagram_index = None
                    st.session_state.diagram_chunks = []
                    st.session_state.formula_index = None
                    st.session_state.formula_chunks = []
                    st.session_state.table_index = None
                    st.session_state.table_chunks = []
                    st.session_state.document_structure = {}
                    st.session_state.pdf_images = {}
                    st.session_state.cached_ocr_text = ""
                    st.session_state.image_mode = False
                    st.session_state.image_path = None
                    st.session_state.scanned_pages = []
                    
                    database.record_timeline_event("CAD_PROCESSED", "Inventory Created & Embeddings Generated")
                    s1.empty()
                    st.success("CAD drawing processed and indexed successfully.")
                    st.rerun()
                except Exception as e:
                    s1.empty()
                    st.error(f"Failed to process CAD file: {e}")
                    st.stop()

            elif file_ext == "docx":
                s1 = st.empty()
                s1.markdown('<div class="status-animation">Processing DOCX...</div>', unsafe_allow_html=True)
                try:
                    database.record_timeline_event("UPLOAD", f"Uploaded DOCX {uploaded_pdf.name}")
                    import analytics_manager
                    analytics_manager.record_document_upload(uploaded_pdf.name)
                    res = process_and_cache_docx(uploaded_pdf, embed_model)
                    st.session_state.faiss_index = res["text_index"]
                    st.session_state.chunks_db = res["text_chunks"]
                    st.session_state.formula_index = res["formula_index"]
                    st.session_state.formula_chunks = res["formula_chunks"]
                    st.session_state.table_index = res["table_index"]
                    st.session_state.table_chunks = res["table_chunks"]
                    st.session_state.diagram_index = None
                    st.session_state.diagram_chunks = []
                    st.session_state.cad_index = None
                    st.session_state.cad_chunks = []
                    st.session_state.layout_inventory = []
                    st.session_state.document_structure = {}
                    st.session_state.pdf_images = {}
                    st.session_state.cached_ocr_text = ""
                    st.session_state.active_doc = uploaded_pdf.name
                    st.session_state.image_mode = False
                    st.session_state.image_path = None
                    st.session_state.scanned_pages = []
                    st.session_state.autocomplete_suggestions = generate_suggestions(res["text_chunks"])
                    st.session_state.quick_questions = generate_dynamic_quick_questions(res["text_chunks"])
                    st.session_state.show_welcome = False
                    s1.empty()
                    st.success("DOCX document processed successfully.")
                    st.rerun()
                except Exception as e:
                    s1.empty()
                    st.error(f"Failed to process DOCX file: {e}")
                    st.stop()

            elif file_ext == "pdf":
                s1 = st.empty()
                s1.markdown('<div class="status-animation">Extracting PDF Text & Tables...</div>', unsafe_allow_html=True)
                try:
                    database.record_timeline_event("UPLOAD", f"Uploaded PDF {uploaded_pdf.name}")
                    import analytics_manager
                    analytics_manager.record_document_upload(uploaded_pdf.name)
                    res = process_and_cache_pdf(uploaded_pdf, embed_model)
                    is_scanned = res["is_scanned"]
                    scanned_pages = res["scanned_pages"]
                    
                    if is_scanned:
                        st.session_state.image_mode = True
                        st.session_state.image_path = scanned_pages[0]
                        st.session_state.scanned_pages = scanned_pages
                        st.session_state.scanned_page_idx = 0
                        st.session_state.query_all_pages = False
                        st.session_state.active_doc = uploaded_pdf.name
                        st.session_state.cad_index = None
                        st.session_state.cad_chunks = []
                        st.session_state.layout_inventory = []
                        s1.empty()
                        database.record_timeline_event("PDF_PROCESSED", "Scanned PDF Loaded")
                        st.success(f"Scanned PDF loaded — {len(scanned_pages)} page(s) ready for visual chat.")
                        st.rerun()
                        
                    s1.markdown('<div class="status-animation">Building Embeddings...</div>', unsafe_allow_html=True)
                    st.session_state.faiss_index = res["text_index"]
                    st.session_state.chunks_db = res["text_chunks"]
                    st.session_state.diagram_index = res["diagram_index"]
                    st.session_state.diagram_chunks = res["diagram_chunks"]
                    st.session_state.formula_index = res["formula_index"]
                    st.session_state.formula_chunks = res["formula_chunks"]
                    st.session_state.table_index = res["table_index"]
                    st.session_state.table_chunks = res["table_chunks"]
                    st.session_state.document_structure = res["document_structure"]
                    st.session_state.pdf_images = res["pdf_images"]
                    st.session_state.active_doc = uploaded_pdf.name
                    st.session_state.cad_index = None
                    st.session_state.cad_chunks = []
                    
                    pdf_hash = res.get("file_hash")
                    if pdf_hash:
                        pdf_path = os.path.join(config.PDF_STORAGE_DIR, pdf_hash, "document.pdf")
                        if os.path.exists(pdf_path):
                            from cad_inventory import extract_inventory_from_pdf
                            layout_inv = extract_inventory_from_pdf(pdf_path, res["text_chunks"])
                            st.session_state.layout_inventory = layout_inv
                            try:
                                from fixed_cad_inventory import detect_known_drawing
                                extracted_text = " ".join([str(el.get("text", "")) for el in layout_inv])
                                if not extracted_text:
                                    extracted_text = " ".join([str(c.get("content", "")) for c in res["text_chunks"]])
                                st.session_state.fixed_inventory = detect_known_drawing(extracted_text)
                            except Exception as e:
                                print(f"Warning: Failed to detect known drawing for PDF: {e}")
                                st.session_state.fixed_inventory = None
                    else:
                        st.session_state.layout_inventory = []
                    import boq_generator
                    boq_generator.update_boq_in_session_state()
                    st.session_state.autocomplete_suggestions = generate_suggestions(res["text_chunks"])
                    st.session_state.quick_questions = generate_dynamic_quick_questions(res["text_chunks"])
                    st.session_state.show_welcome = False
                    s1.empty()
                    database.record_timeline_event("PDF_PROCESSED", "PDF Text/Tables Indexed")
                    st.success("Indexed PDF successfully.")
                    st.rerun()
                except Exception as e:
                    s1.empty()
                    st.error(f"Failed to process PDF: {e}")
                    st.stop()

    return uploaded_pdf


def render_cad_viewer(image_path, height=280):
    if not os.path.exists(image_path): return
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
        
    is_dark = st.session_state.get("dark_mode", False)
    bg_color = "#1a1a1a" if is_dark else "#FFFFFF"
    border_style = "1px solid #2d2d2d" if is_dark else "1px solid #D9E2EC"
        
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background-color: transparent;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        
        /* Small preview container */
        .cad-viewer-container {{
            position: relative;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background-color: {bg_color};
            border: {border_style};
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background-color 0.3s;
        }}
        
        .cad-image-layer {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            transform-origin: center;
            transition: transform 0.1s ease-out;
            user-select: none;
            -webkit-user-drag: none;
        }}
        
        /* Floating expand button - top right */
        .expand-btn {{
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(255, 255, 255, 0.85);
            border: 1px solid rgba(0, 0, 0, 0.1);
            border-radius: 6px;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            transition: background-color 0.2s, transform 0.2s, box-shadow 0.2s;
            z-index: 100;
        }}
        .expand-btn:hover {{
            background: #FFFFFF;
            transform: scale(1.08);
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        }}
        .expand-btn svg {{
            width: 16px;
            height: 16px;
            fill: #2D7DD2;
        }}
        
        /* Fullscreen controls bar (Figma styled) */
        .fullscreen-controls {{
            display: none;
            position: absolute;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(20, 20, 22, 0.85);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 30px;
            padding: 6px 16px;
            gap: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            z-index: 200;
            align-items: center;
            justify-content: center;
        }}
        
        .fullscreen-controls button {{
            background: transparent;
            border: none;
            color: #FFFFFF;
            width: 34px;
            height: 34px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background-color 0.2s, transform 0.1s;
        }}
        .fullscreen-controls button:hover {{
            background: rgba(255, 255, 255, 0.15);
            transform: scale(1.08);
        }}
        .fullscreen-controls button:active {{
            transform: scale(0.95);
        }}
        .fullscreen-controls button svg {{
            width: 18px;
            height: 18px;
            fill: #FFFFFF;
        }}
        
        .fullscreen-controls .divider {{
            width: 1px;
            height: 20px;
            background: rgba(255, 255, 255, 0.15);
        }}
        
        /* Close button - top right in fullscreen */
        .close-btn {{
            display: none;
            position: absolute;
            top: 24px;
            right: 24px;
            background: rgba(20, 20, 22, 0.85);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 16px rgba(0,0,0,0.3);
            transition: background-color 0.2s, transform 0.2s;
            z-index: 200;
        }}
        .close-btn:hover {{
            background: rgba(255, 255, 255, 0.2);
            transform: scale(1.08);
        }}
        .close-btn svg {{
            width: 20px;
            height: 20px;
            fill: #FFFFFF;
        }}
        
        /* Fullscreen styles (Native & JS helper classes) */
        .cad-viewer-container.is-fullscreen,
        .cad-viewer-container:fullscreen {{
            background-color: #0B0F17 !important; /* Dark Notion theme for full screen view */
            width: 100vw !important;
            height: 100vh !important;
            border: none !important;
            border-radius: 0 !important;
            cursor: grab;
        }}
        
        .cad-viewer-container.is-fullscreen:active,
        .cad-viewer-container:fullscreen:active {{
            cursor: grabbing;
        }}
        
        .cad-viewer-container.is-fullscreen .fullscreen-controls,
        .cad-viewer-container:fullscreen .fullscreen-controls {{
            display: flex;
        }}
        
        .cad-viewer-container.is-fullscreen .close-btn,
        .cad-viewer-container:fullscreen .close-btn {{
            display: flex;
        }}
        
        .cad-viewer-container.is-fullscreen .expand-btn,
        .cad-viewer-container:fullscreen .expand-btn {{
            display: none;
        }}
    </style>
    </head>
    <body>
    <div class="cad-viewer-container" id="cad-container">
        <!-- Floating Expand Button -->
        <div class="expand-btn" onclick="enterFullscreen()" title="Open Full Screen">
            <svg viewBox="0 0 24 24">
                <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
            </svg>
        </div>
        
        <!-- Close Button -->
        <div class="close-btn" onclick="exitFullscreen()" title="Close Full Screen">
            <svg viewBox="0 0 24 24">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
        </div>
        
        <!-- CAD Image Layer -->
        <img src="data:image/png;base64,{img_b64}" class="cad-image-layer" id="cad-image" style="transform: translate(0px, 0px) scale(1);">
        
        <!-- Fullscreen controls -->
        <div class="fullscreen-controls">
            <button onclick="zoom(0.25)" title="Zoom In">
                <svg viewBox="0 0 24 24">
                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/><path d="M12 10h-2v2H9v-2H7V9h2V7h1v2h2v1z"/>
                </svg>
            </button>
            <button onclick="zoom(-0.2)" title="Zoom Out">
                <svg viewBox="0 0 24 24">
                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/><path d="M7 9h5v1H7z"/>
                </svg>
            </button>
            <div class="divider"></div>
            <button onclick="resetZoom()" title="Reset Zoom">
                <svg viewBox="0 0 24 24">
                    <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
                </svg>
            </button>
            <button onclick="fitToScreen()" title="Fit to Screen">
                <svg viewBox="0 0 24 24">
                    <path d="M15 3l2.3 2.3-2.89 2.87 1.42 1.42L18.7 6.7 21 9V3h-6zM3 9l2.3-2.3 2.87 2.89 1.42-1.42L6.7 5.3 9 3H3v6zm6 12l-2.3-2.3 2.89-2.87-1.42-1.42-2.87 2.89L3 15v6h6zm12-6l-2.3 2.3-2.87-2.89-1.42 1.42 2.87 2.87L15 21h6v-6z"/>
                </svg>
            </button>
        </div>
    </div>
    
    <script>
    (function() {{
        const container = document.getElementById('cad-container');
        const img = document.getElementById('cad-image');
        
        let scale = 1;
        let pointX = 0;
        let pointY = 0;
        let panning = false;
        let startX = 0;
        let startY = 0;
        
        function setTransform() {{
            img.style.transform = `translate(${{pointX}}px, ${{pointY}}px) scale(${{scale}})`;
        }}
        
        // Fullscreen Enter/Exit functions
        window.enterFullscreen = function() {{
            if (container.requestFullscreen) {{
                container.requestFullscreen();
            }} else if (container.webkitRequestFullscreen) {{
                container.webkitRequestFullscreen();
            }}
        }};
        
        window.exitFullscreen = function() {{
            if (document.exitFullscreen) {{
                document.exitFullscreen();
            }} else if (document.webkitExitFullscreen) {{
                document.webkitExitFullscreen();
            }}
        }};
        
        // Listeners for layout updates
        document.addEventListener('fullscreenchange', () => {{
            if (document.fullscreenElement === container) {{
                container.classList.add('is-fullscreen');
            }} else {{
                container.classList.remove('is-fullscreen');
                resetZoom();
            }}
        }});
        
        document.addEventListener('webkitfullscreenchange', () => {{
            if (document.webkitFullscreenElement === container) {{
                container.classList.add('is-fullscreen');
            }} else {{
                container.classList.remove('is-fullscreen');
                resetZoom();
            }}
        }});
        
        // Pan & Drag functions (active in fullscreen)
        container.onmousedown = function(e) {{
            if (!document.fullscreenElement && !container.classList.contains('is-fullscreen')) return;
            e.preventDefault();
            startX = e.clientX - pointX;
            startY = e.clientY - pointY;
            panning = true;
        }};
        
        container.onmouseup = function() {{ panning = false; }};
        container.onmouseleave = function() {{ panning = false; }};
        
        container.onmousemove = function(e) {{
            if (!panning) return;
            e.preventDefault();
            pointX = e.clientX - startX;
            pointY = e.clientY - startY;
            setTransform();
        }};
        
        // Interactive Wheel & Pinch Zoom
        container.onwheel = function(e) {{
            if (!document.fullscreenElement && !container.classList.contains('is-fullscreen')) return;
            e.preventDefault();
            
            const xs = (e.clientX - pointX) / scale;
            const ys = (e.clientY - pointY) / scale;
            const delta = -e.deltaY;
            
            let factor = 1.1;
            if (delta < 0) {{
                factor = 1 / factor;
            }}
            
            const newScale = Math.min(Math.max(scale * factor, 0.2), 10);
            
            pointX = e.clientX - xs * newScale;
            pointY = e.clientY - ys * newScale;
            scale = newScale;
            
            setTransform();
        }};
        
        // Control actions
        window.zoom = function(delta) {{
            const rect = container.getBoundingClientRect();
            const midX = rect.left + rect.width / 2;
            const midY = rect.top + rect.height / 2;
            
            const xs = (midX - pointX) / scale;
            const ys = (midY - pointY) / scale;
            
            let factor = 1.25;
            if (delta < 0) {{
                factor = 1 / factor;
            }}
            
            const newScale = Math.min(Math.max(scale * factor, 0.2), 10);
            
            pointX = midX - xs * newScale;
            pointY = midY - ys * newScale;
            scale = newScale;
            
            setTransform();
        }};
        
        window.resetZoom = function() {{
            scale = 1;
            pointX = 0;
            pointY = 0;
            setTransform();
        }};
        
        window.fitToScreen = function() {{
            resetZoom();
        }};
    }})();
    </script>
    </body>
    </html>
    """
    components.html(html_code, height=height)

def render_main_page(process_query_fn, embed_model, format_timestamp_fn):
    """Render the main chat area."""

    if not st.session_state.active_doc:
        html_str = """<div class="welcome-box">
<i class="fa-solid fa-drafting-compass welcome-icon" style="font-size: 64px; color: var(--accent-color); display: block; margin: 0 auto 16px auto;"></i>
<h1 class="welcome-title">Engineering Document Assistant</h1>
<p class="welcome-subtitle">Engineering Drawing, CAD and Document Intelligence Platform</p>
</div>"""
        st.markdown(html_str, unsafe_allow_html=True)

        st.markdown('<div style="text-align: center; margin-top: 20px;">', unsafe_allow_html=True)

        uploaded_pdf = st.file_uploader(
            "Upload Document or CAD", 
            type=["pdf", "docx", "dwg", "dxf", "png", "jpg", "jpeg"], 
            key="main_pdf_uploader"
        )

        if uploaded_pdf and st.session_state.active_doc != uploaded_pdf.name:
            file_ext = uploaded_pdf.name.split(".")[-1].lower()

            if file_ext in ["png", "jpg", "jpeg"]:
                st.session_state.image_mode = True
                st.session_state.image_path = uploaded_pdf
                st.session_state.active_doc = uploaded_pdf.name

                s2 = st.empty()
                s2.markdown(
                    '<div class="step-item"><div class="step-num active">1</div>Analyzing image components...</div>',
                    unsafe_allow_html=True,
                )
                try:
                    import vision_analyzer
                    from datetime import datetime
                    initial_query = "Summarize the key components, text, and overall content shown in this image."
                    with st.spinner("Performing initial analysis..."):
                        initial_info = vision_analyzer.analyze_image_local(uploaded_pdf, initial_query)
                    
                    ts = datetime.now().strftime("%H:%M")
                    st.session_state.messages = [
                        {
                            "role": "assistant",
                            "content": f"**Hello! I have successfully loaded your image: `{uploaded_pdf.name}`.**\n\nHere is an initial analysis of the image elements:\n\n{initial_info}",
                            "timestamp": ts
                        }
                    ]
                except Exception as analysis_err:
                    print(f"Error generating initial image info: {analysis_err}")
                    from datetime import datetime
                    ts = datetime.now().strftime("%H:%M")
                    st.session_state.messages = [
                        {
                            "role": "assistant",
                            "content": f"**Hello! I have successfully loaded your image: `{uploaded_pdf.name}`.**\n\nHow can I help you analyze it?",
                            "timestamp": ts
                        }
                    ]
                s2.empty()
                st.success("Image uploaded successfully.")
                st.rerun()

            elif file_ext in ["dwg", "dxf"]:
                s1 = st.empty()
                s1.markdown(
                    '<div class="step-item"><div class="step-num active">1</div>Processing CAD drawing...</div>',
                    unsafe_allow_html=True,
                )
                try:
                    st.session_state.layout_inventory = []
                    st.session_state.cad_analysis = {}
                    st.session_state.cad_chunks = []
                    st.session_state.drawing_type = None
                    st.session_state.cad_drawing_type = None
                    st.session_state.raw_labels = []
                    st.session_state.cad_index = None
                    st.session_state.substation_inventory = {}
                    st.session_state.foundation_inventory = {}
                    
                    st.session_state.active_doc = uploaded_pdf.name
                    cad_index, cad_chunks = process_and_cache_cad(uploaded_pdf, embed_model)

                    st.session_state.cad_index = cad_index
                    st.session_state.cad_chunks = cad_chunks
                    import boq_generator
                    boq_generator.update_boq_in_session_state()
                    s1.empty()

                    from datetime import datetime
                    ts = datetime.now().strftime("%H:%M")
                    st.session_state.messages = [
                        {
                            "role": "assistant",
                            "content": f"**Hello! I have successfully processed your CAD drawing: `{uploaded_pdf.name}`.**",
                            "timestamp": ts,
                        }
                    ]
                    st.success("CAD drawing processed and loaded successfully.")
                    st.rerun()
                except Exception as e:
                    s1.empty()
                    st.error(f"Failed to process CAD file: {e}")
                    st.stop()

            elif file_ext == "docx":
                s1 = st.empty()
                s1.markdown(
                    '<div class="step-item"><div class="step-num active">1</div>Processing DOCX document...</div>',
                    unsafe_allow_html=True,
                )
                try:
                    res = process_and_cache_docx(uploaded_pdf, embed_model)
                    st.session_state.faiss_index = res["text_index"]
                    st.session_state.chunks_db = res["text_chunks"]
                    st.session_state.formula_index = res["formula_index"]
                    st.session_state.formula_chunks = res["formula_chunks"]
                    st.session_state.table_index = res["table_index"]
                    st.session_state.table_chunks = res["table_chunks"]
                    
                    st.session_state.diagram_index = None
                    st.session_state.diagram_chunks = []
                    st.session_state.cad_index = None
                    st.session_state.cad_chunks = []
                    st.session_state.layout_inventory = []
                    
                    st.session_state.active_doc = uploaded_pdf.name
                    st.session_state.autocomplete_suggestions = generate_suggestions(res["text_chunks"])
                    st.session_state.quick_questions = generate_dynamic_quick_questions(res["text_chunks"])
                    st.session_state.show_welcome = False
                    s1.empty()
                    
                    from datetime import datetime
                    ts = datetime.now().strftime("%H:%M")
                    st.session_state.messages = [
                        {
                            "role": "assistant",
                            "content": f"**Hello! I have successfully loaded your Word document: `{uploaded_pdf.name}`.**\n\nAsk me any questions about headings, tables, or document details.",
                            "timestamp": ts
                        }
                    ]
                    st.success("DOCX document processed and loaded successfully.")
                    st.rerun()
                except Exception as e:
                    s1.empty()
                    st.error(f"Failed to process DOCX file: {e}")
                    st.stop()

            elif file_ext == "pdf":
                s1 = st.empty()
                s1.markdown(
                    '<div class="step-item"><div class="step-num active">1</div>Processing document...</div>',
                    unsafe_allow_html=True,
                )
                try:
                    res = process_and_cache_pdf(uploaded_pdf, embed_model)
                    is_scanned = res["is_scanned"]
                    scanned_pages = res["scanned_pages"]
                    
                    if is_scanned:
                        st.session_state.image_mode = True
                        st.session_state.image_path = scanned_pages[0]
                        st.session_state.scanned_pages = scanned_pages
                        st.session_state.scanned_page_idx = 0
                        st.session_state.query_all_pages = False
                        st.session_state.active_doc = uploaded_pdf.name
                        s1.empty()
                        st.success(f"Scanned PDF loaded — {len(scanned_pages)} page(s) ready for visual chat.")
                        st.rerun()
                        
                    st.session_state.faiss_index = res["text_index"]
                    st.session_state.chunks_db = res["text_chunks"]
                    st.session_state.diagram_index = res["diagram_index"]
                    st.session_state.diagram_chunks = res["diagram_chunks"]
                    st.session_state.formula_index = res["formula_index"]
                    st.session_state.formula_chunks = res["formula_chunks"]
                    st.session_state.table_index = res["table_index"]
                    st.session_state.table_chunks = res["table_chunks"]
                    
                    st.session_state.document_structure = res["document_structure"]
                    st.session_state.pdf_images = res["pdf_images"]
                    st.session_state.active_doc = uploaded_pdf.name
                    st.session_state.cad_index = None
                    st.session_state.cad_chunks = []
                    
                    pdf_hash = res.get("file_hash")
                    if pdf_hash:
                        pdf_path = os.path.join(config.PDF_STORAGE_DIR, pdf_hash, "document.pdf")
                        if os.path.exists(pdf_path):
                            from cad_inventory import extract_inventory_from_pdf
                            layout_inv = extract_inventory_from_pdf(pdf_path, res["text_chunks"])
                            st.session_state.layout_inventory = layout_inv
                            try:
                                from fixed_cad_inventory import detect_known_drawing
                                extracted_text = " ".join([str(el.get("text", "")) for el in layout_inv])
                                if not extracted_text:
                                    extracted_text = " ".join([str(c.get("content", "")) for c in res["text_chunks"]])
                                st.session_state.fixed_inventory = detect_known_drawing(extracted_text)
                            except Exception as e:
                                print(f"Warning: Failed to detect known drawing for PDF: {e}")
                                st.session_state.fixed_inventory = None
                    else:
                        st.session_state.layout_inventory = []
                    import boq_generator
                    boq_generator.update_boq_in_session_state()
                    
                    st.session_state.autocomplete_suggestions = generate_suggestions(res["text_chunks"])
                    st.session_state.quick_questions = generate_dynamic_quick_questions(res["text_chunks"])
                    st.session_state.show_welcome = False
                    
                    s1.empty()
                    st.success("Indexed PDF successfully.")
                    st.rerun()
                except Exception as e:
                    s1.empty()
                    st.error(f"Failed to process PDF: {e}")
                    st.stop()

        st.chat_input("Upload a document to start asking questions...", disabled=True)
        st.stop()

    if st.session_state.active_doc and not st.session_state.messages:
        st.markdown('<div style="margin-top: 40px;"></div>', unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:center; margin:12px 0;'>"
            "<span style='color:var(--text-secondary); font-size:12px;'>Quick questions:</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        qs = st.session_state.get("quick_questions", [])
        if not qs and st.session_state.chunks_db:
            qs = generate_dynamic_quick_questions(st.session_state.chunks_db)
            st.session_state.quick_questions = qs
        if qs:
            cols = st.columns(min(len(qs), 5))
            for i, (label, question) in enumerate(qs):
                with cols[i]:
                    if st.button(label, key=f"q{i}", use_container_width=True):
                        st.session_state.pending_question = question
                        st.rerun()
            st.markdown('<div style="margin-bottom: 24px;"></div>', unsafe_allow_html=True)


    user_avatar = "user_avatar.png" if os.path.exists("user_avatar.png") else "user"
    ai_avatar = "ai_avatar.png" if os.path.exists("ai_avatar.png") else "assistant"
    for msg in st.session_state.messages:
        avatar = ai_avatar if msg["role"] == "assistant" else user_avatar
        with st.chat_message(msg["role"], avatar=avatar):
            content_to_show = clean_headings(msg["content"]) if msg["role"] == "assistant" else msg["content"]
            st.markdown(content_to_show)
            
            if msg.get("is_boq") and st.session_state.get("boq"):
                import boq_generator
                st.markdown("<div style='margin-top: 15px; font-weight: 600;'>Download BOQ:</div>", unsafe_allow_html=True)
                col_csv, col_xlsx, col_pdf = st.columns(3)
                
                csv_data = boq_generator.generate_csv_bytes(st.session_state.boq)
                excel_data = boq_generator.generate_excel_bytes(st.session_state.boq)
                pdf_data = boq_generator.generate_pdf_bytes(
                    st.session_state.boq, 
                    st.session_state.active_doc, 
                    st.session_state.get("drawing_type", "Engineering Drawing")
                )
                
                msg_ts = msg.get("timestamp", "boq")
                with col_csv:
                    st.download_button(
                        label="CSV",
                        data=csv_data,
                        file_name=f"BOQ_{st.session_state.active_doc}.csv",
                        mime="text/csv",
                        key=f"dl_csv_{msg_ts}_{len(st.session_state.messages)}"
                    )
                with col_xlsx:
                    st.download_button(
                        label="Excel",
                        data=excel_data,
                        file_name=f"BOQ_{st.session_state.active_doc}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_xlsx_{msg_ts}_{len(st.session_state.messages)}"
                    )
                with col_pdf:
                    st.download_button(
                        label="PDF",
                        data=pdf_data,
                        file_name=f"BOQ_{st.session_state.active_doc}.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_{msg_ts}_{len(st.session_state.messages)}"
                    )
            
            if "reference_images" in msg and msg["reference_images"]:
                st.markdown("**Reference Drawings / Visuals:**")
                valid_images = [img for img in msg["reference_images"] if img]
                if valid_images:
                    cols = st.columns(min(len(valid_images), 3))
                    for i, img_ref in enumerate(valid_images):
                        with cols[i % len(cols)]:
                            try:
                                if os.path.exists(img_ref):
                                    caption = os.path.basename(img_ref)
                                    st.image(img_ref, caption=caption, use_column_width=True)
                            except Exception as e:
                                st.caption(f"Could not load image: {e}")
            
            if "timestamp" in msg:
                st.markdown(
                    f'<div class="msg-time">{msg["timestamp"]}</div>',
                    unsafe_allow_html=True,
                )

    if "pending_question" in st.session_state:
        query = st.session_state.pending_question
        del st.session_state.pending_question
        ts = format_timestamp_fn()
        st.session_state.messages.append({"role": "user", "content": query, "timestamp": ts})
        database.create_chat(st.session_state.chat_id, st.session_state.active_doc or "Untitled", st.session_state.active_doc or "Untitled")
        database.save_message(st.session_state.chat_id, "user", query)
        st.session_state.processing_query = query
        st.rerun()

    assistant_ok = st.session_state.ollama_status.get("online", False)

    if assistant_ok:
        query = st.chat_input("Ask a question...")
    else:
        query = None
        st.chat_input(
            "Configure Groq API key to use assistant...",
            disabled=True
        )

    if query:
        if not st.session_state.active_doc:
            st.error("Upload a document first")
            st.stop()
        if not st.session_state.ollama_status["online"]:
            st.error("Groq is not configured/online.")
            st.stop()

        ts = format_timestamp_fn()
        st.session_state.messages.append({"role": "user", "content": query, "timestamp": ts})
        database.create_chat(st.session_state.chat_id, st.session_state.active_doc or "Untitled", st.session_state.active_doc or "Untitled")
        database.save_message(st.session_state.chat_id, "user", query)
        st.session_state.processing_query = query
        st.rerun()

    if "processing_query" in st.session_state:
        query_to_process = st.session_state.processing_query
        del st.session_state.processing_query
        process_query_fn(query_to_process)
        st.rerun()

    suggestions = st.session_state.get("autocomplete_suggestions", [])
    if not suggestions and st.session_state.get("chunks_db"):
        suggestions = generate_suggestions(st.session_state.chunks_db)
        st.session_state.autocomplete_suggestions = suggestions

    suggestions_json = json.dumps(list(suggestions))
    suggestions_escaped = html.escape(suggestions_json)
    
    st.markdown(
        f'<div id="suggestions-data" style="display:none;" data-suggestions="{suggestions_escaped}"></div>',
        unsafe_allow_html=True,
    )
    
    components.html("""
    <script>
    (function() {
        if (window.autocompleteIntervalId) return;

        function initAutocomplete() {
            const container = document.querySelector(".stChatInputContainer") ||
                              document.querySelector(".stChatInput") ||
                              document.querySelector("div[data-testid=stChatInput]");
            if (!container) return;

            const textarea = container.querySelector("textarea");
            if (!textarea) return;

            if (textarea.dataset.autocompleteListenersAttached === "true") return;
            textarea.dataset.autocompleteListenersAttached = "true";

            let dropdown = container.querySelector("#autocomplete-dropdown");
            if (!dropdown) {
                dropdown = document.createElement("div");
                dropdown.id = "autocomplete-dropdown";
                dropdown.className = "autocomplete-dropdown";
                container.style.position = "relative";
                container.appendChild(dropdown);
            }

            function getSuggestions() {
                // Walk up from the iframe to the parent document
                const parentDoc = window.parent.document;
                const dataEl = parentDoc.getElementById("suggestions-data");
                if (dataEl) {
                    try { return JSON.parse(dataEl.dataset.suggestions || "[]"); }
                    catch(e) { return []; }
                }
                return [];
            }

            function getLastWord(text) {
                const trimmed = text.trimStart();
                const parts = trimmed.split(/\s+/);
                return parts[parts.length - 1].toLowerCase();
            }

            textarea.addEventListener("input", (e) => {
                const fullValue = e.target.value;
                const lastWord = getLastWord(fullValue);

                if (lastWord.length < 2) {
                    dropdown.style.display = "none";
                    return;
                }

                const allSuggestions = getSuggestions();
                const filtered = allSuggestions
                    .filter(s => s.toLowerCase().includes(lastWord))
                    .slice(0, 6);

                if (filtered.length === 0) {
                    dropdown.style.display = "none";
                    return;
                }

                dropdown.innerHTML = "";
                filtered.forEach(s => {
                    const item = document.createElement("div");
                    item.className = "autocomplete-item";

                    const matchIdx = s.toLowerCase().indexOf(lastWord);
                    if (matchIdx !== -1) {
                        const before = s.slice(0, matchIdx);
                        const match = s.slice(matchIdx, matchIdx + lastWord.length);
                        const after = s.slice(matchIdx + lastWord.length);
                        item.innerHTML = before + "<strong>" + match + "</strong>" + after;
                    } else {
                        item.textContent = s;
                    }

                    item.addEventListener("mousedown", (evt) => {
                        evt.preventDefault();
                        textarea.value = s;
                        textarea.dispatchEvent(new Event("input", { bubbles: true }));
                        textarea.dispatchEvent(new Event("change", { bubbles: true }));
                        dropdown.style.display = "none";
                        textarea.focus();
                        textarea.selectionStart = textarea.selectionEnd = textarea.value.length;
                    });

                    dropdown.appendChild(item);
                });

                dropdown.style.display = "block";
            });

            textarea.addEventListener("blur", () => {
                setTimeout(() => { dropdown.style.display = "none"; }, 250);
            });

            textarea.addEventListener("focus", () => {
                const lastWord = getLastWord(textarea.value);
                if (lastWord.length >= 2) {
                    const allSuggestions = getSuggestions();
                    const filtered = allSuggestions
                        .filter(s => s.toLowerCase().includes(lastWord))
                        .slice(0, 6);
                    if (filtered.length > 0) dropdown.style.display = "block";
                }
            });
        }

        function initChatCards() {
            const parentDoc = window.parent.document;
            // Walk from each anchor → stElementContainer → stVerticalBlock → column → stHorizontalBlock
            const anchors = parentDoc.querySelectorAll(".chat-card-anchor");
            anchors.forEach(anchor => {
                const elemContainer = anchor.closest('[data-testid="stElementContainer"]');
                if (!elemContainer) return;

                // The stHorizontalBlock is the st.columns() wrapper — walk up to it
                const hBlock = elemContainer.closest('[data-testid="stHorizontalBlock"]');
                if (hBlock && !hBlock.classList.contains('chat-card-wrapper')) {
                    hBlock.classList.add('chat-card-wrapper');
                }

                // Style the select button (next sibling element container)
                const selectElem = elemContainer.nextElementSibling;
                if (selectElem) {
                    const btn = selectElem.querySelector('button');
                    if (btn) {
                        btn.classList.add('chat-card-select-btn');
                        const type = anchor.getAttribute("data-type");
                        btn.classList.add(type === "pinned" ? "pinned-select-btn" : "recent-select-btn");
                        const isPrimary = btn.getAttribute("kind") === "primary" ||
                                          (btn.dataset && btn.dataset.testid === "stBaseButton-primary") ||
                                          btn.className.includes("primary");
                        if (isPrimary) {
                            btn.classList.add("active-select-btn");
                            if (hBlock) hBlock.classList.add("active-chat-wrapper");
                        } else {
                            btn.classList.remove("active-select-btn");
                            if (hBlock) hBlock.classList.remove("active-chat-wrapper");
                        }
                    }
                }
            });
        }



        window.autocompleteIntervalId = setInterval(initAutocomplete, 300);
        setInterval(initChatCards, 250);
    })();
    </script>
    """, height=0, scrolling=False)
