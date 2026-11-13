"""
ARIA ORIGINAL API
Account, entitlement and AI gateway.
Billing is deliberately disabled until the owner enables a payment provider.
The first owner is created once via POST /owner/bootstrap using ARIA_OWNER_BOOTSTRAP_TOKEN.
"""
import os, json, time, hmac, hashlib, secrets, sqlite3, smtplib, io
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta
from typing import Any
from contextlib import contextmanager
import httpx
from fastapi import FastAPI, Request, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field

DB_PATH = os.getenv("ARIA_DB_PATH", "aria_original.sqlite3")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OWNER_BOOTSTRAP_TOKEN = os.getenv("ARIA_OWNER_BOOTSTRAP_TOKEN", "").strip()
OWNER_REPORT_EMAIL = os.getenv("ARIA_OWNER_REPORT_EMAIL", "").strip()
SMTP_HOST = os.getenv("ARIA_SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("ARIA_SMTP_PORT", "587"))
SMTP_USER = os.getenv("ARIA_SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("ARIA_SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("ARIA_SMTP_FROM", SMTP_USER).strip()
BILLING_ENABLED = os.getenv("ARIA_BILLING_ENABLED", "false").lower() == "true"
FREE_DAILY_LIMIT = int(os.getenv("ARIA_FREE_DAILY_LIMIT", "30"))
PREMIUM_DAILY_LIMIT = int(os.getenv("ARIA_PREMIUM_DAILY_LIMIT", "300"))
MAX_BODY_BYTES = int(os.getenv("ARIA_MAX_BODY_BYTES", str(12 * 1024 * 1024)))
MAX_IMAGE_BYTES = int(os.getenv("ARIA_MAX_IMAGE_BYTES", str(50 * 1024 * 1024)))
ALLOWED_MODELS = {x.strip() for x in os.getenv("ARIA_ALLOWED_MODELS", "gpt-4o-mini,gpt-4.1,gpt-image-1,gpt-image-2.5-flare").split(",") if x.strip()}
SESSION_SECONDS = 60 * 60 * 24 * 30

app = FastAPI(title="ARIA ORIGINAL API", version="2.0.0")

@contextmanager
def db():
    """Yield a SQLite connection and always close it after the unit of work."""
    c = sqlite3.connect(DB_PATH, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user',
          plan TEXT NOT NULL DEFAULT 'FREE', plan_source TEXT NOT NULL DEFAULT 'free',
          plan_expires_at TEXT, is_active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions(
          token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          expires_at TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS usage(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          kind TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit(
          id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id INTEGER, target_user_id INTEGER,
          action TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS aria_single_owner
          ON users(role) WHERE role='owner';
        """)
init_db()

def now():
    return datetime.now(timezone.utc)

def iso(dt=None):
    return (dt or now()).isoformat()

def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + "$" + digest.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except Exception:
        return False

def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def audit(actor, target, action, details):
    with db() as c:
        c.execute("INSERT INTO audit(actor_id,target_user_id,action,details,created_at) VALUES(?,?,?,?,?)",
                  (actor, target, action, json.dumps(details, ensure_ascii=False), iso()))

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class BootstrapIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=14, max_length=128)
    bootstrap_token: str = Field(min_length=20, max_length=256)

class PlanIn(BaseModel):
    plan: str
    source: str = "owner_grant"
    expires_at: str | None = None

def public_user(row):
    return {"id": row["id"], "email": row["email"], "role": row["role"], "plan": row["plan"],
            "plan_source": row["plan_source"], "plan_expires_at": row["plan_expires_at"],
            "is_active": bool(row["is_active"]), "created_at": row["created_at"]}

def current_user(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Απαιτείται σύνδεση.")
    token = auth[7:].strip()
    with db() as c:
        row = c.execute("""SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                           WHERE s.token_hash=? AND s.expires_at>?""",
                        (token_digest(token), iso())).fetchone()
    if not row or not row["is_active"]:
        raise HTTPException(401, "Η συνεδρία δεν είναι έγκυρη.")
    if row["plan_expires_at"] and row["plan_source"] == "owner_grant" and row["plan_expires_at"] <= iso():
        with db() as c:
            c.execute("UPDATE users SET plan='FREE',plan_source='free',plan_expires_at=NULL,updated_at=? WHERE id=?", (iso(), row["id"]))
        with db() as c:
            row = c.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone()
    return row

def owner_only(user=Depends(current_user)):
    if user["role"] != "owner":
        raise HTTPException(403, "Μόνο ο ιδιοκτήτης έχει πρόσβαση.")
    return user

def issue_session(user_id):
    token = secrets.token_urlsafe(48)
    with db() as c:
        c.execute("INSERT INTO sessions(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)",
                  (token_digest(token), user_id, iso(now()+timedelta(seconds=SESSION_SECONDS)), iso()))
    return token

@app.get("/health")
def health():
    with db() as c:
        users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    return {"service":"aria-original-api","status":"ready","accounts":users,
            "billing_enabled":BILLING_ENABLED,"billing_price_eur":5,"billing_currency":"EUR"}

@app.post("/owner/bootstrap")
def owner_bootstrap(data: BootstrapIn):
    if not OWNER_BOOTSTRAP_TOKEN or not hmac.compare_digest(data.bootstrap_token, OWNER_BOOTSTRAP_TOKEN):
        raise HTTPException(403, "Μη έγκυρο κλειδί αρχικής ενεργοποίησης ιδιοκτήτη.")
    with db() as c:
        count = c.execute("SELECT COUNT(*) n FROM users WHERE role='owner'").fetchone()["n"]
        if count:
            raise HTTPException(409, "Ο ιδιοκτήτης έχει ήδη οριστεί.")
        try:
            cur = c.execute("""INSERT INTO users(email,password_hash,role,plan,plan_source,created_at,updated_at)
                               VALUES(?,?, 'owner','FREE','free',?,?)""",
                            (data.email.lower(), password_hash(data.password), iso(), iso()))
        except sqlite3.IntegrityError:
            # The partial unique index makes owner creation atomic even if two
            # bootstrap requests arrive concurrently.
            raise HTTPException(409, "Ο ιδιοκτήτης έχει ήδη οριστεί.")
        uid = cur.lastrowid
    audit(uid, uid, "owner_bootstrap", {"email":data.email.lower()})
    token = issue_session(uid)
    return {"token":token,"user":{"id":uid,"email":data.email.lower(),"role":"owner","plan":"FREE"}}

@app.post("/auth/register")
def register(data: RegisterIn):
    email = data.email.lower().strip()
    with db() as c:
        try:
            cur = c.execute("""INSERT INTO users(email,password_hash,created_at,updated_at)
                               VALUES(?,?,?,?)""", (email,password_hash(data.password),iso(),iso()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "Το email χρησιμοποιείται ήδη.")
        uid = cur.lastrowid
    token = issue_session(uid)
    return {"token":token,"user":{"id":uid,"email":email,"role":"user","plan":"FREE","plan_source":"free"}}

@app.post("/auth/login")
def login(data: LoginIn):
    with db() as c:
        row = c.execute("SELECT * FROM users WHERE email=?", (data.email.lower().strip(),)).fetchone()
    if not row or not verify_password(data.password, row["password_hash"]) or not row["is_active"]:
        raise HTTPException(401, "Λάθος email ή κωδικός.")
    token = issue_session(row["id"])
    return {"token":token,"user":public_user(row)}

@app.get("/auth/me")
def me(user=Depends(current_user)):
    return {"user":public_user(user), "premium_price_eur":5, "billing_enabled":BILLING_ENABLED}

@app.post("/auth/logout")
def logout(request: Request, user=Depends(current_user)):
    token = request.headers.get("Authorization","")[7:].strip()
    with db() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (token_digest(token),))
    return {"ok":True}

@app.get("/account/subscription")
def subscription(user=Depends(current_user)):
    return {"plan":user["plan"],"source":user["plan_source"],"expires_at":user["plan_expires_at"],
            "price_eur":5,"billing_enabled":BILLING_ENABLED,
            "status":"inactive_until_owner_enables_billing" if not BILLING_ENABLED else "provider_configuration_required"}

@app.get("/admin/overview")
def admin_overview(owner=Depends(owner_only)):
    with db() as c:
        counts = {r["plan"]:r["n"] for r in c.execute("SELECT plan,COUNT(*) n FROM users WHERE role='user' GROUP BY plan")}
        paid = c.execute("SELECT COUNT(*) n FROM users WHERE plan='PREMIUM' AND plan_source='paid'").fetchone()["n"]
        gifted = c.execute("SELECT COUNT(*) n FROM users WHERE plan='PREMIUM' AND plan_source='owner_grant'").fetchone()["n"]
        recent = c.execute("SELECT * FROM users WHERE role='user' ORDER BY id DESC LIMIT 100").fetchall()
    return {"free_users":counts.get("FREE",0),"premium_paid":paid,"premium_free_granted":gifted,
            "users":[public_user(r) for r in recent]}

@app.get("/admin/users")
def admin_users(owner=Depends(owner_only), q: str = ""):
    with db() as c:
        rows = c.execute("SELECT * FROM users WHERE role='user' AND email LIKE ? ORDER BY id DESC LIMIT 500", ("%"+q+"%",)).fetchall()
    return {"users":[public_user(r) for r in rows]}

@app.patch("/admin/users/{user_id}/plan")
def admin_set_plan(user_id: int, data: PlanIn, owner=Depends(owner_only)):
    plan = data.plan.upper()
    if plan not in ("FREE","PREMIUM"):
        raise HTTPException(400, "Το πρόγραμμα πρέπει να είναι FREE ή PREMIUM.")
    source = "free" if plan == "FREE" else data.source
    if plan == "PREMIUM" and source not in ("owner_grant","paid"):
        raise HTTPException(400, "Μη έγκυρη προέλευση Premium.")
    if source == "paid" and not BILLING_ENABLED:
        raise HTTPException(409, "Οι πληρωμές είναι ανενεργές. Δεν μπορεί να δηλωθεί πληρωμένο Premium.")
    expires = data.expires_at
    if expires:
        try:
            datetime.fromisoformat(expires.replace("Z","+00:00"))
        except ValueError:
            raise HTTPException(400, "Μη έγκυρη ημερομηνία λήξης.")
    with db() as c:
        target = c.execute("SELECT * FROM users WHERE id=? AND role='user'", (user_id,)).fetchone()
        if not target:
            raise HTTPException(404, "Ο χρήστης δεν βρέθηκε.")
        c.execute("UPDATE users SET plan=?,plan_source=?,plan_expires_at=?,updated_at=? WHERE id=?",
                  (plan,source,expires if plan=="PREMIUM" else None,iso(),user_id))
    audit(owner["id"],user_id,"plan_changed",{"plan":plan,"source":source,"expires_at":expires})
    return {"ok":True,"user_id":user_id,"plan":plan,"source":source,"expires_at":expires}

@app.patch("/admin/users/{user_id}/active")
def admin_set_active(user_id: int, active: bool, owner=Depends(owner_only)):
    with db() as c:
        cur = c.execute("UPDATE users SET is_active=?,updated_at=? WHERE id=? AND role='user'", (1 if active else 0,iso(),user_id))
        if not cur.rowcount: raise HTTPException(404,"Ο χρήστης δεν βρέθηκε.")
        if not active: c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    audit(owner["id"],user_id,"account_active_changed",{"active":active})
    return {"ok":True,"active":active}

@app.get("/admin/audit")
def admin_audit(owner=Depends(owner_only), limit: int = 100):
    with db() as c:
        rows=c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?",(max(1,min(limit,500)),)).fetchall()
    return {"events":[dict(r) for r in rows]}

def send_report(subject, body):
    if not (OWNER_REPORT_EMAIL and SMTP_HOST and SMTP_USER and SMTP_PASSWORD and SMTP_FROM):
        return False
    msg=EmailMessage(); msg["Subject"]=subject; msg["From"]=SMTP_FROM; msg["To"]=OWNER_REPORT_EMAIL; msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=20) as s:
        s.starttls(); s.login(SMTP_USER,SMTP_PASSWORD); s.send_message(msg)
    return True

@app.post("/admin/reports/email")
def email_report(owner=Depends(owner_only)):
    with db() as c:
        free=c.execute("SELECT COUNT(*) n FROM users WHERE role='user' AND plan='FREE'").fetchone()["n"]
        paid=c.execute("SELECT COUNT(*) n FROM users WHERE role='user' AND plan='PREMIUM' AND plan_source='paid'").fetchone()["n"]
        gifted=c.execute("SELECT COUNT(*) n FROM users WHERE role='user' AND plan='PREMIUM' AND plan_source='owner_grant'").fetchone()["n"]
        total=c.execute("SELECT COUNT(*) n FROM users WHERE role='user'").fetchone()["n"]
        grants=c.execute("SELECT email,plan_expires_at FROM users WHERE role='user' AND plan='PREMIUM' AND plan_source='owner_grant' ORDER BY email").fetchall()
    body=f"ARIA ORIGINAL — Αναφορά\nΣύνολο χρηστών: {total}\nFREE: {free}\nPREMIUM επί πληρωμή: {paid}\nPREMIUM δωρεάν από ιδιοκτήτη: {gifted}\n\nΔωρεάν παροχές:\n"
    body += "\n".join(f"{r['email']} — λήξη: {r['plan_expires_at'] or 'χωρίς λήξη'}" for r in grants)
    try: sent=send_report("ARIA ORIGINAL — Αναφορά χρηστών",body)
    except Exception: sent=False
    if not sent: raise HTTPException(503,"Το email δεν έχει ρυθμιστεί ακόμη. Η αναφορά δεν στάλθηκε.")
    return {"ok":True,"sent_to":OWNER_REPORT_EMAIL}

def record_usage(user_id, kind):
    today=now().date().isoformat()
    limit=PREMIUM_DAILY_LIMIT if kind.startswith("premium:") else FREE_DAILY_LIMIT
    with db() as c:
        used=c.execute("SELECT COUNT(*) n FROM usage WHERE user_id=? AND substr(created_at,1,10)=?",(user_id,today)).fetchone()["n"]
        if used>=limit: raise HTTPException(429,"Έφτασες το ημερήσιο όριο χρήσης του λογαριασμού σου.")
        c.execute("INSERT INTO usage(user_id,kind,created_at) VALUES(?,?,?)",(user_id,kind,iso()))

async def ai_proxy(request: Request | None, path: str, user, upload: bytes | None = None,
                   prompt: str | None = None, upload_filename: str = "image.jpg",
                   upload_content_type: str = "application/octet-stream",
                   image_quality: str = "medium", output_format: str = "png"):
    if not OPENAI_API_KEY: raise HTTPException(503,"Το Online AI δεν έχει ρυθμιστεί.")
    if upload is None:
        raw=await request.body()
        if len(raw)>MAX_BODY_BYTES: raise HTTPException(413,"Το αίτημα είναι πολύ μεγάλο.")
        try: data=json.loads(raw)
        except Exception: raise HTTPException(400,"Μη έγκυρο JSON.")
        model=str(data.get("model",""))
        if model not in ALLOWED_MODELS: raise HTTPException(400,"Το μοντέλο δεν επιτρέπεται.")
        record_usage(user["id"], ("premium:" if user["plan"]=="PREMIUM" else "free:")+path)
        headers={"Authorization":"Bearer "+OPENAI_API_KEY,"Content-Type":"application/json"}
        content=raw
    else:
        if len(upload)>MAX_IMAGE_BYTES: raise HTTPException(413,"Η εικόνα είναι πολύ μεγάλη.")
        record_usage(user["id"], ("premium:" if user["plan"]=="PREMIUM" else "free:")+path)
        headers={"Authorization":"Bearer "+OPENAI_API_KEY}
        content=None
    timeout=httpx.Timeout(240.0,connect=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if upload is None:
                upstream=await client.post("https://api.openai.com"+path,headers=headers,content=content)
            else:
                files={"image":(upload_filename or "image.jpg",upload,upload_content_type or "application/octet-stream")}
                upstream=await client.post("https://api.openai.com/v1/images/edits",headers={"Authorization":"Bearer "+OPENAI_API_KEY},
                    data={"model":os.getenv("ARIA_IMAGE_EDIT_MODEL","gpt-image-1"),
                          "prompt":prompt or "", "quality":image_quality,
                          "output_format":output_format},files=files)
        except httpx.HTTPError: raise HTTPException(502,"Η υπηρεσία AI δεν είναι διαθέσιμη.")
    try: result=upstream.json()
    except Exception: raise HTTPException(502,"Μη έγκυρη απάντηση AI.")
    return JSONResponse(status_code=upstream.status_code,content=result,headers={"Cache-Control":"no-store"})

@app.post("/v1/chat/completions")
async def chat(request: Request, user=Depends(current_user)):
    return await ai_proxy(request,"/v1/chat/completions",user)

@app.post("/v1/images/generations")
async def images(request: Request, user=Depends(current_user)):
    return await ai_proxy(request,"/v1/images/generations",user)

@app.post("/v1/images/edits")
async def image_edits(image: UploadFile=File(...), prompt: str=Form(...),
                      quality: str=Form("medium"), output_format: str=Form("png"),
                      user=Depends(current_user)):
    data=await image.read(MAX_IMAGE_BYTES+1)
    if len(data)>MAX_IMAGE_BYTES:
        raise HTTPException(413,"Η εικόνα είναι πολύ μεγάλη.")
    if quality not in ("low","medium","high"):
        raise HTTPException(400,"Μη έγκυρη ποιότητα εικόνας.")
    if output_format not in ("png","jpeg","webp"):
        raise HTTPException(400,"Μη έγκυρη μορφή εξόδου εικόνας.")
    return await ai_proxy(None,"/v1/images/edits",user,upload=data,prompt=prompt,
                          upload_filename=image.filename or "image.jpg",
                          upload_content_type=image.content_type or "application/octet-stream",
                          image_quality=quality,output_format=output_format)

@app.on_event("startup")
def startup():
    init_db()
