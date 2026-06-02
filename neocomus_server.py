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
    """DuckDuckGo search — runs in thread pool to avoid blocking."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def _search():
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if results:
                return "\n".join(f"• {r['title']}: {r['body']}" for r in results)
            return ""
        except Exception as e:
            logger.warning(f"DDG search error: {e}")
            return ""

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, _search)
    return result


def build_research_queries(member_key: str, user_message: str) -> List[str]:
    """Generate English search queries for better results."""
    # Always search in English for better coverage
    msg = user_message[:100]
    primary = msg
    secondary = f"{msg} 2025 2026"
    return [primary, secondary]


async def gather_research(member_key: str, user_message: str) -> str:
    # Turkish → English: stem-based replacements (handles suffixes via substring match)
    tr_en = [
        ("ne zaman", "when"), ("nezaman", "when"), ("nerede", "where"),
        ("hangi", "which"), ("nasil", "how"), ("nasıl", "how"),
        ("ne kadar", "how much"), ("kimdi", "who was"), ("kimle", "with who"),
        ("iptal", "cancelled"), ("ertelendi", "postponed"),
        ("son konser", "latest concert"), ("konser", "concert"),
        ("turne", "tour"), ("tur ", "tour "),
        ("tarih", "date"), ("sehir", "city"), ("şehir", "city"),
        ("ulke", "country"), ("ülke", "country"),
        ("bugun", "today"), ("bugün", "today"), ("yarin", "tomorrow"), ("yarın", "tomorrow"),
        ("sarki", "song"), ("şarkı", "song"), ("muzik", "music"), ("müzik", "music"),
        ("dinlenme", "streams"), ("akis", "streams"), ("akış", "streams"),
        ("sanatci", "artist"), ("sanatçı", "artist"),
        ("album", "album"), ("albüm", "album"),
        ("liste", "chart"), ("grafik", "chart"),
        ("sene", "year"), ("yil", "year"), ("yıl", "year"),
        ("hafta", "week"), ("ay", "month"),
        ("biletin", "ticket"), ("bilet", "ticket"),
        ("stadyum", "stadium"), ("arena", "arena"), ("sahne", "stage"),
        ("kapali", "indoor"), ("kapalı", "indoor"), ("acik", "outdoor"), ("açık", "outdoor"),
        ("ne zaman", "when"), ("kac", "how many"), ("kaç", "how many"),
        ("verdi", "performed"), ("yapti", "did"), ("yaptı", "did"),
        ("geldi", "came"), ("gitti", "went"), ("oldu", "happened"),
        ("vardi", "was"), ("vardı", "was"), ("neydi", "what was"),
    ]
    msg = user_message.lower()
    for tr, en in tr_en:
        msg = msg.replace(tr, en)

    # Remove leftover Turkish suffix noise (common endings)
    import re
    msg = re.sub(r'\b\w*(inde|ında|nda|nde|ını|ini|unu|ünu|dan|den|tan|ten|ları|leri|ında|nın|nin|nun|nün|mı|mi|mu|mü|dı|di|du|dü|tı|ti|tu|tü)\b', '', msg)
    msg = re.sub(r'\s+', ' ', msg).strip()

    # Build smart queries: original cleaned + force 2025/2026 year
    queries = [msg[:120], f"{msg[:90]} 2025 OR 2026"]

    all_results = []
    for q in queries:
        result = await web_search(q)
        if result:
            all_results.append(f"[Search: {q}]\n{result}")
            logger.info(f"Search '{q}' → {len(result)} chars")
        else:
            logger.info(f"Search '{q}' → NO RESULTS")
    return "\n\n".join(all_results)


# ── LLM Call ─────────────────────────────────────────────────────────────────

async def call_llm(system_prompt: str, messages: list, max_tokens: int = 1200) -> str:
    use_openrouter = bool(OPENROUTER_API_KEY) and not bool(ANTHROPIC_API_KEY)

    if use_openrouter:
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_API_KEY}"}
        payload = {
            "model": "openai/gpt-4o",
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
    from datetime import datetime
    today = datetime.utcnow().strftime("%B %d, %Y")
    enriched_system = (
        f"Today's date is {today}.\n\n"
        "CRITICAL RULES:\n"
        "1. You have access to LIVE web search results below. Always use them.\n"
        "2. If search results contain the answer, quote facts directly from them.\n"
        "3. If search results came back EMPTY for a topic, say: 'I searched the web but found no information about [topic]. This event may not exist, may not have been announced, or is too recent to index.'\n"
        "4. NEVER say 'I cannot browse the internet' — you have real search results.\n"
        "5. NEVER hallucinate dates, venues, or stats.\n\n"
    ) + req.system_prompt
    if research_context:
        enriched_system += f"\n\n=== LIVE WEB SEARCH RESULTS ===\n{research_context}\n\nAnswer based on these results. If they answer the question, use that data directly."
    else:
        enriched_system += f"\n\n=== SEARCH STATUS ===\nWeb search ran but returned NO RESULTS for this query. Tell the user you searched but found nothing, and explain the event may not exist or hasn't been announced publicly."
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
