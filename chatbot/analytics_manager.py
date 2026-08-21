import json
import os
import time

ANALYTICS_FILE = "analytics.json"

def load_analytics():
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading analytics: {e}")
            
    return {
        "total_documents": 0,
        "cad_documents": 0,
        "pdf_documents": 0,
        "total_queries": 0,
        "total_processing_time_ms": 0.0
    }

def save_analytics(data):
    try:
        with open(ANALYTICS_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving analytics: {e}")

def record_document_upload(filename):
    data = load_analytics()
    data["total_documents"] += 1
    
    ext = os.path.splitext(filename)[1].lower()
    if ext in [".dwg", ".dxf"]:
        data["cad_documents"] += 1
    else:
        data["pdf_documents"] += 1
        
    save_analytics(data)

def record_query(processing_time_ms):
    data = load_analytics()
    data["total_queries"] += 1
    data["total_processing_time_ms"] += processing_time_ms
    save_analytics(data)

def get_average_response_time():
    data = load_analytics()
    if data["total_queries"] == 0:
        return 0.0
    return data["total_processing_time_ms"] / data["total_queries"]
