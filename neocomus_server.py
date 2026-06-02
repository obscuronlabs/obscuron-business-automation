"""
Neocomus Music — Command Center Backend
- Perplexity (sonar) for real-time web search via OpenRouter
- Anthropic fallback
- Cross-agent coordination
"""

import os
import logging
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NeocomusServer")

app = FastAPI(title="Neocomus Command Center", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "")

valid_tokens: set = set()
agent_memory: dict = {}


class AuthRequest(BaseModel):
    password: str


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    token: str
    member_key: str
    system_prompt: str
    messages: List[Message]
    max_tokens: int = 1200
    enable_research: bool = True
    coordinate_with: Optional[List[str]] = None


# ── LLM Call ─────────────────────────────────────────────────────────────────

async def call_llm(system_prompt: str, messages: list, max_tokens: int = 1200, search: bool = False) -> str:
    """
    search=True  → uses perplexity/sonar-pro (built-in live web search, like Claude)
    search=False → uses openai/gpt-4o for regular tasks
    Falls back to Anthropic if no OpenRouter key.
    """
    if OPENROUTER_API_KEY:
        model = "perplexity/sonar-pro-search" if search else "openai/gpt-4o"
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
        }
        logger.info(f"LLM call → {model}")
    else:
        api_url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        }
        payload = {
            "model": "claude-sonnet-4-6",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(api_url, headers=headers, json=payload)

    if resp.status_code != 200:
        logger.error(f"LLM error {resp.status_code}: {resp.text[:300]}")
        raise HTTPException(status_code=502, detail="AI service error. Try again.")

    data = resp.json()
    if OPENROUTER_API_KEY:
        return data["choices"][0]["message"]["content"] if data.get("choices") else ""
    else:
        return data["content"][0]["text"] if data.get("content") else ""


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_command_center():
    html_path = os.path.join(os.path.dirname(__file__), "command.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/auth")
async def authenticate(req: AuthRequest):
    if req.password != ACCESS_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect access code")
    token = str(uuid.uuid4())
    valid_tokens.add(token)
    logger.info("Auth success")
    return {"token": token}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if req.token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid session. Please re-authenticate.")

    if not ANTHROPIC_API_KEY and not OPENROUTER_API_KEY:
        raise HTTPException(status_code=503, detail="No API key configured.")

    user_message = req.messages[-1].content if req.messages else ""
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    # ── Cross-agent coordination context ─────────────────────────────────────
    coord_context = ""
    if req.coordinate_with:
        parts = []
        for key in req.coordinate_with:
            if key in agent_memory and agent_memory[key]:
                parts.append(f"[{key}]: {agent_memory[key][:400]}")
        if parts:
            coord_context = "\n\n=== TEAM INSIGHTS ===\n" + "\n\n".join(parts)

    # ── Build system prompt ───────────────────────────────────────────────────
    from datetime import datetime
    today = datetime.utcnow().strftime("%B %d, %Y")

    enriched_system = (
        f"Today's date is {today}.\n\n"
        "You have LIVE internet access. Search the web for current facts, dates, events, charts, and news. "
        "Always give specific, accurate answers with real data. "
        "Never say 'I cannot browse the internet' — you can and must search.\n\n"
        + req.system_prompt
    )
    if coord_context:
        enriched_system += coord_context

    # ── Call LLM (Perplexity sonar = built-in web search) ────────────────────
    use_search = req.enable_research and bool(OPENROUTER_API_KEY)
    reply = await call_llm(enriched_system, messages, req.max_tokens, search=use_search)

    agent_memory[req.member_key] = reply[:600]

    return {
        "reply": reply,
        "research_used": use_search,
        "coordination_used": bool(coord_context),
    }


@app.get("/api/agent-memory")
async def get_agent_memory():
    return agent_memory


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "openrouter": bool(OPENROUTER_API_KEY),
        "anthropic": bool(ANTHROPIC_API_KEY),
        "agents_active": len(agent_memory),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
