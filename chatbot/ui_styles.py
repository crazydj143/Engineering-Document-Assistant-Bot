from fastapi import background
import streamlit as st

def apply_custom_css():
    is_dark = st.session_state.get("dark_mode", False)
    
    if is_dark:
        bg_primary = "#121212"
        bg_secondary = "#1E1E1E"
        sidebar_bg = "#1E1E1E"
        border_color = "#2A2A2A"
        text_primary = "#f5f5f7"
        text_secondary = "#8e8e93"
        user_bubble_bg = "#2c2c2e"
        user_bubble_text = "#f5f5f7"
        assistant_bubble_bg = "transparent"
        assistant_bubble_text = "#f5f5f7"
        assistant_bubble_border = "none"
        assistant_bubble_shadow = "none"
        assistant_bubble_padding = "12px 0"
        assistant_bubble_border_radius = "0"
        input_bg = "#1c1c1e"
        input_border = "#2A2A2A"
        input_text = "#f5f5f7"
        card_bg = "#1E1E1E"
        card_border = "#2A2A2A"
        hover_bg = "#2c2c2e"
        
        green_bg = "rgba(34, 197, 94, 0.1)"
        green_text = "#22C55E"
        red_bg = "rgba(239, 68, 68, 0.1)"
        red_text = "#EF4444"
        yellow_bg = "rgba(245, 158, 11, 0.1)"
        yellow_text = "#F59E0B"
        accent_color = "#3B82F6"
        dashboard_value_color = "var(--text-primary)"
        status_pill_bg = "rgba(255, 255, 255, 0.02)"
        primary_btn_bg = "var(--text-primary)"
        primary_btn_text = "var(--bg-primary)"
        primary_btn_hover = "var(--hover-bg)"
        secondary_btn_hover_bg = "var(--hover-bg)"
        secondary_btn_hover_border = "var(--text-primary)"
        ghost_btn_hover = "#2A2A2A"
        theme_icon_name = "'\\f185'"
    else:
        bg_primary = "#F8FAFC"
        bg_secondary = "#FFFFFF"
        sidebar_bg = "#F5F7FA"
        border_color = "#D1D5DB"
        text_primary = "#111827"
        text_secondary = "#4B5563"
        user_bubble_bg = "#2D7DD2"
        user_bubble_text = "#FFFFFF"
        assistant_bubble_bg = "#FFFFFF"
        assistant_bubble_text = "#111827"
        assistant_bubble_border = "1px solid #D1D5DB"
        assistant_bubble_shadow = "0 2px 8px rgba(0, 0, 0, 0.04)"
        assistant_bubble_padding = "12px 18px"
        assistant_bubble_border_radius = "12px"
        input_bg = "#FFFFFF"
        input_border = "#D1D5DB"
        input_text = "#111827"
        card_bg = "#FFFFFF"
        card_border = "#D1D5DB"
        hover_bg = "#EAF3FF"
        
        green_bg = "rgba(34, 197, 94, 0.08)"
        green_text = "#22C55E"
        red_bg = "rgba(239, 68, 68, 0.08)"
        red_text = "#EF4444"
        yellow_bg = "rgba(245, 158, 11, 0.08)"
        yellow_text = "#F59E0B"
        accent_color = "#2D7DD2"
        dashboard_value_color = "#2D7DD2"
        status_pill_bg = "#FFFFFF"
        primary_btn_bg = "#2D7DD2"
        primary_btn_text = "#FFFFFF"
        primary_btn_hover = "#2368B2"
        secondary_btn_hover_bg = "#EAF3FF"
        secondary_btn_hover_border = "#2D7DD2"
        ghost_btn_hover = "#E5E7EB"
        theme_icon_name = "'\\f186'"

    theme_css = f"""
        :root {{
            --bg-primary: {bg_primary};
            --bg-secondary: {bg_secondary};
            --sidebar-bg: {sidebar_bg};
            --border-color: {border_color};
            --text-primary: {text_primary};
            --text-secondary: {text_secondary};
            --user-bubble-bg: {user_bubble_bg};
            --user-bubble-text: {user_bubble_text};
            --assistant-bubble-bg: {assistant_bubble_bg};
            --assistant-bubble-text: {assistant_bubble_text};
            --assistant-bubble-border: {assistant_bubble_border};
            --assistant-bubble-shadow: {assistant_bubble_shadow};
            --assistant-bubble-padding: {assistant_bubble_padding};
            --assistant-bubble-border-radius: {assistant_bubble_border_radius};
            --input-bg: {input_bg};
            --input-border: {input_border};
            --input-text: {input_text};
            --card-bg: {card_bg};
            --card-border: {card_border};
            --hover-bg: {hover_bg};
            --green-bg: {green_bg};
            --green-text: {green_text};
            --red-bg: {red_bg};
            --red-text: {red_text};
            --yellow-bg: {yellow_bg};
            --yellow-text: {yellow_text};
            --accent-color: {accent_color};
            --dashboard-value-color: {dashboard_value_color};
            --status-pill-bg: {status_pill_bg};
            --primary-btn-bg: {primary_btn_bg};
            --primary-btn-text: {primary_btn_text};
            --primary-btn-hover: {primary_btn_hover};
            --secondary-btn-hover-bg: {secondary_btn_hover_bg};
            --secondary-btn-hover-border: {secondary_btn_hover_border};
            --theme-icon-name: {theme_icon_name};
            --ghost-btn-hover: {ghost_btn_hover};
        }}
    """

    st.markdown(f"""
        <style>
            @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');
            @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Roboto:wght@400;500&display=swap');
            
            {theme_css}
            
            /* Clean base - Enterprise style */
            .stApp {{
                background-color: var(--bg-primary) !important;
                color: var(--text-primary) !important;
                font-family: 'Inter', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
            }}
            
            .enterprise-icon {{
                margin-right: 8px;
                font-size: 16px !important;
                color: var(--text-secondary);
                vertical-align: middle;
                display: inline-block;
            }}

            /* Center content and restrict max-width */
            .main .block-container {{
                max-width: 800px !important;
                padding-top: 2rem !important;
                padding-bottom: 2rem !important;
                margin: 0 auto !important;
            }}

            /* Hide Streamlit branding */
            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            header {{visibility: hidden;}}

            /* Scrollbar */
            ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
            ::-webkit-scrollbar-track {{ background: transparent; }}
            ::-webkit-scrollbar-thumb {{ background: var(--border-color); border-radius: 4px; }}
            ::-webkit-scrollbar-thumb:hover {{ background: var(--text-secondary); }}

            /* Chat messages */
            .stChatMessage {{
                background-color: transparent !important;
                border: none !important;
                padding: 1rem 0 !important;
            }}

            /* Align user message right */
            [data-testid="stChatMessageUser"] {{
                flex-direction: row-reverse !important;
            }}

            /* User bubble */
            [data-testid="stChatMessageUser"] > div > div {{
                background-color: var(--user-bubble-bg) !important;
                color: var(--user-bubble-text) !important;
                border-radius: 18px !important;
                padding: 12px 18px !important;
                max-width: 70% !important;
                font-size: 15px !important;
                line-height: 1.5 !important;
                border: 1px solid var(--border-color) !important;
                box-shadow: none !important;
            }}

            /* Assistant bubble */
            [data-testid="stChatMessageAssistant"] > div > div {{
                background-color: var(--assistant-bubble-bg) !important;
                color: var(--assistant-bubble-text) !important;
                border: var(--assistant-bubble-border) !important;
                box-shadow: var(--assistant-bubble-shadow) !important;
                padding: var(--assistant-bubble-padding) !important;
                border-radius: var(--assistant-bubble-border-radius) !important;
                max-width: 85% !important;
                font-size: 15px !important;
                line-height: 1.6 !important;
            }}

            /* Avatars */
            [data-testid="stChatMessageAvatar"] {{
                background-color: var(--bg-secondary) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 50% !important;
                width: 32px !important;
                height: 32px !important;
            }}
            [data-testid="stChatMessageUser"] [data-testid="stChatMessageAvatar"] {{
                margin-left: 12px !important;
                margin-right: 0 !important;
            }}
            [data-testid="stChatMessageAssistant"] [data-testid="stChatMessageAvatar"] {{
                margin-right: 12px !important;
                margin-left: 0 !important;
            }}

            /* Chat input container */
            .stChatInputContainer {{
                background-color: var(--input-bg) !important;
                border: 1px solid var(--input-border) !important;
                border-radius: 12px !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03) !important;
            }}
            
            /* Fix: Chat input cursor/vertical line visible */
            .stChatInputContainer textarea,
            .stChatInput textarea,
            div[data-testid="stChatInput"] textarea,
            textarea[data-testid="stChatInputTextArea"],
            [data-testid="stChatInputContainer"] textarea,
            .stApp textarea {{
                caret-color: var(--text-primary) !important;
                color: var(--text-primary) !important;
            }}
            .stChatInputContainer textarea::placeholder,
            .stChatInput textarea::placeholder,
            div[data-testid="stChatInput"] textarea::placeholder,
            textarea[data-testid="stChatInputTextArea"]::placeholder,
            [data-testid="stChatInputContainer"] textarea::placeholder {{
                color: var(--text-secondary) !important;
            }}
            /* Force the bottom input area border visible */
            div[data-testid="stBottom"] {{
                border-top: 1px solid var(--border-color) !important;
                background-color: var(--bg-primary) !important;
            }}
            
            section[data-testid="stSidebar"] {{
                background-color: var(--sidebar-bg) !important;
                border-right: 1px solid var(--border-color) !important;
                transition: transform 0.3s ease !important;
            }}

            /* Style the sidebar drag handle resizer */
            section[data-testid="stSidebar"] + div {{
                cursor: col-resize !important;
                width: 6px !important;
                background-color: transparent !important;
                transition: background-color 0.2s ease !important;
            }}
            section[data-testid="stSidebar"] + div:hover {{
                background-color: var(--accent-color) !important;
            }}

            /* Custom Status Pill */
            .status-pill {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
                margin-bottom: 8px;
                border: 1px solid var(--border-color);
                background-color: var(--status-pill-bg) !important;
            }}
            .status-dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                display: inline-block;
            }}

            /* Cards style */
            .simple-card {{
                background-color: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 10px;
                padding: 16px;
                margin: 12px 0;
                transition: border-color 0.2s, background-color 0.2s;
            }}
            .simple-card:hover {{
                border-color: var(--text-secondary);
                background-color: var(--hover-bg);
            }}

            /* Accuracy Widget */
            .accuracy-container {{
                background-color: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 10px;
                padding: 16px;
                margin: 12px 0;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
            }}
            .accuracy-value-row {{
                display: flex;
                align-items: baseline;
                justify-content: space-between;
                margin-bottom: 6px;
            }}
            .accuracy-value {{
                font-size: 24px;
                font-weight: 700;
                color: var(--text-primary);
            }}
            .accuracy-label {{
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }}
            .accuracy-bar-bg {{
                background-color: var(--border-color);
                height: 6px;
                border-radius: 3px;
                overflow: hidden;
                width: 100%;
                margin-bottom: 8px;
            }}
            .accuracy-bar-fill {{
                height: 100%;
                border-radius: 3px;
                transition: width 0.8s cubic-bezier(0.1, 0.8, 0.2, 1);
            }}
            .accuracy-description {{
                font-size: 11px;
                color: var(--text-secondary);
                line-height: 1.4;
            }}

            /* Timestamp */
            .msg-time {{
                font-size: 11px;
                color: var(--text-secondary);
                margin-top: 6px;
            }}

            /* Typing dots */
            .typing-dots {{
                display: flex;
                gap: 5px;
                padding: 10px 0;
            }}
            .typing-dots span {{
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background-color: var(--text-secondary);
                animation: bounce 1.4s infinite ease-in-out both;
            }}
            .typing-dots span:nth-child(1) {{ animation-delay: -0.32s; }}
            .typing-dots span:nth-child(2) {{ animation-delay: -0.16s; }}
            @keyframes bounce {{
                0%, 80%, 100% {{ transform: scale(0); opacity: 0.4; }}
                40% {{ transform: scale(1.0); opacity: 1; }}
            }}

            /* Source box */
            .source-box {{
                background-color: var(--bg-secondary);
                border-radius: 8px;
                padding: 10px 14px;
                margin: 8px 0;
                font-size: 13px;
                color: var(--text-primary);
                border: 1px solid var(--border-color);
                border-left: 3px solid var(--text-secondary);
            }}

            /* Title block */
            .app-title {{
                text-align: center;
                padding: 24px 0;
                border-bottom: 1px solid var(--border-color);
                margin-bottom: 24px;
            }}
            .app-title h1 {{
                font-size: 24px;
                font-weight: 700;
                color: var(--text-primary);
                margin: 0;
                letter-spacing: -0.5px;
            }}
            .app-title p {{
                font-size: 14px;
                color: var(--text-secondary);
                margin: 6px 0 0 0;
            }}

            /* Welcome container */
            .welcome-box {{
                background-color: var(--bg-primary);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 24px;
                text-align: center;
                max-width: 600px;
                margin: 40px auto;
            }}
            .welcome-box h2 {{
                font-size: 20px;
                font-weight: 600;
                color: var(--text-primary);
                margin-bottom: 12px;
            }}
            .welcome-box p {{
                font-size: 14px;
                color: var(--text-secondary);
                line-height: 1.6;
                margin: 0;
            }}

            /* Step processing indicator */
            .step-item {{
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 6px 0;
                font-size: 13px;
                color: var(--text-secondary);
            }}
            .step-item.done {{ color: var(--text-primary); }}
            .step-num {{
                width: 20px;
                height: 20px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 11px;
                font-weight: 600;
                background-color: var(--bg-secondary);
                color: var(--text-secondary);
                border: 1px solid var(--border-color);
            }}
            .step-num.done {{
                background-color: var(--text-primary);
                color: var(--bg-primary);
                border-color: var(--text-primary);
            }}
            .step-num.active {{
                border-color: var(--text-primary);
                color: var(--text-primary);
            }}

            /* Quick action buttons style */
            .quick-btn {{
                background-color: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                color: var(--text-primary);
                cursor: pointer;
                transition: all 0.2s ease;
                text-align: center;
                width: 100%;
            }}
            .quick-btn:hover {{
                border-color: var(--text-primary);
                background-color: var(--hover-bg);
            }}
            
            /* Force general button text colors */
            .stButton > button, 
            .stButton > button * {{
                color: var(--text-primary) !important;
            }}

            /* Style primary buttons cleanly */
            .stApp .stButton > button[kind="primary"],
            .stApp .stButton > button[data-testid="stBaseButton-primary"],
            section[data-testid="stSidebar"] .stButton > button[kind="primary"],
            section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] {{
                background-color: var(--primary-btn-bg) !important;
                border: 1px solid var(--primary-btn-bg) !important;
                border-radius: 8px !important;
                text-align: center !important;
                justify-content: center !important;
            }}
            .stApp .stButton > button[kind="primary"] *,
            .stApp .stButton > button[data-testid="stBaseButton-primary"] *,
            section[data-testid="stSidebar"] .stButton > button[kind="primary"] *,
            section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"] * {{
                color: var(--primary-btn-text) !important;
            }}
            .stApp .stButton > button[kind="primary"]:hover,
            .stApp .stButton > button[data-testid="stBaseButton-primary"]:hover,
            section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover,
            section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"]:hover {{
                background-color: var(--primary-btn-hover) !important;
                border-color: var(--primary-btn-hover) !important;
            }}
            .stApp .stButton > button[kind="primary"]:hover *,
            .stApp .stButton > button[data-testid="stBaseButton-primary"]:hover *,
            section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover *,
            section[data-testid="stSidebar"] .stButton > button[data-testid="stBaseButton-primary"]:hover * {{
                color: var(--primary-btn-text) !important;
            }}

            /* Style download buttons matching the accent theme color */
            .stDownloadButton > button {{
                background-color: var(--accent-color) !important;
                color: #FFFFFF !important;
                border: 1px solid var(--accent-color) !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                font-size: 12px !important;
                padding: 6px 2px !important;
                width: 100% !important;
                text-align: center !important;
                justify-content: center !important;
                white-space: nowrap !important;
                overflow: visible !important;
                transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.1s ease !important;
            }}
            .stDownloadButton > button:hover {{
                background-color: var(--accent-color) !important;
                border-color: var(--accent-color) !important;
                color: #FFFFFF !important;
                filter: brightness(0.9) !important;
            }}
            .stDownloadButton > button:active {{
                transform: scale(0.98) !important;
            }}
            .stDownloadButton > button * {{
                color: #FFFFFF !important;
                white-space: nowrap !important;
                font-size: 12px !important;
            }}

            /* Style selectbox controls (choose format bar) and dropdown popup menus */
            div[data-baseweb="select"] {{
                background-color: var(--bg-secondary) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 8px !important;
            }}
            div[data-baseweb="select"] > div {{
                background-color: transparent !important;
                color: var(--text-primary) !important;
            }}
            div[data-baseweb="select"] span,
            div[data-baseweb="select"] div {{
                color: var(--text-primary) !important;
            }}
            
            div[role="listbox"],
            ul[role="listbox"],
            div[data-baseweb="popover"],
            div[data-baseweb="menu"] {{
                background-color: var(--bg-secondary) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 8px !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
            }}
            div[data-baseweb="popover"] ul,
            div[data-baseweb="popover"] li,
            div[data-baseweb="popover"] li * {{
                background-color: var(--bg-secondary) !important;
                color: var(--text-primary) !important;
            }}
            div[data-baseweb="popover"] li:hover,
            div[data-baseweb="popover"] li:hover *,
            div[data-baseweb="popover"] li[aria-selected="true"],
            div[data-baseweb="popover"] li[aria-selected="true"] * {{
                background-color: var(--hover-bg) !important;
                color: var(--text-primary) !important;
            }}

            /* Style regular buttons cleanly (e.g. quick questions, clear button) */
            .stApp .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) {{
                background-color: var(--card-bg) !important;
                border: 1px solid var(--card-border) !important;
                border-radius: 8px !important;
                text-align: center !important;
                justify-content: center !important;
                
                /* Alignment & wrapping fixes for quick questions */
                height: auto !important;
                min-height: 52px !important;
                padding: 10px 14px !important;
                white-space: normal !important;
                word-break: break-word !important;
                line-height: 1.4 !important;
                display: inline-flex !important;
                align-items: center !important;
            }}
            .stApp .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) * {{
                color: var(--text-primary) !important;
                white-space: normal !important;
                line-height: 1.4 !important;
                font-size: 13px !important;
            }}
            .stApp .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]):hover {{
                background-color: var(--secondary-btn-hover-bg) !important;
                border-color: var(--secondary-btn-hover-border) !important;
            }}

            /* Style sidebar secondary buttons to look like ChatGPT navigation links */
            section[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) {{
                background-color: transparent !important;
                border: none !important;
                border-radius: 6px !important;
                text-align: left !important;
                justify-content: flex-start !important;
                padding: 8px 12px !important;
                font-size: 14px !important;
                transition: background-color 0.15s ease !important;
            }}
            section[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) * {{
                color: var(--text-primary) !important;
            }}
            section[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]):hover {{
                background-color: var(--hover-bg) !important;
            }}

            [data-testid="stFileUploader"] {{
                background-color: var(--bg-secondary) !important;
                border: 1px dashed var(--border-color) !important;
                border-radius: 8px !important;
                padding: 10px !important;
            }}
            [data-testid="stFileUploader"] section {{
                background-color: transparent !important;
            }}

            [data-testid="stExpander"] {{
                background-color: var(--bg-secondary) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 8px !important;
                box-shadow: none !important;
            }}

            /* Force text and label colors to follow theme variables */
            .stApp [data-testid="stWidgetLabel"] p,
            .stApp [data-testid="stWidgetLabel"] span {{
                color: var(--text-primary) !important;
            }}
            .stApp [data-testid="stMarkdownContainer"] p,
            .stApp [data-testid="stMarkdownContainer"] span,
            .stApp [data-testid="stMarkdownContainer"] li {{
                color: var(--text-primary) !important;
            }}
            .stApp .stMarkdown p {{
                color: var(--text-primary) !important;
            }}
            
            /* Expander headers styling */
            .stApp [data-testid="stExpander"] details summary,
            .stApp [data-testid="stExpander"] details summary * {{
                color: var(--text-primary) !important;
            }}
            
            .stApp [data-testid="stExpander"] p,
            .stApp [data-testid="stExpander"] span {{
                color: var(--text-primary) !important;
            }}

            /* Sidebar specific overrides to prevent default white-on-white */
            section[data-testid="stSidebar"] label,
            section[data-testid="stSidebar"] .stMarkdown p,
            section[data-testid="stSidebar"] h1,
            section[data-testid="stSidebar"] h2,
            section[data-testid="stSidebar"] h3 {{
                color: var(--text-primary) !important;
            }}
            
            /* File uploader container text overrides */
            [data-testid="stFileUploader"] {{
                color: var(--text-primary) !important;
            }}
            [data-testid="stFileUploader"] label, 
            [data-testid="stFileUploader"] p, 
            [data-testid="stFileUploader"] span, 
            [data-testid="stFileUploader"] div {{
                color: var(--text-primary) !important;
            }}

            /* Text input fields styling */
            .stApp input, .stApp textarea {{
                color: var(--text-primary) !important;
                background-color: var(--input-bg) !important;
                caret-color: var(--text-primary) !important;
            }}

            /* Force the bottom pinned container to have transparent/theme background */
            div[data-testid="stBottom"], 
            div[data-testid="stBottom"] > div,
            .stChatInput,
            div[data-testid="stChatInput"] {{
                background-color: var(--bg-primary) !important;
            }}
            div[data-testid="stBottom"] {{
                border-top: 1px solid var(--border-color) !important;
            }}

            /* Status overrides at the bottom for maximum specificity */
            .stApp .status-pill.status-green,
            .stApp .status-pill.status-green span,
            .stApp .status-pill.status-green div {{
                color: var(--green-text) !important;
            }}
            .stApp .status-pill.status-red,
            .stApp .status-pill.status-red span,
            .stApp .status-pill.status-red div {{
                color: var(--red-text) !important;
            }}
            .stApp .status-pill.status-yellow,
            .stApp .status-pill.status-yellow span,
            .stApp .status-pill.status-yellow div {{
                color: var(--yellow-text) !important;
            }}

            /* Smooth transitions for theme switching */
            .stApp, section[data-testid="stSidebar"], .simple-card, .status-pill, .stChatInputContainer {{
                transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
            }}

            /* Nuclear override: force ALL small text, helper text, captions to follow theme */
            .stApp small,
            .stApp [data-testid="stFileUploaderDropzoneInstructions"] *,
            .stApp [data-testid="stFileUploaderDropzone"] *,
            .stApp .uploadedFileName,
            .stApp [data-testid="stFileUploader"] small,
            .stApp [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"],
            .stApp [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] *,
            .stApp .stFileUploader label + div small,
            .stApp .stFileUploader label + div span {{
                color: var(--text-secondary) !important;
            }}

            /* Force sidebar background on all child containers */
            section[data-testid="stSidebar"] > div,
            section[data-testid="stSidebar"] > div > div,
            section[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
            section[data-testid="stSidebar"] [data-testid="stExpander"] {{
                background-color: var(--sidebar-bg) !important;
            }}

            /* Make sure slider and all form elements are visible */
            .stApp .stSlider label,
            .stApp .stSlider p,
            .stApp .stSlider span,
            .stApp [data-testid="stThumbValue"],
            .stApp [data-testid="stTickBarMin"],
            .stApp [data-testid="stTickBarMax"] {{
                color: var(--text-primary) !important;
            }}

            /* Override Streamlit default dark-on-dark for Browse files button */
            .stApp [data-testid="stFileUploaderDropzone"] button {{
                background-color: var(--bg-primary) !important;
                color: var(--text-primary) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 6px !important;
            }}
            .stApp [data-testid="stFileUploaderDropzone"] button * {{
                color: var(--text-primary) !important;
            }}
            .stApp [data-testid="stFileUploaderDropzone"] button:hover {{
                background-color: var(--hover-bg) !important;
                border-color: var(--text-primary) !important;
            }}

            /* Sidebar base text styling */
            section[data-testid="stSidebar"] {{
                color: var(--text-primary) !important;
            }}

            section[data-testid="stSidebar"] .stAlert {{
                background-color: var(--card-bg) !important;
                border: 1px solid var(--border-color) !important;
            }}
            section[data-testid="stSidebar"] .stAlert p,
            section[data-testid="stSidebar"] .stAlert span,
            section[data-testid="stSidebar"] .stAlert div {{
                color: var(--text-primary) !important;
            }}
            section[data-testid="stSidebar"] [data-testid="stToggle"] button {{
                background-color: var(--hover-bg) !important;
                border: 2px solid var(--text-secondary) !important;
            }}
            section[data-testid="stSidebar"] [data-testid="stToggle"] button[aria-checked="true"] {{
                background-color: var(--text-primary) !important;
                border-color: var(--text-primary) !important;
            }}
            section[data-testid="stSidebar"] [data-testid="stToggle"] button div {{
                background-color: var(--text-primary) !important;
            }}
            section[data-testid="stSidebar"] [data-testid="stToggle"] button[aria-checked="true"] div {{
                background-color: var(--bg-secondary) !important;
            }}

            /* ======================================================== */
            /* DOCUMENT INTELLIGENCE PANEL & DEMO DASHBOARD             */
            /* ======================================================== */
            
            /* Redesigned Dashboard Cards */
            .dashboard-card {{
                background-color: var(--card-bg) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 12px !important;
                padding: 18px !important;
                margin-bottom: 16px !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
                transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease !important;
            }}
            .dashboard-card:hover {{
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
                border-color: var(--accent-color) !important;
            }}
            
            .dashboard-card-title {{
                font-size: 11px !important;
                font-weight: 600 !important;
                color: var(--text-secondary) !important;
                text-transform: uppercase !important;
                letter-spacing: 0.5px !important;
                margin-bottom: 6px !important;
                display: flex !important;
                align-items: center !important;
                gap: 6px !important;
            }}
            .dashboard-card-value {{
                font-size: 28px !important;
                font-weight: 700 !important;
                color: var(--text-primary) !important;
                line-height: 1.2 !important;
            }}
            .dashboard-card-subtitle {{
                font-size: 11px !important;
                color: var(--text-secondary) !important;
                margin-top: 4px !important;
            }}
            .dashboard-trend-positive {{
                color: var(--green-text) !important;
                font-size: 11px !important;
                font-weight: 600 !important;
                display: inline-flex !important;
                align-items: center !important;
                gap: 2px !important;
            }}
            .dashboard-trend-neutral {{
                color: var(--text-secondary) !important;
                font-size: 11px !important;
                font-weight: 500 !important;
                display: inline-flex !important;
                align-items: center !important;
                gap: 2px !important;
            }}

            /* Component statistics */
            .comp-stat-grid {{
                display: grid !important;
                grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)) !important;
                gap: 12px !important;
                width: 100% !important;
                margin-top: 8px !important;
            }}
            .comp-stat-card {{
                background: var(--bg-primary) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 8px !important;
                padding: 12px !important;
                display: flex !important;
                align-items: center !important;
                gap: 10px !important;
                transition: border-color 0.15s ease, background 0.15s ease !important;
            }}
            .comp-stat-card:hover {{
                border-color: var(--accent-color) !important;
                background: var(--hover-bg) !important;
            }}
            .comp-stat-icon-wrapper {{
                background: rgba(59, 130, 246, 0.08) !important;
                border-radius: 6px !important;
                width: 32px !important;
                height: 32px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                color: var(--accent-color) !important;
                flex-shrink: 0 !important;
            }}
            .comp-stat-info {{
                display: flex !important;
                flex-direction: column !important;
                overflow: hidden !important;
            }}
            .comp-stat-count {{
                font-size: 16px !important;
                font-weight: 700 !important;
                color: var(--text-primary) !important;
                line-height: 1.1 !important;
            }}
            .comp-stat-label {{
                font-size: 11px !important;
                color: var(--text-secondary) !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }}

            /* Vertical Timeline Feed */
            .timeline-container {{
                position: relative !important;
                padding-left: 20px !important;
                margin: 10px 0 !important;
                border-left: 2px solid var(--border-color) !important;
            }}
            .timeline-item {{
                position: relative !important;
                margin-bottom: 20px !important;
            }}
            .timeline-item:last-child {{
                margin-bottom: 0 !important;
            }}
            .timeline-badge {{
                position: absolute !important;
                left: -27px !important;
                top: 2px !important;
                width: 12px !important;
                height: 12px !important;
                border-radius: 50% !important;
                background: var(--border-color) !important;
                border: 2px solid var(--card-bg) !important;
                z-index: 2 !important;
                transition: background 0.2s ease !important;
            }}
            .timeline-badge.active {{
                background: var(--accent-color) !important;
            }}
            .timeline-badge.success {{
                background: var(--green-text) !important;
            }}
            .timeline-badge.warning {{
                background: var(--yellow-text) !important;
            }}
            .timeline-content {{
                display: flex !important;
                flex-direction: column !important;
                gap: 2px !important;
            }}
            .timeline-header {{
                display: flex !important;
                align-items: center;
                justify-content: space-between;
                gap: 8px !important;
            }}
            .timeline-title {{
                font-size: 12px !important;
                font-weight: 600 !important;
                color: var(--text-primary) !important;
            }}
            .timeline-time {{
                font-size: 11px !important;
                color: var(--text-secondary) !important;
            }}
            .timeline-desc {{
                font-size: 11px !important;
                color: var(--text-secondary) !important;
                line-height: 1.4 !important;
            }}

            /* Document Insight Cards */
            .top-docs-grid {{
                display: flex !important;
                flex-direction: column !important;
                gap: 10px !important;
                width: 100% !important;
                margin-top: 8px !important;
            }}
            .top-doc-card {{
                background: var(--bg-primary) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 8px !important;
                padding: 12px !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                transition: border-color 0.15s ease, background 0.15s ease !important;
            }}
            .top-doc-card:hover {{
                border-color: var(--accent-color) !important;
                background: var(--hover-bg) !important;
            }}
            .top-doc-info {{
                display: flex !important;
                flex-direction: column !important;
                gap: 2px !important;
                overflow: hidden !important;
            }}
            .top-doc-name {{
                font-size: 13px !important;
                font-weight: 600 !important;
                color: var(--text-primary) !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }}
            .top-doc-meta {{
                font-size: 11px !important;
                color: var(--text-secondary) !important;
            }}
            .top-doc-stats {{
                display: flex !important;
                flex-direction: column !important;
                align-items: flex-end !important;
                flex-shrink: 0 !important;
            }}
            .top-doc-badge {{
                font-size: 11px !important;
                font-weight: 600 !important;
                padding: 2px 6px !important;
                border-radius: 4px !important;
                background: rgba(59, 130, 246, 0.08) !important;
                color: var(--accent-color) !important;
            }}

            /* Q&A Cards */
            .qa-list {{
                display: flex !important;
                flex-direction: column !important;
                gap: 10px !important;
                width: 100% !important;
                margin-top: 8px !important;
            }}
            .qa-item-card {{
                background: var(--bg-primary) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 8px !important;
                padding: 12px !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                gap: 12px !important;
                transition: border-color 0.15s ease, background 0.15s ease !important;
            }}
            .qa-item-card:hover {{
                border-color: var(--accent-color) !important;
                background: var(--hover-bg) !important;
            }}
            .qa-item-body {{
                display: flex !important;
                flex-direction: column !important;
                gap: 2px !important;
                overflow: hidden !important;
            }}
            .qa-item-question {{
                font-size: 13px !important;
                font-weight: 500 !important;
                color: var(--text-primary) !important;
                line-height: 1.4 !important;
            }}
            .qa-item-category {{
                font-size: 10px !important;
                font-weight: 600 !important;
                text-transform: uppercase !important;
                color: var(--accent-color) !important;
            }}
            .qa-item-right {{
                display: flex !important;
                align-items: center !important;
                gap: 10px !important;
                flex-shrink: 0 !important;
            }}
            .qa-item-count-badge {{
                font-size: 11px !important;
                font-weight: 700 !important;
                background: var(--border-color) !important;
                color: var(--text-primary) !important;
                border-radius: 12px !important;
                padding: 2px 8px !important;
                min-width: 28px !important;
                text-align: center !important;
            }}
            
            .query-intelligence-panel {{
                background-color: var(--bg-secondary);
                border-left: 3px solid var(--accent-color);
                padding: 12px 16px;
                margin-top: 8px;
                margin-bottom: 16px;
                border-radius: 0 6px 6px 0;
                font-family: monospace;
                font-size: 13px;
                color: var(--text-primary);
            }}
            
            .query-intelligence-panel strong {{
                color: var(--text-secondary);
            }}

            .demo-mode-header {{
                font-size: 14px;
                font-weight: 600;
                color: var(--accent-color);
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 8px;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            /* ======================================================== */
            /* ANIMATIONS AND STATUS EFFECTS                            */
            /* ======================================================== */
            
            @keyframes fadeInOut {{
                0% {{ opacity: 0.3; }}
                50% {{ opacity: 1; }}
                100% {{ opacity: 0.3; }}
            }}
            .status-animation {{
                animation: fadeInOut 2s infinite ease-in-out;
                color: var(--text-secondary);
                font-size: 13px;
                font-weight: 500;
                margin-top: 8px;
            }}
            
            @keyframes pulseIndicator {{
                0% {{ box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4); }}
                70% {{ box-shadow: 0 0 0 6px rgba(34, 197, 94, 0); }}
                100% {{ box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }}
            }}
            .status-dot.active {{
                animation: pulseIndicator 2s infinite;
            }}
            
            /* CAD Viewer Container */
            .cad-viewer-container {{
                position: relative;
                width: 100%;
                height: 500px;
                overflow: hidden;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                background-color: var(--bg-secondary);
                cursor: grab;
            }}
            .cad-viewer-container:active {{
                cursor: grabbing;
            }}
            .cad-image-layer {{
                width: 100%;
                height: 100%;
                object-fit: contain;
                transform-origin: center;
                transition: transform 0.1s ease-out;
            }}
            .cad-controls {{
                position: absolute;
                bottom: 16px;
                right: 16px;
                display: flex;
                gap: 8px;
                background: var(--card-bg);
                padding: 4px;
                border-radius: 6px;
                border: 1px solid var(--border-color);
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            .cad-controls button {{
                background: transparent;
                border: none;
                color: var(--text-primary);
                width: 32px;
                height: 32px;
                border-radius: 4px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .cad-controls button:hover {{
                background: var(--hover-bg);
            }}
            


            /* Completely hide the hidden theme trigger button */
            .st-key-_theme_trigger_hidden {{
                display: none !important;
            }}


            /* Reduce sidebar width slightly and adjust main content spacing */
            section[data-testid="stSidebar"] {{
                width: 300px !important;
                min-width: 300px !important;
                max-width: 300px !important;
            }}
            @media (min-width: 576px) {{
                .stApp [data-testid="stSidebarCollapsedControl"] {{
                    left: 300px !important;
                }}
            }}
            /* Remove excessive sidebar spacing */
            section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
                gap: 0.6rem !important;
                padding-top: 0.8rem !important;
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
            }}
            section[data-testid="stSidebar"] hr {{
                margin: 6px 0 !important;
            }}

            /* ---------------------------------------------------------- */
            /* INDIVIDUAL CHAT CARD BOX (wrapper around each history item) */
            /* ---------------------------------------------------------- */
            .chat-card-wrapper {{
                border: 1px solid var(--border-color) !important;
                border-radius: 10px !important;
                margin: 0 0 8px 0 !important;
                padding: 0 !important;
                background: var(--card-bg) !important;
                overflow: hidden !important;
                transition: border-color 0.15s ease, background 0.15s ease !important;
            }}
            .chat-card-wrapper:hover {{
                border-color: var(--text-secondary) !important;
            }}
            /* Active chat card - accent left border */
            .chat-card-wrapper.active-chat-wrapper {{
                border-left: 3px solid var(--accent-color) !important;
            }}

            /* Title select button inside card - borderless, transparent */
            .chat-card-select-btn {{
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                border-radius: 0 !important;
                padding: 16px 16px 6px 16px !important;
                width: 100% !important;
                text-align: left !important;
                justify-content: flex-start !important;
                height: auto !important;
                min-height: 0 !important;
                transition: background 0.15s ease !important;
            }}
            .chat-card-select-btn:hover {{
                background: var(--hover-bg) !important;
            }}
            /* Selected chat: accent color text, subtle left indicator */
            .stApp section[data-testid="stSidebar"] .active-select-btn {{
                background: transparent !important;
                border: none !important;
            }}

            /* Text wrapping for chat titles inside select buttons */
            .chat-card-select-btn * {{
                white-space: normal !important;
                word-break: break-word !important;
                overflow-wrap: break-word !important;
                display: -webkit-box !important;
                -webkit-line-clamp: 2 !important;
                -webkit-box-orient: vertical !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                text-align: left !important;
                line-height: 1.6 !important;
                font-weight: 500 !important;
                font-size: 17px !important;
                color: var(--text-primary) !important;
                text-transform: none !important;
                letter-spacing: normal !important;
            }}
            .stApp section[data-testid="stSidebar"] .active-select-btn * {{
                color: var(--accent-color) !important;
            }}

            /* Date inside card: aligned with title, no extra margin */
            .chat-card-date {{
                padding: 0 12px 10px 12px !important;
                margin: 0 !important;
                font-size: 14px !important;
                color: var(--text-secondary);
                font-weight: 500;
                line-height: 1.5;
            }}


            /* The ⋮ trigger button inside the narrow menu column */
            section[data-testid="stSidebar"] [data-testid="stPopover"] button,
            section[data-testid="stSidebar"] div[data-testid="stPopover"] button {{
                background: transparent !important;
                background-color: transparent !important;
                border: none !important;
                padding: 4px 6px !important;
                min-width: 28px !important;
                width: 28px !important;
                height: 36px !important;
                font-size: 18px !important;
                color: var(--accent-color) !important;
                border-radius: 6px !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                margin-top: 4px !important;
                box-shadow: none !important;
            }}
            section[data-testid="stSidebar"] [data-testid="stPopover"] button *,
            section[data-testid="stSidebar"] div[data-testid="stPopover"] button * {{
                color: var(--accent-color) !important;
            }}
            section[data-testid="stSidebar"] [data-testid="stPopover"] button:hover,
            section[data-testid="stSidebar"] div[data-testid="stPopover"] button:hover {{
                color: var(--accent-color) !important;
                background-color: var(--hover-bg) !important;
            }}
            section[data-testid="stSidebar"] [data-testid="stPopover"] button:hover *,
            section[data-testid="stSidebar"] div[data-testid="stPopover"] button:hover * {{
                color: var(--accent-color) !important;
            }}

            /* Popover panel itself */
            div[data-testid="stPopoverBody"],
            [data-testid="stPopoverBody"] {{
                background-color: var(--card-bg) !important;
                border: 1.5px solid var(--accent-color) !important;
                border-radius: 10px !important;
                box-shadow: 0 8px 24px rgba(45, 125, 210, 0.15) !important;
                padding: 6px !important;
                min-width: 140px !important;
            }}
            /* Reset nested wrappers inside popover to prevent duplicate borders/padding */
            div[data-testid="stPopoverBody"] > div,
            [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {{
                background-color: transparent !important;
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
                margin: 0 !important;
            }}
            /* Buttons inside popover */
            div[data-testid="stPopoverBody"] button,
            [data-testid="stPopoverBody"] button {{
                background: transparent !important;
                background-color: transparent !important;
                border: none !important;
                border-radius: 6px !important;
                text-align: left !important;
                justify-content: flex-start !important;
                padding: 8px 12px !important;
                font-size: 13px !important;
                color: var(--text-primary) !important;
                width: 100% !important;
                transition: background-color 0.15s ease, color 0.15s ease !important;
                white-space: nowrap !important;
                box-shadow: none !important;
            }}
            div[data-testid="stPopoverBody"] button *,
            [data-testid="stPopoverBody"] button * {{
                color: var(--text-primary) !important;
            }}
            div[data-testid="stPopoverBody"] button:hover,
            [data-testid="stPopoverBody"] button:hover {{
                background-color: var(--hover-bg) !important;
                color: var(--accent-color) !important;
            }}
            div[data-testid="stPopoverBody"] button:hover *,
            [data-testid="stPopoverBody"] button:hover * {{
                color: var(--accent-color) !important;
            }}
            /* Delete option gets a red tint on hover */
            div[data-testid="stPopoverBody"] button:last-child:hover,
            [data-testid="stPopoverBody"] button:last-child:hover {{
                color: var(--red-text) !important;
                background-color: var(--red-bg) !important;
            }}
            div[data-testid="stPopoverBody"] button:last-child:hover *,
            [data-testid="stPopoverBody"] button:last-child:hover * {{
                color: var(--red-text) !important;
            }}

            /* The col_menu column: narrow and tight */
            section[data-testid="stSidebar"] .chat-card-action-col {{
                width: auto !important;
                flex: 0 0 auto !important;
                min-width: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
            }}


            /* Enterprise Tab Styling */
            div[data-testid="stTabBar"],
            [data-testid="stTabBar"] {{
                background-color: var(--bg-primary) !important;
                border-bottom: 1px solid var(--border-color) !important;
            }}
            div[data-testid="stTabBar"] button,
            button[data-testid^="stTabBar-tab"] {{
                color: #6B7280 !important;
                font-weight: 500 !important;
                border-bottom: 2px solid transparent !important;
                transition: all 0.2s ease !important;
                background-color: transparent !important;
            }}
            div[data-testid="stTabBar"] button:hover,
            button[data-testid^="stTabBar-tab"]:hover {{
                color: #1D4ED8 !important;
                border-bottom: 2px solid transparent !important;
            }}
            div[data-testid="stTabBar"] button[aria-selected="true"],
            button[data-testid^="stTabBar-tab"][aria-selected="true"] {{
                color: #2D7DD2 !important;
                border-bottom: 2px solid #2D7DD2 !important;
            }}
            /* Hide the default highlight line which might be red */
            div[data-testid="stTabBar"] div[role="tablist"] + div,
            div[data-testid="stTabBar"] div[data-baseweb="tab-highlight-id"],
            [data-testid="stTabBar"] [data-baseweb="tab-highlight-id"] {{
                display: none !important;
                background-color: transparent !important;
                height: 0 !important;
            }}

            /* Welcome Page Visibility */
            .welcome-box {{
                text-align: center;
                padding: 40px 20px;
            }}
            .welcome-icon {{
                font-size: 64px !important;
                color: var(--accent-color) !important;
            }}
            .welcome-title {{
                font-size: 32px !important;
                font-weight: 700 !important;
                color: var(--text-primary) !important;
                margin-top: 16px !important;
                margin-bottom: 8px !important;
            }}
            .welcome-subtitle {{
                font-size: 16px !important;
                font-weight: 400 !important;
                color: var(--text-secondary) !important;
                margin-bottom: 40px !important;
            }}


        </style>
    """, unsafe_allow_html=True)
