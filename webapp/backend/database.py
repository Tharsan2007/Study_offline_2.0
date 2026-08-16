"""
AI StudyMate - Database Layer
Same schema/idea as the original desktop app's database.py,
rewritten to be safe for a multi-threaded Flask server
(check_same_thread=False + a lock) instead of a single Tkinter process.

Also tracks login activity so the admin account can see who has
logged in, and who is currently online.
"""

import sqlite3
import threading
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "AIStudyMate.db")

# Anyone who hasn't made a request in this long is considered offline.
ONLINE_WINDOW_MINUTES = 5

_lock = threading.Lock()
_connection = sqlite3.connect(DB_PATH, check_same_thread=False)
_cursor = _connection.cursor()

# ---------------- Create Tables ----------------
_cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

_cursor.execute("""
CREATE TABLE IF NOT EXISTS login_logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    login_time TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

_connection.commit()

# Seed the default admin account used by the original app (admin / 1234)
# so login keeps working out of the box.
_cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
if not _cursor.fetchone():
    _cursor.execute(
        "INSERT INTO users(username, password) VALUES (?, ?)",
        ("admin", "1234"),
    )
    _connection.commit()


# ---------------- Users ----------------
def save_user(username, password):
    with _lock:
        _cursor.execute(
            "INSERT INTO users(username, password) VALUES (?, ?)",
            (username, password),
        )
        _connection.commit()


def find_user(username, password):
    with _lock:
        _cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        return _cursor.fetchone()


def username_exists(username):
    with _lock:
        _cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        return _cursor.fetchone() is not None


def is_admin(username):
    return username == "admin"


# ---------------- Login activity (admin-only visibility) ----------------
def record_login(username):
    """Called every time someone logs in — one row per login event."""
    with _lock:
        _cursor.execute(
            "INSERT INTO login_logs(username) VALUES (?)",
            (username,),
        )
        _connection.commit()
        return _cursor.lastrowid


def touch_last_seen(username):
    """Called on authenticated requests so 'currently online' stays accurate."""
    with _lock:
        _cursor.execute(
            """UPDATE login_logs SET last_seen = CURRENT_TIMESTAMP
               WHERE id = (SELECT id FROM login_logs WHERE username = ? ORDER BY id DESC LIMIT 1)""",
            (username,),
        )
        _connection.commit()


def get_login_history(limit=100):
    """All login events, most recent first — 'who has logged in'."""
    with _lock:
        _cursor.execute(
            "SELECT username, login_time FROM login_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return _cursor.fetchall()


def get_online_users():
    """Distinct usernames whose most recent activity is within the online window."""
    cutoff = (datetime.utcnow() - timedelta(minutes=ONLINE_WINDOW_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    with _lock:
        _cursor.execute(
            """
            SELECT username, MAX(last_seen) as latest
            FROM login_logs
            GROUP BY username
            HAVING latest >= ?
            ORDER BY latest DESC
            """,
            (cutoff,),
        )
        return _cursor.fetchall()


def get_total_registered_users():
    with _lock:
        _cursor.execute("SELECT COUNT(*) FROM users")
        return _cursor.fetchone()[0]


def get_total_logins():
    with _lock:
        _cursor.execute("SELECT COUNT(*) FROM login_logs")
        return _cursor.fetchone()[0]


print("Database Connected Successfully")
