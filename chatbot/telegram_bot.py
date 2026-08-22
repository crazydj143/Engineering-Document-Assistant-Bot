import os
import sys
import logging
import tempfile
import json
import pickle
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============================================================
# PATH SETUP
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ============================================================
# EXISTING PROJECT MODULES
# ============================================================

import config
try:
    import groq_client
except Exception as exc:
    groq_client = None
    logger.warning("Groq client unavailable at startup: %s", exc)

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("engineering_telegram_bot")

# ============================================================
# ENVIRONMENT
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Telegram upload storage
UPLOAD_DIR = PROJECT_DIR / "storage" / "telegram_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# SUPPORTED FILES
# ============================================================

PDF_EXTENSIONS = {".pdf"}

CAD_EXTENSIONS = {
    ".dxf",
    ".dwg",
}

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}

DOCUMENT_EXTENSIONS = {
    ".docx",
}

SUPPORTED_EXTENSIONS = (
    PDF_EXTENSIONS
    | CAD_EXTENSIONS
    | IMAGE_EXTENSIONS
    | DOCUMENT_EXTENSIONS
)


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    await update.message.reply_text(
        "🤖 Engineering Document Assistant\n\n"
        "Send an engineering document or ask a question.\n\n"
        "Supported files:\n"
        "📄 PDF\n"
        "📐 DXF / DWG\n"
        "📝 DOCX\n"
        "🖼 PNG / JPG\n\n"
        "Examples:\n"
        "• Explain diagram on page 14\n"
        "• What is the material?\n"
        "• Give dimensions from page 5\n"
        "• Explain this drawing\n"
        "• What components are shown?"
    )


# ============================================================
# HELP
# ============================================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    await update.message.reply_text(
        "📘 Engineering Document Assistant\n\n"
        "/start - Start bot\n"
        "/help - Show help\n\n"
        "Upload your engineering document and then ask questions "
        "about it."
    )


# ============================================================
# HEALTH / STATUS
# ============================================================

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    groq_ok = bool(
        os.getenv("GROQ_API_KEY")
        and os.getenv("GROQ_API_KEY") != "xxxxx"
    )

    await update.message.reply_text(
        "🟢 Telegram Bot: ONLINE\n"
        f"🧠 Groq API: {'CONFIGURED' if groq_ok else 'NOT CONFIGURED'}\n"
        "📁 Document storage: READY"
    )


# ============================================================
# FILE NAME SAFETY
# ============================================================

def safe_filename(filename: str) -> str:
    """
    Prevent path traversal and unsafe filenames.
    """
    filename = Path(filename).name

    if not filename:
        filename = "uploaded_file"

    return filename


# ============================================================
# SAVE TELEGRAM FILE
# ============================================================

async def save_telegram_file(
    telegram_file,
    filename: str,
) -> Path:

    filename = safe_filename(filename)

    destination = UPLOAD_DIR / filename

    # Avoid accidental overwrite
    if destination.exists():
        stem = destination.stem
        suffix = destination.suffix

        counter = 1

        while destination.exists():
            destination = (
                UPLOAD_DIR
                / f"{stem}_{counter}{suffix}"
            )
            counter += 1

    await telegram_file.download_to_drive(
        custom_path=str(destination)
    )

    return destination


# ============================================================
# STREAMLIT-COMPATIBLE UPLOAD OBJECT
# ============================================================

class TelegramUploadedFile:
    """
    Small adapter that provides the interface used by the
    existing process_and_cache_pdf/process_and_cache_cad
    functions.

    This avoids changing the existing processors.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.name = self.path.name

    def seek(self, position=0):
        return None

    def read(self):
        return self.path.read_bytes()



# ============================================================
# TELEGRAM DOCUMENT MEMORY
# ============================================================

def set_active_document(context, file_path, pdf_result=None):
    """
    Store the currently uploaded document for this Telegram chat.
    """
    context.chat_data["active_document"] = str(file_path)

    if pdf_result:
        context.chat_data["pdf_result"] = pdf_result


def get_active_document(context):
    return context.chat_data.get("active_document")


def get_pdf_context(context):
    """
    Collect useful text from the currently processed PDF.

    Uses the existing pdf_processor result.
    """
    result = context.chat_data.get("pdf_result")

    if not result:
        return ""

    chunks = result.get("text_chunks", [])

    if not chunks:
        return ""

    parts = []

    for chunk in chunks[:40]:
        page = chunk.get("page", "?")
        content = chunk.get("content", "")

        if content:
            parts.append(
                f"[Page {page}]\n{content}"
            )

    return "\n\n".join(parts)


def find_page_context(context, page_number):
    """
    Return text chunks belonging to a requested PDF page.
    """
    result = context.chat_data.get("pdf_result")

    if not result:
        return ""

    chunks = result.get("text_chunks", [])

    page_parts = []

    for chunk in chunks:
        try:
            page = int(chunk.get("page"))
        except Exception:
            continue

        if page == page_number:
            content = chunk.get("content", "")

            if content:
                page_parts.append(content)

    return "\n\n".join(page_parts)


# ============================================================
# PDF PROCESSING
# ============================================================

def process_pdf_file(file_path: Path):
    """
    Uses the EXISTING pdf_processor.py.

    No redesign of PDF processing.
    """

    from pdf_processor import process_and_cache_pdf

    logger.info(
        "Processing PDF through existing PDF pipeline: %s",
        file_path.name,
    )

    # The existing processor requires an embedding model.
    from sentence_transformers import SentenceTransformer

    embed_model = SentenceTransformer(
        "BAAI/bge-small-en-v1.5"
    )

    uploaded_file = TelegramUploadedFile(file_path)

    result = process_and_cache_pdf(
        uploaded_file,
        embed_model,
    )

    return result


# ============================================================
# CAD PROCESSING
# ============================================================

def process_cad_file(file_path: Path):
    """
    Uses the EXISTING cad_processor.py.
    """

    from cad_processor import process_and_cache_cad

    logger.info(
        "Processing CAD through existing CAD pipeline: %s",
        file_path.name,
    )

    from sentence_transformers import SentenceTransformer

    embed_model = SentenceTransformer(
        "BAAI/bge-small-en-v1.5"
    )

    uploaded_file = TelegramUploadedFile(file_path)

    result = process_and_cache_cad(
        uploaded_file,
        embed_model,
    )

    return result


# ============================================================
# FILE DOCUMENT HANDLER
# ============================================================

async def handle_document(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message or not update.message.document:
        return

    document = update.message.document

    filename = safe_filename(
        document.file_name or "uploaded_file"
    )

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:

        await update.message.reply_text(
            "❌ Unsupported file type.\n\n"
            "Supported:\n"
            "PDF, DXF, DWG, DOCX, PNG, JPG"
        )

        return

    await update.message.reply_text(
        f"📥 Receiving `{filename}`...",
        parse_mode="Markdown",
    )

    try:

        telegram_file = await document.get_file()

        file_path = await save_telegram_file(
            telegram_file,
            filename,
        )

        logger.info(
            "Telegram file saved: %s",
            file_path,
        )

        # ----------------------------------------------------
        # PDF
        # ----------------------------------------------------

        if extension in PDF_EXTENSIONS:

            await update.message.reply_text(
                "📄 PDF received.\n"
                "🔍 Processing document..."
            )

            try:

                result = process_pdf_file(
                    file_path
                )

                set_active_document(
                    context,
                    file_path,
                    result,
                )

                if result:
                    await update.message.reply_text(
                        "✅ PDF processed successfully.\n\n"
                        "You can now ask questions about this document."
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ PDF processing returned no result."
                    )

            except Exception as exc:

                logger.exception(
                    "PDF processing failed"
                )

                await update.message.reply_text(
                    "❌ PDF processing failed.\n\n"
                    f"{type(exc).__name__}: {exc}"
                )

            return

        # ----------------------------------------------------
        # CAD
        # ----------------------------------------------------

        if extension in CAD_EXTENSIONS:

            await update.message.reply_text(
                "📐 CAD file received.\n"
                "🔍 Processing drawing..."
            )

            try:

                result = process_cad_file(
                    file_path
                )

                if result:
                    await update.message.reply_text(
                        "✅ CAD drawing processed successfully.\n\n"
                        "You can now ask questions about the drawing."
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ CAD processing returned no result."
                    )

            except Exception as exc:

                logger.exception(
                    "CAD processing failed"
                )

                await update.message.reply_text(
                    "❌ CAD processing failed.\n\n"
                    f"{type(exc).__name__}: {exc}"
                )

            return

        # ----------------------------------------------------
        # DOCX
        # ----------------------------------------------------

        if extension in DOCUMENT_EXTENSIONS:

            await update.message.reply_text(
                "📝 DOCX received.\n"
                "The document has been saved successfully."
            )

            return

        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

        if extension in IMAGE_EXTENSIONS:

            await update.message.reply_text(
                "🖼 Image received.\n"
                "Image analysis connection will use the existing "
                "vision pipeline."
            )

            return

    except Exception as exc:

        logger.exception(
            "Telegram document handling failed"
        )

        await update.message.reply_text(
            "❌ File handling failed.\n\n"
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================
# PHOTO HANDLER
# ============================================================

async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message or not update.message.photo:
        return

    try:

        photo = update.message.photo[-1]

        telegram_file = await photo.get_file()

        filename = (
            f"telegram_image_"
            f"{photo.file_unique_id}.jpg"
        )

        destination = await save_telegram_file(
            telegram_file,
            filename,
        )

        await update.message.reply_text(
            "🖼 Image received successfully."
        )

        logger.info(
            "Image saved: %s",
            destination,
        )

    except Exception as exc:

        logger.exception(
            "Photo handling failed"
        )

        await update.message.reply_text(
            f"❌ Image handling failed:\n{exc}"
        )


# ============================================================
# ENGINEERING QUESTION
# ============================================================

async def handle_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.message:
        return

    question = (update.message.text or "").strip()

    if not question:
        return

    if not os.getenv("GROQ_API_KEY"):
        await update.message.reply_text(
            "⚠️ GROQ_API_KEY is not configured on the server."
        )
        return

    active_document = get_active_document(context)

    if not active_document:
        await update.message.reply_text(
            "📄 Please upload an engineering document first."
        )
        return

    await update.message.reply_text(
        "🧠 Analyzing your engineering question..."
    )

    try:
        import re

        # ----------------------------------------------------
        # Detect requested page
        # Examples:
        # page 14
        # page no 14
        # on page 14
        # ----------------------------------------------------

        page_match = re.search(
            r"\bpage\s*(?:no\.?|number)?\s*(\d+)\b",
            question.lower(),
        )

        requested_page = (
            int(page_match.group(1))
            if page_match
            else None
        )

        # ----------------------------------------------------
        # Build document context
        # ----------------------------------------------------

        if requested_page is not None:
            page_context = find_page_context(
                context,
                requested_page,
            )

            if page_context:
                document_context = (
                    f"DOCUMENT CONTEXT — PAGE "
                    f"{requested_page}\n\n"
                    f"{page_context}"
                )
            else:
                document_context = (
                    f"No extracted text was found for "
                    f"page {requested_page}."
                )

        else:
            document_context = get_pdf_context(
                context
            )

        # Keep prompt reasonably small
        max_context = 18000

        if len(document_context) > max_context:
            document_context = (
                document_context[:max_context]
                + "\n\n[Context truncated]"
            )

        # ----------------------------------------------------
        # Engineering system prompt
        # ----------------------------------------------------

        system_prompt = """
You are an Engineering Document Assistant.

Answer questions using the supplied engineering-document
context.

Rules:

1. Do not invent dimensions, specifications, materials,
   tolerances, components or drawing information.

2. If the requested information is not available in the
   supplied context, clearly say that it could not be
   confirmed from the available document data.

3. Preserve engineering units and tolerances exactly.

4. If the user asks about a specific page, answer only from
   that page/context when possible.

5. For diagram questions, explain the identifiable
   engineering elements, labels, connections and purpose
   supported by the supplied context.

6. Keep the answer practical and concise.

7. Never claim to have visually inspected an image unless
   actual image information is provided.
"""

        user_prompt = f"""
ENGINEERING DOCUMENT:

{document_context}

USER QUESTION:

{question}

Provide the best engineering answer supported by the
document context.
"""

        answer = groq_client.generate_groq_response(
            system_prompt,
            user_prompt,
        )

        if not answer:
            answer = (
                "⚠️ No answer was generated."
            )

        # ----------------------------------------------------
        # Telegram message size protection
        # ----------------------------------------------------

        max_length = 4000

        if len(answer) <= max_length:
            await update.message.reply_text(answer)
        else:
            for start in range(
                0,
                len(answer),
                max_length,
            ):
                await update.message.reply_text(
                    answer[start:start + max_length]
                )

    except Exception as exc:
        logger.exception(
            "Question handling failed"
        )

        await update.message.reply_text(
            "❌ AI processing failed.\n\n"
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Telegram error: %s",
        context.error,
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN environment variable "
            "is not set."
        )

    logger.info(
        "Starting Engineering Document Assistant Telegram Bot..."
    )

    application = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "status",
            status_command,
        )
    )

    # Documents
    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            handle_document,
        )
    )

    # Photos
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo,
        )
    )

    # Text questions
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_text,
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Engineering Document Assistant Telegram Bot is ONLINE."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
