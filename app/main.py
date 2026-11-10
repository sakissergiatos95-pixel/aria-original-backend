import os
import json
import time
import hmac
from collections import deque
from datetime import date
from typing import Any

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
ARIA_ACCESS_TOKEN = os.getenv("ARIA_ACCESS_TOKEN", "").strip()

ALLOWED_MODELS = {
    x.strip()
    for x in os.getenv(
        "ARIA_ALLOWED_MODELS",
        "gpt-4o-mini,gpt-4.1,gpt-image-1"
    ).split(",")
    if x.strip()
}

MAX_BODY_BYTES = int(os.getenv("ARIA_MAX_BODY_BYTES", "1048576"))
MAX_PER_MINUTE = int(os.getenv("ARIA_MAX_REQUESTS_PER_MINUTE", "20"))
MAX_PER_DAY = int(os.getenv("ARIA_MAX_REQUESTS_PER_DAY", "100"))

minute_hits = deque()
daily_hits = deque()
daily_date = date.today()

app = FastAPI(title="ARIA ORIGINAL API", version="1.1.0")


@app.get("/health")
async def health():
    return {
        "service": "aria-original-api",
        "status": "ready" if OPENAI_API_KEY and ARIA_ACCESS_TOKEN else "needs_configuration"
    }


def authorize(request: Request):
    if not ARIA_ACCESS_TOKEN:
        raise HTTPException(503, "Η υπηρεσία δεν έχει ρυθμιστεί.")

    supplied = request.headers.get("Authorization", "")
    expected = "Bearer " + ARIA_ACCESS_TOKEN

    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(401, "Μη εξουσιοδοτημένη πρόσβαση.")


def check_limits():
    global daily_date

    now = time.time()
    today = date.today()

    if today != daily_date:
        daily_hits.clear()
        daily_date = today

    while minute_hits and now - minute_hits[0] >= 60:
        minute_hits.popleft()

    if len(minute_hits) >= MAX_PER_MINUTE:
        raise HTTPException(429, "Υπέρβαση ορίου αιτημάτων ανά λεπτό.")

    if len(daily_hits) >= MAX_PER_DAY:
        raise HTTPException(429, "Εξαντλήθηκε το ημερήσιο όριο.")

    minute_hits.append(now)
    daily_hits.append(now)


@app.post("/v1/chat/completions")
async def chat(request: Request):
    return await proxy(request, "/v1/chat/completions")


@app.post("/v1/images/generations")
async def images(request: Request):
    return await proxy(request, "/v1/images/generations")


async def proxy(request: Request, path: str):
    authorize(request)

    if not OPENAI_API_KEY:
        raise HTTPException(503, "Το Online AI δεν έχει ρυθμιστεί.")

    raw = await request.body()

    if len(raw) > MAX_BODY_BYTES:
        raise HTTPException(413, "Το αίτημα είναι πολύ μεγάλο.")

    try:
        data: dict[str, Any] = json.loads(raw)
    except Exception:
        raise HTTPException(400, "Μη έγκυρο JSON.")

    model = str(data.get("model", ""))

    if model not in ALLOWED_MODELS:
        raise HTTPException(400, "Το μοντέλο δεν επιτρέπεται.")

    check_limits()

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
