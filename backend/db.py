"""SQLite helpers untuk GuruWali."""
import os
import sqlite3
import time

DB_PATH = os.environ.get("GURUWALI_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nama TEXT DEFAULT '',
    sekolah TEXT DEFAULT '',
    mapel TEXT DEFAULT '',
    jenjang TEXT DEFAULT '',
    npsn TEXT DEFAULT '',
    alamat_sekolah TEXT DEFAULT '',
    kota_sekolah TEXT DEFAULT '',
    nama_kepala TEXT DEFAULT '',
    nip_kepala TEXT DEFAULT '',
    jabatan_guru TEXT DEFAULT 'Guru',
    nip_guru TEXT DEFAULT '',
    signature_mode TEXT DEFAULT 'guru-kepala',
    quota_used INTEGER DEFAULT 0,
    quota_limit INTEGER DEFAULT 5,
    is_pro INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    is_favorite INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        # Migrasi ringan untuk instalasi lama yang sudah memiliki users.
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        migrations = {
            "npsn": "TEXT DEFAULT ''",
            "alamat_sekolah": "TEXT DEFAULT ''",
            "kota_sekolah": "TEXT DEFAULT ''",
            "nama_kepala": "TEXT DEFAULT ''",
            "nip_kepala": "TEXT DEFAULT ''",
            "jabatan_guru": "TEXT DEFAULT 'Guru'",
            "nip_guru": "TEXT DEFAULT ''",
            "signature_mode": "TEXT DEFAULT 'guru-kepala'",
        }
        for name, definition in migrations.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")
        conn.commit()
    finally:
        conn.close()


def now():
    return int(time.time())
