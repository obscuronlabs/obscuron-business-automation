"""
Obscuron Labs — Discord Webhook Reporter
Sends rich pipeline results to Discord channels.
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Optional

logger = logging.getLogger("DiscordReporter")

# Colour palette for embeds
COLORS = {
    "success": 0x00D26A,
    "warning": 0xFFB300,
    "error": 0xFF3B30,
    "info": 0x5865F2,
    "intel": 0x7C3AED,
}


def _post_embed(webhook_url: str, embed: dict) -> bool:
    """Post a single embed to a Discord webhook."""
    try:
        resp = requests.post(
            webhook_url,
            json={"embeds": [embed]},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Discord post failed: {e}")
        return False


def _truncate(text: str, max_chars: int = 1000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."


def report_pipeline_result(result, webhooks: dict) -> dict:
    """
    Send all pipeline stage results to their respective Discord channels.

    webhooks: dict mapping channel names to webhook URLs, e.g.:
        {
            "automation-reports": "https://discord.com/api/webhooks/...",
            "client-analysis": "https://discord.com/api/webhooks/...",
            "operations": "https://discord.com/api/webhooks/...",
            "workflow-alerts": "https://discord.com/api/webhooks/...",
            "market-research": "https://discord.com/api/webhooks/...",
            "sales-reports": "https://discord.com/api/webhooks/...",
            "ai-leads": "https://discord.com/api/webhooks/...",
        }
    """
    sent = {}
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    status_color = COLORS["success"] if result.success else COLORS["error"]

    # ── automation-reports: Executive Summary ─────────────────────────────────
    if url := webhooks.get("automation-reports"):
        nyra = result.orchestration_summary
        embed = {
            "title": "🧠 Obscuron Labs — Executive Summary",
            "description": _truncate(nyra.output if nyra else "No summary generated."),
            "color": status_color,
            "fields": [
                {
                    "name": "Client",
                    "value": result.client_email,
                    "inline": True,
                },
                {
                    "name": "Pipeline Duration",
                    "value": f"{result.total_duration:.1f}s",
                    "inline": True,
                },
                {
                    "name": "Status",
                    "value": "✅ Success" if result.success else "❌ Failed",
                    "inline": True,
                },
            ],
            "footer": {"text": f"Nyra Solis — Orchestration AI • {ts}"},
        }
        sent["automation-reports"] = _post_embed(url, embed)

    # ── client-analysis: Triage + Psychology ──────────────────────────────────
    if url := webhooks.get("client-analysis"):
        triage = result.triage
        psych = result.psychology_profile
        embed = {
            "title": "🎯 Client Analysis Report",
            "color": COLORS["intel"],
            "fields": [
                {
                    "name": "📋 Triage (Maya Serrin)",
                    "value": _truncate(triage.output if triage else "N/A", 500),
                    "inline": False,
                },
                {
                    "name": "🧩 Psychology Profile (Pery Ashcroft)",
                    "value": _truncate(psych.output if psych else "N/A", 500),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Client Analysis • {ts}"},
        }
        sent["client-analysis"] = _post_embed(url, embed)

    # ── operations: Strategy + Infrastructure ─────────────────────────────────
    if url := webhooks.get("operations"):
        strategy = result.strategy
        infra = result.infra_assessment
        embed = {
            "title": "⚙️ Operations & Delivery Report",
            "color": COLORS["info"],
            "fields": [
                {
                    "name": "🗺 Delivery Strategy (Leo Mercer)",
                    "value": _truncate(strategy.output if strategy else "N/A", 500),
                    "inline": False,
                },
                {
                    "name": "🖥 Infrastructure (Orion Graves)",
                    "value": _truncate(infra.output if infra else "N/A", 500),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Operations • {ts}"},
        }
        sent["operations"] = _post_embed(url, embed)

    # ── workflow-alerts: Threats + Security ───────────────────────────────────
    if url := webhooks.get("workflow-alerts"):
        threat = result.threat_analysis
        security = result.security_assessment
        embed = {
            "title": "🔴 Threat & Security Alerts",
            "color": COLORS["warning"],
            "fields": [
                {
                    "name": "⚠️ Threat Analysis (Nox Vale)",
                    "value": _truncate(threat.output if threat else "N/A", 500),
                    "inline": False,
                },
                {
                    "name": "🔒 Security Assessment (Kael Draven)",
                    "value": _truncate(security.output if security else "N/A", 500),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Security & Threats • {ts}"},
        }
        sent["workflow-alerts"] = _post_embed(url, embed)

    # ── market-research: Market Intel + Signal Intel ──────────────────────────
    if url := webhooks.get("market-research"):
        market = result.market_research
        signal = result.signal_intel
        embed = {
            "title": "📊 Market Intelligence Report",
            "color": COLORS["intel"],
            "fields": [
                {
                    "name": "📈 Market Intel (Selene Ward)",
                    "value": _truncate(market.output if market else "N/A", 500),
                    "inline": False,
                },
                {
                    "name": "📡 Signal Intel (Echo Virel)",
                    "value": _truncate(signal.output if signal else "N/A", 500),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Market Research • {ts}"},
        }
        sent["market-research"] = _post_embed(url, embed)

    # ── sales-reports: Revenue + Brand ────────────────────────────────────────
    if url := webhooks.get("sales-reports"):
        revenue = result.revenue_plan
        brand = result.brand_recommendations
        analytics = result.analytics_summary
        embed = {
            "title": "💰 Sales & Revenue Report",
            "color": COLORS["success"],
            "fields": [
                {
                    "name": "💵 Revenue Plan (Atlas Reed)",
                    "value": _truncate(revenue.output if revenue else "N/A", 400),
                    "inline": False,
                },
                {
                    "name": "🎨 Brand Notes (Vera Hollow)",
                    "value": _truncate(brand.output if brand else "N/A", 300),
                    "inline": False,
                },
                {
                    "name": "📉 Analytics (Iris Vale)",
                    "value": _truncate(analytics.output if analytics else "N/A", 300),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Sales & Revenue • {ts}"},
        }
        sent["sales-reports"] = _post_embed(url, embed)

    # ── ai-leads: Lead Qualification + Final Email ────────────────────────────
    if url := webhooks.get("ai-leads"):
        lead_qual = result.lead_qualification
        email = result.final_email
        embed = {
            "title": "🎣 Lead Intelligence & Response",
            "color": COLORS["success"],
            "fields": [
                {
                    "name": "🏆 Lead Qualification (Damon Cross)",
                    "value": _truncate(lead_qual.output if lead_qual else "N/A", 400),
                    "inline": False,
                },
                {
                    "name": "✉️ Client Email (Sophia Everdain)",
                    "value": _truncate(email.output if email else "N/A", 600),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Lead Gen • {ts}"},
        }
        sent["ai-leads"] = _post_embed(url, embed)

    success_count = sum(1 for v in sent.values() if v)
    logger.info(f"Discord: {success_count}/{len(sent)} channels notified")
    return sent


def get_webhooks_from_env() -> dict:
    """Load webhook URLs from environment variables."""
    return {
        k: v for k, v in {
            "automation-reports": os.getenv("DISCORD_WEBHOOK_REPORTS"),
            "client-analysis": os.getenv("DISCORD_WEBHOOK_CLIENT_ANALYSIS"),
            "operations": os.getenv("DISCORD_WEBHOOK_OPERATIONS"),
            "workflow-alerts": os.getenv("DISCORD_WEBHOOK_ALERTS"),
            "market-research": os.getenv("DISCORD_WEBHOOK_MARKET"),
            "sales-reports": os.getenv("DISCORD_WEBHOOK_SALES"),
            "ai-leads": os.getenv("DISCORD_WEBHOOK_LEADS"),
        }.items()
        if v
    }
