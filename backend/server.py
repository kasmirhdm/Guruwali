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
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ai
import auth
import db
import exporter
import prompts

HOST = os.environ.get("GURUWALI_HOST", "127.0.0.1")
PORT = int(os.environ.get("GURUWALI_PORT", "8081"))
SECURE_COOKIE = os.environ.get("GURUWALI_SECURE_COOKIE", "").lower() in ("1", "true", "yes", "on")
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# Rate limit: 10 request/menit/IP untuk /api/*
RATE_WINDOW = 60
RATE_MAX = 60
AI_RATE_MAX = 20
AUTH_RATE_MAX = 10
_rate = {}


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
            if not rate_ok(self.client_address[0], "general", RATE_MAX):
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
        if not rate_ok(self.client_address[0], bucket, limit):
            self._send_json(429, {"error": "Terlalu banyak permintaan. Coba lagi sebentar."})
            return
        self._api_post(parsed.path)

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._send_json(404, {"error": "Tidak ditemukan."})
            return
        if not rate_ok(self.client_address[0]):
            self._send_json(429, {"error": "Terlalu banyak permintaan. Coba lagi sebentar."})
            return
        self._api_put(parsed.path)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self._send_json(404, {"error": "Tidak ditemukan."})
            return
        if not rate_ok(self.client_address[0]):
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

    def _api_get(self, path, qs):
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
        params = {str(k)[:40]: str(v)[:4000] for k, v in list(params.items())[:30]}
        save = body.get("save", True)
        if gen_type not in prompts.TEMPLATES:
            self._send_json(400, {"error": f"Tipe generator tidak dikenal: {gen_type}."})
            return
        if not ai.is_configured():
            self._send_json(503, {"error": "Layanan AI belum dikonfigurasi."})
            return
        # --- cek kuota ---
        conn = db.get_conn()
        try:
            row = conn.execute(
                "SELECT quota_used, quota_limit, is_pro FROM users WHERE id = ?",
                (user["id"],),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            self._send_json(401, {"error": "Belum masuk."})
            return
        if not row["is_pro"] and (row["quota_used"] or 0) >= (row["quota_limit"] or 0):
            self._send_json(402, {
                "error": "Kuota generate gratis habis. Upgrade ke GuruWali Pro untuk kuota tanpa batas.",
                "quota": {"used": row["quota_used"], "limit": row["quota_limit"], "is_pro": False},
            })
            return
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
            self._send_json(502, {"error": str(e)})
            return
        except Exception as e:
            self._send_json(502, {"error": f"Gagal menghubungi AI: {e}"})
            return
        # --- simpan + kurangi kuota ---
        doc = None
        conn = db.get_conn()
        try:
            conn.execute(
                "UPDATE users SET quota_used = quota_used + 1 WHERE id = ?", (user["id"],)
            )
            if save and content:
                title = prompts.make_title(gen_type, params)
                cur = conn.execute(
                    "INSERT INTO documents (user_id, type, title, content, created_at, updated_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (user["id"], gen_type, title, content, db.now(), db.now()),
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
        self._send_json(200, {
            "content": content,
            "document": doc,
            "model": model_used,
            "model_label": ai.model_label(model_used),
            "quota": {
                "used": qrow["quota_used"],
                "limit": qrow["quota_limit"],
                "is_pro": bool(qrow["is_pro"]),
            },
        })

    def _api_generate_image(self, body):
        user = self._user()
        if not user:
            self._send_json(401, {"error": "Belum masuk."})
            return
        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            self._send_json(400, {"error": "Deskripsi gambar wajib diisi."})
            return
        if ai.provider() != "invibuilder":
            self._send_json(503, {"error": "Generate gambar belum tersedia."})
            return
        # --- cek kuota (gambar = 2 kuota) ---
        conn = db.get_conn()
        try:
            row = conn.execute(
                "SELECT quota_used, quota_limit, is_pro FROM users WHERE id = ?",
                (user["id"],),
            ).fetchone()
        finally:
            conn.close()
        if not row["is_pro"] and row["quota_used"] + 2 > row["quota_limit"]:
            self._send_json(402, {"error": "Kuota tidak cukup (gambar = 2 kuota)."})
            return
        # --- panggil AI image ---
        model_used = (body.get("model") or "").strip() or ai._IMAGE_MODEL
        style = (body.get("style") or "").strip()
        full_prompt = f"{prompt}. Gaya: {style}. Cocok untuk media pembelajaran Indonesia." if style else prompt
        try:
            result = ai.generate_image(full_prompt, model=model_used)
        except RuntimeError as e:
            self._send_json(502, {"error": str(e)})
            return
        # --- simpan hasil ---
        image_url = result.get("url")
        if result.get("b64"):
            import base64, os, time
            updir = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(updir, exist_ok=True)
            fname = f"img_{user['id']}_{int(time.time())}.png"
            with open(os.path.join(updir, fname), "wb") as f:
                f.write(base64.b64decode(result["b64"]))
            image_url = f"/uploads/{fname}"
        doc = None
        conn = db.get_conn()
        try:
            conn.execute(
                "UPDATE users SET quota_used = quota_used + 2 WHERE id = ?", (user["id"],)
            )
            title = f"Ilustrasi: {prompt[:50]}"
            content = f"![Ilustrasi]({image_url})\n\n*Prompt: {prompt}*"
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
        self._send_json(200, {
            "image_url": image_url,
            "document": doc,
            "model": model_used,
            "quota": {
                "used": qrow["quota_used"],
                "limit": qrow["quota_limit"],
                "is_pro": bool(qrow["is_pro"]),
            },
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
        "is_favorite": bool(row["is_favorite"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def main():
    db.init_db()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"GuruWali berjalan di http://{HOST}:{PORT} (Ctrl+C untuk berhenti)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
