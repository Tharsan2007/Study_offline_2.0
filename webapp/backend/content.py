"""
AI StudyMate - Content extraction
One place that turns an uploaded file (PDF or image) into plain text,
so chat.py, search.py, summary.py, and quiz_gen.py can all work off
the same extracted text regardless of whether the student uploaded a
PDF or a photo of their notes.
"""

import os
from pypdf import PdfReader
from ocr import extract_text_from_image


def extract_text(file_path):
    """Returns (text, error). error is None on success."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            if not text.strip():
                return "", "No text found in this PDF."
            return text, None
        except Exception as e:
            return "", f"Could not read PDF: {e}"

    if ext in (".png", ".jpg", ".jpeg"):
        text = extract_text_from_image(file_path)
        if text.startswith("error:"):
            return "", text.replace("error:", "").strip()
        if not text.strip():
            return "", "No readable text found in this image."
        return text, None

    return "", "Unsupported file type."
