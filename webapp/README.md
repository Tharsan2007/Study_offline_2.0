# AI StudyMate — Web Edition

Your original **Ai StudyMate** project was a Tkinter desktop app: `splash.py` →
`login.py` → `dashboard.py`, with logic split across `chat.py`, `search.py`,
`summary.py`, `voice.py`, and `database.py`.

This package keeps that same logic as the **backend**, wraps it in a Flask
REST API, and adds a brand-new **web frontend** (HTML/CSS/JS) so the whole
thing runs as one ordinary web app in a browser — no Tkinter window needed,
and no internet required to run it (see "Runs fully offline" below).

```
webapp/
├── backend/
│   ├── app.py            # Flask API — one route per dashboard button
│   ├── database.py       # users + login activity (SQLite)
│   ├── content.py        # turns an uploaded PDF or image into plain text
│   ├── ocr.py             # image -> text, via Tesseract OCR
│   ├── chat.py            # content-aware AI chat
│   ├── quiz_gen.py        # generates a quiz from the uploaded content
│   ├── search.py          # keyword search inside the uploaded PDF
│   ├── summary.py         # summarizes the uploaded PDF
│   └── requirements.txt
├── frontend/
│   ├── templates/index.html
│   └── static/{css,js}
├── uploads/               # uploaded PDFs & images land here
└── README.md
```

## What's new in this version

1. **AI Chat reads your actual uploaded PDF/image.** Upload a PDF or a photo
   of your notes on the Desk tab, then ask a question — the answer comes
   from the sentence(s) in your own notes that best match your question
   (word-overlap scoring), not a generic canned reply.
2. **Quiz is generated from your uploaded PDF/image too.** It picks
   sentences from your notes, blanks out a key word, and builds
   multiple-choice options around it. If nothing is uploaded yet, it falls
   back to a small sample quiz so the page still works.
3. **Image uploads now go through OCR** (`ocr.py`, using the Tesseract
   engine) so a photo of a whiteboard or handwritten page can be used for
   Ask AI and Quiz exactly like a PDF can.
4. **Admin-only "Admin" tab.** Only the `admin` account sees it. It shows:
   - How many people are registered and how many total logins there have
     been
   - **Who is online right now** (anyone active in the last 5 minutes)
   - **Full login history** — every username and the time they logged in

   Regular accounts never see this tab or its data — the backend rejects
   the request with a 403 if a non-admin tries to call it directly.

## Runs fully offline

Once installed, `python app.py` needs **no internet connection** — no
external fonts, no external AI API calls. Everything (Flask, SQLite, PDF
reading, OCR, chat, quiz, voice) runs on your own machine. The only time
you need internet is to `pip install` the dependencies once, and (if you
choose to) to deploy it online later.

## Run it

```bash
cd webapp/backend
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

Log in with the demo account **admin / 1234** (seeded automatically, and
this is the account that sees the Admin tab), or use "Create account" to
register a new one.

### One extra install for image OCR

Image-to-text needs the **Tesseract OCR engine** on your machine (separate
from the `pytesseract` Python package already in `requirements.txt`):

- **Windows:** download the installer from the
  [UB-Mannheim Tesseract build](https://github.com/UB-Mannheim/tesseract/wiki),
  install it, then make sure `tesseract.exe`'s folder is on your PATH
  (same idea as the pip PATH fix from earlier).
- **Mac:** `brew install tesseract`
- **Linux:** `sudo apt install tesseract-ocr`

If Tesseract isn't installed, PDF upload/chat/quiz still work fine —
only image OCR will show a friendly error instead of extracted text.

**If you deploy to Render:** the free web service doesn't have Tesseract
pre-installed, so image OCR won't work there unless you add a build step
that installs it (outside the scope of the free tier's default Python
environment). PDF-based features work on Render regardless.

## Every dashboard feature -> API route

| Feature | API route |
|---|---|
| Upload PDF | `POST /api/pdf/upload` |
| Upload Image (OCR'd) | `POST /api/image/upload` |
| Summarize Notes | `POST /api/pdf/summarize` |
| Search PDF | `POST /api/pdf/search` |
| AI Chat (content-aware) | `POST /api/chat` |
| Quiz (content-aware) | `GET /api/quiz` |
| Study Planner | `GET /api/planner` |
| Admin: login activity | `GET /api/admin/logins` (admin only) |
| Voice ON/OFF | handled client-side in the browser |
| About | `GET /api/about` |

## Notes

- No history is kept in the dashboard (as requested earlier) — chat shows
  only the current question, and there's no visible list of past uploads
  or a progress tracker. The one exception is the **Admin** tab, which
  intentionally keeps a login log so the admin account can see usage.
- The extracted text from your current upload lives in server memory
  (not the database) and is cleared on logout or when you upload a new
  file — this keeps things simple, but means it only works with Flask
  running as a single process (the default for both `python app.py` and
  `gunicorn app:app`).
- The SQLite database (`AIStudyMate.db`, created automatically in
  `backend/`) now stores two tables: `users` (accounts) and `login_logs`
  (used only for the Admin tab).
