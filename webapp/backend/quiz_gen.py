"""
AI StudyMate - Quiz generator
Builds fill-in-the-blank multiple-choice questions straight out of the
uploaded PDF/image text: pick a sentence, blank out one meaningful word,
offer that word plus three other words pulled from elsewhere in the
text as distractors.
"""

import re
import random

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "am", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "with", "about", "as", "by", "and",
    "or", "but", "if", "so", "than", "that", "this", "these", "those", "it",
    "its", "can", "could", "should", "would", "will", "shall", "may", "might",
    "not", "also", "such", "into", "from", "which", "there", "their", "have",
    "has", "had", "you", "your", "we", "our",
}


def _sentences(text):
    raw = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in raw if 25 <= len(s.strip()) <= 200]


def _candidate_words(sentence):
    words = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", sentence)
    return [w for w in words if w.lower() not in STOPWORDS]


def generate_quiz(content_text, num_questions=5):
    """
    Returns a list of {question, options, answer} dicts built from the
    supplied text, or an empty list if the text is too short to build
    good questions from.
    """
    sentences = _sentences(content_text or "")
    random.shuffle(sentences)

    all_words = set()
    for s in sentences:
        all_words.update(w for w in _candidate_words(s))

    questions = []
    used_sentences = set()

    for sentence in sentences:
        if len(questions) >= num_questions:
            break
        if sentence in used_sentences:
            continue

        candidates = _candidate_words(sentence)
        if not candidates:
            continue

        # Prefer a longer, more "meaningful" word to blank out.
        answer_word = max(candidates, key=len)

        blanked = re.sub(
            r"\b" + re.escape(answer_word) + r"\b", "______", sentence, count=1
        )
        if "______" not in blanked:
            continue

        distractor_pool = list(all_words - {answer_word})
        random.shuffle(distractor_pool)
        distractors = distractor_pool[:3]
        # Pad with generic distractors if the document is short on words.
        filler = ["Concept", "Process", "System", "Method", "Function", "Data"]
        i = 0
        while len(distractors) < 3 and i < len(filler):
            if filler[i] != answer_word and filler[i] not in distractors:
                distractors.append(filler[i])
            i += 1

        options = distractors + [answer_word]
        random.shuffle(options)

        questions.append({
            "question": blanked,
            "options": options,
            "answer": answer_word,
        })
        used_sentences.add(sentence)

    return questions
