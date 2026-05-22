import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = 'data.db'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                sheets_id TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                date TEXT NOT NULL,
                title TEXT,
                audio_filename TEXT,
                transcript TEXT,
                summary TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS coaching_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                date TEXT NOT NULL,
                note TEXT,
                remaining TEXT,
                motivation TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        ''')
        # Migration: add sheets_id if missing (for existing DBs)
        try:
            conn.execute("ALTER TABLE users ADD COLUMN sheets_id TEXT DEFAULT ''")
        except Exception:
            pass


def create_user(name, password, is_admin=False, sheets_id=''):
    with get_db() as conn:
        conn.execute(
            'INSERT INTO users (name, password_hash, is_admin, sheets_id) VALUES (?, ?, ?, ?)',
            (name, generate_password_hash(password), 1 if is_admin else 0, sheets_id)
        )


def update_password(name, new_password):
    with get_db() as conn:
        conn.execute(
            'UPDATE users SET password_hash = ? WHERE name = ?',
            (generate_password_hash(new_password), name)
        )


def update_sheets_id(name, sheets_id):
    with get_db() as conn:
        conn.execute('UPDATE users SET sheets_id = ? WHERE name = ?', (sheets_id, name))


def verify_user(name, password):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM users WHERE name = ?', (name,)).fetchone()
        if row and check_password_hash(row['password_hash'], password):
            return dict(row)
    return None


def get_user(name):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM users WHERE name = ?', (name,)).fetchone()
        return dict(row) if row else None


def get_all_clients():
    with get_db() as conn:
        rows = conn.execute(
            'SELECT id, name, sheets_id FROM users WHERE is_admin = 0 ORDER BY name'
        ).fetchall()
        return [dict(r) for r in rows]


def get_meetings(client_name):
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM meetings WHERE client_name = ? ORDER BY date DESC, id DESC',
            (client_name,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_meeting(meeting_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM meetings WHERE id = ?', (meeting_id,)).fetchone()
        return dict(row) if row else None


def save_meeting(client_name, date, title, audio_filename, transcript, summary):
    with get_db() as conn:
        cur = conn.execute(
            'INSERT INTO meetings (client_name, date, title, audio_filename, transcript, summary) VALUES (?, ?, ?, ?, ?, ?)',
            (client_name, date, title, audio_filename, transcript, summary)
        )
        return cur.lastrowid


def save_coaching_note(client_name, note, remaining, motivation):
    with get_db() as conn:
        from datetime import datetime
        conn.execute(
            'INSERT INTO coaching_notes (client_name, date, note, remaining, motivation) VALUES (?, ?, ?, ?, ?)',
            (client_name, datetime.now().strftime('%Y-%m-%d'), note, remaining, motivation)
        )


def get_coaching_notes(client_name, limit=10):
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM coaching_notes WHERE client_name = ? ORDER BY id DESC LIMIT ?',
            (client_name, limit)
        ).fetchall()
        return [dict(r) for r in rows]
