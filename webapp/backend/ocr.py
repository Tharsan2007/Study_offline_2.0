"""
AI StudyMate - Image OCR
Extracts text from an uploaded photo (whiteboard, handwritten page, etc.)
so the same image can be used for AI Chat and Quiz generation, the same
way an uploaded PDF is used.

Requires the Tesseract OCR engine installed on the machine running the
server (separate from the pytesseract Python package). See README for
install instructions per OS. If Tesseract isn't installed, this fails
gracefully with a clear message instead of crashing the app.
"""

from PIL import Image

try:
    import pytesseract
    _PYTESSERACT_AVAILABLE = True
except ImportError:
    _PYTESSERACT_AVAILABLE = False


def extract_text_from_image(image_path):
    """Returns extracted text, or an 'error: ...' string on failure."""
    if not _PYTESSERACT_AVAILABLE:
        return "error: OCR library not installed on the server."

    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        # Most common cause: the Tesseract *engine* (not the Python
        # package) isn't installed on this machine.
        return f"error: Could not read text from image ({e})"
