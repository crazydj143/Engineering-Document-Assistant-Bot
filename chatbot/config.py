import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
PDF_STORAGE_DIR = os.path.join(BASE_DIR, "pdf_storage")
CAD_STORAGE_DIR = os.path.join(BASE_DIR, "cad_storage")
EXTRACTED_IMAGES_DIR = os.path.join(BASE_DIR, "extracted_images")

def ensure_directories():
    """Ensure all required data and storage directories exist."""
    for directory in [DATA_DIR, PDF_STORAGE_DIR, CAD_STORAGE_DIR, EXTRACTED_IMAGES_DIR]:
        os.makedirs(directory, exist_ok=True)
