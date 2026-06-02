"""
Obscuron AI Chatbot — Embeddable Widget Backend
White-label AI chatbot for any business website.
"""

import os
import uuid
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChatbotServer")

app = FastAPI(title="Obscuron AI Chatbot", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ── Client registry — each client has a widget_id + config ───────────────────
# In production this would be a database
CLIENTS = {
    "demo": {
        "business_name": "Demo Business",
        "business_type": "general",
        "primary_color": "#6c5fff",
        "greeting": "Hi! How can I help you today?",
        "system_prompt": "You are a helpful AI assistant for Demo Business. Answer questions professionally and helpfully. Keep responses concise.",
        "allowed_domains": ["*"],
    }
}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    widget_id: str
    messages: List[ChatMessage]
    visitor_id: Optional[str] = None


class RegisterRequest(BaseModel):
    business_name: str
    business_type: str
    primary_color: str = "#6c5fff"
    greeting: str = "Hi! How can I help you today?"
    system_prompt: str = ""
    allowed_domains: List[str] = ["*"]


@app.post("/api/register")
async def register_client(req: RegisterRequest):
    """Register a new business and get their widget_id."""
    widget_id = str(uuid.uuid4())[:12]
    if not req.system_prompt:
        req.system_prompt = (
            f"You are a helpful AI assistant for {req.business_name}, a {req.business_type}. "
            "Answer questions about the business professionally and helpfully. "
            "Keep responses concise and friendly. "
            "If you don't know something specific about the business, politely say to contact them directly."
        )
    CLIENTS[widget_id] = {
        "business_name": req.business_name,
        "business_type": req.business_type,
        "primary_color": req.primary_color,
        "greeting": req.greeting,
        "system_prompt": req.system_prompt,
        "allowed_domains": req.allowed_domains,
    }
    logger.info(f"New client registered: {req.business_name} → {widget_id}")
    return {
        "widget_id": widget_id,
        "embed_code": f'<script src="https://YOUR_DOMAIN/widget.js" data-widget="{widget_id}"></script>',
        "business_name": req.business_name,
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    client = CLIENTS.get(req.widget_id)
    if not client:
        raise HTTPException(status_code=404, detail="Widget not found.")

    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=503, detail="API not configured.")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    from datetime import datetime
    today = datetime.utcnow().strftime("%B %d, %Y")
    system = f"Today is {today}.\n\n{client['system_prompt']}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    }
    payload = {
        "model": "openai/gpt-4o-mini",
        "max_tokens": 400,
        "messages": [{"role": "system", "content": system}] + messages,
    }

    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="AI error.")

    data = resp.json()
    reply = data["choices"][0]["message"]["content"].strip()
    return {"reply": reply}


@app.get("/api/config/{widget_id}")
async def get_config(widget_id: str):
    client = CLIENTS.get(widget_id)
    if not client:
        raise HTTPException(status_code=404, detail="Widget not found.")
    return {
        "business_name": client["business_name"],
        "primary_color": client["primary_color"],
        "greeting": client["greeting"],
    }


@app.get("/widget.js")
async def serve_widget():
    return FileResponse("widget.js", media_type="application/javascript")


@app.get("/demo")
async def demo_page():
    html_path = os.path.join(os.path.dirname(__file__), "demo.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
