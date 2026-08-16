from pypdf import PdfReader


def summarize_pdf(pdf_path):
    """Naive extractive summary: first 5 non-empty sentences of the PDF."""
    try:
        reader = PdfReader(pdf_path)
        text = ""

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

        if text.strip() == "":
            return "No text found in PDF."

        sentences = text.replace("\n", " ").split(".")

        bullets = []
        for sentence in sentences[:5]:
            if sentence.strip():
                bullets.append(sentence.strip() + ".")

        return bullets

    except Exception as e:
        return f"error: {e}"
