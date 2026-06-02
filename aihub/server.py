"""
Obscuron AI Hub — Unified AI API Gateway
Chat, Image, Voice, Music, Stems, Transcribe
"""

import os
import uuid
import logging
import httpx
import base64
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AIHub")

app = FastAPI(title="Obscuron AI Hub", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
STABILITY_KEY = os.getenv("STABILITY_API_KEY", "")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY", "")
SUNO_KEY = os.getenv("SUNO_API_KEY", "")
MOISES_KEY = os.getenv("MOISES_API_KEY", "")


# ── Models ────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "openai/gpt-4o"
    system: Optional[str] = None

class ImageRequest(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    steps: int = 30

class VoiceRequest(BaseModel):
    text: str
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"  # default: Sarah
    model: str = "eleven_multilingual_v2"

class MusicRequest(BaseModel):
    prompt: str
    style: Optional[str] = ""
    duration: int = 30

class MoisesRequest(BaseModel):
    url: str
    stems: str = "2stems"  # 2stems, 4stems, 5stems


# ── Chat ─────────────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not OPENROUTER_KEY:
        raise HTTPException(503, "OPENROUTER_API_KEY not set")

    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages += [{"role": m.role, "content": m.content} for m in req.messages]

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
            json={"model": req.model, "messages": messages, "max_tokens": 2000}
        )
    if resp.status_code != 200:
        raise HTTPException(502, f"OpenRouter error: {resp.text}")
    data = resp.json()
    return {"reply": data["choices"][0]["message"]["content"].strip(), "model": req.model}


# ── Image ─────────────────────────────────────────────────────────────────────

@app.post("/api/image")
async def generate_image(req: ImageRequest):
    if not STABILITY_KEY:
        raise HTTPException(503, "STABILITY_API_KEY not set")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={"Authorization": f"Bearer {STABILITY_KEY}", "Accept": "application/json"},
            data={"prompt": req.prompt, "output_format": "jpeg"},
            files={"none": ("", b"", "text/plain")}
        )
    if resp.status_code != 200:
        raise HTTPException(502, f"Stability error: {resp.text}")
    data = resp.json()
    image_b64 = data.get("image", "")
    return {"image": image_b64, "prompt": req.prompt}


# ── Voice (ElevenLabs) ────────────────────────────────────────────────────────

@app.post("/api/voice")
async def text_to_speech(req: VoiceRequest):
    if not ELEVENLABS_KEY:
        raise HTTPException(503, "ELEVENLABS_API_KEY not set")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{req.voice_id}",
            headers={"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"},
            json={"text": req.text, "model_id": req.model, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
        )
    if resp.status_code != 200:
        raise HTTPException(502, f"ElevenLabs error: {resp.text}")

    audio_b64 = base64.b64encode(resp.content).decode()
    return {"audio": audio_b64, "format": "mp3"}


@app.get("/api/voices")
async def list_voices():
    if not ELEVENLABS_KEY:
        return {"voices": []}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": ELEVENLABS_KEY}
        )
    if resp.status_code != 200:
        return {"voices": []}
    data = resp.json()
    voices = [{"id": v["voice_id"], "name": v["name"]} for v in data.get("voices", [])]
    return {"voices": voices}


# ── Music (Suno via OpenRouter) ───────────────────────────────────────────────

@app.post("/api/music")
async def generate_music(req: MusicRequest):
    if not OPENROUTER_KEY:
        raise HTTPException(503, "OPENROUTER_API_KEY not set")

    prompt = req.prompt
    if req.style:
        prompt = f"[{req.style}] {prompt}"

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
            json={
                "model": "suno/bark",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            }
        )
    if resp.status_code != 200:
        raise HTTPException(502, f"Music generation error: {resp.text}")
    data = resp.json()
    return {"result": data["choices"][0]["message"]["content"], "prompt": req.prompt}


# ── Stems (Moises) ────────────────────────────────────────────────────────────

@app.post("/api/stems")
async def separate_stems(req: MoisesRequest):
    if not MOISES_KEY:
        raise HTTPException(503, "MOISES_API_KEY not set")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://developer-api.moises.ai/api/job",
            headers={"Authorization": MOISES_KEY, "Content-Type": "application/json"},
            json={
                "name": f"stem-{uuid.uuid4().hex[:8]}",
                "workflow": f"moises/stems-{req.stems}",
                "params": {"inputUrl": req.url}
            }
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(502, f"Moises error: {resp.text}")
    data = resp.json()
    return {"job_id": data.get("id"), "status": data.get("status"), "message": "Job started. Check status with /api/stems/status/{job_id}"}


@app.get("/api/stems/status/{job_id}")
async def stem_status(job_id: str):
    if not MOISES_KEY:
        raise HTTPException(503, "MOISES_API_KEY not set")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"https://developer-api.moises.ai/api/job/{job_id}",
            headers={"Authorization": MOISES_KEY}
        )
    if resp.status_code != 200:
        raise HTTPException(502, f"Moises error: {resp.text}")
    return resp.json()


# ── Transcribe (Whisper via OpenRouter) ───────────────────────────────────────

@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not OPENROUTER_KEY:
        raise HTTPException(503, "OPENROUTER_API_KEY not set")

    audio_data = await file.read()
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            files={"file": (file.filename, audio_data, file.content_type)},
            data={"model": "openai/whisper-1"}
        )
    if resp.status_code != 200:
        raise HTTPException(502, f"Transcription error: {resp.text}")
    data = resp.json()
    return {"text": data.get("text", "")}


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
