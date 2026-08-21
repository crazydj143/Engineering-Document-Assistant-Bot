import os
import torch
import numpy as np
from PIL import Image
import io
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info

ocr_engine = None
try:
    from rapidocr_onnxruntime import RapidOCR
    ocr_engine = RapidOCR()
    print("[vision_analyzer] RapidOCR loaded successfully.")
except ImportError:
    try:
        from paddleocr import PaddleOCR
        ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')
        print("[vision_analyzer] PaddleOCR loaded successfully.")
    except ImportError:
        print("[vision_analyzer] Warning: Neither RapidOCR nor PaddleOCR is installed.")

_model = None
_processor = None

def load_vision_model():
    """
    Loads Qwen/Qwen2.5-VL-3B-Instruct in 4-bit quantization once (singleton).
    """
    global _model, _processor
    if _model is not None:
        return _model, _processor

    print("[vision_analyzer] Initializing Qwen2.5-VL-3B-Instruct in 4-bit quantization...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True
    )

    model_name = "Qwen/Qwen2.5-VL-3B-Instruct"
    try:
        _model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_name,
            quantization_config=quantization_config if device == "cuda" else None,
            device_map="auto" if device == "cuda" else None,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        )
        _processor = AutoProcessor.from_pretrained(model_name)
        print("[vision_analyzer] Qwen2.5-VL model and processor loaded successfully.")
    except Exception as e:
        print(f"[vision_analyzer] Error loading model: {e}")
        raise e
        
    return _model, _processor

def run_ocr_on_image(pil_image: Image.Image) -> str:
    """
    Runs OCR on the given PIL Image using the loaded OCR engine.
    """
    if ocr_engine is None:
        return ""
    try:
        img_np = np.array(pil_image)
        if hasattr(ocr_engine, "__call__"):
            result, elapse = ocr_engine(img_np)
        else:
            result = ocr_engine.ocr(img_np, cls=True)
            if result and isinstance(result, list):
                result = result[0]
                
        lines = []
        if result:
            for item in result:
                if len(item) >= 2:
                    if isinstance(item[1], (tuple, list)):  # PaddleOCR format
                        text = item[1][0]
                    else:  # RapidOCR format
                        text = item[1]
                    lines.append(text)
        return "\n".join(lines)
    except Exception as e:
        print(f"[vision_analyzer] OCR processing error: {e}")
        return ""

def analyze_image_local(image_input, prompt: str) -> str:
    """
    Performs OCR and visual reasoning on the image using local Qwen2.5-VL-3B-Instruct.
    Accepts image path, bytes, file stream, or PIL Image.
    """
    model, processor = load_vision_model()
    
    pil_img = None
    try:
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return f"Error: Image path '{image_input}' does not exist."
            pil_img = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(image_input)).convert("RGB")
        elif hasattr(image_input, "read"):
            if hasattr(image_input, "seek"):
                image_input.seek(0)
            raw = image_input.read()
            if hasattr(image_input, "seek"):
                image_input.seek(0)
            pil_img = Image.open(io.BytesIO(raw)).convert("RGB")
        elif isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
        else:
            return "Error: Unsupported image input type."
    except Exception as e:
        return f"Error opening image: {str(e)}"

    ocr_text = run_ocr_on_image(pil_img)
    
    merged_prompt = prompt
    if ocr_text:
        merged_prompt += f"\n\n[OCR Transcribed Text Context]:\n{ocr_text}"

    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_img},
                    {"type": "text", "text": merged_prompt}
                ]
            }
        ]
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        ).to(device)
        
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=512)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )
            return output_text[0].strip()
    except Exception as e:
        print(f"[vision_analyzer] Local Qwen inference failed: {e}")
        if ocr_text:
            return f"[Model Inference Failed, falling back to OCR]:\n\n{ocr_text}"
        return f"Error during local Qwen vision analysis: {str(e)}"