"""Modul Akun Sekolah GuruWali: sekolah, anggota, undangan, kuota sharing."""
import secrets
import time
import db


def now():
    return int(time.time())


def create_school(admin_user_id, nama, npsn="", alamat="", kota="", telp="", email=""):
    """Buat sekolah baru, admin_user_id jadi admin."""
    conn = db.get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO schools (nama, npsn, alamat, kota, telp, email, admin_user_id, quota_limit, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nama, npsn, alamat, kota, telp, email, admin_user_id, 1000, now()),
        )
        school_id = cur.lastrowid
        conn.execute(
            "INSERT INTO school_members (school_id, user_id, role, joined_at) VALUES (?, ?, 'admin', ?)",
            (school_id, admin_user_id, now()),
        )
        conn.execute("UPDATE users SET school_id = ? WHERE id = ?", (school_id, admin_user_id))
        conn.commit()
        return get_school(school_id)
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_school(school_id):
    conn = db.get_conn()
    try:
        row = conn.execute("SELECT * FROM schools WHERE id = ?", (school_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_school(user_id):
    """Ambil sekolah milik user (jika ada)."""
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT s.* FROM schools s JOIN school_members m ON m.school_id = s.id"
            " WHERE m.user_id = ? LIMIT 1", (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def is_school_admin(user_id, school_id):
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM school_members WHERE school_id = ? AND user_id = ? AND role = 'admin'",
            (school_id, user_id),
        ).fetchone()
        return bool(row)
    finally:
        conn.close()


def generate_invite_code(school_id):
    """Generate kode undangan 8 karakter."""
    code = secrets.token_hex(4).upper()
    conn = db.get_conn()
    try:
        conn.execute("UPDATE schools SET invite_code = ? WHERE id = ?", (code, school_id))
        conn.commit()
        return code
    finally:
        conn.close()


def join_school(user_id, invite_code):
    """Gabung ke sekolah via kode undangan."""
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM schools WHERE invite_code = ?", (invite_code.upper(),)
        ).fetchone()
        if not row:
            return None, "Kode undangan tidak valid."
        school_id = row["id"]
        # Satu akun hanya boleh aktif pada satu sekolah.
        current = conn.execute(
            "SELECT school_id FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if current and current["school_id"]:
            if int(current["school_id"]) == int(school_id):
                return get_school(school_id), "Sudah menjadi anggota."
            return None, "Akun sudah tergabung di sekolah lain. Keluar dari sekolah lama terlebih dahulu."
        conn.execute(
            "INSERT INTO school_members (school_id, user_id, role, joined_at) VALUES (?, ?, 'guru', ?)",
            (school_id, user_id, now()),
        )
        conn.execute("UPDATE users SET school_id = ? WHERE id = ?", (school_id, user_id))
        conn.commit()
        return get_school(school_id), "Berhasil bergabung."
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        conn.close()


def transfer_admin(school_id, current_admin_id, new_admin_id):
    """Alihkan admin sekolah ke anggota lain. Admin lama tetap menjadi guru."""
    if current_admin_id == new_admin_id:
        return False, "Admin baru harus anggota lain."
    if not is_school_admin(current_admin_id, school_id):
        return False, "Hanya admin sekolah yang dapat mengalihkan admin."
    conn = db.get_conn()
    try:
        member = conn.execute(
            "SELECT role FROM school_members WHERE school_id = ? AND user_id = ?",
            (school_id, new_admin_id),
        ).fetchone()
        if not member:
            return False, "Pengguna tersebut bukan anggota sekolah."
        conn.execute("UPDATE school_members SET role = 'guru' WHERE school_id = ? AND user_id = ?", (school_id, current_admin_id))
        conn.execute("UPDATE school_members SET role = 'admin' WHERE school_id = ? AND user_id = ?", (school_id, new_admin_id))
        conn.execute("UPDATE schools SET admin_user_id = ? WHERE id = ?", (new_admin_id, school_id))
        conn.commit()
        return True, "Admin sekolah berhasil dialihkan."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def list_members(school_id):
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT u.id, u.email, u.nama, u.mapel, m.role, m.joined_at"
            " FROM school_members m JOIN users u ON u.id = m.user_id"
            " WHERE m.school_id = ? ORDER BY m.joined_at", (school_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def remove_member(school_id, admin_id, target_user_id):
    """Keluarkan anggota (hanya admin, tidak bisa keluarkan diri sendiri)."""
    if admin_id == target_user_id:
        return False, "Tidak bisa mengeluarkan diri sendiri."
    if not is_school_admin(admin_id, school_id):
        return False, "Hanya admin sekolah."
    conn = db.get_conn()
    try:
        conn.execute(
            "DELETE FROM school_members WHERE school_id = ? AND user_id = ?",
            (school_id, target_user_id),
        )
        # Hanya kosongkan users.school_id jika sekolah yang dihapus memang sekolah aktifnya.
        conn.execute(
            "UPDATE users SET school_id = NULL WHERE id = ? AND school_id = ?",
            (target_user_id, school_id),
        )
        conn.commit()
        return True, "Anggota dikeluarkan."
    finally:
        conn.close()


def check_school_quota(user_id):
    """Cek kuota: pakai kuota sekolah jika user anggota sekolah Pro, else kuota pribadi."""
    school = get_user_school(user_id)
    if school and school.get("is_pro"):
        return {
            "type": "school",
            "used": school["quota_used"] or 0,
            "limit": school["quota_limit"] or 1000,
            "school_name": school["nama"],
        }
    return None


def increment_quota(user_id):
    """Tambah pemakaian kuota (sekolah jika ada, else pribadi)."""
    school = get_user_school(user_id)
    conn = db.get_conn()
    try:
        if school and school.get("is_pro"):
            conn.execute(
                "UPDATE schools SET quota_used = quota_used + 1 WHERE id = ?", (school["id"],)
            )
        else:
            conn.execute(
                "UPDATE users SET quota_used = quota_used + 1 WHERE id = ?", (user_id,)
            )
        conn.commit()
    finally:
        conn.close()
