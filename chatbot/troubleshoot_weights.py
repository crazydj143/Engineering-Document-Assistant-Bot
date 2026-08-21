import sys
import os
import traceback

def log_and_print(msg):
    print(msg)
    with open("troubleshoot_error.log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

if os.path.exists("troubleshoot_error.log"):
    os.remove("troubleshoot_error.log")

log_and_print("==================================================")
log_and_print("      CHATBOT WEIGHTS LOADING DIAGNOSTIC TEST     ")
log_and_print("==================================================")

try:
    import torch
    log_and_print(f"Python Version: {sys.version}")
    log_and_print(f"PyTorch Version: {torch.__version__}")
    log_and_print(f"CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        log_and_print(f"CUDA Device Name: {torch.cuda.get_device_name(0)}")
        log_and_print(f"CUDA VRAM Total: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
except Exception as e:
    log_and_print(f"PyTorch Check Failed:\n{traceback.format_exc()}")

try:
    log_and_print("\nTesting bitsandbytes import...")
    import bitsandbytes
    log_and_print(f"bitsandbytes version: {getattr(bitsandbytes, '__version__', 'unknown')}")
except Exception as e:
    log_and_print(f"bitsandbytes Import Failed:\n{traceback.format_exc()}")

try:
    log_and_print("\nTesting SentenceTransformer loading (BAAI/bge-small-en-v1.5)...")
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
    log_and_print("SentenceTransformer loaded successfully.")
except Exception as e:
    log_and_print(f"SentenceTransformer Load Failed:\n{traceback.format_exc()}")

try:
    log_and_print("\nTesting Qwen2.5-VL-3B-Instruct model loading...")
    import vision_analyzer
    vision_analyzer.load_vision_model()
    log_and_print("Qwen2.5-VL-3B-Instruct loaded successfully!")
except Exception as e:
    log_and_print(f"Qwen2.5-VL Loading Failed:\n{traceback.format_exc()}")

log_and_print("\n==================================================")
log_and_print("Diagnostics complete. Output written to troubleshoot_error.log")
log_and_print("==================================================")
