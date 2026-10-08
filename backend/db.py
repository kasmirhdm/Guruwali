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
    kop_mode TEXT DEFAULT 'admin',
    kop_judul TEXT DEFAULT '',
    kop_subjudul TEXT DEFAULT '',
    kop_telp TEXT DEFAULT '',
    kop_email TEXT DEFAULT '',
    kop_website TEXT DEFAULT '',
    school_id INTEGER,
    is_platform_admin INTEGER DEFAULT 0,
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
CREATE TABLE IF NOT EXISTS schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    npsn TEXT DEFAULT '',
    alamat TEXT DEFAULT '',
    kota TEXT DEFAULT '',
    telp TEXT DEFAULT '',
    email TEXT DEFAULT '',
    invite_code TEXT DEFAULT '',
    admin_user_id INTEGER NOT NULL,
    quota_used INTEGER DEFAULT 0,
    quota_limit INTEGER DEFAULT 1000,
    is_pro INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_schools_invite ON schools(invite_code);
CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,action TEXT NOT NULL,target_type TEXT DEFAULT '',target_id INTEGER,details TEXT DEFAULT '',created_at INTEGER NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);
CREATE TABLE IF NOT EXISTS school_members (
    school_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'guru',
    joined_at INTEGER NOT NULL,
    PRIMARY KEY (school_id, user_id),
    FOREIGN KEY (school_id) REFERENCES schools(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_school_members_user ON school_members(user_id);
CREATE TABLE IF NOT EXISTS dapodik_imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT DEFAULT '',
    rows_imported INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_dapodik_imports_user ON dapodik_imports(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);\nCREATE TABLE IF NOT EXISTS curriculum_subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jenjang TEXT NOT NULL,
    fase TEXT DEFAULT '',
    semester TEXT NOT NULL,
    mapel TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_curriculum_subject_unique ON curriculum_subjects(jenjang,fase,semester,mapel);
CREATE TABLE IF NOT EXISTS curriculum_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    nama TEXT NOT NULL,
    urutan INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    FOREIGN KEY(subject_id) REFERENCES curriculum_subjects(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS curriculum_cp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    kode TEXT DEFAULT '',
    deskripsi TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    FOREIGN KEY(material_id) REFERENCES curriculum_materials(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS curriculum_tp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cp_id INTEGER NOT NULL,
    kode TEXT DEFAULT '',
    deskripsi TEXT NOT NULL,
    urutan INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    FOREIGN KEY(cp_id) REFERENCES curriculum_cp(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_curriculum_material_subject ON curriculum_materials(subject_id);
CREATE INDEX IF NOT EXISTS idx_curriculum_cp_material ON curriculum_cp(material_id);
CREATE INDEX IF NOT EXISTS idx_curriculum_tp_cp ON curriculum_tp(cp_id);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
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
            "kop_mode": "TEXT DEFAULT 'admin'",
            "kop_judul": "TEXT DEFAULT ''",
            "kop_subjudul": "TEXT DEFAULT ''",
            "kop_telp": "TEXT DEFAULT ''",
            "kop_email": "TEXT DEFAULT ''",
            "kop_website": "TEXT DEFAULT ''",
            "school_id": "INTEGER",
            "is_platform_admin": "INTEGER DEFAULT 0",
        }
        for name, definition in migrations.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")
        school_cols = {row["name"] for row in conn.execute("PRAGMA table_info(schools)").fetchall()}
        school_migrations = {
            "telp": "TEXT DEFAULT ''", "email": "TEXT DEFAULT ''", "invite_code": "TEXT DEFAULT ''",
            "quota_used": "INTEGER DEFAULT 0", "quota_limit": "INTEGER DEFAULT 1000", "is_pro": "INTEGER DEFAULT 0",
            "nama_kepala": "TEXT DEFAULT ''", "nip_kepala": "TEXT DEFAULT ''",
            "kop_judul": "TEXT DEFAULT ''", "kop_subjudul": "TEXT DEFAULT ''", "kop_website": "TEXT DEFAULT ''"
        }
        for name, definition in school_migrations.items():
            if name not in school_cols:
                conn.execute(f"ALTER TABLE schools ADD COLUMN {name} {definition}")
        conn.commit()
    finally:
        conn.close()

def now():
    return int(time.time())
