# database.py — Database for Clip Curator (Updated with user support)

import sqlite3
import os
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'bookmarks.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_conn():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create all tables if they don't exist"""
    conn = get_conn()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Videos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id    TEXT UNIQUE NOT NULL,
            title       TEXT,
            duration    INTEGER,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Bookmarks table (now includes username + topic_title + youtube_link)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT NOT NULL DEFAULT 'guest',
            video_id        TEXT NOT NULL,
            video_title     TEXT,
            topic_title     TEXT,
            start_time      REAL,
            end_time        REAL,
            start_formatted TEXT,
            end_formatted   TEXT,
            summary         TEXT,
            youtube_link    TEXT,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized! ✅")

# ── USER FUNCTIONS ─────────────────────────────────────────────────────────────

def hash_password(password):
    """Simple password hashing for security"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    """Create new user. Returns True if created, False if username taken."""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (username, password) VALUES (?, ?)',
            (username, hash_password(password))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists
    finally:
        conn.close()

def verify_user(username, password):
    """Check if username + password match. Returns True/False."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM users WHERE username=? AND password=?',
        (username, hash_password(password))
    )
    user = cursor.fetchone()
    conn.close()
    return user is not None

# ── VIDEO FUNCTIONS ────────────────────────────────────────────────────────────

def save_video(video_id, title, duration):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO videos (video_id, title, duration) VALUES (?, ?, ?)',
        (video_id, title, duration)
    )
    conn.commit()
    conn.close()

# ── BOOKMARK FUNCTIONS ─────────────────────────────────────────────────────────

def save_bookmark(username, video_id, video_title, topic_title,
                  start_time, end_time, start_formatted,
                  end_formatted, summary, youtube_link):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bookmarks
        (username, video_id, video_title, topic_title,
         start_time, end_time, start_formatted,
         end_formatted, summary, youtube_link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (username, video_id, video_title, topic_title,
          start_time, end_time, start_formatted,
          end_formatted, summary, youtube_link))
    bookmark_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return bookmark_id

def get_all_bookmarks():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookmarks ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_bookmarks(username):
    """Get bookmarks for a specific user"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM bookmarks WHERE username=? ORDER BY created_at DESC',
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def search_bookmarks(username, query):
    conn = get_conn()
    cursor = conn.cursor()
    term = f"%{query}%"
    cursor.execute('''
        SELECT * FROM bookmarks
        WHERE username=?
        AND (summary LIKE ? OR topic_title LIKE ? OR video_title LIKE ?)
        ORDER BY created_at DESC
    ''', (username, term, term, term))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_bookmark(bookmark_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM bookmarks WHERE id=?', (bookmark_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0