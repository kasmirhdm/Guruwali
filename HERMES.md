# GuruWali — Panduan untuk Hermes

Aplikasi web untuk guru Indonesia. Kamu (Hermes) bisa melanjutkan development proyek ini.

## Lokasi
- Kode lokal: `/home/hatch/workspace/guruwali/`
- VPS produksi: `ssh -F /home/hatch/.ssh/config vps-tailscale`
- Path VPS: `/opt/guruwali/` (backend + frontend)
- URL publik: http://103.147.32.34:18082

## Arsitektur
- `backend/server.py` — HTTP server (stdlib), API di `/api/*`
- `backend/ai.py` — klien AI (Invibuilder gateway, OpenAI-compatible)
- `backend/prompts.py` — 29 prompt generator Kurikulum Merdeka 2025
- `backend/exporter.py` — export Word/PDF
- `frontend/` — index.html (landing), app.html (aplikasi), js/, css/
- DB: SQLite `/opt/guruwali/backend/auth.db` (JANGAN timpa via rsync!)

## Deploy ke VPS
```bash
# JANGAN sertakan auth.db!
rsync -avz --exclude 'auth.db' -e "ssh -F /home/hatch/.ssh/config" \
  /home/hatch/workspace/guruwali/ vps-tailscale:/opt/guruwali/
ssh -F /home/hatch/.ssh/config vps-tailscale \
  "chmod -R 755 /opt/guruwali/frontend && chmod 755 /opt/guruwali && systemctl restart guruwali"
```

## AI Backend
- Provider: Invibuilder (`https://api.invibuilder.com/v1`)
- Key: env `GURUWALI_AI_KEY` di `/opt/guruwali-key.env` (JANGAN tampilkan di chat/log)
- Model routing di `backend/ai.py` (MODEL_MAP): ringan→`openai/gpt-4o-mini`, berat→`ar1/claude-sonnet-4-6`
- Generate gambar: `mg-image-0.1` via `POST /api/generate-image`

## Aturan
- Backup sebelum ubah kode penting
- Test lokal dulu (`node --check`, `python3 -c "import ..."`)
- Jangan tampilkan API key di output
- Akun demo: demo@guruwali.id / demo123 (jangan hapus)
