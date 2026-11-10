import os, time, json
from collections import defaultdict, deque
from typing import Any
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
ALLOWED_MODELS = {
    x.strip() for x in os.getenv(
        "ARIA_ALLOWED_MODELS",
        "gpt-4o-mini,gpt-4.1,gpt-image-1"
    ).split(",") if x.strip()
}
MAX_BODY_BYTES = int(os.getenv("ARIA_MAX_BODY_BYTES", "1048576"))
RATE_LIMIT = int(os.getenv("ARIA_REQUESTS_PER_MINUTE", "12"))
hits = defaultdict(deque)

app = FastAPI(title="ARIA ORIGINAL API", version="1.0.0")

@app.get("/health")
async def health():
    return {
        "service": "aria-original-api",
        "status": "ready" if OPENAI_API_KEY else "needs_secret"
    }

def check_rate(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    q = hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(429, "Πάρα πολλά αιτήματα.")
    q.append(now)

@app.post("/v1/chat/completions")
async def chat(request: Request):
    return await proxy(request, "/v1/chat/completions")

@app.post("/v1/images/generations")
async def images(request: Request):
    return await proxy(request, "/v1/images/generations")

async def proxy(request: Request, path: str):
    check_rate(request)
    if not OPENAI_API_KEY:
        raise HTTPException(503, "Η online υπηρεσία δεν έχει ρυθμιστεί.")
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        raise HTTPException(413, "Το αίτημα είναι πολύ μεγάλο.")
    try:
        data: dict[str, Any] = json.loads(raw)
    except Exception:
        raise HTTPException(400, "Μη έγκυρο JSON.")
    if str(data.get("model", "")) not in ALLOWED_MODELS:
        raise HTTPException(400, "Το μοντέλο δεν επιτρέπεται.")
    timeout = httpx.Timeout(180.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            upstream = await client.post(
                "https://api.openai.com" + path,
                headers={
                    "Authorization": "Bearer " + OPENAI_API_KEY,
                    "Content-Type": "application/json"
                },
                content=raw
            )
        except httpx.HTTPError:
            raise HTTPException(502, "Η υπηρεσία AI δεν είναι διαθέσιμη.")
    try:
        result = upstream.json()
    except Exception:
        raise HTTPException(502, "Μη έγκυρη απάντηση AI.")
    return JSONResponse(
        status_code=upstream.status_code,
        content=result,
        headers={"Cache-Control": "no-store"}
    )
