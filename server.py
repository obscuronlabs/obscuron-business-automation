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
    "bob_captain":    {"display_name": "Bob Captain",    "role": "Founder · Strategic Coordination"},
    "nox_vale":       {"display_name": "Nox Vale",       "role": "Threat Analysis AI"},
    "pery_ashcroft":  {"display_name": "Pery Ashcroft",  "role": "Psychology · Human Pattern AI"},
    "echo_virel":     {"display_name": "Echo Virel",     "role": "Signal Intel · Surveillance AI"},
    "maya_serrin":    {"display_name": "Maya Serrin",    "role": "CRM · Client Relations AI"},
    "selene_ward":    {"display_name": "Selene Ward",    "role": "Market Intel · Trend AI"},
    "damon_cross":    {"display_name": "Damon Cross",    "role": "Lead Gen · Acquisition AI"},
    "kael_draven":    {"display_name": "Kael Draven",    "role": "Security · Cybersecurity AI"},
    "leo_mercer":     {"display_name": "Leo Mercer",     "role": "Operations · Workflow AI"},
    "atlas_reed":     {"display_name": "Atlas Reed",     "role": "Revenue · Sales AI"},
    "vera_hollow":    {"display_name": "Vera Hollow",    "role": "Brand · Content AI"},
    "orion_graves":   {"display_name": "Orion Graves",   "role": "Infrastructure · DevOps AI"},
    "iris_vale":      {"display_name": "Iris Vale",      "role": "Analytics · Reporting AI"},
    "sophia_everdain":{"display_name": "Sophia Everdain","role": "QA · Client Communications AI"},
    "nyra_solis":     {"display_name": "Nyra Solis",     "role": "Orchestration · Coordinator AI"},
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


class WebhookOrderRequest(BaseModel):
    name: str = ""
    email: str
    subject: str = ""
    message: str
    service: str = ""        # e.g. "Music Production", "Mixing", "Consultation"
    budget: str = ""
    source: str = "website"  # where the order came from


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


def _emit_stage(job_id: str, agent_key: str, stage_name: str, result):
    """Helper: set status working→result→idle and emit SSE event."""
    display = AGENT_DISPLAY[agent_key]["display_name"]
    output = result.output if result.success else f"[ERROR] {result.error}"
    stage = {
        "stage": stage_name,
        "agent": display,
        "agent_key": agent_key,
        "output": output,
        "success": result.success,
        "duration": round(result.duration_seconds, 2),
    }
    jobs[job_id]["stages"].append(stage)
    emit_event(job_id, {
        "event": "stage_complete",
        "stage": stage_name,
        "agent": display,
        "agent_key": agent_key,
        "output": output,
        "success": result.success,
        "job_id": job_id,
    })
    return result.success


def run_pipeline_background(job_id: str):
    job = jobs[job_id]
    job["status"] = "running"

    try:
        from agents import ObscuronPipeline

        openai_key = os.getenv("OPENAI_API_KEY")
        router_key = os.getenv("OPENROUTER_API_KEY")
        if not openai_key and not router_key:
            raise ValueError("No API key found. Set OPENAI_API_KEY or OPENROUTER_API_KEY in .env")

        use_router = bool(router_key) and not bool(openai_key)
        pipeline = ObscuronPipeline(
            openrouter_mode=use_router,
            openrouter_api_key=router_key if use_router else None,
            openai_api_key=openai_key if not use_router else None,
            enable_web_research=True,
        )

        ctx = f"Client Email: {job['client_email']}\n\nClient Message:\n{job['message']}"

        # ── Stage 1: Intel Gathering ──────────────────────────────────────
        for key in ["bob_captain", "nox_vale", "pery_ashcroft", "echo_virel"]:
            set_agent_status(job_id, key, "working")

        r_bob   = pipeline.bob_captain.run(ctx)
        set_agent_status(job_id, "bob_captain", "idle")
        _emit_stage(job_id, "bob_captain", "strategic_brief", r_bob)

        r_nox   = pipeline.nox_vale.run(ctx)
        set_agent_status(job_id, "nox_vale", "idle")
        _emit_stage(job_id, "nox_vale", "threat_analysis", r_nox)

        r_pery  = pipeline.pery_ashcroft.run(ctx)
        set_agent_status(job_id, "pery_ashcroft", "idle")
        _emit_stage(job_id, "pery_ashcroft", "psychology_profile", r_pery)

        r_echo  = pipeline.echo_virel.run(ctx)
        set_agent_status(job_id, "echo_virel", "idle")
        _emit_stage(job_id, "echo_virel", "signal_intel", r_echo)

        stage1_ctx = (
            f"{ctx}\n\n"
            f"=== STRATEGIC BRIEF ===\n{r_bob.output}\n\n"
            f"=== THREAT ANALYSIS ===\n{r_nox.output}\n\n"
            f"=== PSYCHOLOGY PROFILE ===\n{r_pery.output}\n\n"
            f"=== SIGNAL INTEL ===\n{r_echo.output}"
        )

        # ── Stage 2: Analysis ─────────────────────────────────────────────
        for key in ["maya_serrin", "selene_ward", "damon_cross", "kael_draven"]:
            set_agent_status(job_id, key, "working")

        r_maya  = pipeline.maya_serrin.run(stage1_ctx)
        set_agent_status(job_id, "maya_serrin", "idle")
        _emit_stage(job_id, "maya_serrin", "triage", r_maya)

        r_sel   = pipeline.selene_ward.run(stage1_ctx)
        set_agent_status(job_id, "selene_ward", "idle")
        _emit_stage(job_id, "selene_ward", "market_research", r_sel)

        r_damon = pipeline.damon_cross.run(stage1_ctx)
        set_agent_status(job_id, "damon_cross", "idle")
        _emit_stage(job_id, "damon_cross", "lead_qualification", r_damon)

        r_kael  = pipeline.kael_draven.run(stage1_ctx)
        set_agent_status(job_id, "kael_draven", "idle")
        _emit_stage(job_id, "kael_draven", "security_assessment", r_kael)

        stage2_ctx = (
            f"{stage1_ctx}\n\n"
            f"=== TRIAGE ===\n{r_maya.output}\n\n"
            f"=== MARKET RESEARCH ===\n{r_sel.output}\n\n"
            f"=== LEAD QUALIFICATION ===\n{r_damon.output}\n\n"
            f"=== SECURITY ASSESSMENT ===\n{r_kael.output}"
        )

        # ── Stage 3: Planning ─────────────────────────────────────────────
        for key in ["leo_mercer", "atlas_reed", "vera_hollow", "orion_graves"]:
            set_agent_status(job_id, key, "working")

        r_leo   = pipeline.leo_mercer.run(stage2_ctx)
        set_agent_status(job_id, "leo_mercer", "idle")
        _emit_stage(job_id, "leo_mercer", "strategy", r_leo)

        r_atlas = pipeline.atlas_reed.run(stage2_ctx)
        set_agent_status(job_id, "atlas_reed", "idle")
        _emit_stage(job_id, "atlas_reed", "revenue_plan", r_atlas)

        r_vera  = pipeline.vera_hollow.run(stage2_ctx)
        set_agent_status(job_id, "vera_hollow", "idle")
        _emit_stage(job_id, "vera_hollow", "brand_recommendations", r_vera)

        r_orion = pipeline.orion_graves.run(stage2_ctx)
        set_agent_status(job_id, "orion_graves", "idle")
        _emit_stage(job_id, "orion_graves", "infra_assessment", r_orion)

        stage3_ctx = (
            f"{stage2_ctx}\n\n"
            f"=== STRATEGY ===\n{r_leo.output}\n\n"
            f"=== REVENUE PLAN ===\n{r_atlas.output}\n\n"
            f"=== BRAND ===\n{r_vera.output}\n\n"
            f"=== INFRASTRUCTURE ===\n{r_orion.output}"
        )

        # ── Stage 4: Delivery ─────────────────────────────────────────────
        for key in ["iris_vale", "sophia_everdain", "nyra_solis"]:
            set_agent_status(job_id, key, "working")

        r_iris  = pipeline.iris_vale.run(stage3_ctx)
        set_agent_status(job_id, "iris_vale", "idle")
        _emit_stage(job_id, "iris_vale", "analytics_summary", r_iris)

        r_sophia = pipeline.sophia_everdain.run(
            f"Original Client Message:\n{job['message']}\n\n"
            f"Leo's Strategy:\n{r_leo.output}\n\n"
            f"Pery's Psychology:\n{r_pery.output}\n\n"
            f"Vera's Brand Notes:\n{r_vera.output}"
        )
        set_agent_status(job_id, "sophia_everdain", "idle")
        _emit_stage(job_id, "sophia_everdain", "final_email", r_sophia)

        r_nyra  = pipeline.nyra_solis.run(stage3_ctx)
        set_agent_status(job_id, "nyra_solis", "idle")
        _emit_stage(job_id, "nyra_solis", "orchestration_summary", r_nyra)

        job["status"] = "done"
        job["result"] = {
            "final_email": r_sophia.output,
            "orchestration_summary": r_nyra.output,
        }
        emit_event(job_id, {"event": "job_done", "job_id": job_id, "success": True})

        # ── Discord notifications ─────────────────────────────────────────
        try:
            from discord_reporter import get_webhooks_from_env
            webhooks = get_webhooks_from_env()
            if webhooks:
                import requests as req_lib
                ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                for channel, url in webhooks.items():
                    if "reports" in channel or "automation" in channel:
                        summary = r_nyra.output[:1800] if len(r_nyra.output) > 1800 else r_nyra.output
                        payload = {"embeds": [{
                            "title": "🤖 New Order Processed — Obscuron Labs",
                            "description": summary,
                            "color": 0x00D26A,
                            "fields": [
                                {"name": "Client", "value": job.get("client_email", "N/A"), "inline": True},
                                {"name": "Job ID", "value": job_id, "inline": True},
                                {"name": "Source", "value": job.get("source", "dashboard"), "inline": True},
                            ],
                            "footer": {"text": f"Obscuron Automation • {ts}"},
                        }]}
                        req_lib.post(url, json=payload, timeout=8)
                        break
        except Exception as disc_err:
            logger.warning(f"Discord notification failed: {disc_err}")

    except Exception as e:
        logger.error(f"Pipeline error for job {job_id}: {e}")
        job["status"] = "error"
        job["result"] = {"error": str(e)}
        # Reset all agents to idle
        for key in agent_status:
            agent_status[key] = "idle"
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
                model="perplexity/sonar-pro-search",
                api_key=router_key,
                base_url="https://openrouter.ai/api/v1",
                temperature=0.3,
            )
        else:
            llm = ChatOpenAI(model="gpt-4o", api_key=openai_key, temperature=0.3)

        # Import the actual agent class with its real system prompt
        import agents as agent_module
        agent_class_map = {
            "bob_captain": "BobCaptainAgent", "nox_vale": "NoxValeAgent",
            "pery_ashcroft": "PeryAshcroftAgent", "echo_virel": "EchoVirelAgent",
            "maya_serrin": "MayaSerrinAgent", "selene_ward": "SeleneWardAgent",
            "damon_cross": "DamonCrossAgent", "kael_draven": "KaelDravenAgent",
            "leo_mercer": "LeoMercerAgent", "atlas_reed": "AtlasReedAgent",
            "vera_hollow": "VeraHollowAgent", "orion_graves": "OrionGravesAgent",
            "iris_vale": "IrisValeAgent", "sophia_everdain": "SophiaEverdainAgent",
            "nyra_solis": "NyraSolisAgent",
        }
        cls_name = agent_class_map.get(agent_key)
        if cls_name and hasattr(agent_module, cls_name):
            agent = getattr(agent_module, cls_name)(llm)
        else:
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

        import agents as agent_module
        agent_class_map = {
            "bob_captain": "BobCaptainAgent", "nox_vale": "NoxValeAgent",
            "pery_ashcroft": "PeryAshcroftAgent", "echo_virel": "EchoVirelAgent",
            "maya_serrin": "MayaSerrinAgent", "selene_ward": "SeleneWardAgent",
            "damon_cross": "DamonCrossAgent", "kael_draven": "KaelDravenAgent",
            "leo_mercer": "LeoMercerAgent", "atlas_reed": "AtlasReedAgent",
            "vera_hollow": "VeraHollowAgent", "orion_graves": "OrionGravesAgent",
            "iris_vale": "IrisValeAgent", "sophia_everdain": "SophiaEverdainAgent",
            "nyra_solis": "NyraSolisAgent",
        }
        display = AGENT_DISPLAY.get(agent_name, {"display_name": agent_name, "role": "Agent"})
        cls_name = agent_class_map.get(agent_name)
        if cls_name and hasattr(agent_module, cls_name):
            agent = getattr(agent_module, cls_name)(llm)
        else:
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


@app.post("/api/webhook/order")
async def webhook_order(req: WebhookOrderRequest, request: Request):
    """
    Receives an incoming order/contact from obscuronlabs.com and
    automatically triggers the full 15-agent pipeline.

    Connect your Webflow / Netlify form to POST here with JSON:
        { "name": "...", "email": "...", "message": "...", "service": "..." }
    """
    # Build a rich context message for the pipeline
    context_lines = []
    if req.name:
        context_lines.append(f"Client Name: {req.name}")
    context_lines.append(f"Client Email: {req.email}")
    if req.service:
        context_lines.append(f"Service Requested: {req.service}")
    if req.subject:
        context_lines.append(f"Subject: {req.subject}")
    if req.budget:
        context_lines.append(f"Budget: {req.budget}")
    context_lines.append(f"Source: {req.source}")
    context_lines.append("")
    context_lines.append("Message:")
    context_lines.append(req.message)

    full_message = "\n".join(context_lines)

    job = make_job(req.email, full_message, "pipeline")
    job["source"] = req.source
    job["client_name"] = req.name
    job_id = job["id"]
    jobs[job_id] = job
    job_queues[job_id] = queue.Queue()

    t = threading.Thread(target=run_pipeline_background, args=(job_id,), daemon=True)
    t.start()

    logger.info(f"Auto-triggered pipeline for website order from {req.email} — job {job_id}")

    # Alert Discord immediately when order arrives
    try:
        from discord_reporter import get_webhooks_from_env
        import requests as req_lib
        webhooks = get_webhooks_from_env()
        for channel, url in webhooks.items():
            if "alerts" in channel or "reports" in channel or "leads" in channel:
                ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
                payload = {"embeds": [{
                    "title": "📥 New Order Received!",
                    "description": f"**{req.name or req.email}** submitted a new order from **{req.source}**\n\n> {req.message[:500]}",
                    "color": 0x5865F2,
                    "fields": [
                        {"name": "Email", "value": req.email, "inline": True},
                        {"name": "Service", "value": req.service or "Not specified", "inline": True},
                        {"name": "Job ID", "value": job_id, "inline": True},
                    ],
                    "footer": {"text": f"Agents activated — processing now • {ts}"},
                }]}
                req_lib.post(url, json=payload, timeout=8)
                break
    except Exception as e:
        logger.warning(f"Discord order alert failed: {e}")

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Order received. 15 agents activated. Results will be sent to Discord.",
    }


@app.get("/api/status")
async def system_status():
    """Quick health check — shows active jobs, agent states, env config."""
    active = sum(1 for j in jobs.values() if j["status"] == "running")
    done = sum(1 for j in jobs.values() if j["status"] == "done")
    errors = sum(1 for j in jobs.values() if j["status"] == "error")
    return {
        "status": "ok",
        "jobs": {"active": active, "done": done, "errors": errors, "total": len(jobs)},
        "agents": {k: v for k, v in agent_status.items()},
        "config": {
            "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "discord_configured": bool(os.getenv("DISCORD_WEBHOOK_REPORTS")),
            "n8n_configured": bool(os.getenv("N8N_WEBHOOK_URL")),
        },
    }


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
