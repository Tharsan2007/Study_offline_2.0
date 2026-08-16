import re

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "am", "be", "been", "being",
    "what", "when", "where", "which", "who", "whom", "why", "how", "do", "does",
    "did", "of", "in", "on", "at", "to", "for", "with", "about", "as", "by",
    "and", "or", "but", "if", "so", "than", "that", "this", "these", "those",
    "it", "its", "can", "could", "should", "would", "will", "shall", "may",
    "might", "i", "you", "he", "she", "they", "we", "me", "my", "your", "please",
    "tell", "explain", "define", "meaning", "mean",
}


def _tokenize(text):
    return [w for w in re.findall(r"[a-zA-Z']+", text.lower()) if w not in STOPWORDS and len(w) > 2]


def _sentences(text):
    # Simple sentence splitter — good enough for lecture-note style text.
    raw = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in raw if len(s.strip()) > 15]


def get_ai_response(question, content_text=None):
    """
    Answers from the uploaded PDF/image text when available (matches the
    sentences whose words best overlap the question), otherwise falls
    back to a small built-in glossary.
    """
    q_words = set(_tokenize(question))

    if content_text and q_words:
        sentences = _sentences(content_text)
        scored = []
        for sent in sentences:
            sent_words = set(_tokenize(sent))
            overlap = len(q_words & sent_words)
            if overlap > 0:
                scored.append((overlap, sent))

        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            best_score = scored[0][0]
            top_sentences = [s for score, s in scored if score == best_score][:2]
            return " ".join(top_sentences)

    # Fallback glossary (also used when nothing is uploaded)
    question_lower = question.lower()
    if "python" in question_lower:
        return "Python is a programming language."
    elif "java" in question_lower:
        return "Java is an object-oriented programming language."
    elif "html" in question_lower:
        return "HTML is used to create web pages."
    elif "ai" in question_lower:
        return "Artificial Intelligence allows computers to learn and solve problems."

    if content_text:
        return "I couldn't find anything about that in your uploaded notes. Try a different keyword."
    return "Sorry, I couldn't find the answer. Try uploading a PDF or image of your notes first."
