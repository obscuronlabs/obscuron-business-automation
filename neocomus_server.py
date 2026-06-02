"""
Neocomus Music — Command Center Backend
Proxies Anthropic API calls so the key never reaches the browser.
"""

import os
import hashlib
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NeocomusServer")

app = FastAPI(title="Neocomus Command Center", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
ACCESS_PASSWORD_HASH = os.getenv("ACCESS_PASSWORD_HASH", "")
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "")


def _check_password(provided: str) -> bool:
    if ACCESS_PASSWORD and provided == ACCESS_PASSWORD:
        return True
    if ACCESS_PASSWORD_HASH:
        return hashlib.sha256(provided.encode()).hexdigest() == ACCESS_PASSWORD_HASH
    return False


class AuthRequest(BaseModel):
    password: str


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    token: str          # session token after auth
    member_key: str
    system_prompt: str
    messages: List[Message]
    max_tokens: int = 1000


# Simple in-memory session tokens (reset on server restart)
valid_tokens: set = set()


@app.get("/")
async def serve_command_center():
    html_path = os.path.join(os.path.dirname(__file__), "command.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="command.html not found")


@app.get("/index")
async def serve_website():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html not found")


@app.post("/api/auth")
async def authenticate(req: AuthRequest):
    if not _check_password(req.password):
        raise HTTPException(status_code=401, detail="Incorrect access code")
    import uuid
    token = str(uuid.uuid4())
    valid_tokens.add(token)
    logger.info("Auth success — token issued")
    return {"token": token}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if req.token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please re-authenticate.")

    use_openrouter = bool(OPENROUTER_API_KEY) and not bool(ANTHROPIC_API_KEY)

    if not ANTHROPIC_API_KEY and not OPENROUTER_API_KEY:
        raise HTTPException(status_code=503, detail="API key not configured on server.")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    if use_openrouter:
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        }
        payload = {
            "model": "openai/gpt-4o-mini",
            "max_tokens": req.max_tokens,
            "messages": [{"role": "system", "content": req.system_prompt}] + messages,
        }
    else:
        api_url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": "claude-sonnet-4-6",
            "max_tokens": req.max_tokens,
            "system": req.system_prompt,
            "messages": messages,
        }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(api_url, headers=headers, json=payload)

    if resp.status_code != 200:
        logger.error(f"AI API error {resp.status_code}: {resp.text}")
        raise HTTPException(status_code=502, detail="AI service error. Try again.")

    data = resp.json()
    if use_openrouter:
        reply = data["choices"][0]["message"]["content"] if data.get("choices") else ""
    else:
        reply = data["content"][0]["text"] if data.get("content") else ""
    return {"reply": reply}


@app.get("/api/health")
async def health():
    return {"status": "ok", "api_key_set": bool(ANTHROPIC_API_KEY)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
