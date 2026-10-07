# GuruWali 📚

Platform AI untuk guru Indonesia — rebuild dari "Guru AI" sebagai website responsif
(desktop-first, navigasi atas), bukan PWA bergaya Android.

## Struktur

```
guruwali/
├── backend/
│   ├── server.py   # API server (stdlib http.server, tanpa dependensi)
│   ├── auth.py     # PBKDF2 + session token
│   ├── ai.py       # Klien Gemini OpenAI-compatible (key dari env)
│   ├── db.py       # SQLite helpers
│   └── prompts.py  # Template prompt Kurikulum Merdeka (placeholder)
├── frontend/
│   ├── index.html  # Landing page
│   ├── app.html    # Aplikasi: dashboard + 12 seksi navigasi
│   ├── css/style.css
│   └── js/app.js
```

## Cara menjalankan (dev lokal)

```bash
cd /home/hatch/workspace/guruwali/backend
python3 server.py
# → GuruWali berjalan di http://127.0.0.1:8081
```

Environment (opsional):

| Var | Default | Keterangan |
|---|---|---|
| `GURUWALI_HOST` | `127.0.0.1` | Bind address |
| `GURUWALI_PORT` | `8081` | Port |
| `GURUWALI_DB` | `backend/auth.db` | Path SQLite |
| `GURUWALI_AI_KEY` | _(kosong)_ | API key Invibuilder (gateway multi-model) — **prioritas, jangan commit!** |
| `GURUWALI_GEMINI_KEY` | _(kosong)_ | API key Gemini (fallback bila `GURUWALI_AI_KEY` kosong) — **jangan commit!** |
| `GURUWALI_AI_BASE` | _(otomatis)_ | Base URL OpenAI-compatible kustom. Default: Invibuilder bila `GURUWALI_AI_KEY` ada, else Gemini |
| `GURUWALI_MODEL | `gemini-flash-lite-latest` | Model default bila routing tidak menentukan lain |

## Model AI & Smart Routing

Backend memakai endpoint OpenAI-compatible (`/chat/completions`):

- **Invibuilder** (`https://api.invibuilder.com/v1`) — aktif otomatis bila `GURUWALI_AI_KEY` diset. Satu key untuk banyak model.
- **Gemini** (`https://generativelanguage.googleapis.com/v1beta/openai`) — fallback bila hanya `GURUWALI_GEMINI_KEY` yang diset (satu model saja).

**Smart routing** (`backend/ai.py` → `MODEL_MAP`): tiap tipe generator otomatis memakai model yang
paling cocok — saling melengkapi:

| Kategori | Model | Untuk tipe |
|---|---|---|
| Ringan/cepat | `openai/gpt-4o-mini` | ice-breaking, refleksi, jurnal-mengajar, pengayaan, chat-bebas |
| Standar | `deepseek/deepseek-v4-flash` | rpp, materi, soal-pg/uraian, kisi-kisi, lkpd, rubrik, surat, proposal, dll |
| Berat/penalaran | `ar1/claude-sonnet-4-6` | modul-ajar, atp, tp, kktp, prota, prosem, soal-hots, pembahasan |

> Tugas berat memakai `deepseek-reasoner`. Alternatif premium `ar1/claude-sonnet-4-6`
> sudah ada di katalog — cukup ganti satu baris `_MODEL_HEAVY` di `ai.py` bila ingin Claude.
> ID model mengikuti penamaan umum provider; sesuaikan di `MODELS` bila gateway memakai alias berbeda.

**Override manual:** user bisa memilih model lewat dropdown "Model AI" di topbar aplikasi
(pilihan tersimpan di `localStorage`, dikirim sebagai field `model` di `/api/generate`).
Mode "Otomatis (disarankan)" memakai smart routing di atas. Setiap hasil menampilkan
badge model yang dipakai ("Dibuat dengan …").

Mode Gemini (tanpa `GURUWALI_AI_KEY`): routing dinonaktifkan, selalu pakai `GURUWALI_MODEL`.

## Deployment HTTPS

Untuk produksi di belakang HTTPS/reverse proxy, set `GURUWALI_SECURE_COOKIE=1` agar session cookie memakai flag `Secure`. Biarkan kosong saat pengembangan lokal melalui HTTP.

## Dependensi Python

Server inti hanya memakai stdlib. Untuk **export Word/PDF**:

```bash
pip install python-docx reportlab
```

| Package | Untuk |
|---|---|
| `python-docx` | Export `.docx` |
| `reportlab` | Export `.pdf` |

Tanpa kedua package ini, endpoint export mengembalikan 500 dengan pesan jelas.

## API

| Method | Endpoint | Auth | Keterangan |
|---|---|---|---|
| POST | `/api/register` | — | email, password, nama, sekolah, mapel, jenjang |
| POST | `/api/login` | — | email, password → set cookie `gw_session` |
| POST | `/api/logout` | — | hapus sesi |
| GET | `/api/me` | ✅ | profil user |
| PUT | `/api/me` | ✅ | update profil |
| GET | `/api/documents?type=&favorite=1` | ✅ | daftar dokumen |
| POST | `/api/documents` | ✅ | simpan dokumen (`type`, `title`, `content`) |
| GET | `/api/documents/:id` | ✅ | detail |
| PUT | `/api/documents/:id` | ✅ | update |
| DELETE | `/api/documents/:id` | ✅ | hapus |
| POST | `/api/documents/:id/favorite` | ✅ | toggle favorit |
| GET | `/api/documents/:id/export?format=docx` | ✅ | download Word (hanya pemilik) |
| GET | `/api/documents/:id/export?format=pdf` | ✅ | download PDF (hanya pemilik) |
| POST | `/api/generate` | ✅ | `{type, params, save, model?}` → konten AI + simpan otomatis ke documents + potong kuota. `save:false` untuk chat (tidak disimpan). `model` opsional = override manual (bila kosong → smart routing). Respons berisi `model` + `model_label` yang dipakai. 402 jika kuota habis, 503 jika AI belum dikonfigurasi. |
| GET | `/api/models` | ✅ | katalog model (`models`), info routing per kategori (`routing`), provider aktif (`provider`: invibuilder/gemini), dan `default_model`. Untuk dropdown frontend. |

Field dokumen konsisten memakai **`type`** (bukan `doc_type`) di backend & frontend.

## Generator (29 tipe)

| Seksi | Generator |
|---|---|
| Perangkat Ajar | Modul Ajar, RPP, ATP, Tujuan Pembelajaran, KKTP, Prota, Prosem, Remedial, Pengayaan |
| Materi | Materi lengkap, Ringkasan, Materi versi siswa |
| Soal & Evaluasi | Pilihan Ganda, Uraian, HOTS, Kisi-kisi, Kunci Jawaban, Pembahasan |
| Media | LKPD, Worksheet, Outline PPT |
| Alat Bantu | Rubrik, Ice Breaking, Refleksi, Jurnal Mengajar |
| Administrasi | Surat Tugas, Berita Acara, Proposal |
| Chat AI | Tanya jawab bebas (tanpa simpan otomatis, tombol 💾 manual) |

**Fitur unggulan:** kartu "⚡ SATU INPUT → 11 DOKUMEN" di Beranda — satu form
(Mapel + Jenjang + Kelas + Materi + Alokasi + CP) → 11 dokumen berurutan
(Modul Ajar, Materi, LKPD, Kisi-kisi, Soal, Kunci, Pembahasan, Rubrik, Remedial,
Pengayaan, Outline PPT) dengan progres per dokumen. Kunci & pembahasan memakai
soal yang baru dibuat agar konsisten.

Semua prompt memakai terminologi Kurikulum Merdeka 2025: Pembelajaran Mendalam
(Memahami → Mengaplikasi → Merefleksi), Profil Lulusan 8 dimensi, KKTP
(bukan KKM), template Modul Ajar A–E. AI tidak mengarang CP.

## Status

v0.2 — 29 generator + chat + paket lengkap jadi. Plumbing `/api/generate`
terverifikasi (200/400/401/402/503, auto-save, save:false, kuota). **Test AI asli
belum bisa dijalankan** — tidak ada `GURUWALI_GEMINI_KEY` di VM ini (key milik
user ada di VPS lama `/opt/guruai-backend`). Set env tersebut saat deploy untuk
mengaktifkan generate.

## Keamanan

- Password: PBKDF2-SHA256, 200.000 iterasi + salt acak
- Session token 14 hari via cookie HttpOnly (fallback: header `Authorization: Bearer`)
- Rate limit 10 req/menit/IP untuk `/api/*`
- API key AI hanya dari environment, tidak pernah ke frontend
- Bind default `127.0.0.1` untuk dev lokal

## Status

Scaffold v0.1 — auth + kerangka 12 seksi. ✅ v0.2 — 29 generator + chat + paket lengkap (lihat di atas).
