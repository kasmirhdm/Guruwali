"""Platform admin helpers for GuruWali."""
import json
import os
from db import get_conn, now

def is_platform_admin(user):
    if not user: return False
    if int(user.get("is_platform_admin") or 0) == 1: return True
    emails={x.strip().lower() for x in os.environ.get("GURUWALI_ADMIN_EMAILS","").split(",") if x.strip()}
    return user.get("email","").lower() in emails

def bootstrap_env_admins():
    emails=[x.strip().lower() for x in os.environ.get("GURUWALI_ADMIN_EMAILS","").split(",") if x.strip()]
    if not emails: return
    conn=get_conn()
    try:
        for email in emails: conn.execute("UPDATE users SET is_platform_admin=1 WHERE email=?",(email,))
        conn.commit()
    finally: conn.close()

def audit(user_id, action, target_type="", target_id=None, details=None):
    conn=get_conn()
    try:
        conn.execute("INSERT INTO audit_logs (user_id,action,target_type,target_id,details,created_at) VALUES (?,?,?,?,?,?)",
                     (user_id,action,target_type,target_id,json.dumps(details or {},ensure_ascii=False),now()))
        conn.commit()
    finally: conn.close()

def dashboard():
    conn=get_conn()
    try:
        q=lambda sql: conn.execute(sql).fetchone()["c"]
        recent=conn.execute("SELECT id,nama,email,sekolah,created_at,is_pro,is_platform_admin FROM users ORDER BY created_at DESC LIMIT 10").fetchall()
        return {"users":q("SELECT COUNT(*) c FROM users"),"schools":q("SELECT COUNT(*) c FROM schools"),
                "pro_users":q("SELECT COUNT(*) c FROM users WHERE is_pro=1"),"pro_schools":q("SELECT COUNT(*) c FROM schools WHERE is_pro=1"),
                "documents":q("SELECT COUNT(*) c FROM documents"),"members":q("SELECT COUNT(*) c FROM school_members"),
                "recent_users":[dict(r) for r in recent]}
    finally: conn.close()

def users(limit=200):
    conn=get_conn()
    try:
        rows=conn.execute("""SELECT u.id,u.nama,u.email,u.sekolah,u.school_id,u.is_pro,u.is_platform_admin,u.quota_used,u.quota_limit,u.created_at,
                             sm.role school_role FROM users u LEFT JOIN school_members sm ON sm.user_id=u.id AND sm.school_id=u.school_id
                             ORDER BY u.created_at DESC LIMIT ?""",(max(1,min(int(limit),500)),)).fetchall()
        return [dict(r) for r in rows]
    finally: conn.close()

def schools(limit=200):
    conn=get_conn()
    try:
        rows=conn.execute("""SELECT s.id,s.nama,s.npsn,s.kota,s.admin_user_id,s.quota_used,s.quota_limit,s.is_pro,s.created_at,
                             u.nama admin_nama,u.email admin_email,
                             (SELECT COUNT(*) FROM school_members m WHERE m.school_id=s.id) member_count
                             FROM schools s LEFT JOIN users u ON u.id=s.admin_user_id ORDER BY s.created_at DESC LIMIT ?""",
                          (max(1,min(int(limit),500)),)).fetchall()
        return [dict(r) for r in rows]
    finally: conn.close()

def set_user_pro(user_id,enabled,actor_id):
    conn=get_conn()
    try:
        ql=100 if enabled else 5
        cur=conn.execute("UPDATE users SET is_pro=?, quota_limit=? WHERE id=?",(1 if enabled else 0,ql,user_id)); conn.commit(); ok=cur.rowcount>0
    finally: conn.close()
    if ok: audit(actor_id,"set_user_pro","user",user_id,{"enabled":bool(enabled)})
    return ok

def set_school_pro(school_id,enabled,actor_id):
    conn=get_conn()
    try:
        ql=1000 if enabled else 50
        cur=conn.execute("UPDATE schools SET is_pro=?, quota_limit=? WHERE id=?",(1 if enabled else 0,ql,school_id)); conn.commit(); ok=cur.rowcount>0
    finally: conn.close()
    if ok: audit(actor_id,"set_school_pro","school",school_id,{"enabled":bool(enabled)})
    return ok

def recent_audit(limit=100):
    conn=get_conn()
    try:
        rows=conn.execute("""SELECT a.*,u.nama actor_name,u.email actor_email FROM audit_logs a LEFT JOIN users u ON u.id=a.user_id
                             ORDER BY a.created_at DESC LIMIT ?""",(max(1,min(int(limit),200)),)).fetchall()
        return [dict(r) for r in rows]
    finally: conn.close()
