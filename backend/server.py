#!/usr/bin/env python3
"""GuruWali API server — stdlib saja, tanpa dependensi berat.

Jalankan:  python3 server.py
Env:       GURUWALI_PORT (default 8081), GURUWALI_HOST (default 127.0.0.1),
           GURUWALI_DB (path sqlite),
           GURUWALI_AI_KEY (API key Invibuilder — prioritas),
           GURUWALI_GEMINI_KEY (API key Gemini — fallback),
           GURUWALI_AI_BASE (base URL kustom, opsional),
           GURUWALI_MODEL (model default, opsional)
"""
import json
import os
import re
import sys
import sqlite3
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ai
import auth
import google_auth
import db
import school
import dapodik
import exporter
import prompts
import platform_admin

HOST = os.environ.get("GURUWALI_HOST", "127.0.0.1")
PORT = int(os.environ.get("GURUWALI_PORT", "8081"))
SECURE_COOKIE = os.environ.get("GURUWALI_SECURE_COOKIE", "").lower() in ("1", "true", "yes", "on")
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# Rate limit per IP untuk melindungi API dari abuse.
RATE_WINDOW = 60
RATE_MAX = 60
AI_RATE_MAX = 20
AUTH_RATE_MAX = 10
_rate = {}


def _client_ip(handler):
    # Ambil IP asli dari header proxy
    fwd = handler.headers.get("X-Real-IP") or handler.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return handler.client_address[0]


def rate_ok(ip, bucket="general", limit=RATE_MAX):
    t = time.time()
    key = (bucket, ip)
    hits = [x for x in _rate.get(key, []) if t - x < RATE_WINDOW]
    if len(hits) >= limit:
        return False
    hits.append(t)
    _rate[key] = hits
    return True


MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "GuruWali/0.1"

    # ---------- helpers ----------
    def _send_json(self, code, obj, set_cookie=None, clear_cookie=False):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if SECURE_COOKIE:
            self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
        if set_cookie:
            self.send_header(
                "Set-Cookie",
                f"gw_session={set_cookie}; Path=/; HttpOnly; SameSite=Lax; Max-Age={14*24*3600}" + ("; Secure" if SECURE_COOKIE else ""),
            )
        if clear_cookie:
            self.send_header("Set-Cookie", "gw_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0" + ("; Secure" if SECURE_COOKIE else ""))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            n = 0
        if n <= 0 or n > 1_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            return {}

    def _token(self):
        ah = self.headers.get("Authorization", "")
        if ah.lower().startswith("bearer "):
            return ah[7:].strip()
        for part in (self.headers.get("Cookie", "") or "").split(";"):
            part = part.strip()
            if part.startswith("gw_session="):
                return part[len("gw_session="):].strip()
        return ""

    def _user(self):
        return auth.get_user_by_token(self._token())

    def _serve_static(self, path):
        rel = urllib.parse.unquote(path)
        if rel.startswith("/uploads/"):
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            name = rel[len("/uploads/")]
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), "uploads"))
            full = os.path.abspath(os.path.join(root, name))
            # File gambar hasil generate disimpan dengan pola img_<user_id>_<timestamp>.png.
            # Batasi akses ke pemilik file agar user lain tidak dapat menebak URL gambar.
            mimg = re.match(r"^img_(\d+)_\d+_[a-z0-9]+\.(?:png|jpg|jpeg|webp)$", name, re.IGNORECASE)
            if not mimg or int(mimg.group(1)) != int(user["id"]):
                self._send_json(404, {"error": "Tidak ditemukan."})
                return
            if not full.startswith(root + os.sep) or not os.path.isfile(full):
                self._send_json(404, {"error": "Tidak ditemukan."})
                return
            try:
                with open(full, "rb") as f:
                    body = f.read()
            except OSError:
                self._send_json(404, {"error": "Tidak ditemukan."})
                return
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(os.path.splitext(full)[1].lower(), "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "private, max-age=3600")
            self.end_headers()
            self.wfile.write(body)
            return
        if rel == "/":
            rel = "/index.html"
        # cegah path traversal
        full = os.path.normpath(os.path.join(FRONTEND_DIR, rel.lstrip("/")))
        if not full.startswith(FRONTEND_DIR) or not os.path.isfile(full):
            self._send_json(404, {"error": "Tidak ditemukan."})
            return
        ext = os.path.splitext(full)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")
        try:
            with open(full, "rb") as f:
                body = f.read()
        except OSError:
            self._send_json(404, {"error": "Tidak ditemukan."})
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cache-Control", "no-cache" if ext == ".html" else "public, max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")

    # ---------- routing ----------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/"):
            if not rate_ok(_client_ip(self), "general", RATE_MAX):
                self._send_json(429, {"error": "Terlalu banyak permintaan. Coba lagi sebentar."})
                return
            self._api_get(path, urllib.parse.parse_qs(parsed.query))
        else:
            self._serve_static(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._send_json(404, {"error": "Tidak ditemukan."})
            return
        bucket = "ai" if parsed.path in ("/api/generate", "/api/generate-image") else ("auth" if parsed.path in ("/api/login", "/api/register") else "general")
        limit = AI_RATE_MAX if bucket == "ai" else (AUTH_RATE_MAX if bucket == "auth" else RATE_MAX)
        if not rate_ok(_client_ip(self), bucket, limit):
            self._send_json(429, {"error": "Terlalu banyak permintaan. Coba lagi sebentar."})
            return
        self._api_post(parsed.path)

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._send_json(404, {"error": "Tidak ditemukan."})
            return
        if not rate_ok(_client_ip(self)):
            self._send_json(429, {"error": "Terlalu banyak permintaan. Coba lagi sebentar."})
            return
        self._api_put(parsed.path)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._send_json(404, {"error": "Tidak ditemukan."})
            return
        if not rate_ok(_client_ip(self)):
            self._send_json(429, {"error": "Terlalu banyak permintaan. Coba lagi sebentar."})
            return
        m = re.match(r"^/api/documents/(\d+)$", parsed.path)
        if not m:
            self._send_json(404, {"error": "Tidak ditemukan."})
            return
        user = self._user()
        if not user:
            self._send_json(401, {"error": "Belum masuk."})
            return
        conn = db.get_conn()
        try:
            cur = conn.execute(
                "DELETE FROM documents WHERE id = ? AND user_id = ?", (int(m.group(1)), user["id"])
            )
            conn.commit()
            if cur.rowcount == 0:
                self._send_json(404, {"error": "Dokumen tidak ditemukan."})
            else:
                self._send_json(200, {"ok": True})
        finally:
            conn.close()

    # ---------- API ----------
    def _send_file(self, filename, data, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Content-Disposition",
            'attachment; filename="%s"' % filename.replace('"', ""),
        )
        self.end_headers()
        self.wfile.write(data)

    def _export_document(self, doc_id, fmt):
        user = self._user()
        if not user:
            self._send_json(401, {"error": "Belum masuk."})
            return
        # Export hanya untuk Pro (perorangan atau via sekolah)
        is_pro = user.get("is_pro")
        if not is_pro:
            sq = school.check_school_quota(user["id"])
            is_pro = bool(sq)
        if not is_pro:
            self._send_json(403, {"error": "Export Word/PDF hanya untuk pengguna Pro. Upgrade di menu Upgrade!"})
            return
        conn = db.get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ? AND user_id = ?",
                (doc_id, user["id"]),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            self._send_json(404, {"error": "Dokumen tidak ditemukan."})
            return
        title = row["title"] or "Dokumen GuruWali"
        safe = re.sub(r"[^\w\- ]+", "", title).strip().replace(" ", "-")[:60] or "dokumen"
        try:
            if fmt == "docx":
                data = exporter.to_docx(title, row["content"] or "")
                self._send_file(safe + ".docx",
                                data,
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            elif fmt == "pdf":
                data = exporter.to_pdf(title, row["content"] or "")
                self._send_file(safe + ".pdf", data, "application/pdf")
            else:
                self._send_json(400, {"error": "Format harus docx atau pdf."})
        except ImportError as e:
            self._send_json(500, {"error": "Library export belum terinstal: %s" % e})
        except Exception as e:
            self._send_json(500, {"error": "Gagal membuat file: %s" % e})

    def _redirect(self, url, set_cookie=None):
        self.send_response(302)
        self.send_header("Location", url)
        if set_cookie:
            secure = "; Secure" if SECURE_COOKIE else ""
            self.send_header("Set-Cookie",
                f"gw_session={set_cookie}; Path=/; HttpOnly; SameSite=Lax; Max-Age={14*24*3600}" + secure)
        self.end_headers()

    def _api_get(self, path, qs):
        # Google OAuth login
        if path == "/api/auth/google":
            if not google_auth.is_configured():
                self._send_json(500, {"error": "Google login belum dikonfigurasi."})
                return
            self._redirect(google_auth.get_login_url())
            return
        if path == "/api/auth/google/callback":
            code = (qs.get("code") or [None])[0]
            state = (qs.get("state") or [None])[0]
            err = (qs.get("error") or [None])[0]
            if err or not code:
                self._redirect("/app.html#masuk?error=" + (err or "batal"))
                return
            if not google_auth.verify_state(state):
                self._redirect("/app.html#masuk?error=state")
                return
            userinfo, uerr = google_auth.exchange_code(code)
            if uerr or not userinfo or not userinfo.get("email"):
                self._redirect("/app.html#masuk?error=gagal")
                return
            email = userinfo["email"].lower().strip()
            nama = userinfo.get("name", email.split("@")[0])
            # Cari atau buat user
            conn = db.get_conn()
            try:
                row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
                if row:
                    uid = row["id"]
                else:
                    from datetime import datetime
                    cur = conn.execute(
                        "INSERT INTO users (email, password_hash, nama, quota_limit, created_at) VALUES (?,?,?,?,?)",
                        (email, "google-oauth", nama, 5, datetime.now().isoformat()))
                    conn.commit()
                    uid = cur.lastrowid
                user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
            finally:
                conn.close()
            token = auth.create_session(uid)
            self._redirect("/app.html#beranda", set_cookie=token)
            return
        # Master Data GET - hanya platform admin
        if path == "/api/platform-admin/master-cp":
            user = self._user()
            if not user or not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses ditolak."}); return
            conn = db.get_conn()
            try:
                rows = conn.execute("SELECT * FROM master_cp ORDER BY jenjang, fase, mapel").fetchall()
                self._send_json(200, {"data": [dict(r) for r in rows]})
            finally: conn.close()
            return
        if path == "/api/platform-admin/master-tp":
            user = self._user()
            if not user or not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses ditolak."}); return
            conn = db.get_conn()
            try:
                rows = conn.execute("SELECT * FROM master_tp ORDER BY jenjang, fase, mapel").fetchall()
                self._send_json(200, {"data": [dict(r) for r in rows]})
            finally: conn.close()
            return
        if path == "/api/me":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            self._send_json(200, {"user": auth.public_user(user)})
            return

        m = re.match(r"^/api/documents/(\d+)$", path)
        if m:
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            conn = db.get_conn()
            try:
                cur = conn.execute(
                    "SELECT * FROM documents WHERE id = ? AND user_id = ?",
                    (int(m.group(1)), user["id"]),
                )
                row = cur.fetchone()
            finally:
                conn.close()
            if not row:
                self._send_json(404, {"error": "Dokumen tidak ditemukan."})
                return
            self._send_json(200, {"document": _doc(row)})
            return

        m = re.match(r"^/api/documents/(\d+)/export$", path)
        if m:
            fmt = (qs.get("format", [""])[0] or "").lower()
            self._export_document(int(m.group(1)), fmt)
            return

        if path == "/api/billing/packages":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."}); return
            conn = db.get_conn()
            try:
                rows = conn.execute(
                    "SELECT id,kode,nama,harga,kredit,masa_hari,target FROM billing_packages WHERE aktif=1 ORDER BY harga"
                ).fetchall()
            finally:
                conn.close()
            self._send_json(200, {"packages": [dict(x) for x in rows]})
            return

        if path == "/api/billing/orders":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."}); return
            conn = db.get_conn()
            try:
                rows = conn.execute(
                    """SELECT o.id,o.order_no,o.amount,o.kredit,o.target,o.status,o.payment_ref,o.paid_at,o.created_at,
                              p.kode,p.nama
                       FROM billing_orders o JOIN billing_packages p ON p.id=o.package_id
                       WHERE o.user_id=? ORDER BY o.id DESC LIMIT 30""", (user["id"],)
                ).fetchall()
            finally:
                conn.close()
            self._send_json(200, {"orders": [dict(x) for x in rows]})
            return

        if path == "/api/models":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            self._send_json(200, {
                "provider": ai.provider(),
                "models": ai.available_models(),
                "routing": ai.routing_info(),
                "default_model": ai.default_model(),
            })
            return

        if path == "/api/platform-admin/curriculum/export":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            try:
                vid=int(qs.get("version_id",["0"])[0])
            except Exception:
                vid=0
            conn=db.get_conn()
            try:
                v=conn.execute("SELECT * FROM curriculum_versions WHERE id=?",(vid,)).fetchone()
                if not v:
                    self._send_json(404, {"error":"Versi kurikulum tidak ditemukan."}); return
                subjects=[]
                for s in conn.execute("SELECT * FROM curriculum_subjects WHERE version_id=? ORDER BY id",(vid,)).fetchall():
                    mats=[]
                    for m in conn.execute("SELECT * FROM curriculum_materials WHERE subject_id=? ORDER BY urutan,id",(s["id"],)).fetchall():
                        cps=[]
                        for cp in conn.execute("SELECT * FROM curriculum_cp WHERE material_id=? ORDER BY id",(m["id"],)).fetchall():
                            tps=[dict(x) for x in conn.execute("SELECT kode,deskripsi,urutan FROM curriculum_tp WHERE cp_id=? ORDER BY urutan,id",(cp["id"],)).fetchall()]
                            cps.append({"kode":cp["kode"],"deskripsi":cp["deskripsi"],"tp":tps})
                        mats.append({"nama":m["nama"],"urutan":m["urutan"],"cp":cps})
                    subjects.append({"jenjang":s["jenjang"],"fase":s["fase"],"semester":s["semester"],"mapel":s["mapel"],"materi":mats})
                payload={"format":"guruwali-master-kurikulum-v1","exported_at":db.now(),"version":{"nama":v["nama"],"tahun_ajaran":v["tahun_ajaran"]},"subjects":subjects}
            finally:
                conn.close()
            data=json.dumps(payload,ensure_ascii=False).encode("utf-8")
            self._send_file("backup-master-kurikulum.json",data,"application/json; charset=utf-8")
            return

        if path == "/api/platform-admin/curriculum-versions":
            user=self._user()
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            conn=db.get_conn()
            try:
                rows=conn.execute("SELECT * FROM curriculum_versions ORDER BY id DESC").fetchall()
            finally: conn.close()
            self._send_json(200, {"versions":[dict(r) for r in rows]}); return

        if path == "/api/platform-admin/curriculum":
            user=self._user()
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            jenjang=str(qs.get("jenjang",[""])[0] or "")
            semester=str(qs.get("semester",[""])[0] or "")
            if semester.startswith("1"): semester="1"
            elif semester.startswith("2"): semester="2"
            elif semester.lower().startswith("ganjil"): semester="1"
            elif semester.lower().startswith("genap"): semester="2"
            mapel=str(qs.get("mapel",[""])[0] or "")
            version_id=int(qs.get("version_id",["0"])[0] or 0)
            conn=db.get_conn()
            try:
                if version_id:
                    subjects=conn.execute("SELECT * FROM curriculum_subjects WHERE version_id=? AND (?='' OR jenjang=?) AND (?='' OR semester=?) AND (?='' OR mapel=?) ORDER BY jenjang,semester,mapel",
                    (version_id,jenjang,jenjang,semester,semester,mapel,mapel)).fetchall()
                else:
                    subjects=conn.execute("SELECT * FROM curriculum_subjects WHERE version_id=(SELECT id FROM curriculum_versions WHERE aktif=1 LIMIT 1) AND (?='' OR jenjang=?) AND (?='' OR semester=?) AND (?='' OR mapel=?) ORDER BY jenjang,semester,mapel",
                        (jenjang,jenjang,semester,semester,mapel,mapel)).fetchall()
                result=[]
                for s in subjects:
                    mats=conn.execute("SELECT * FROM curriculum_materials WHERE subject_id=? ORDER BY urutan,nama",(s["id"],)).fetchall()
                    md=[]
                    for m in mats:
                        cps=conn.execute("SELECT * FROM curriculum_cp WHERE material_id=? ORDER BY id",(m["id"],)).fetchall()
                        cd=[]
                        for cp in cps:
                            tps=conn.execute("SELECT * FROM curriculum_tp WHERE cp_id=? ORDER BY urutan,id",(cp["id"],)).fetchall()
                            cd.append({**dict(cp),"tp":[dict(t) for t in tps]})
                        md.append({**dict(m),"cp":cd})
                    result.append({**dict(s),"materi":md})
            finally: conn.close()
            self._send_json(200, {"data":result}); return

        if path == "/api/master-curriculum":
            user=self._user()
            if not user:
                self._send_json(401, {"error":"Belum masuk."}); return
            jenjang=str(qs.get("jenjang",[""])[0] or "")
            semester=str(qs.get("semester",[""])[0] or "")
            if semester.startswith("1"): semester="1"
            elif semester.startswith("2"): semester="2"
            elif semester.lower().startswith("ganjil"): semester="1"
            elif semester.lower().startswith("genap"): semester="2"
            mapel=str(qs.get("mapel",[""])[0] or "")
            materi=str(qs.get("materi",[""])[0] or "")
            version_id=int(qs.get("version_id",["0"])[0] or 0)
            conn=db.get_conn()
            try:
                if not version_id:
                    vr=conn.execute("SELECT id FROM curriculum_versions WHERE aktif=1 LIMIT 1").fetchone()
                    version_id=vr["id"] if vr else 0
                s=conn.execute("SELECT * FROM curriculum_subjects WHERE version_id=? AND jenjang=? AND semester=? AND mapel=? LIMIT 1",(version_id,jenjang,semester,mapel)).fetchone()
                data=[]
                if s:
                    mats=conn.execute("SELECT * FROM curriculum_materials WHERE subject_id=? AND (?='' OR nama=?) ORDER BY urutan,nama",(s["id"],materi,materi)).fetchall()
                    for m in mats:
                        cps=conn.execute("SELECT * FROM curriculum_cp WHERE material_id=? ORDER BY id",(m["id"],)).fetchall()
                        for cp in cps:
                            tps=conn.execute("SELECT * FROM curriculum_tp WHERE cp_id=? ORDER BY urutan,id",(cp["id"],)).fetchall()
                            data.append({"materi":m["nama"],"cp":dict(cp),"tp":[dict(t) for t in tps]})
            finally: conn.close()
            self._send_json(200, {"data":data}); return

        if path == "/api/platform-admin/dashboard":
            user=self._user()
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            self._send_json(200, {"dashboard":platform_admin.dashboard()}); return
        if path == "/api/platform-admin/users":
            user=self._user()
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            self._send_json(200, {"users":platform_admin.users()}); return
        if path == "/api/platform-admin/schools":
            user=self._user()
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            self._send_json(200, {"schools":platform_admin.schools()}); return
        if path == "/api/platform-admin/audit":
            user=self._user()
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            self._send_json(200, {"logs":platform_admin.recent_audit()}); return
        if path == "/api/school":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            s = school.get_user_school(user["id"])
            if not s:
                self._send_json(200, {"school": None})
                return
            members = school.list_members(s["id"])
            self._send_json(200, {"school": s, "members": members,
                "is_admin": school.is_school_admin(user["id"], s["id"])})
            return
        if path == "/api/documents":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            ftype = (qs.get("type", [""])[0] or "")[:50]
            fav = qs.get("favorite", [""])[0] == "1"
            q = "SELECT * FROM documents WHERE user_id = ?"
            vals = [user["id"]]
            if ftype:
                q += " AND type = ?"
                vals.append(ftype)
            if fav:
                q += " AND is_favorite = 1"
            q += " ORDER BY updated_at DESC LIMIT 200"
            conn = db.get_conn()
            try:
                rows = conn.execute(q, vals).fetchall()
            finally:
                conn.close()
            self._send_json(200, {"documents": [_doc(r) for r in rows]})
            return

        self._send_json(404, {"error": "Tidak ditemukan."})

    def _api_post(self, path):
        body = self._read_json()

        if path == "/api/register":
            uid, err = auth.create_user(
                body.get("email", ""), body.get("password", ""),
                body.get("nama", ""), body.get("sekolah", ""),
                body.get("mapel", ""), body.get("jenjang", ""),
            )
            if err:
                self._send_json(400, {"error": err})
                return
            token = auth.create_session(uid)
            user = auth.get_user_by_token(token)
            self._send_json(200, {"user": auth.public_user(user)}, set_cookie=token)
            return

        if path == "/api/login":
            user, err = auth.authenticate(body.get("email", ""), body.get("password", ""))
            if err:
                self._send_json(401, {"error": err})
                return
            token = auth.create_session(user["id"])
            self._send_json(200, {"user": auth.public_user(user)}, set_cookie=token)
            return

        if path == "/api/logout":
            auth.destroy_session(self._token())
            self._send_json(200, {"ok": True}, clear_cookie=True)
            return

        if path == "/api/generate":
            return self._handle_generate(body)

        if path == "/api/generate-image":
            return self._api_generate_image(body)

        user = self._user()
        if not user:
            self._send_json(401, {"error": "Belum masuk."})
            return

        if path == "/api/billing/order":
            package_id = int(body.get("package_id") or 0)
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."}); return
            conn = db.get_conn()
            try:
                pkg = conn.execute(
                    "SELECT * FROM billing_packages WHERE id=? AND aktif=1", (package_id,)
                ).fetchone()
                if not pkg:
                    self._send_json(404, {"error": "Paket tidak ditemukan."}); return
                # Paket sekolah hanya dapat dibuat oleh anggota/admin sekolah pada tahap pembayaran sekolah.
                if pkg["target"] != "user":
                    self._send_json(400, {"error": "Paket ini menggunakan pembayaran sekolah."}); return
                order_no = "GW" + time.strftime("%Y%m%d%H%M%S") + ("%04d" % (int(time.time()*1000) % 10000))
                cur = conn.execute(
                    """INSERT INTO billing_orders(order_no,user_id,package_id,amount,kredit,target,status,created_at)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (order_no,user["id"],pkg["id"],pkg["harga"],pkg["kredit"],pkg["target"],"pending",db.now())
                )
                conn.commit()
                self._send_json(201, {"order": {
                    "id": cur.lastrowid, "order_no": order_no, "amount": pkg["harga"],
                    "kredit": pkg["kredit"], "status": "pending", "package": pkg["nama"]
                }})
            finally:
                conn.close()
            return

        if path == "/api/billing/webhook":
            # Endpoint payment-gateway neutral. Gateway harus mengirim secret yang sama.
            secret = os.environ.get("GURUWALI_PAYMENT_WEBHOOK_SECRET", "")
            if not secret or str(body.get("secret") or "") != secret:
                self._send_json(403, {"error": "Webhook ditolak."}); return
            order_no = str(body.get("order_no") or "").strip()
            status = str(body.get("status") or "").lower()
            if status not in ("paid","settlement","success"):
                self._send_json(200, {"ok": True, "ignored": True}); return
            conn = db.get_conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                order = conn.execute(
                    "SELECT o.*,p.kode,p.masa_hari FROM billing_orders o JOIN billing_packages p ON p.id=o.package_id WHERE o.order_no=?",
                    (order_no,)
                ).fetchone()
                if not order:
                    conn.rollback(); self._send_json(404, {"error": "Order tidak ditemukan."}); return
                if order["status"] == "paid":
                    conn.commit(); self._send_json(200, {"ok": True, "already_paid": True}); return
                cur = conn.execute(
                    "UPDATE billing_orders SET status='paid',payment_ref=?,paid_at=? WHERE id=? AND status='pending'",
                    (str(body.get("payment_ref") or "")[:120], db.now(), order["id"])
                )
                if cur.rowcount != 1:
                    conn.rollback(); self._send_json(409, {"error": "Order sedang diproses."}); return
                # Kredit masuk atomik dan tidak boleh melebihi limit paket.
                u = conn.execute("SELECT quota_used,quota_limit FROM users WHERE id=?", (order["user_id"],)).fetchone()
                if not u:
                    conn.rollback(); self._send_json(404, {"error": "Pengguna tidak ditemukan."}); return
                new_limit = max(int(u["quota_limit"] or 0), int(order["kredit"]))
                conn.execute(
                    "UPDATE users SET is_pro=1,quota_used=0,quota_limit=? WHERE id=?",
                    (new_limit, order["user_id"])
                )
                conn.commit()
                self._send_json(200, {"ok": True, "order_no": order_no, "kredit": order["kredit"], "quota_limit": new_limit})
            finally:
                conn.close()
            return

        if path == "/api/platform-admin/curriculum/import":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            payload=body if isinstance(body,dict) else {}
            if payload.get("format")!="guruwali-master-kurikulum-v1":
                self._send_json(400, {"error":"Format backup tidak dikenali."}); return
            src=payload.get("version") or {}
            nama=str(src.get("nama","")).strip()[:120]
            tahun=str(src.get("tahun_ajaran","")).strip()[:30]
            subjects=payload.get("subjects")
            if not nama or not isinstance(subjects,list):
                self._send_json(400, {"error":"Backup tidak lengkap."}); return
            if len(subjects)>500:
                self._send_json(400, {"error":"Backup terlalu besar (maksimal 500 mapel)."}); return
            conn=db.get_conn()
            try:
                cur=conn.execute("INSERT INTO curriculum_versions(nama,tahun_ajaran,aktif,created_at) VALUES(?,?,0,?)",(nama+" (Restore)",tahun,db.now()))
                vid=cur.lastrowid; count={"subject":0,"material":0,"cp":0,"tp":0}
                for s in subjects:
                    sc=conn.execute("INSERT INTO curriculum_subjects(version_id,jenjang,fase,semester,mapel,created_at) VALUES(?,?,?,?,?,?)",
                        (vid,str(s.get("jenjang",""))[:30],str(s.get("fase",""))[:10],str(s.get("semester",""))[:30],str(s.get("mapel",""))[:120],db.now()))
                    count["subject"]+=1
                    for m in (s.get("materi") or [])[:500]:
                        mc=conn.execute("INSERT INTO curriculum_materials(subject_id,nama,urutan,created_at) VALUES(?,?,?,?)",(sc.lastrowid,str(m.get("nama",""))[:200],int(m.get("urutan",0)),db.now()))
                        count["material"]+=1
                        for cp in (m.get("cp") or [])[:500]:
                            cc=conn.execute("INSERT INTO curriculum_cp(material_id,kode,deskripsi,created_at) VALUES(?,?,?,?)",(mc.lastrowid,str(cp.get("kode",""))[:50],str(cp.get("deskripsi",""))[:10000],db.now()))
                            count["cp"]+=1
                            for tp in (cp.get("tp") or [])[:500]:
                                conn.execute("INSERT INTO curriculum_tp(cp_id,kode,deskripsi,urutan,created_at) VALUES(?,?,?,?,?)",(cc.lastrowid,str(tp.get("kode",""))[:50],str(tp.get("deskripsi",""))[:10000],int(tp.get("urutan",0)),db.now()))
                                count["tp"]+=1
                conn.commit()
                platform_admin.audit(user["id"],"import_curriculum_version","curriculum_version",vid,count)
                self._send_json(200,{"ok":True,"id":vid,"count":count})
            except sqlite3.IntegrityError as e:
                conn.rollback(); self._send_json(400,{"error":"Data backup memiliki mapel duplikat atau format tidak sesuai: "+str(e)})
            except Exception as e:
                conn.rollback(); self._send_json(400,{"error":str(e)})
            finally:
                conn.close()
            return

        if path == "/api/platform-admin/curriculum/save":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            action=str(body.get("action",""))
            conn=db.get_conn()
            try:
                if action=="version":
                    nama=str(body.get("nama","")).strip()[:120]
                    tahun=str(body.get("tahun_ajaran","")).strip()[:30]
                    if not nama:
                        self._send_json(400, {"error":"Nama versi wajib diisi."}); return
                    if body.get("id"):
                        cur=conn.execute("UPDATE curriculum_versions SET nama=?,tahun_ajaran=? WHERE id=?",(nama,tahun,int(body.get("id"))))
                    else:
                        cur=conn.execute("INSERT INTO curriculum_versions(nama,tahun_ajaran,aktif,created_at) VALUES(?,?,0,?)",(nama,tahun,db.now()))
                elif action=="activate-version":
                    vid=int(body.get("id",0))
                    if not conn.execute("SELECT 1 FROM curriculum_versions WHERE id=?",(vid,)).fetchone():
                        self._send_json(404, {"error":"Versi tidak ditemukan."}); return
                    conn.execute("UPDATE curriculum_versions SET aktif=0")
                    cur=conn.execute("UPDATE curriculum_versions SET aktif=1 WHERE id=?",(vid,))
                elif action=="subject":
                    vid=int(body.get("version_id",0))
                    if not vid:
                        vr=conn.execute("SELECT id FROM curriculum_versions WHERE aktif=1 LIMIT 1").fetchone()
                        vid=vr["id"] if vr else 0
                    if not vid:
                        self._send_json(400, {"error":"Versi kurikulum belum tersedia."}); return
                    if body.get("id"):
                        cur=conn.execute("UPDATE curriculum_subjects SET version_id=?,jenjang=?,fase=?,semester=?,mapel=? WHERE id=?",(vid,str(body.get("jenjang",""))[:30],str(body.get("fase",""))[:10],str(body.get("semester",""))[:30],str(body.get("mapel",""))[:120],int(body.get("id"))))
                    else:
                        cur=conn.execute("INSERT INTO curriculum_subjects(version_id,jenjang,fase,semester,mapel,created_at) VALUES(?,?,?,?,?,?)",
                            (vid,str(body.get("jenjang",""))[:30],str(body.get("fase",""))[:10],str(body.get("semester",""))[:30],str(body.get("mapel",""))[:120],db.now()))
                elif action=="material":
                    subject_id=int(body.get("subject_id",0))
                    nama=str(body.get("nama","")).strip()[:200]
                    if not subject_id or not nama or not conn.execute("SELECT 1 FROM curriculum_subjects WHERE id=?",(subject_id,)).fetchone():
                        self._send_json(400, {"error":"Mapel induk materi tidak valid atau nama materi kosong."}); return
                    if body.get("id"): cur=conn.execute("UPDATE curriculum_materials SET subject_id=?,nama=?,urutan=? WHERE id=?",(subject_id,nama,int(body.get("urutan",0)),int(body.get("id"))))
                    else: cur=conn.execute("INSERT INTO curriculum_materials(subject_id,nama,urutan,created_at) VALUES(?,?,?,?)",
                        (subject_id,nama,int(body.get("urutan",0)),db.now()))
                elif action=="cp":
                    material_id=int(body.get("material_id",0))
                    kode=str(body.get("kode","")).strip()[:50]
                    deskripsi=str(body.get("deskripsi","")).strip()[:10000]
                    if not material_id or not deskripsi or not conn.execute("SELECT 1 FROM curriculum_materials WHERE id=?",(material_id,)).fetchone():
                        self._send_json(400, {"error":"Materi induk CP tidak valid atau deskripsi CP kosong."}); return
                    if body.get("id"): cur=conn.execute("UPDATE curriculum_cp SET material_id=?,kode=?,deskripsi=? WHERE id=?",(material_id,kode,deskripsi,int(body.get("id"))))
                    else: cur=conn.execute("INSERT INTO curriculum_cp(material_id,kode,deskripsi,created_at) VALUES(?,?,?,?)",
                        (material_id,kode,deskripsi,db.now()))
                elif action=="tp":
                    cp_id=int(body.get("cp_id",0))
                    kode=str(body.get("kode","")).strip()[:50]
                    deskripsi=str(body.get("deskripsi","")).strip()[:10000]
                    if not cp_id or not deskripsi or not conn.execute("SELECT 1 FROM curriculum_cp WHERE id=?",(cp_id,)).fetchone():
                        self._send_json(400, {"error":"CP induk TP tidak valid atau deskripsi TP kosong."}); return
                    if body.get("id"): cur=conn.execute("UPDATE curriculum_tp SET cp_id=?,kode=?,deskripsi=?,urutan=? WHERE id=?",(cp_id,kode,deskripsi,int(body.get("urutan",0)),int(body.get("id"))))
                    else: cur=conn.execute("INSERT INTO curriculum_tp(cp_id,kode,deskripsi,urutan,created_at) VALUES(?,?,?,?,?)",
                        (cp_id,kode,deskripsi,int(body.get("urutan",0)),db.now()))
                else:
                    self._send_json(400, {"error":"Jenis master tidak dikenal."}); return
                conn.commit()
                try:
                    platform_admin.audit(user["id"], "save_curriculum_"+action, "curriculum_"+action, cur.lastrowid, {
                        "version_id": body.get("version_id"),
                        "parent_id": body.get("subject_id") or body.get("material_id") or body.get("cp_id")
                    })
                except Exception:
                    pass
                self._send_json(200, {"ok":True,"id":cur.lastrowid})
            except sqlite3.IntegrityError as e:
                conn.rollback()
                msg=str(e)
                if "idx_curriculum_subject_unique" in msg or "UNIQUE constraint failed: curriculum_subjects" in msg:
                    msg="Mapel dengan jenjang, fase, semester, dan nama yang sama sudah ada pada versi ini."
                self._send_json(400, {"error":msg})
            except Exception as e:
                conn.rollback(); self._send_json(400, {"error":str(e)})
            finally: conn.close()
            return

        if path == "/api/platform-admin/curriculum/clone-version":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            src=int(body.get("source_version_id",0))
            nama=str(body.get("nama","")).strip()[:120]
            tahun=str(body.get("tahun_ajaran","")).strip()[:30]
            if not src or not nama:
                self._send_json(400, {"error":"Versi sumber dan nama versi baru wajib diisi."}); return
            conn=db.get_conn()
            try:
                if not conn.execute("SELECT 1 FROM curriculum_versions WHERE id=?",(src,)).fetchone():
                    self._send_json(404, {"error":"Versi sumber tidak ditemukan."}); return
                cur=conn.execute("INSERT INTO curriculum_versions(nama,tahun_ajaran,aktif,created_at) VALUES(?,?,0,?)",(nama,tahun,db.now()))
                dst=cur.lastrowid
                subjects=conn.execute("SELECT * FROM curriculum_subjects WHERE version_id=? ORDER BY id",(src,)).fetchall()
                for s in subjects:
                    sc=conn.execute("INSERT INTO curriculum_subjects(version_id,jenjang,fase,semester,mapel,created_at) VALUES(?,?,?,?,?,?)",(dst,s["jenjang"],s["fase"],s["semester"],s["mapel"],db.now()))
                    sm=sc.lastrowid
                    mats=conn.execute("SELECT * FROM curriculum_materials WHERE subject_id=? ORDER BY urutan,id",(s["id"],)).fetchall()
                    for m in mats:
                        mc=conn.execute("INSERT INTO curriculum_materials(subject_id,nama,urutan,created_at) VALUES(?,?,?,?)",(sm,m["nama"],m["urutan"],db.now()))
                        mm=mc.lastrowid
                        cps=conn.execute("SELECT * FROM curriculum_cp WHERE material_id=? ORDER BY id",(m["id"],)).fetchall()
                        for cp in cps:
                            cc=conn.execute("INSERT INTO curriculum_cp(material_id,kode,deskripsi,created_at) VALUES(?,?,?,?)",(mm,cp["kode"],cp["deskripsi"],db.now()))
                            cpnew=cc.lastrowid
                            tps=conn.execute("SELECT * FROM curriculum_tp WHERE cp_id=? ORDER BY urutan,id",(cp["id"],)).fetchall()
                            for tp in tps:
                                conn.execute("INSERT INTO curriculum_tp(cp_id,kode,deskripsi,urutan,created_at) VALUES(?,?,?,?,?)",(cpnew,tp["kode"],tp["deskripsi"],tp["urutan"],db.now()))
                conn.commit()
                platform_admin.audit(user["id"],"clone_curriculum_version","curriculum_version",dst,{"source_version_id":src})
                self._send_json(200, {"ok":True,"id":dst})
            except Exception as e:
                conn.rollback(); self._send_json(400, {"error":str(e)})
            finally: conn.close()
            return

        if path == "/api/platform-admin/curriculum/delete":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            entity=str(body.get("entity","")); item_id=int(body.get("id",0))
            tables={"subject":"curriculum_subjects","material":"curriculum_materials","cp":"curriculum_cp","tp":"curriculum_tp"}
            table=tables.get(entity)
            if not table:
                self._send_json(400, {"error":"Jenis master tidak dikenal."}); return
            conn=db.get_conn()
            try:
                cur=conn.execute("DELETE FROM "+table+" WHERE id=?",(item_id,))
                if cur.rowcount==0:
                    conn.rollback()
                    self._send_json(404, {"error":"Data tidak ditemukan."})
                    return
                conn.commit()
                try:
                    platform_admin.audit(user["id"], "delete_curriculum_"+entity, "curriculum_"+entity, item_id, {})
                except Exception:
                    pass
                self._send_json(200, {"ok":True})
            finally: conn.close()
            return

        if path == "/api/platform-admin/user-pro":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            ok=platform_admin.set_user_pro(int(body.get("user_id",0)),bool(body.get("enabled")),user["id"])
            self._send_json(200 if ok else 404, {"ok":ok}); return
        if path == "/api/platform-admin/school-pro":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses admin GuruWali ditolak."}); return
            ok=platform_admin.set_school_pro(int(body.get("school_id",0)),bool(body.get("enabled")),user["id"])
            self._send_json(200 if ok else 404, {"ok":ok}); return
        # === Master Data (CP/TP) - hanya platform admin ===
        if path == "/api/platform-admin/master-cp/add":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses ditolak."}); return
            body = self._read_json()
            conn = db.get_conn()
            try:
                cur = conn.execute(
                    "INSERT INTO master_cp (jenjang, fase, mapel, kode, deskripsi) VALUES (?,?,?,?,?)",
                    (body.get("jenjang",""), body.get("fase",""), body.get("mapel",""),
                     body.get("kode",""), body.get("deskripsi","")))
                conn.commit()
                self._send_json(200, {"ok": True, "id": cur.lastrowid})
            finally: conn.close()
            return
        if path == "/api/platform-admin/master-cp/delete":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses ditolak."}); return
            body = self._read_json()
            conn = db.get_conn()
            try:
                conn.execute("DELETE FROM master_cp WHERE id = ?", (body.get("id",0),))
                conn.commit()
                self._send_json(200, {"ok": True})
            finally: conn.close()
            return
        if path == "/api/platform-admin/master-tp/add":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses ditolak."}); return
            body = self._read_json()
            conn = db.get_conn()
            try:
                cur = conn.execute(
                    "INSERT INTO master_tp (cp_id, jenjang, fase, mapel, kelas, deskripsi) VALUES (?,?,?,?,?,?)",
                    (body.get("cp_id"), body.get("jenjang",""), body.get("fase",""),
                     body.get("mapel",""), body.get("kelas",""), body.get("deskripsi","")))
                conn.commit()
                self._send_json(200, {"ok": True, "id": cur.lastrowid})
            finally: conn.close()
            return
        if path == "/api/platform-admin/master-tp/delete":
            if not platform_admin.is_platform_admin(user):
                self._send_json(403, {"error":"Akses ditolak."}); return
            body = self._read_json()
            conn = db.get_conn()
            try:
                conn.execute("DELETE FROM master_tp WHERE id = ?", (body.get("id",0),))
                conn.commit()
                self._send_json(200, {"ok": True})
            finally: conn.close()
            return
        if path == "/api/school/create":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            if school.get_user_school(user["id"]):
                self._send_json(400, {"error": "Sudah tergabung di sekolah."})
                return
            body = self._read_json()
            s = school.create_school(user["id"], body.get("nama", ""),
                body.get("npsn", ""), body.get("alamat", ""),
                body.get("kota", ""), body.get("telp", ""), body.get("email", ""))
            if not s:
                self._send_json(400, {"error": "Gagal membuat sekolah."})
                return
            self._send_json(200, {"school": s})
            return
        if path == "/api/school/invite-code":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            s = school.get_user_school(user["id"])
            if not s or not school.is_school_admin(user["id"], s["id"]):
                self._send_json(403, {"error": "Hanya admin sekolah."})
                return
            code = school.generate_invite_code(s["id"])
            self._send_json(200, {"invite_code": code})
            return
        if path == "/api/school/join":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            body = self._read_json()
            s, msg = school.join_school(user["id"], body.get("code", ""))
            if not s:
                self._send_json(400, {"error": msg})
                return
            self._send_json(200, {"school": s, "message": msg})
            return
        if path == "/api/school/transfer-admin":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            s = school.get_user_school(user["id"])
            if not s:
                self._send_json(400, {"error": "Belum tergabung."})
                return
            body = self._read_json()
            try:
                new_admin_id = int(body.get("user_id", 0))
            except (TypeError, ValueError):
                new_admin_id = 0
            ok, msg = school.transfer_admin(s["id"], user["id"], new_admin_id)
            if ok:
                platform_admin.audit(user["id"], "transfer_school_admin", "school", s["id"], {"new_admin_id": new_admin_id})
            self._send_json(200 if ok else 400, {"ok": ok, "message": msg})
            return
        if path == "/api/school/remove-member":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            s = school.get_user_school(user["id"])
            if not s:
                self._send_json(400, {"error": "Belum tergabung."})
                return
            body = self._read_json()
            ok, msg = school.remove_member(s["id"], user["id"], int(body.get("user_id", 0)))
            self._send_json(200 if ok else 400, {"ok": ok, "message": msg})
            return
        if path == "/api/dapodik/import":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            # Hanya admin sekolah yang boleh import Dapodik
            u_school = user.get("school_id")
            if not u_school or not school.is_school_admin(user["id"], u_school):
                self._send_json(403, {"error": "Hanya admin sekolah yang dapat import Dapodik."})
                return
            body = self._read_json()
            csv_text = body.get("csv", "")
            if not csv_text or len(csv_text) > 500000:
                self._send_json(400, {"error": "Data CSV kosong atau terlalu besar."})
                return
            try:
                rows = dapodik.parse_dapodik_csv(csv_text)
            except Exception as e:
                self._send_json(400, {"error": f"Gagal parse CSV: {e}"})
                return
            if not rows:
                self._send_json(400, {"error": "Tidak ada data di CSV."})
                return
            # Ambil baris pertama (atau cari yang cocok dengan user)
            target = rows[0]
            for r in rows:
                if r.get('nama') and user.get('nama') and r['nama'].lower() in user['nama'].lower():
                    target = r
                    break
            ok = dapodik.apply_to_profile(user["id"], target)
            # Jika ada data sekolah, buat/update sekolah otomatis
            school_msg = ""
            if target.get('sekolah'):
                s = school.get_user_school(user["id"])
                if not s:
                    s = school.create_school(user["id"], target['sekolah'],
                        target.get('npsn', ''), target.get('alamat', ''),
                        target.get('kota', ''))
                    school_msg = " Sekolah otomatis dibuat."
            self._send_json(200, {"ok": ok, "imported": target,
                "message": f"Profil diperbarui dari Dapodik.{school_msg}"})
            return
        if path == "/api/school/update":
            s=school.get_user_school(user["id"])
            if not s or not school.is_school_admin(user["id"],s["id"]):
                self._send_json(403, {"error":"Hanya admin sekolah."}); return
            fields={k:str(body.get(k,""))[:200] for k in ("nama","npsn","alamat","kota","telp","email","nama_kepala","nip_kepala","kop_judul","kop_subjudul","kop_website") if k in body}
            if not fields:
                self._send_json(400, {"error":"Tidak ada perubahan."}); return
            conn=db.get_conn()
            try:
                sets=", ".join(f"{k}=?" for k in fields)
                conn.execute(f"UPDATE schools SET {sets} WHERE id=?",list(fields.values())+[s["id"]]); conn.commit()
            finally: conn.close()
            platform_admin.audit(user["id"],"update_school","school",s["id"],fields)
            self._send_json(200, {"school":school.get_school(s["id"])}); return
        if path == "/api/school/leave":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            s = school.get_user_school(user["id"])
            if not s:
                self._send_json(400, {"error": "Belum tergabung."})
                return
            if school.is_school_admin(user["id"], s["id"]):
                self._send_json(400, {"error": "Admin tidak bisa keluar. Tunjuk admin baru terlebih dahulu."})
                return
            import db as _db
            conn = _db.get_conn()
            try:
                conn.execute("DELETE FROM school_members WHERE school_id=? AND user_id=?", (s["id"], user["id"]))
                conn.execute("UPDATE users SET school_id=NULL WHERE id=?", (user["id"],))
                conn.commit()
            finally:
                conn.close()
            self._send_json(200, {"ok": True})
            return
        if path == "/api/documents":
            dtype = str(body.get("type", ""))[:50]
            title = str(body.get("title", ""))[:200]
            content = str(body.get("content", ""))
            if not dtype or not title:
                self._send_json(400, {"error": "type dan title wajib diisi."})
                return
            conn = db.get_conn()
            try:
                cur = conn.execute(
                    "INSERT INTO documents (user_id, type, title, content, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (user["id"], dtype, title, content, db.now(), db.now()),
                )
                conn.commit()
                did = cur.lastrowid
                row = conn.execute("SELECT * FROM documents WHERE id = ?", (did,)).fetchone()
            finally:
                conn.close()
            self._send_json(200, {"document": _doc(row)})
            return

        m = re.match(r"^/api/documents/(\d+)/favorite$", path)
        if m:
            conn = db.get_conn()
            try:
                cur = conn.execute(
                    "UPDATE documents SET is_favorite = 1 - is_favorite, updated_at = ?"
                    " WHERE id = ? AND user_id = ?",
                    (db.now(), int(m.group(1)), user["id"]),
                )
                conn.commit()
                if cur.rowcount == 0:
                    self._send_json(404, {"error": "Dokumen tidak ditemukan."})
                else:
                    self._send_json(200, {"ok": True})
            finally:
                conn.close()
            return

        self._send_json(404, {"error": "Tidak ditemukan."})

    def _handle_generate(self, body):
        user = self._user()
        if not user:
            self._send_json(401, {"error": "Belum masuk."})
            return
        gen_type = str(body.get("type", ""))[:50]
        params = body.get("params", {}) or {}
        if not isinstance(params, dict):
            params = {}
        # batasi ukuran params agar tidak disalahgunakan
        params = {str(k)[:40]: str(v)[:(12000 if str(k) == "soal" and gen_type in ("kunci-jawaban", "pembahasan") else 4000)] for k, v in list(params.items())[:30]}
        # Master Kurikulum: ambil dari versi aktif dan simpan snapshot pada dokumen.
        curriculum_version_id = None
        curriculum_snapshot = ""
        try:
            jenjang=str(params.get("jenjang","")).strip()
            semester=str(params.get("semester","")).strip()
            mapel=str(params.get("mapel","")).strip()
            materi=str(params.get("materi","")).strip()
            if jenjang and semester and mapel:
                conn_m=db.get_conn()
                try:
                    vrow=conn_m.execute("SELECT id,nama,tahun_ajaran FROM curriculum_versions WHERE aktif=1 LIMIT 1").fetchone()
                    if vrow:
                        curriculum_version_id=vrow["id"]
                    srow=conn_m.execute("SELECT id FROM curriculum_subjects WHERE version_id=? AND jenjang=? AND semester=? AND mapel=? LIMIT 1",(curriculum_version_id or 0,jenjang,semester,mapel)).fetchone()
                    if srow:
                        mrow=conn_m.execute("SELECT id,nama FROM curriculum_materials WHERE subject_id=? AND (?='' OR nama=?) ORDER BY urutan,nama LIMIT 1",(srow["id"],materi,materi)).fetchone()
                        if mrow:
                            cp_rows=conn_m.execute("SELECT id,kode,deskripsi FROM curriculum_cp WHERE material_id=? ORDER BY id",(mrow["id"],)).fetchall()
                            if cp_rows:
                                cp_lines=[]; tp_lines=[]
                                for cp_row in cp_rows:
                                    cp_lines.append((cp_row["kode"]+": " if cp_row["kode"] else "")+cp_row["deskripsi"])
                                    for tp_row in conn_m.execute("SELECT kode,deskripsi FROM curriculum_tp WHERE cp_id=? ORDER BY urutan,id",(cp_row["id"],)).fetchall():
                                        tp_lines.append((tp_row["kode"]+": " if tp_row["kode"] else "")+tp_row["deskripsi"])
                                # CP selalu berasal dari Master. TP boleh dipilih guru,
                                # tetapi hanya dari daftar TP resmi untuk materi tersebut.
                                params["cp"]="\n".join(cp_lines)
                                requested_tp=str(params.get("tp","")).strip()
                                official_set={x.strip() for x in tp_lines if x.strip()}
                                if requested_tp:
                                    selected_tp=[line.strip() for line in requested_tp.splitlines() if line.strip() and line.strip() in official_set]
                                    # Jangan biarkan guru memasukkan TP di luar Master.
                                    params["tp"]="\n".join(selected_tp)
                                else:
                                    params["tp"]="\n".join(tp_lines)
                                params["master_kurikulum"]="Gunakan CP resmi Master Kurikulum GuruWali. TP yang digunakan hanya boleh berasal dari daftar Master; jangan mengarang, mengubah, atau menambahkan CP/TP."
                                curriculum_snapshot=json.dumps({"version_id":curriculum_version_id,"version":dict(vrow) if vrow else {}, "jenjang":jenjang,"semester":semester,"mapel":mapel,"materi":materi,"cp":cp_lines,"tp":tp_lines,"selected_tp":params.get("tp","") .split("\n") if params.get("tp") else []}, ensure_ascii=False)
                finally:
                    conn_m.close()
        except Exception:
            pass
        # Identitas resmi dokumen berasal dari server, bukan dari browser.
        signature_types = {"modul-ajar", "rpp", "atp", "program-tahunan", "program-semester",
                           "jurnal-mengajar", "surat-tugas", "berita-acara", "proposal"}
        if gen_type in signature_types:
            school_data = school.get_user_school(user["id"])
            if school_data:
                params.update({
                    "npsn": school_data.get("npsn") or "",
                    "sekolah": school_data.get("nama") or "",
                    "alamat_sekolah": school_data.get("alamat") or "",
                    "kota_sekolah": school_data.get("kota") or "",
                    "nama_kepala": school_data.get("nama_kepala") or "",
                    "nip_kepala": school_data.get("nip_kepala") or "",
                    "kop_judul": school_data.get("kop_judul") or "",
                    "kop_subjudul": school_data.get("kop_subjudul") or "",
                    "kop_telp": school_data.get("telp") or "",
                    "kop_email": school_data.get("email") or "",
                    "kop_website": school_data.get("kop_website") or "",
                })
            params["nama_guru"] = user.get("nama") or ""
        save = body.get("save", True)
        if gen_type not in prompts.TEMPLATES:
            self._send_json(400, {"error": f"Tipe generator tidak dikenal: {gen_type}."})
            return
        if not ai.is_configured():
            self._send_json(503, {"error": "Layanan AI belum dikonfigurasi."})
            return
        # --- reservasi kuota atomik sebelum memanggil AI ---
        consumed = school.consume_quota(user["id"], 1)
        if not consumed:
            sq0 = school.check_school_quota(user["id"])
            if sq0:
                self._send_json(402, {
                    "error": f"Kuota sekolah {sq0['school_name']} habis. Hubungi admin sekolah.",
                    "quota": {"used": sq0["used"], "limit": sq0["limit"], "is_pro": True, "school": True},
                })
            else:
                self._send_json(402, {
                    "error": "Kuota generate habis. Upgrade ke GuruWali Pro atau tunggu kuota tersedia.",
                })
            return
        sq = school.check_school_quota(user["id"])
        # --- panggil AI ---
        # smart routing: override user > rekomendasi per tipe > default
        model_used = ai.resolve_model(gen_type, body.get("model"))
        try:
            prompt = prompts.build_prompt(gen_type, params)
            content = ai.chat(
                [
                    {"role": "system", "content": prompts.SYSTEM_ID},
                    {"role": "user", "content": prompt},
                ],
                model=model_used,
                max_tokens=prompts.max_tokens_for(gen_type),
                temperature=0.7,
            )
        except RuntimeError as e:
            school.refund_quota(consumed)
            self._send_json(502, {"error": str(e)})
            return
        except Exception as e:
            school.refund_quota(consumed)
            self._send_json(502, {"error": f"Gagal menghubungi AI: {e}"})
            return
        # Normalisasi notasi matematika sebelum ditampilkan/disimpan.
        content = prompts.sanitize_math_output(content)
        # --- simpan hasil (kuota sudah dicadangkan secara atomik) ---
        doc = None
        conn = db.get_conn()
        try:
            if save and content:
                title = prompts.make_title(gen_type, params)
                cur = conn.execute(
                    "INSERT INTO documents (user_id, type, title, content, curriculum_version_id, curriculum_snapshot, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (user["id"], gen_type, title, content, curriculum_version_id, curriculum_snapshot, db.now(), db.now()),
                )
                conn.commit()
                r = conn.execute(
                    "SELECT * FROM documents WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
                doc = _doc(r) if r else None
            else:
                conn.commit()
            qrow = conn.execute(
                "SELECT quota_used, quota_limit, is_pro FROM users WHERE id = ?",
                (user["id"],),
            ).fetchone()
        finally:
            conn.close()
        # Kembalikan kuota yang benar-benar dipakai: kuota sekolah jika anggota sekolah Pro.
        if sq:
            quota_out = {
                "used": school.get_user_school(user["id"])["quota_used"] or 0,
                "limit": sq["limit"],
                "is_pro": True,
                "school": True,
            }
        else:
            quota_out = {
                "used": qrow["quota_used"],
                "limit": qrow["quota_limit"],
                "is_pro": bool(qrow["is_pro"]),
                "school": False,
            }
        self._send_json(200, {
            "content": content,
            "document": doc,
            "model": model_used,
            "model_label": ai.model_label(model_used),
            "quota": quota_out,
        })

    def _api_generate_image(self, body):
        user = self._user()
        if not user:
            self._send_json(401, {"error": "Belum masuk."})
            return
        prompt = str(body.get("prompt") or "").strip()[:4000]
        if not prompt:
            self._send_json(400, {"error": "Deskripsi gambar wajib diisi."})
            return
        if ai.provider() != "invibuilder":
            self._send_json(503, {"error": "Generate gambar belum tersedia."})
            return
        # --- reservasi kuota atomik (gambar = 2 kuota) ---
        consumed = school.consume_quota(user["id"], 2)
        if not consumed:
            sq=school.check_school_quota(user["id"])
            msg = ("Kuota sekolah %s tidak cukup untuk gambar (2 kuota)." % sq["school_name"]) if sq else "Kuota tidak cukup (gambar = 2 kuota)."
            self._send_json(402, {"error": msg})
            return
        sq=school.check_school_quota(user["id"])
        school_row=school.get_user_school(user["id"]) if sq else None
        # --- panggil AI image ---
        model_used = (body.get("model") or "").strip() or ai._IMAGE_MODEL
        style = str(body.get("style") or "").strip()[:500]
        full_prompt = f"{prompt}. Gaya: {style}. Cocok untuk media pembelajaran Indonesia." if style else prompt
        try:
            result = ai.generate_image(full_prompt, model=model_used)
        except RuntimeError as e:
            school.refund_quota(consumed)
            self._send_json(502, {"error": str(e)})
            return
        except Exception as e:
            school.refund_quota(consumed)
            self._send_json(502, {"error": f"Gagal membuat gambar: {e}"})
            return
        # --- simpan hasil ---
        image_url = result.get("url")
        if result.get("b64"):
            import base64, os, time, secrets
            updir = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(updir, exist_ok=True)
            fname = f"img_{user['id']}_{time.time_ns()}_{secrets.token_hex(4)}.png"
            with open(os.path.join(updir, fname), "wb") as f:
                f.write(base64.b64decode(result["b64"]))
            image_url = f"/uploads/{fname}"
        doc = None
        qrow = None
        try:
            conn = db.get_conn()
            try:
                title = f"Ilustrasi: {prompt[:50]}"
                content = f"![Ilustrasi]({image_url})\\n\\n*Prompt: {prompt}*"
                cur = conn.execute(
                    "INSERT INTO documents (user_id, type, title, content, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (user["id"], "gambar-ilustrasi", title, content, db.now(), db.now()),
                )
                conn.commit()
                r = conn.execute(
                    "SELECT * FROM documents WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
                doc = _doc(r) if r else None
                qrow = conn.execute(
                    "SELECT quota_used, quota_limit, is_pro FROM users WHERE id = ?",
                    (user["id"],),
                ).fetchone()
            finally:
                conn.close()
        except Exception as e:
            school.refund_quota(consumed)
            self._send_json(500, {"error": f"Gambar berhasil dibuat tetapi gagal disimpan: {e}"})
            return

        if sq:
            current_school = school.get_user_school(user["id"])
            quota_out = {
                "used": current_school["quota_used"] if current_school else sq["used"] + 2,
                "limit": sq["limit"],
                "is_pro": True,
                "school": True,
            }
        else:
            quota_out = {
                "used": qrow["quota_used"],
                "limit": qrow["quota_limit"],
                "is_pro": bool(qrow["is_pro"]),
                "school": False,
            }
        self._send_json(200, {
            "image_url": image_url,
            "document": doc,
            "model": model_used,
            "quota": quota_out,
        })

    def _api_put(self, path):
        m = re.match(r"^/api/documents/(\d+)$", path)
        if path == "/api/me":
            user = self._user()
            if not user:
                self._send_json(401, {"error": "Belum masuk."})
                return
            ok = auth.update_profile(user["id"], self._read_json())
            if not ok:
                self._send_json(400, {"error": "Tidak ada perubahan."})
                return
            self._send_json(200, {"user": auth.public_user(auth.get_user_by_token(self._token()))})
            return
        if not m:
            self._send_json(404, {"error": "Tidak ditemukan."})
            return
        user = self._user()
        if not user:
            self._send_json(401, {"error": "Belum masuk."})
            return
        body = self._read_json()
        title = str(body.get("title", ""))[:200]
        content = str(body.get("content", ""))
        conn = db.get_conn()
        try:
            cur = conn.execute(
                "UPDATE documents SET title = ?, content = ?, updated_at = ?"
                " WHERE id = ? AND user_id = ?",
                (title, content, db.now(), int(m.group(1)), user["id"]),
            )
            conn.commit()
            if cur.rowcount == 0:
                self._send_json(404, {"error": "Dokumen tidak ditemukan."})
            else:
                self._send_json(200, {"ok": True})
        finally:
            conn.close()


def _doc(row):
    return {
        "id": row["id"],
        "type": row["type"],  # konsisten: selalu "type", bukan "doc_type"
        "title": row["title"],
        "content": row["content"],
        "curriculum_version_id": row["curriculum_version_id"] if "curriculum_version_id" in row.keys() else None,
        "curriculum_snapshot": row["curriculum_snapshot"] if "curriculum_snapshot" in row.keys() else "",
        "is_favorite": bool(row["is_favorite"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def main():
    db.init_db()
    platform_admin.bootstrap_env_admins()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"GuruWali berjalan di http://{HOST}:{PORT} (Ctrl+C untuk berhenti)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
