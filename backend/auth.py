"""Auth logic: PBKDF2 password hashing + session tokens."""
import hashlib
import os
import secrets

from db import get_conn, now

SESSION_TTL = 14 * 24 * 3600  # 14 hari


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2$200000${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, hexhash = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iters))
        return secrets.compare_digest(dk.hex(), hexhash)
    except Exception:
        return False


def create_user(email, password, nama="", sekolah="", mapel="", jenjang=""):
    email = email.strip().lower()
    if not email or "@" not in email:
        return None, "Email tidak valid."
    if len(password) < 6:
        return None, "Kata sandi minimal 6 karakter."
    conn = get_conn()
    try:
        cur = conn.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cur.fetchone():
            return None, "Email sudah terdaftar."
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, nama, sekolah, mapel, jenjang, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (email, hash_password(password), nama, sekolah, mapel, jenjang, now()),
        )
        conn.commit()
        return cur.lastrowid, None
    finally:
        conn.close()


def authenticate(email, password):
    email = email.strip().lower()
    conn = get_conn()
    try:
        cur = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None, "Email atau kata sandi salah."
        return dict(row), None
    finally:
        conn.close()


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires) VALUES (?, ?, ?)",
            (token, user_id, now() + SESSION_TTL),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_user_by_token(token):
    if not token:
        return None
    conn = get_conn()
    try:
        cur = conn.execute(
            "SELECT u.* FROM users u JOIN sessions s ON s.user_id = u.id"
            " WHERE s.token = ? AND s.expires > ?",
            (token, now()),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def destroy_session(token):
    if not token:
        return
    conn = get_conn()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def public_user(row):
    return {
        "id": row["id"],
        "email": row["email"],
        "nama": row["nama"],
        "sekolah": row["sekolah"],
        "mapel": row["mapel"],
        "jenjang": row["jenjang"],
        "npsn": row["npsn"],
        "alamat_sekolah": row["alamat_sekolah"],
        "kota_sekolah": row["kota_sekolah"],
        "nama_kepala": row["nama_kepala"],
        "nip_kepala": row["nip_kepala"],
        "jabatan_guru": row["jabatan_guru"],
        "nip_guru": row["nip_guru"],
        "signature_mode": row["signature_mode"],
        "kop_mode": row["kop_mode"],
        "kop_judul": row["kop_judul"],
        "kop_subjudul": row["kop_subjudul"],
        "kop_telp": row["kop_telp"],
        "kop_email": row["kop_email"],
        "kop_website": row["kop_website"],
        "school_id": row["school_id"],
        "is_platform_admin": bool(row["is_platform_admin"]),
        "quota_used": row["quota_used"],
        "quota_limit": row["quota_limit"],
        "is_pro": bool(row["is_pro"]),
    }


def update_profile(user_id, fields):
    allowed = ("nama", "sekolah", "mapel", "jenjang", "npsn", "alamat_sekolah", "kota_sekolah", "nama_kepala", "nip_kepala", "jabatan_guru", "nip_guru", "signature_mode", "kop_mode", "kop_judul", "kop_subjudul", "kop_telp", "kop_email", "kop_website")
    sets = []
    vals = []
    for k in allowed:
        if k in fields and isinstance(fields[k], str):
            sets.append(f"{k} = ?")
            vals.append(fields[k][:200])
    if not sets:
        return False
    vals.append(user_id)
    conn = get_conn()
    try:
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
        return True
    finally:
        conn.close()
