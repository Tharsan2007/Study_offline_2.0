from pypdf import PdfReader


def search_keyword(pdf_path, keyword):
    reader = PdfReader(pdf_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text.lower()

    keyword_lower = keyword.lower()

    if keyword_lower in text:
        index = text.find(keyword_lower)
        start = max(0, index - 100)
        end = min(len(text), index + 200)
        snippet = text[start:end].strip()
        return {"found": True, "message": f"'{keyword}' found in the PDF.", "snippet": snippet}
    else:
        return {"found": False, "message": f"'{keyword}' not found in the PDF.", "snippet": ""}
