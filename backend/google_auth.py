"""Google OAuth login untuk GuruWali."""
import json
import os
import secrets
import urllib.parse
import urllib.request

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Simpan state sementara (in-memory)
_pending_states = {}


def get_client_id():
    return os.environ.get("GOOGLE_CLIENT_ID", "")


def get_client_secret():
    return os.environ.get("GOOGLE_CLIENT_SECRET", "")


def get_redirect_uri():
    return os.environ.get("GOOGLE_REDIRECT_URI", "https://guruwali.web.id/api/auth/google/callback")


def is_configured():
    return bool(get_client_id() and get_client_secret())


def get_login_url():
    """Buat URL login Google."""
    state = secrets.token_urlsafe(32)
    _pending_states[state] = True
    # Bersihkan state lama (maks 100)
    if len(_pending_states) > 100:
        _pending_states.pop(next(iter(_pending_states)))
    params = {
        "client_id": get_client_id(),
        "redirect_uri": get_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)


def verify_state(state):
    return _pending_states.pop(state, None) is not None


def exchange_code(code):
    """Tukar code dengan access token, lalu ambil userinfo."""
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": get_client_id(),
        "client_secret": get_client_secret(),
        "redirect_uri": get_redirect_uri(),
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(GOOGLE_TOKEN_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            token_data = json.loads(r.read().decode())
    except Exception as e:
        return None, f"Gagal tukar kode: {e}"
    
    access_token = token_data.get("access_token")
    if not access_token:
        return None, "Tidak dapat access token"
    
    # Ambil userinfo
    req = urllib.request.Request(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            userinfo = json.loads(r.read().decode())
    except Exception as e:
        return None, f"Gagal ambil data user: {e}"
    
    return userinfo, None
