"""
Neocomus Music — Command Center Backend
- OpenRouter / Anthropic AI
- DuckDuckGo web research per agent
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

# ── Agent coordination memory (cross-agent context) ──────────────────────────
agent_memory: dict = {}  # member_key → last output


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
    coordinate_with: Optional[List[str]] = None  # other agent keys to pull context from


# ── Web Search ───────────────────────────────────────────────────────────────

async def web_search(query: str, max_results: int = 4) -> str:
    """DuckDuckGo instant search — no API key needed."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                headers={"User-Agent": "NeocomusBot/2.0"},
            )
            data = resp.json()

        results = []
        # Abstract
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"])

        if results:
            return "\n".join(f"• {r}" for r in results[:max_results])

        # Fallback: search via HTML scrape
        resp2 = await httpx.AsyncClient(timeout=10).get(
            f"https://duckduckgo.com/html/?q={query}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        import re
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp2.text)
        clean = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:max_results]]
        return "\n".join(f"• {s}" for s in clean if s) or "No results found."

    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return ""


def build_research_queries(member_key: str, user_message: str) -> List[str]:
    """Generate relevant search queries per agent role."""
    queries = [f"Neocomus Music {user_message[:60]}"]
    role_queries = {
        "SW": [f"music industry trends {user_message[:50]}", "streaming music market 2025"],
        "AR": [f"Spotify royalties streaming revenue {user_message[:50]}", "music monetization 2025"],
        "NV": [f"music copyright licensing {user_message[:50]}"],
        "PA": [f"music listener behavior psychology {user_message[:50]}"],
        "OOK": [f"jazz blues world music trends {user_message[:50]}"],
        "VH": [f"music branding visual identity {user_message[:50]}"],
        "MS": [f"artist relations music label {user_message[:50]}"],
        "BC": [f"music business strategy {user_message[:50]}"],
        "OL": [f"music visual design creative direction {user_message[:50]}"],
    }
    queries += role_queries.get(member_key, [f"music business {user_message[:50]}"])
    return queries[:2]


async def gather_research(member_key: str, user_message: str) -> str:
    queries = build_research_queries(member_key, user_message)
    all_results = []
    for q in queries:
        result = await web_search(q)
        if result:
            all_results.append(f"[Search: {q}]\n{result}")
    return "\n\n".join(all_results)


# ── LLM Call ─────────────────────────────────────────────────────────────────

async def call_llm(system_prompt: str, messages: list, max_tokens: int = 1200) -> str:
    use_openrouter = bool(OPENROUTER_API_KEY) and not bool(ANTHROPIC_API_KEY)

    if use_openrouter:
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
        payload = {
            "model": "openai/gpt-4o-mini",
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
        }
    else:
        api_url = "https://api.anthropic.com/v1/messages"
        headers = {"Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"}
        payload = {"model": "claude-sonnet-4-6", "max_tokens": max_tokens, "system": system_prompt, "messages": messages}

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(api_url, headers=headers, json=payload)

    if resp.status_code != 200:
        logger.error(f"LLM error {resp.status_code}: {resp.text[:300]}")
        raise HTTPException(status_code=502, detail="AI service error. Try again.")

    data = resp.json()
    if use_openrouter:
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

    # ── 1. Web research ───────────────────────────────────────────────────────
    research_context = ""
    if req.enable_research and user_message:
        research_context = await gather_research(req.member_key, user_message)

    # ── 2. Cross-agent coordination context ──────────────────────────────────
    coord_context = ""
    if req.coordinate_with:
        parts = []
        for key in req.coordinate_with:
            if key in agent_memory and agent_memory[key]:
                parts.append(f"[{key}]: {agent_memory[key][:400]}")
        if parts:
            coord_context = "\n\n=== TEAM INSIGHTS ===\n" + "\n\n".join(parts)

    # ── 3. Build enriched system prompt ──────────────────────────────────────
    enriched_system = req.system_prompt
    if research_context:
        enriched_system += f"\n\n=== CURRENT WEB RESEARCH ===\n{research_context}\n\nUse this real-time data in your response where relevant."
    if coord_context:
        enriched_system += coord_context

    # ── 4. Call LLM ──────────────────────────────────────────────────────────
    reply = await call_llm(enriched_system, messages, req.max_tokens)

    # ── 5. Store in agent memory for coordination ─────────────────────────────
    agent_memory[req.member_key] = reply[:600]

    return {
        "reply": reply,
        "research_used": bool(research_context),
        "coordination_used": bool(coord_context),
    }


@app.get("/api/agent-memory")
async def get_agent_memory():
    """Returns what each agent last said — for cross-agent awareness."""
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
