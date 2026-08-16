"""
AI StudyMate - Flask Backend
Turns the original Tkinter desktop app (login.py + dashboard.py) into a
REST API, so the new web frontend can talk to the exact same logic
(database.py, chat.py, search.py, summary.py) over HTTP instead of
tkinter widgets.

Extra features on top of the original desktop app:
- AI Chat and Quiz now read the ACTUAL uploaded PDF/image content
  (image text comes from OCR — see content.py / ocr.py).
- The "admin" account gets an extra Admin view showing who has logged
  in and who is online right now — hidden from every other user.
"""

import os
import uuid
from datetime import timedelta

from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.utils import secure_filename
from pypdf import PdfReader

import database
from chat import get_ai_response
from search import search_keyword
from summary import summarize_pdf
from content import extract_text
from quiz_gen import generate_quiz

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "..", "frontend", "static"),
    template_folder=os.path.join(BASE_DIR, "..", "frontend", "templates"),
)
app.secret_key = os.environ.get("STUDYMATE_SECRET_KEY", "ai-studymate-dev-secret")
app.permanent_session_lifetime = timedelta(days=7)

ALLOWED_PDF = {"pdf"}
ALLOWED_IMAGE = {"png", "jpg", "jpeg"}

# Extracted text for the CURRENT upload only, per session — nothing is
# kept once a new file is uploaded or the process restarts (matches
# "no history" from before). Keyed by a small token stored in the
# session cookie, since full document text is too big for a cookie.
# NOTE: this only works with a single server process/worker.
_CONTENT_CACHE = {}


def _allowed(filename, allowed_ext):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_ext


def _require_login():
    return session.get("user") is not None


def _current_username():
    return session.get("user")


@app.before_request
def _mark_activity():
    # Keeps the admin's "who's online" view accurate.
    user = session.get("user")
    if user:
        database.touch_last_seen(user)


def _admin_only():
    if not _require_login():
        return jsonify({"success": False, "message": "Please log in."}), 401
    if not session.get("is_admin"):
        return jsonify({"success": False, "message": "Admins only."}), 403
    return None


# ---------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------
@app.route("/")
def index():
    from flask import render_template
    return render_template("index.html")


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ---------------------------------------------------------------------
# Auth (mirrors login.py)
# ---------------------------------------------------------------------
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(force=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if database.find_user(username, password):
        session.permanent = True
        session["user"] = username
        session["is_admin"] = database.is_admin(username)
        database.record_login(username)
        database.touch_last_seen(username)
        return jsonify({
            "success": True,
            "message": "Login Successful!",
            "username": username,
            "is_admin": session["is_admin"],
        })

    return jsonify({"success": False, "message": "Invalid Username or Password!"}), 401


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(force=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"success": False, "message": "Username and password are required."}), 400

    if database.username_exists(username):
        return jsonify({"success": False, "message": "That username is already taken."}), 409

    database.save_user(username, password)
    return jsonify({"success": True, "message": "Account created! You can log in now."})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    _CONTENT_CACHE.pop(session.get("content_token"), None)
    session.clear()
    return jsonify({"success": True})


@app.route("/api/auth/me", methods=["GET"])
def me():
    return jsonify({
        "logged_in": _require_login(),
        "username": session.get("user"),
        "is_admin": bool(session.get("is_admin")),
    })


# ---------------------------------------------------------------------
# PDF upload (mirrors dashboard.upload_pdf)
# ---------------------------------------------------------------------
@app.route("/api/pdf/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file received."}), 400

    file = request.files["file"]
    if file.filename == "" or not _allowed(file.filename, ALLOWED_PDF):
        return jsonify({"success": False, "message": "Please choose a valid PDF file."}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    try:
        reader = PdfReader(save_path)
        pages = len(reader.pages)
    except Exception:
        pages = 0

    size_kb = round(os.path.getsize(save_path) / 1024, 2)

    text, err = extract_text(save_path)
    _store_content(save_path, text)

    return jsonify({
        "success": True,
        "file_name": filename,
        "pages": pages,
        "size_kb": size_kb,
        "text_ready": bool(text),
        "text_warning": err,
    })


def _store_content(path, text):
    token = str(uuid.uuid4())
    session["content_token"] = token
    session["current_pdf_path"] = path
    _CONTENT_CACHE[token] = text


def _current_text():
    token = session.get("content_token")
    return _CONTENT_CACHE.get(token, "")


def _resolve_pdf_path(_note_id=None):
    return session.get("current_pdf_path")


# ---------------------------------------------------------------------
# Image upload (mirrors dashboard.upload_image) — now OCR'd so it can
# be used for AI Chat and Quiz the same way an uploaded PDF is.
# ---------------------------------------------------------------------
@app.route("/api/image/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file received."}), 400

    file = request.files["file"]
    if file.filename == "" or not _allowed(file.filename, ALLOWED_IMAGE):
        return jsonify({"success": False, "message": "Please choose a PNG or JPG image."}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    text, err = extract_text(save_path)
    _store_content(save_path, text)

    return jsonify({
        "success": True,
        "file_name": filename,
        "url": f"/uploads/{filename}",
        "text_ready": bool(text),
        "text_warning": err,
    })


# ---------------------------------------------------------------------
# Summarize (mirrors dashboard.summarize)
# ---------------------------------------------------------------------
@app.route("/api/pdf/summarize", methods=["POST"])
def summarize():
    pdf_path = _resolve_pdf_path()

    if not pdf_path:
        return jsonify({"success": False, "message": "Please upload a PDF first!"}), 400

    summary = summarize_pdf(pdf_path)
    if isinstance(summary, str) and summary.startswith("error:"):
        return jsonify({"success": False, "message": summary}), 500

    return jsonify({"success": True, "summary": summary})


# ---------------------------------------------------------------------
# Search PDF (mirrors dashboard.search_pdf)
# ---------------------------------------------------------------------
@app.route("/api/pdf/search", methods=["POST"])
def search():
    data = request.get_json(force=True) or {}
    pdf_path = _resolve_pdf_path()
    keyword = (data.get("keyword") or "").strip()

    if not pdf_path:
        return jsonify({"success": False, "message": "Please upload a PDF first!"}), 400
    if not keyword:
        return jsonify({"success": False, "message": "Please enter a keyword."}), 400

    result = search_keyword(pdf_path, keyword)
    return jsonify({"success": True, **result})


# ---------------------------------------------------------------------
# AI Chat — now answers from the uploaded PDF/image content
# ---------------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    question = (data.get("question") or "").strip()

    if not question:
        return jsonify({"success": False, "message": "Ask a question first."}), 400

    content_text = _current_text()
    answer = get_ai_response(question, content_text)
    return jsonify({"success": True, "answer": answer, "used_upload": bool(content_text)})


# ---------------------------------------------------------------------
# Quiz — generated from the uploaded PDF/image when available,
# otherwise falls back to the default sample quiz.
# ---------------------------------------------------------------------
@app.route("/api/quiz", methods=["GET"])
def quiz():
    content_text = _current_text()
    questions = generate_quiz(content_text, num_questions=5) if content_text else []

    if not questions:
        questions = [
            {
                "question": "Python is a ________?",
                "options": ["Animal", "Programming Language", "Game", "Browser"],
                "answer": "Programming Language",
            },
            {
                "question": "Which keyword is used to create a function?",
                "options": ["function", "define", "def", "func"],
                "answer": "def",
            },
            {
                "question": "Which symbol is used for comments in Python?",
                "options": ["//", "#", "<!--", "**"],
                "answer": "#",
            },
        ]

    return jsonify({"questions": questions, "from_upload": bool(content_text)})


# ---------------------------------------------------------------------
# Study Planner (mirrors dashboard.planner)
# ---------------------------------------------------------------------
@app.route("/api/planner", methods=["GET"])
def planner():
    plan = [
        {"day": "Monday", "task": "Unit 1"},
        {"day": "Tuesday", "task": "Unit 2"},
        {"day": "Wednesday", "task": "Unit 3"},
        {"day": "Thursday", "task": "Unit 4"},
        {"day": "Friday", "task": "Revision"},
        {"day": "Saturday", "task": "Mock Test"},
        {"day": "Sunday", "task": "Final Revision"},
    ]
    return jsonify({"plan": plan})


# ---------------------------------------------------------------------
# Admin — visible only to the "admin" account: who has logged in,
# and who is online right now.
# ---------------------------------------------------------------------
@app.route("/api/admin/logins", methods=["GET"])
def admin_logins():
    denied = _admin_only()
    if denied:
        return denied

    history = database.get_login_history(limit=100)
    online = database.get_online_users()

    return jsonify({
        "success": True,
        "total_registered_users": database.get_total_registered_users(),
        "total_logins": database.get_total_logins(),
        "online_count": len(online),
        "online_users": [{"username": u, "last_seen": t} for u, t in online],
        "login_history": [{"username": u, "login_time": t} for u, t in history],
    })


# ---------------------------------------------------------------------
# About (mirrors dashboard.about)
# ---------------------------------------------------------------------
@app.route("/api/about", methods=["GET"])
def about():
    return jsonify({
        "app": "AI StudyMate",
        "version": "2.0 (Web Edition)",
        "developed_by": "L. Tharsan",
        "department": "CSE (IoT)",
        "college": "KLN College of Engineering",
        "features": [
            "PDF Upload",
            "Image Upload (OCR)",
            "AI Chat (reads your uploaded notes)",
            "PDF Summary",
            "Search PDF",
            "Quiz Generator (from your uploaded notes)",
            "Voice Assistant (browser-based)",
            "Admin login activity view",
        ],
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
