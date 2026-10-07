"""Klien AI OpenAI-compatible (Gemini / Invibuilder gateway).
Key HANYA dari env, tidak pernah di frontend.

Env:
  GURUWALI_AI_KEY    API key Invibuilder (gateway multi-model) — prioritas utama
  GURUWALI_GEMINI_KEY API key Gemini (fallback bila AI_KEY kosong)
  GURUWALI_AI_BASE   base URL kustom (default: Invibuilder bila AI_KEY ada, else Gemini)
  GURUWALI_MODEL     model default Gemini (default: gemini-2.5-flash-lite)
"""
import json
import os
import re
import urllib.request

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
INVIBUILDER_BASE = "https://api.invibuilder.com/v1"


def get_key():
    """Prioritas: GURUWALI_AI_KEY (Invibuilder) lalu GURUWALI_GEMINI_KEY."""
    return os.environ.get("GURUWALI_AI_KEY", "") or os.environ.get("GURUWALI_GEMINI_KEY", "")


def provider():
    """'invibuilder' bila GURUWALI_AI_KEY diset, else 'gemini'."""
    return "invibuilder" if os.environ.get("GURUWALI_AI_KEY", "") else "gemini"


def ai_base():
    """Base URL: env GURUWALI_AI_BASE, default Invibuilder bila key-nya ada, fallback Gemini."""
    env = os.environ.get("GURUWALI_AI_BASE", "").strip()
    if env:
        return env.rstrip("/")
    if provider() == "invibuilder":
        return INVIBUILDER_BASE
    return GEMINI_BASE


def default_model():
    return os.environ.get("GURUWALI_MODEL", "gemini-2.5-flash-lite")


def is_configured():
    return bool(get_key())


# ---------------------------------------------------------------- katalog model
# ID ASLI dari API Invibuilder (/v1/models) — JANGAN diubah sembarangan.
MODELS = [
    {"id": "auto:hemat", "label": "Otomatis Hemat",
     "desc": "Paling murah — tugas ringan dan chat"},
    {"id": "openai/gpt-4o-mini", "label": "GPT-4o mini",
     "desc": "Cepat & hemat — dokumen standar"},
    {"id": "deepseek/deepseek-v4-flash", "label": "DeepSeek V4 Flash",
     "desc": "Seimbang — dokumen standar berkualitas"},
    {"id": "ar1/claude-sonnet-4-6", "label": "Claude Sonnet 4.6",
     "desc": "Kualitas premium — tugas berat & penalaran"},
    {"id": "deepseek/deepseek-v4-pro", "label": "DeepSeek V4 Pro",
     "desc": "Penalaran kuat — HOTS, pembahasan"},
    {"id": "auto", "label": "Otomatis (Smart Routing)",
     "desc": "Gateway memilihkan model terbaik"},
]

IMAGE_MODELS = [
    {"id": "mg-image-0.1", "label": "Image Generator",
     "desc": "Generate ilustrasi pembelajaran"},
]

MODEL_IDS = {m["id"] for m in MODELS} | {m["id"] for m in IMAGE_MODELS}

# ------------------------------------------------------- smart routing
# Tiap kategori tugas memakai model yang paling cocok (saling melengkapi):
# ringan  -> cepat & murah | standar -> seimbang | berat -> penalaran kuat.
_MODEL_LIGHT = "openai/gpt-4o-mini"
_MODEL_STANDARD = "deepseek/deepseek-v4-flash"
_MODEL_HEAVY = "ar1/claude-sonnet-4-6"
_IMAGE_MODEL = "mg-image-0.1"

MODEL_MAP = {
    # --- ringan / cepat ---
    "ice-breaking": _MODEL_LIGHT,
    "refleksi": _MODEL_LIGHT,
    "jurnal-mengajar": _MODEL_LIGHT,
    "pengayaan": _MODEL_LIGHT,
    "chat-bebas": _MODEL_LIGHT,
    # --- standar ---
    "rpp": _MODEL_STANDARD,
    "materi": _MODEL_STANDARD,
    "ringkasan-materi": _MODEL_STANDARD,
    "materi-siswa": _MODEL_STANDARD,
    "soal-pg": _MODEL_STANDARD,
    "soal-uraian": _MODEL_STANDARD,
    "kisi-kisi": _MODEL_STANDARD,
    "kunci-jawaban": _MODEL_STANDARD,
    "lkpd": _MODEL_STANDARD,
    "worksheet": _MODEL_STANDARD,
    "ppt-outline": _MODEL_STANDARD,
    "rubrik": _MODEL_STANDARD,
    "remedial": _MODEL_STANDARD,
    "surat-tugas": _MODEL_STANDARD,
    "berita-acara": _MODEL_STANDARD,
    "proposal": _MODEL_STANDARD,
    # --- berat / penalaran ---
    "modul-ajar": _MODEL_HEAVY,
    "atp": _MODEL_HEAVY,
    "tujuan-pembelajaran": _MODEL_HEAVY,
    "kktp": _MODEL_HEAVY,
    "program-tahunan": _MODEL_HEAVY,
    "program-semester": _MODEL_HEAVY,
    "soal-hots": _MODEL_HEAVY,
    "pembahasan": _MODEL_HEAVY,
}


def model_for_type(gen_type):
    """Model rekomendasi untuk tipe generator; fallback ke model default."""
    return MODEL_MAP.get(gen_type, default_model())


def model_label(model_id):
    for m in MODELS:
        if m["id"] == model_id:
            return m["label"]
    return model_id or default_model()


def available_models():
    """Katalog model sesuai provider aktif (untuk dropdown frontend)."""
    if provider() == "invibuilder":
        return MODELS
    dm = default_model()
    return [{"id": dm, "label": "Gemini (default)", "desc": "Model Gemini yang dikonfigurasi server"}]


def routing_info():
    """Ringkasan routing per kategori untuk /api/models."""
    cats = {}
    for t, m in MODEL_MAP.items():
        cats.setdefault(m, []).append(t)
    return [
        {"model": mid, "label": model_label(mid), "types": sorted(types)}
        for mid, types in sorted(cats.items())
    ]


_SAFE_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\-]{0,99}$")


def resolve_model(gen_type, override=None):
    """Tentukan model final: override user > routing per tipe (Invibuilder) > default.

    Di provider Gemini (satu model), selalu pakai default_model().
    Override di luar katalog tetap diterima bila polanya aman (untuk model baru di gateway).
    """
    if provider() != "invibuilder":
        return default_model()
    if override:
        override = str(override).strip()[:100]
        # Empty/auto berarti gunakan smart routing berdasarkan tipe generator.
        if override in ("", "auto"):
            return model_for_type(gen_type)
        # Mode hemat memakai model ringan yang konsisten dan murah.
        if override == "auto:hemat":
            return _MODEL_LIGHT
        if override in MODEL_IDS or _SAFE_MODEL.match(override):
            return override
    return model_for_type(gen_type)


def chat(messages, model=None, max_tokens=4000, temperature=0.7):
    """messages: list of {role, content}. Mengembalikan teks balasan."""
    key = get_key()
    if not key:
        raise RuntimeError("API key AI belum diset (GURUWALI_AI_KEY / GURUWALI_GEMINI_KEY).")
    model = model or default_model()
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{ai_base()}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"AI backend error: {e}")
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"Respons AI tidak terduga: {str(data)[:300]}")


def generate_image(prompt, model=None, size="1024x1024"):
    """Generate gambar via /images/generations. Mengembalikan dict {url|b64, revised_prompt}."""
    key = get_key()
    if not key:
        raise RuntimeError("API key AI belum diset (GURUWALI_AI_KEY).")
    if provider() != "invibuilder":
        raise RuntimeError("Generate gambar hanya tersedia via Invibuilder.")
    model = model or _IMAGE_MODEL
    # Catatan: endpoint image Invibuilder memakai prefix /api/v1 (beda dari /v1 chat)
    img_base = "https://api.invibuilder.com/api/v1"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "size": size,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{img_base}/images/generations",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Image backend error: {e}")
    # Format respons bervariasi antar gateway; coba beberapa pola umum
    try:
        # Pola 1: OpenAI standar {"data": [{"url"|"b64_json"}]}
        item = data["data"][0]
        if item.get("url") or item.get("b64_json"):
            return {"url": item.get("url"), "b64": item.get("b64_json"),
                    "revised_prompt": item.get("revised_prompt", "")}
        # Pola 2: list langsung [{"mime_type","data"|"b64",...}]
        if isinstance(item, dict):
            for k in ("b64", "data", "image", "base64"):
                v = item.get(k)
                if isinstance(v, str) and len(v) > 1000:
                    return {"url": None, "b64": v, "revised_prompt": ""}
        # Pola 3: data adalah list langsung
        if isinstance(data, list) and data:
            return generate_image_from_item(data[0])
    except (KeyError, IndexError, TypeError):
        pass
    raise RuntimeError(f"Respons image tidak terduga: {str(data)[:300]}")


def generate_image_from_item(item):
    if isinstance(item, dict):
        for k in ("b64_json", "b64", "data", "image", "base64"):
            v = item.get(k)
            if isinstance(v, str) and len(v) > 1000:
                return {"url": None, "b64": v, "revised_prompt": ""}
        if item.get("url"):
            return {"url": item["url"], "b64": None, "revised_prompt": ""}
    raise ValueError("Format item gambar tidak dikenal")
