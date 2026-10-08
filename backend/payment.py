"""Integrasi pembayaran Midtrans Snap untuk GuruWali.

Env:
  GURUWALI_MIDTRANS_SERVER_KEY   Server Key Midtrans
  GURUWALI_MIDTRANS_CLIENT_KEY   Client Key (untuk frontend bila diperlukan)
  GURUWALI_MIDTRANS_PRODUCTION   1 untuk production, default sandbox
"""
import base64
import hashlib
import json
import os
import urllib.request

def configured():
    return bool(os.environ.get("GURUWALI_MIDTRANS_SERVER_KEY","").strip())

def base_url():
    return "https://app.midtrans.com" if os.environ.get("GURUWALI_MIDTRANS_PRODUCTION","").lower() in ("1","true","yes","on") else "https://app.sandbox.midtrans.com"

def create_snap(order_id, gross_amount, item_name, customer):
    key=os.environ.get("GURUWALI_MIDTRANS_SERVER_KEY","").strip()
    if not key:
        raise RuntimeError("Midtrans belum dikonfigurasi.")
    payload={
        "transaction_details":{"order_id":str(order_id),"gross_amount":int(gross_amount)},
        "item_details":[{"id":str(order_id),"price":int(gross_amount),"quantity":1,"name":str(item_name)[:50]}],
        "customer_details":{
            "first_name":str((customer or {}).get("nama") or "GuruWali")[:80],
            "email":str((customer or {}).get("email") or "")[:100],
        },
    }
    data=json.dumps(payload).encode("utf-8")
    token=base64.b64encode((key+":").encode()).decode()
    req=urllib.request.Request(
        base_url()+"/snap/v1/transactions", data=data,
        headers={"Accept":"application/json","Content-Type":"application/json","Authorization":"Basic "+token},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out=json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError("Gagal membuat checkout Midtrans: %s" % e)
    return {
        "token":out.get("token",""),
        "redirect_url":out.get("redirect_url",""),
    }

def verify_notification(body):
    key=os.environ.get("GURUWALI_MIDTRANS_SERVER_KEY","").strip()
    order_id=str(body.get("order_id") or "")
    status_code=str(body.get("status_code") or "")
    gross_amount=str(body.get("gross_amount") or "")
    received=str(body.get("signature_key") or "").lower()
    expected=hashlib.sha512((order_id+status_code+gross_amount+key).encode()).hexdigest().lower()
    return bool(key and received and received == expected)

def successful(body):
    status=str(body.get("transaction_status") or "").lower()
    fraud=str(body.get("fraud_status") or "").lower()
    code=str(body.get("status_code") or "")
    return code == "200" and status in ("settlement","capture") and (not fraud or fraud == "accept")
