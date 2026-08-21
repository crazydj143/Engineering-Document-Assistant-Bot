# Engineering Document Assistant

An AI-powered Engineering Document Assistant designed to simplify the analysis of engineering documents and CAD drawings. The application combines Retrieval-Augmented Generation (RAG), computer vision, and Large Language Models to provide intelligent answers from technical documents and engineering layouts.

The system supports PDF documents, CAD drawings, engineering images, semantic document search, electrical symbol detection, BOQ generation, and AI-powered engineering explanations through a simple chat interface.

---

# Features

- AI-powered engineering document chatbot
- PDF document processing and question answering
- CAD drawing (DWG/DXF) analysis
- Electrical symbol detection using YOLOv8n
- Engineering inventory generation
- Vision-based engineering drawing interpretation
- Semantic document search using FAISS
- Retrieval-Augmented Generation (RAG)
- Chat history storage and export
- BOQ (Bill of Quantities) generation
- Analytics dashboard
- Dark/Light theme support

---

# Technology Stack

## Frontend

- Streamlit

## Backend

- Python

## AI Models

- Llama 3.3 70B Versatile (Groq API)
- Qwen2.5-VL Vision Language Model
- YOLOv8n (Electrical Symbol Detection)

## Vector Database

- FAISS

## Embedding Model

- all-MiniLM-L6-v2 (Sentence Transformers)

## Database

- SQLite

---

# Libraries Used

- Streamlit
- PyMuPDF
- ezdxf
- FAISS
- Sentence Transformers
- Transformers
- Ultralytics (YOLOv8)
- PyTorch
- OpenCV
- Pillow
- SQLAlchemy
- SQLite3
- Pandas
- NumPy
- Matplotlib
- ReportLab

---

# Project Structure

```
Engineering-Document-Assistant
│
├── README.md
├── requirements.txt
│
└── chatbot
    ├── frontend.py
    ├── cad_processor.py
    ├── pdf_processor.py
    ├── vision_analyzer.py
    ├── boq_generator.py
    ├── analytics_manager.py
    ├── training
    ├── pdf_storage
    ├── cad_storage
    ├── sqlite
    └── ...
```

---

# Supported File Formats

- PDF
- DWG
- DXF
- PNG
- JPG
- JPEG

---

# Installation

## Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/Engineering-Document-Assistant.git

cd Engineering-Document-Assistant
```

## Create Virtual Environment

Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

Linux

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# API Keys

Create a `.env` file inside the `chatbot` folder.

Example:

```env
GROQ_API_KEY=YOUR_GROQ_API_KEY
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
HUGGINGFACE_TOKEN=YOUR_HUGGINGFACE_TOKEN
```

Replace the values with your own API keys.

---

# Download Required Models

## YOLOv8n

Download or train your own electrical symbol detection model.

Example:

```
best.pt
```

Place it inside the appropriate model directory used by the application.

---

## Qwen Vision Model

Download the required Qwen Vision model from Hugging Face if running locally.

Alternatively, update the model name in the configuration file.

---

# Run the Application

Navigate to the chatbot folder.

```bash
cd chatbot
```

Run

```bash
streamlit run frontend.py
```

The application will open in your browser.

---

# How It Works

1. Upload an engineering document or CAD drawing.
2. Text is extracted from PDFs.
3. CAD entities are extracted from engineering drawings.
4. Engineering images are analyzed using the Vision Language Model.
5. Electrical symbols are detected using YOLOv8n.
6. Documents are converted into embeddings.
7. FAISS retrieves the most relevant document chunks.
8. The retrieved information is passed to the Large Language Model.
9. The chatbot generates context-aware engineering responses.

---

# Electrical Symbol Detection

YOLOv8n is used to detect electrical symbols including:

- Transformer
- Circuit Breaker
- Current Transformer (CT)
- Potential Transformer (PT)
- Isolator
- Busbar

The detected symbols are converted into an engineering inventory that is used by the chatbot during response generation.

---

# Current Capabilities

- Engineering document understanding
- CAD layout interpretation
- Engineering inventory extraction
- Semantic search
- AI-powered engineering explanations
- BOQ generation
- Chat history export
- Analytics dashboard

---

# Future Improvements

- BIM integration
- Multi-language support
- Voice interaction
- Cloud deployment
- Real-time collaboration
- Additional engineering drawing formats
- Fine-tuned engineering language models

---

# Notes

- This repository does not include API keys.
- Generated databases, temporary files, and caches are excluded.
- Large AI model weights are not included in the repository.
- Use your own API keys and model checkpoints before running the application.
