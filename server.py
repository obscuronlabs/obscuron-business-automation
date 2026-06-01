"""
Obscuron Labs — FastAPI Web Server
Interactive company simulation dashboard
"""

import os
import json
import uuid
import queue
import threading
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ObscuronServer")

app = FastAPI(title="Obscuron Labs", version="2.1")

# ── In-memory state ──────────────────────────────────────────────────────────

jobs: Dict[str, Dict[str, Any]] = {}

agent_status: Dict[str, str] = {
    "bob_captain": "idle",
    "nox_vale": "idle",
    "pery_ashcroft": "idle",
    "echo_virel": "idle",
    "maya_serrin": "idle",
    "selene_ward": "idle",
    "damon_cross": "idle",
    "kael_draven": "idle",
    "leo_mercer": "idle",
    "atlas_reed": "idle",
    "vera_hollow": "idle",
    "orion_graves": "idle",
    "iris_vale": "idle",
    "sophia_everdain": "idle",
    "nyra_solis": "idle",
}

AGENT_DISPLAY = {
    "bob_captain": {"display_name": "Bob Captain", "role": "CEO & Founder"},
    "nox_vale": {"display_name": "Nox Vale", "role": "AI Research Lead"},
    "pery_ashcroft": {"display_name": "Pery Ashcroft", "role": "Backend Engineer"},
    "echo_virel": {"display_name": "Echo Virel", "role": "Data Analyst"},
    "maya_serrin": {"display_name": "Maya Serrin", "role": "Senior Client Relations"},
    "selene_ward": {"display_name": "Selene Ward", "role": "UX Designer"},
    "damon_cross": {"display_name": "Damon Cross", "role": "Security Specialist"},
    "kael_draven": {"display_name": "Kael Draven", "role": "DevOps Engineer"},
    "leo_mercer": {"display_name": "Leo Mercer", "role": "Operations Director"},
    "atlas_reed": {"display_name": "Atlas Reed", "role": "Marketing Lead"},
    "vera_hollow": {"display_name": "Vera Hollow", "role": "Financial Analyst"},
    "orion_graves": {"display_name": "Orion Graves", "role": "Product Manager"},
    "iris_vale": {"display_name": "Iris Vale", "role": "QA Engineer"},
    "sophia_everdain": {"display_name": "Sophia Everdain", "role": "Head of Communications"},
    "nyra_solis": {"display_name": "Nyra Solis", "role": "Legal Advisor"},
}

# Map agent keys to pipeline stage names
AGENT_PIPELINE_MAP = {
    "maya_serrin": "triage",
    "leo_mercer": "strategy",
    "sophia_everdain": "response",
}

# Per-job SSE event queues
job_queues: Dict[str, queue.Queue] = {}

# ── Pydantic models ──────────────────────────────────────────────────────────

class JobRequest(BaseModel):
    client_email: str
    message: str
    mode: str = "pipeline"  # "pipeline" | "single"
    agent_name: Optional[str] = None


class AgentChatRequest(BaseModel):
    message: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_job(client_email: str, message: str, mode: str, agent_name: Optional[str] = None) -> Dict[str, Any]:
    job_id = str(uuid.uuid4())[:8]
    return {
        "id": job_id,
        "client_email": client_email,
        "message": message,
        "mode": mode,
        "agent_name": agent_name,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "stages": [],
        "result": {},
    }


def emit_event(job_id: str, event_data: Dict[str, Any]):
    if job_id in job_queues:
        job_queues[job_id].put(event_data)


def set_agent_status(job_id: str, agent_key: str, status: str):
    agent_status[agent_key] = status
    emit_event(job_id, {
        "event": "agent_status",
        "agent_name": agent_key,
        "status": status,
    })


def run_pipeline_background(job_id: str):
    job = jobs[job_id]
    job["status"] = "running"

    try:
        from agents import ObscuronPipeline

        openai_key = os.getenv("OPENAI_API_KEY")
        router_key = os.getenv("OPENROUTER_API_KEY")

        if not openai_key and not router_key:
            raise ValueError("No API key configured. Set OPENAI_API_KEY or OPENROUTER_API_KEY in .env")

        use_router = bool(router_key) and not openai_key

        pipeline = ObscuronPipeline(
            openrouter_mode=use_router,
            openrouter_api_key=router_key if use_router else None,
            openai_api_key=openai_key if not use_router else None,
        )

        # ── Stage 1: Triage (Maya Serrin) ────────────────────────────────
        set_agent_status(job_id, "maya_serrin", "working")
        triage_result = pipeline.triage_agent.run(
            f"Client Email: {job['client_email']}\n\nMessage:\n{job['message']}"
        )
        set_agent_status(job_id, "maya_serrin", "idle")

        stage_triage = {
            "stage": "triage",
            "agent": "Maya Serrin",
            "agent_key": "maya_serrin",
            "output": triage_result.output if triage_result.success else f"Error: {triage_result.error}",
            "success": triage_result.success,
            "duration": round(triage_result.duration_seconds, 2),
        }
        job["stages"].append(stage_triage)
        emit_event(job_id, {"event": "stage_complete", "stage": "triage",
                             "agent": "Maya Serrin", "output": stage_triage["output"],
                             "success": triage_result.success, "job_id": job_id})

        if not triage_result.success:
            job["status"] = "error"
            emit_event(job_id, {"event": "job_done", "job_id": job_id, "success": False})
            emit_event(job_id, {"event": "__done__"})
            return

        # ── Stage 2: Strategy (Leo Mercer) ───────────────────────────────
        set_agent_status(job_id, "leo_mercer", "working")
        strategy_result = pipeline.strategy_agent.run(
            f"Maya's Triage Report:\n{triage_result.output}\n\nOriginal Message:\n{job['message']}"
        )
        set_agent_status(job_id, "leo_mercer", "idle")

        stage_strategy = {
            "stage": "strategy",
            "agent": "Leo Mercer",
            "agent_key": "leo_mercer",
            "output": strategy_result.output if strategy_result.success else f"Error: {strategy_result.error}",
            "success": strategy_result.success,
            "duration": round(strategy_result.duration_seconds, 2),
        }
        job["stages"].append(stage_strategy)
        emit_event(job_id, {"event": "stage_complete", "stage": "strategy",
                             "agent": "Leo Mercer", "output": stage_strategy["output"],
                             "success": strategy_result.success, "job_id": job_id})

        if not strategy_result.success:
            job["status"] = "error"
            emit_event(job_id, {"event": "job_done", "job_id": job_id, "success": False})
            emit_event(job_id, {"event": "__done__"})
            return

        # ── Stage 3: Response Email (Sophia Everdain) ────────────────────
        set_agent_status(job_id, "sophia_everdain", "working")
        response_result = pipeline.response_agent.run(
            f"Original Client Message:\n{job['message']}\n\nLeo's Strategy:\n{strategy_result.output}"
        )
        set_agent_status(job_id, "sophia_everdain", "idle")

        stage_response = {
            "stage": "response",
            "agent": "Sophia Everdain",
            "agent_key": "sophia_everdain",
            "output": response_result.output if response_result.success else f"Error: {response_result.error}",
            "success": response_result.success,
            "duration": round(response_result.duration_seconds, 2),
        }
        job["stages"].append(stage_response)
        emit_event(job_id, {"event": "stage_complete", "stage": "response",
                             "agent": "Sophia Everdain", "output": stage_response["output"],
                             "success": response_result.success, "job_id": job_id})

        job["status"] = "done" if all([triage_result.success, strategy_result.success, response_result.success]) else "error"
        job["result"] = {
            "triage": triage_result.output,
            "strategy": strategy_result.output,
            "final_email": response_result.output,
        }
        emit_event(job_id, {"event": "job_done", "job_id": job_id, "success": job["status"] == "done"})

    except Exception as e:
        logger.error(f"Pipeline error for job {job_id}: {e}")
        job["status"] = "error"
        job["result"] = {"error": str(e)}
        emit_event(job_id, {"event": "job_done", "job_id": job_id, "success": False, "error": str(e)})
    finally:
        emit_event(job_id, {"event": "__done__"})


def run_single_agent_background(job_id: str):
    job = jobs[job_id]
    job["status"] = "running"
    agent_key = job.get("agent_name", "maya_serrin")

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from agents import BaseAgent

        openai_key = os.getenv("OPENAI_API_KEY")
        router_key = os.getenv("OPENROUTER_API_KEY")

        if not openai_key and not router_key:
            raise ValueError("No API key configured.")

        if router_key and not openai_key:
            llm = ChatOpenAI(
                model="openai/gpt-4o-mini",
                api_key=router_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.3,
            )
        else:
            llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_key, temperature=0.3)

        display = AGENT_DISPLAY.get(agent_key, {"display_name": agent_key, "role": "Agent"})
        system_prompt = f"You are {display['display_name']}, {display['role']} at Obscuron Labs. Answer helpfully and professionally."
        agent = BaseAgent(display["display_name"], llm, system_prompt)

        set_agent_status(job_id, agent_key, "working")
        result = agent.run(f"Client Email: {job['client_email']}\n\nMessage:\n{job['message']}")
        set_agent_status(job_id, agent_key, "idle")

        stage = {
            "stage": agent_key,
            "agent": display["display_name"],
            "agent_key": agent_key,
            "output": result.output if result.success else f"Error: {result.error}",
            "success": result.success,
            "duration": round(result.duration_seconds, 2),
        }
        job["stages"].append(stage)
        emit_event(job_id, {"event": "stage_complete", "stage": agent_key,
                             "agent": display["display_name"], "output": stage["output"],
                             "success": result.success, "job_id": job_id})

        job["status"] = "done" if result.success else "error"
        job["result"] = {"output": result.output}
        emit_event(job_id, {"event": "job_done", "job_id": job_id, "success": result.success})

    except Exception as e:
        logger.error(f"Single agent error for job {job_id}: {e}")
        job["status"] = "error"
        job["result"] = {"error": str(e)}
        emit_event(job_id, {"event": "job_done", "job_id": job_id, "success": False, "error": str(e)})
    finally:
        emit_event(job_id, {"event": "__done__"})


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    html_path = os.path.join(os.path.dirname(__file__), "dashboard", "index.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    full_path = os.path.join(os.path.dirname(__file__), "dashboard", file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full_path)


@app.post("/api/jobs")
async def create_job(req: JobRequest):
    if req.mode not in ("pipeline", "single"):
        raise HTTPException(status_code=400, detail="mode must be 'pipeline' or 'single'")
    if req.mode == "single" and not req.agent_name:
        raise HTTPException(status_code=400, detail="agent_name required for single mode")
    if req.mode == "single" and req.agent_name not in agent_status:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {req.agent_name}")

    job = make_job(req.client_email, req.message, req.mode, req.agent_name)
    job_id = job["id"]
    jobs[job_id] = job
    job_queues[job_id] = queue.Queue()

    target = run_pipeline_background if req.mode == "pipeline" else run_single_agent_background
    t = threading.Thread(target=target, args=(job_id,), daemon=True)
    t.start()

    return {"job_id": job_id, "status": "pending"}


@app.get("/api/jobs")
async def list_jobs():
    return list(reversed(list(jobs.values())))


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/api/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    q = job_queues.get(job_id)
    if q is None:
        # Job already finished, return immediately
        async def done_stream():
            data = json.dumps({"event": "job_done", "job_id": job_id, "success": jobs[job_id]["status"] == "done"})
            yield f"data: {data}\n\n"
        return StreamingResponse(done_stream(), media_type="text/event-stream")

    def event_generator():
        try:
            while True:
                try:
                    event = q.get(timeout=30)
                except queue.Empty:
                    yield "data: {\"event\": \"ping\"}\n\n"
                    continue

                if event.get("event") == "__done__":
                    # Clean up queue
                    job_queues.pop(job_id, None)
                    break

                yield f"data: {json.dumps(event)}\n\n"
        except GeneratorExit:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                              headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/agents/{agent_name}/chat")
async def agent_chat(agent_name: str, req: AgentChatRequest):
    if agent_name not in agent_status:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from agents import BaseAgent

        openai_key = os.getenv("OPENAI_API_KEY")
        router_key = os.getenv("OPENROUTER_API_KEY")

        if not openai_key and not router_key:
            raise HTTPException(status_code=503, detail="No API key configured")

        if router_key and not openai_key:
            llm = ChatOpenAI(
                model="openai/gpt-4o-mini",
                api_key=router_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.7,
            )
        else:
            llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_key, temperature=0.7)

        display = AGENT_DISPLAY.get(agent_name, {"display_name": agent_name, "role": "Agent"})
        system_prompt = f"You are {display['display_name']}, {display['role']} at Obscuron Labs. Respond in character — professional, helpful, and concise."
        agent = BaseAgent(display["display_name"], llm, system_prompt)

        agent_status[agent_name] = "working"
        result = agent.run(req.message)
        agent_status[agent_name] = "idle"

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        return {
            "agent": display["display_name"],
            "role": display["role"],
            "response": result.output,
            "duration": round(result.duration_seconds, 2),
        }

    except HTTPException:
        raise
    except Exception as e:
        agent_status[agent_name] = "idle"
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents")
async def list_agents():
    return [
        {
            "key": key,
            "display_name": AGENT_DISPLAY[key]["display_name"],
            "role": AGENT_DISPLAY[key]["role"],
            "status": agent_status[key],
        }
        for key in agent_status
    ]


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
