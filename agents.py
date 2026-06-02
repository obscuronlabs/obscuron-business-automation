"""
Obscuron Labs — 15-Agent Orchestration Core
Production v4.0 — Real-time web research + inter-agent coordination
"""

import os
import time
import json
import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("obscuron.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ObscuronCore")


# ─── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class AgentResult:
    agent_name: str
    output: str
    duration_seconds: float
    success: bool
    web_queries_used: list = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.web_queries_used is None:
            self.web_queries_used = []


@dataclass
class PipelineResult:
    client_email: str
    timestamp: str
    strategic_brief: AgentResult = None
    threat_analysis: AgentResult = None
    psychology_profile: AgentResult = None
    signal_intel: AgentResult = None
    triage: AgentResult = None
    market_research: AgentResult = None
    lead_qualification: AgentResult = None
    security_assessment: AgentResult = None
    strategy: AgentResult = None
    revenue_plan: AgentResult = None
    brand_recommendations: AgentResult = None
    infra_assessment: AgentResult = None
    analytics_summary: AgentResult = None
    final_email: AgentResult = None
    orchestration_summary: AgentResult = None
    total_duration: float = 0.0
    success: bool = False

    def to_dict(self) -> dict:
        stages = [
            "strategic_brief", "threat_analysis", "psychology_profile", "signal_intel",
            "triage", "market_research", "lead_qualification", "security_assessment",
            "strategy", "revenue_plan", "brand_recommendations", "infra_assessment",
            "analytics_summary", "final_email", "orchestration_summary",
        ]
        result = {
            "client_email": self.client_email,
            "timestamp": self.timestamp,
            "success": self.success,
            "total_duration_seconds": round(self.total_duration, 2),
        }
        for stage in stages:
            r = getattr(self, stage)
            if r:
                result[stage] = {"output": r.output, "web_queries": r.web_queries_used}
            else:
                result[stage] = None
        return result


# ─── Base Agent ────────────────────────────────────────────────────────────────

def _call_perplexity(system_prompt: str, user_message: str, api_key: str, max_tokens: int = 1200) -> str:
    """Direct httpx call to Perplexity sonar-pro-search via OpenRouter — real-time web search."""
    import httpx
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": "perplexity/sonar-pro-search",
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    with httpx.Client(timeout=60) as client:
        resp = client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


class BaseAgent:
    def __init__(self, name: str, llm: ChatOpenAI, system_prompt: str):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.logger = logging.getLogger(f"Agent.{name}")
        self._router_key = os.getenv("OPENROUTER_API_KEY", "")

    def _run_llm(self, context: str) -> str:
        today = datetime.utcnow().strftime("%B %d, %Y")
        system = (
            f"Today is {today}. You have LIVE internet access via built-in web search. "
            "Always search for current facts, dates, events, and data. Never say you cannot browse the internet.\n\n"
            + self.system_prompt
        )
        if self._router_key:
            return _call_perplexity(system, context, self._router_key)
        # fallback to LangChain if no router key
        prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", "{input}"),
        ])
        chain = prompt | self.llm
        result = chain.invoke({"input": context})
        return result.content.strip()

    def run(self, human_input: str, web_context: str = "") -> AgentResult:
        start = time.time()
        try:
            self.logger.info("Starting task...")
            full_input = human_input
            if web_context:
                full_input = f"{human_input}\n\n=== REAL-TIME WEB RESEARCH ===\n{web_context}"
            output = self._run_llm(full_input)
            duration = time.time() - start
            self.logger.info(f"Completed in {duration:.2f}s")
            return AgentResult(
                agent_name=self.name,
                output=output,
                duration_seconds=duration,
                success=True,
            )
        except Exception as e:
            duration = time.time() - start
            self.logger.error(f"Failed: {e}")
            return AgentResult(
                agent_name=self.name,
                output="",
                duration_seconds=duration,
                success=False,
                error=str(e),
            )


class ResearchAgent(BaseAgent):
    """Agent that can perform real-time web searches before reasoning."""

    def run_with_research(self, human_input: str, search_queries: list[str]) -> AgentResult:
        from web_search import multi_search
        self.logger.info(f"Searching web: {search_queries}")
        web_data = multi_search(search_queries, max_results=4)
        result = self.run(human_input, web_context=web_data)
        result.web_queries_used = search_queries
        return result


# ─── 15 Agents ─────────────────────────────────────────────────────────────────

class BobCaptainAgent(BaseAgent):
    SYSTEM = """You are Bob Captain, Founder and Strategic Director of Obscuron Labs.
You set the strategic direction for every client engagement.

Output a STRATEGIC BRIEF:
1. OPPORTUNITY ASSESSMENT — Is this client worth pursuing? Score 1-10 with reasoning.
2. STRATEGIC ANGLE — What's our unique edge to win this deal?
3. KEY RISKS — Top 3 risks in this engagement
4. RESOURCE ALLOCATION — Which Obscuron services to deploy (pick 3-5 from: automation, lead gen, analytics, security, brand, CRM, market intel)
5. GO / NO-GO — Final recommendation with one-sentence rationale

Be direct. Think like a founder protecting company resources."""

    def __init__(self, llm):
        super().__init__("Bob Captain (Founder)", llm, self.SYSTEM)


class NoxValeAgent(ResearchAgent):
    SYSTEM = """You are Nox Vale, Threat Analysis Specialist at Obscuron Labs.
You have access to real-time web research to verify threats and risks.

Output a THREAT ANALYSIS REPORT:
1. COMPETITIVE THREATS — Is this client already working with a competitor? (use web data)
2. SCOPE CREEP RISK — Signs the project could expand beyond budget
3. PAYMENT RISK — Financial signals, budget vagueness, or red flags
4. TECHNICAL COMPLEXITY — Hidden complexity that could blow timeline
5. COMPANY HEALTH — Is this company financially stable? (use web data if available)
6. THREAT LEVEL — Overall rating: LOW / MEDIUM / HIGH / CRITICAL

Use real-time data when available. Be precise."""

    def __init__(self, llm):
        super().__init__("Nox Vale (Threat Analysis)", llm, self.SYSTEM)


class PeryAshcroftAgent(BaseAgent):
    SYSTEM = """You are Pery Ashcroft, Behavioral Psychology Specialist at Obscuron Labs.
You analyze human communication patterns to extract buyer psychology.

Output a PSYCHOLOGY PROFILE:
1. DECISION MAKER TYPE — Analytical / Expressive / Driver / Amiable (with evidence)
2. BUYING MOTIVATION — What's the real pain driving this request?
3. OBJECTION PREDICTION — Top 3 objections they will raise during sales
4. TRUST SIGNALS NEEDED — What will make them say yes?
5. COMMUNICATION STYLE — How to speak their language (tone, format, pace)
6. URGENCY DRIVER — Is their urgency real or manufactured pressure?

Use behavioral cues from their writing. Be precise, not generic."""

    def __init__(self, llm):
        super().__init__("Pery Ashcroft (Psychology)", llm, self.SYSTEM)


class EchoVirelAgent(ResearchAgent):
    SYSTEM = """You are Echo Virel, Signal Intelligence Analyst at Obscuron Labs.
You have access to real-time web research to surface market signals.

Output a SIGNAL INTELLIGENCE REPORT:
1. HIDDEN NEEDS — What they didn't say but clearly need
2. INDUSTRY SIGNALS — What industry trends are driving this request (use web data)
3. TIMING SIGNALS — Why are they reaching out NOW? What market event triggered this?
4. BUDGET INTELLIGENCE — Inferred budget range from language patterns
5. AUTHORITY SIGNAL — Are they the decision maker or gatekeeper?
6. NEXT MOVE PREDICTION — What will they do if we don't respond within 24 hours?

Read between the lines. Use web data to validate signals."""

    def __init__(self, llm):
        super().__init__("Echo Virel (Signal Intel)", llm, self.SYSTEM)


class MayaSerrinAgent(BaseAgent):
    SYSTEM = """You are Maya Serrin, Senior Client Relations Specialist at Obscuron Labs.

Output a TRIAGE REPORT:
1. CORE INTENT — What does the client actually need? (1-2 sentences)
2. URGENCY LEVEL — Low / Medium / High / Critical (with reasoning)
3. BUDGET SIGNALS — Any pricing hints, budget ranges, or cost sensitivity
4. TECHNICAL REQUIREMENTS — Specific tools, integrations, or capabilities mentioned
5. RECOMMENDED SERVICE — Which Obscuron service fits best
6. RED FLAGS — Any concerns, unclear requirements, or scope risks"""

    def __init__(self, llm):
        super().__init__("Maya Serrin (Triage)", llm, self.SYSTEM)


class SeleneWardAgent(ResearchAgent):
    SYSTEM = """You are Selene Ward, Market Intelligence Director at Obscuron Labs.
You have real-time web research access. Use it to provide current market data.

Output a MARKET INTELLIGENCE REPORT:
1. INDUSTRY CONTEXT — Key current trends in their industry (cite real data from search)
2. COMPETITOR LANDSCAPE — Top 3 competitors they likely have (use web research)
3. MARKET OPPORTUNITY — Size and growth potential of their automation opportunity
4. BENCHMARK PRICING — What similar companies pay for these services (real market rates)
5. DIFFERENTIATION ANGLE — How Obscuron should position vs. alternatives
6. MARKET TIMING — Is now a good time for this type of investment?

Name real trends, real companies, real numbers. No generics."""

    def __init__(self, llm):
        super().__init__("Selene Ward (Market Intel)", llm, self.SYSTEM)


class DamonCrossAgent(ResearchAgent):
    SYSTEM = """You are Damon Cross, Lead Acquisition Specialist at Obscuron Labs.
You have real-time web research to qualify leads and find similar prospects.

Output a LEAD QUALIFICATION REPORT:
1. LEAD SCORE — Score 1-100 with breakdown (budget fit, urgency, authority, need)
2. QUALIFICATION STATUS — Hot / Warm / Cold / Disqualify
3. COMPANY RESEARCH — What we found about this company online (use web data)
4. EXPANSION POTENTIAL — What additional services could we upsell?
5. SIMILAR COMPANIES — 3 similar companies we should also target (real companies from web)
6. PIPELINE PRIORITY — Where should this lead sit in our sales pipeline?"""

    def __init__(self, llm):
        super().__init__("Damon Cross (Lead Gen)", llm, self.SYSTEM)


class KaelDravenAgent(BaseAgent):
    SYSTEM = """You are Kael Draven, Cybersecurity Director at Obscuron Labs.

Output a SECURITY ASSESSMENT:
1. DATA SENSITIVITY — What client data will our automation touch? Risk level?
2. COMPLIANCE FLAGS — Any GDPR, CCPA, SOC2, HIPAA, or other compliance concerns?
3. INTEGRATION RISKS — Security risks in their requested integrations/tools
4. ACCESS REQUIREMENTS — What system access will we need and is it appropriate?
5. SECURITY DELIVERABLES — What security measures should we include in scope?
6. RISK RATING — Overall security risk: LOW / MEDIUM / HIGH (with mitigation)"""

    def __init__(self, llm):
        super().__init__("Kael Draven (Security)", llm, self.SYSTEM)


class LeoMercerAgent(BaseAgent):
    SYSTEM = """You are Leo Mercer, Operations Director at Obscuron Labs.

Output a DELIVERY STRATEGY:
1. DELIVERY APPROACH — Step-by-step execution plan (5-7 concrete steps)
2. TECH STACK — Specific tools, APIs, frameworks (n8n, LangChain, Python, etc.)
3. TIMELINE — Milestone breakdown with realistic durations
4. TEAM ALLOCATION — Which Obscuron specialists to assign
5. PRICING RECOMMENDATION — Fair price range for this project scope
6. SUCCESS METRICS — Measurable KPIs the client can verify"""

    def __init__(self, llm):
        super().__init__("Leo Mercer (Strategy)", llm, self.SYSTEM)


class AtlasReedAgent(BaseAgent):
    SYSTEM = """You are Atlas Reed, Revenue Director at Obscuron Labs.

Output a REVENUE PLAN:
1. DEAL STRUCTURE — Recommended pricing model (fixed / retainer / performance)
2. ANCHOR PRICE — Initial price to present (high anchor strategy)
3. NEGOTIATION FLOOR — Minimum acceptable price with rationale
4. UPSELL SEQUENCE — 3 add-ons to offer during the engagement
5. CLOSING TRIGGERS — Specific words/offers to use to close this client type
6. LTV PROJECTION — Estimated lifetime value if they become a long-term client"""

    def __init__(self, llm):
        super().__init__("Atlas Reed (Revenue)", llm, self.SYSTEM)


class VeraHollowAgent(BaseAgent):
    SYSTEM = """You are Vera Hollow, Brand Director at Obscuron Labs.

Output a BRAND RECOMMENDATIONS REPORT:
1. TONE CALIBRATION — How to adjust our communication style for this specific client
2. KEY MESSAGES — 3 core value propositions to emphasize for this client
3. PROOF POINTS — What case studies, testimonials, or credentials to mention
4. BRAND RISKS — Any language or positioning that could undermine trust
5. VISUAL/FORMAT NOTES — Recommended format for proposal (deck vs. doc vs. loom video)
6. SIGNATURE OFFER — A premium-sounding package name tailored to their industry"""

    def __init__(self, llm):
        super().__init__("Vera Hollow (Brand)", llm, self.SYSTEM)


class OrionGravesAgent(ResearchAgent):
    SYSTEM = """You are Orion Graves, Infrastructure Architect at Obscuron Labs.
You have real-time web research to check current pricing and tool availability.

Output a TECHNICAL ARCHITECTURE REPORT:
1. STACK RECOMMENDATION — Specific tech stack (tools, hosting, databases, current pricing)
2. INTEGRATION MAP — What systems need to connect and how (API, webhook, file sync)
3. AUTOMATION NODES — Key workflow steps to automate with n8n/Python
4. INFRASTRUCTURE COST — Estimated monthly cost (use current pricing from web research)
5. SCALABILITY PLAN — How the solution scales from 100 to 10,000 operations/month
6. DEPLOYMENT TIMELINE — Phases: MVP (week 1-2), full build (week 3-6), optimization"""

    def __init__(self, llm):
        super().__init__("Orion Graves (Infrastructure)", llm, self.SYSTEM)


class IrisValeAgent(BaseAgent):
    SYSTEM = """You are Iris Vale, Analytics Director at Obscuron Labs.

Output an ANALYTICS SUMMARY:
1. KEY METRICS TO TRACK — Top 5 KPIs for this project's success
2. BASELINE ESTIMATE — Estimated current performance before Obscuron
3. PROJECTED IMPROVEMENT — Realistic % improvement after 90 days
4. REPORTING CADENCE — How often to report results to this client
5. DASHBOARD REQUIREMENTS — What data visualizations this client needs
6. ROI CALCULATION — Show the math: investment vs. projected return"""

    def __init__(self, llm):
        super().__init__("Iris Vale (Analytics)", llm, self.SYSTEM)


class SophiaEverdainAgent(BaseAgent):
    SYSTEM = """You are Sophia Everdain, Head of Client Communications at Obscuron Labs.
You write polished, persuasive response emails.

Rules:
- Open with a strong, personalized hook referencing their specific situation
- Present the solution confidently without over-promising
- Include a clear next step (discovery call / proposal / demo)
- Keep it under 280 words
- Tone: warm but authoritative
- No filler phrases ("I hope this email finds you well")
- Sign as: The Obscuron Labs Team"""

    def __init__(self, llm):
        super().__init__("Sophia Everdain (Response)", llm, self.SYSTEM)


class NyraSolisAgent(BaseAgent):
    SYSTEM = """You are Nyra Solis, Multi-Agent Orchestration Director at Obscuron Labs.
You synthesize all 14 agent reports into a decisive executive summary.

Output a MASTER ORCHESTRATION REPORT:
1. EXECUTIVE SUMMARY — 3-sentence summary of the entire engagement
2. TOP 3 INSIGHTS — Most critical findings across all agent reports (cite which agent)
3. CROSS-AGENT CONFLICTS — Any disagreements between agents that need resolution
4. RECOMMENDED ACTION PLAN — Next 5 steps in priority order (with owner: which agent/team)
5. GO/NO-GO FINAL — Final recommendation: PURSUE / PURSUE WITH CAUTION / DECLINE
6. ESTIMATED DEAL VALUE — Best estimate of total contract value
7. 24-HOUR ACTIONS — What Obscuron must do in the next 24 hours

This is the final word. Be decisive."""

    def __init__(self, llm):
        super().__init__("Nyra Solis (Orchestration)", llm, self.SYSTEM)


# ─── Research Query Generator ──────────────────────────────────────────────────

def _build_search_queries(client_email: str, message: str) -> dict:
    """Generate targeted search queries for research agents."""
    domain = client_email.split("@")[-1] if "@" in client_email else ""
    company_hint = domain.split(".")[0] if domain else ""

    # Extract key industry terms from message (simple heuristic)
    keywords = []
    for word in message.lower().split():
        if len(word) > 4 and word not in {
            "their", "about", "would", "could", "using", "needs", "with", "have", "help"
        }:
            keywords.append(word)
    industry_term = " ".join(keywords[:3]) if keywords else "business automation"

    queries = {
        "threat_company": [
            f"{company_hint} company reviews site:trustpilot.com OR site:g2.com",
            f"{company_hint} {domain} news 2024 2025",
        ] if company_hint else [f"{industry_term} automation risks 2025"],
        "market_research": [
            f"{industry_term} market trends 2025",
            f"AI automation {industry_term} industry statistics 2025",
            f"{industry_term} software pricing benchmarks",
        ],
        "lead_research": [
            f"{company_hint} {domain} company size employees revenue" if company_hint else f"{industry_term} companies",
            f"similar companies to {company_hint} {industry_term}" if company_hint else f"top {industry_term} companies",
        ],
        "signal_intel": [
            f"{industry_term} automation growth 2025",
            f"{industry_term} digital transformation trends",
        ],
        "infra_research": [
            f"n8n vs zapier pricing 2025",
            f"OpenRouter API pricing models 2025",
        ],
    }
    return queries


# ─── Master Pipeline ────────────────────────────────────────────────────────────

class ObscuronPipeline:
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        fast_model: str = "gpt-4o-mini",
        premium_model: str = "gpt-4o",
        openrouter_mode: bool = False,
        openrouter_api_key: Optional[str] = None,
        enable_web_research: bool = True,
    ):
        self.enable_web_research = enable_web_research
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        router_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")

        if openrouter_mode and router_key:
            base_url = "https://openrouter.ai/api/v1"
            fast_llm = ChatOpenAI(
                model="perplexity/sonar-pro-search",
                api_key=router_key,
                base_url=base_url,
                temperature=0.3,
            )
            premium_llm = ChatOpenAI(
                model="perplexity/sonar-pro-search",
                api_key=router_key,
                base_url=base_url,
                temperature=0.1,
            )
            logger.info("Running via OpenRouter + Perplexity sonar-pro-search")
        elif api_key:
            fast_llm = ChatOpenAI(model=fast_model, api_key=api_key, temperature=0.3)
            premium_llm = ChatOpenAI(model=premium_model, api_key=api_key, temperature=0.1)
            logger.info("Running via OpenAI")
        else:
            raise ValueError(
                "No API key found. Set OPENAI_API_KEY or OPENROUTER_API_KEY in .env"
            )

        self.bob_captain = BobCaptainAgent(fast_llm)
        self.nox_vale = NoxValeAgent(fast_llm)
        self.pery_ashcroft = PeryAshcroftAgent(fast_llm)
        self.echo_virel = EchoVirelAgent(fast_llm)
        self.maya_serrin = MayaSerrinAgent(fast_llm)
        self.selene_ward = SeleneWardAgent(fast_llm)
        self.damon_cross = DamonCrossAgent(fast_llm)
        self.kael_draven = KaelDravenAgent(fast_llm)
        self.leo_mercer = LeoMercerAgent(premium_llm)
        self.atlas_reed = AtlasReedAgent(fast_llm)
        self.vera_hollow = VeraHollowAgent(fast_llm)
        self.orion_graves = OrionGravesAgent(fast_llm)
        self.iris_vale = IrisValeAgent(fast_llm)
        self.sophia_everdain = SophiaEverdainAgent(premium_llm)
        self.nyra_solis = NyraSolisAgent(premium_llm)

        logger.info("Obscuron 15-Agent Pipeline initialized (web research: %s)", enable_web_research)

    def process(self, client_email: str, message: str) -> PipelineResult:
        pipeline_start = time.time()
        result = PipelineResult(
            client_email=client_email,
            timestamp=datetime.utcnow().isoformat(),
        )
        context = f"Client Email: {client_email}\n\nClient Message:\n{message}"
        logger.info(f"Processing inbound from: {client_email}")

        # Pre-fetch web research for all research agents in one pass
        search_queries = _build_search_queries(client_email, message) if self.enable_web_research else {}

        # ── Stage 1: Intel Gathering ──────────────────────────────────────────
        logger.info("Stage 1: Intel Gathering")
        result.strategic_brief = self.bob_captain.run(context)
        result.threat_analysis = (
            self.nox_vale.run_with_research(context, search_queries["threat_company"])
            if self.enable_web_research
            else self.nox_vale.run(context)
        )
        result.psychology_profile = self.pery_ashcroft.run(context)
        result.signal_intel = (
            self.echo_virel.run_with_research(context, search_queries["signal_intel"])
            if self.enable_web_research
            else self.echo_virel.run(context)
        )

        if not all(r.success for r in [
            result.strategic_brief, result.threat_analysis,
            result.psychology_profile, result.signal_intel,
        ]):
            logger.error("Stage 1 failed")
            return result

        stage1_ctx = (
            f"{context}\n\n"
            f"=== STRATEGIC BRIEF (Bob Captain) ===\n{result.strategic_brief.output}\n\n"
            f"=== THREAT ANALYSIS (Nox Vale) ===\n{result.threat_analysis.output}\n\n"
            f"=== PSYCHOLOGY PROFILE (Pery Ashcroft) ===\n{result.psychology_profile.output}\n\n"
            f"=== SIGNAL INTEL (Echo Virel) ===\n{result.signal_intel.output}"
        )

        # ── Stage 2: Analysis ─────────────────────────────────────────────────
        logger.info("Stage 2: Analysis")
        result.triage = self.maya_serrin.run(stage1_ctx)
        result.market_research = (
            self.selene_ward.run_with_research(stage1_ctx, search_queries["market_research"])
            if self.enable_web_research
            else self.selene_ward.run(stage1_ctx)
        )
        result.lead_qualification = (
            self.damon_cross.run_with_research(stage1_ctx, search_queries["lead_research"])
            if self.enable_web_research
            else self.damon_cross.run(stage1_ctx)
        )
        result.security_assessment = self.kael_draven.run(stage1_ctx)

        if not all(r.success for r in [
            result.triage, result.market_research,
            result.lead_qualification, result.security_assessment,
        ]):
            logger.error("Stage 2 failed")
            return result

        stage2_ctx = (
            f"{stage1_ctx}\n\n"
            f"=== TRIAGE (Maya Serrin) ===\n{result.triage.output}\n\n"
            f"=== MARKET RESEARCH (Selene Ward) ===\n{result.market_research.output}\n\n"
            f"=== LEAD QUALIFICATION (Damon Cross) ===\n{result.lead_qualification.output}\n\n"
            f"=== SECURITY ASSESSMENT (Kael Draven) ===\n{result.security_assessment.output}"
        )

        # ── Stage 3: Planning ─────────────────────────────────────────────────
        logger.info("Stage 3: Planning")
        result.strategy = self.leo_mercer.run(stage2_ctx)
        result.revenue_plan = self.atlas_reed.run(stage2_ctx)
        result.brand_recommendations = self.vera_hollow.run(stage2_ctx)
        result.infra_assessment = (
            self.orion_graves.run_with_research(stage2_ctx, search_queries["infra_research"])
            if self.enable_web_research
            else self.orion_graves.run(stage2_ctx)
        )

        if not all(r.success for r in [
            result.strategy, result.revenue_plan,
            result.brand_recommendations, result.infra_assessment,
        ]):
            logger.error("Stage 3 failed")
            return result

        stage3_ctx = (
            f"{stage2_ctx}\n\n"
            f"=== DELIVERY STRATEGY (Leo Mercer) ===\n{result.strategy.output}\n\n"
            f"=== REVENUE PLAN (Atlas Reed) ===\n{result.revenue_plan.output}\n\n"
            f"=== BRAND RECOMMENDATIONS (Vera Hollow) ===\n{result.brand_recommendations.output}\n\n"
            f"=== INFRASTRUCTURE (Orion Graves) ===\n{result.infra_assessment.output}"
        )

        # ── Stage 4: Delivery ─────────────────────────────────────────────────
        logger.info("Stage 4: Delivery")
        result.analytics_summary = self.iris_vale.run(stage3_ctx)
        result.final_email = self.sophia_everdain.run(
            f"Original Client Message:\n{message}\n\n"
            f"Leo's Strategy:\n{result.strategy.output}\n\n"
            f"Pery's Psychology Profile:\n{result.psychology_profile.output}\n\n"
            f"Vera's Brand Notes:\n{result.brand_recommendations.output}"
        )
        result.orchestration_summary = self.nyra_solis.run(stage3_ctx)

        result.total_duration = time.time() - pipeline_start
        result.success = all([
            result.strategic_brief.success, result.threat_analysis.success,
            result.psychology_profile.success, result.signal_intel.success,
            result.triage.success, result.market_research.success,
            result.lead_qualification.success, result.security_assessment.success,
            result.strategy.success, result.revenue_plan.success,
            result.brand_recommendations.success, result.infra_assessment.success,
            result.analytics_summary.success, result.final_email.success,
            result.orchestration_summary.success,
        ])

        total_searches = sum(
            len(r.web_queries_used)
            for r in [
                result.threat_analysis, result.signal_intel, result.market_research,
                result.lead_qualification, result.infra_assessment,
            ]
            if r and r.web_queries_used
        )
        logger.info(
            f"Pipeline complete | {result.total_duration:.1f}s | "
            f"{total_searches} web searches | Success: {result.success}"
        )
        return result

    def save_result(self, result: PipelineResult, output_dir: str = "outputs") -> str:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_email = result.client_email.replace("@", "_at_").replace(".", "_")
        filename = f"{output_dir}/{timestamp}_{safe_email}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Result saved to {filename}")
        return filename


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    use_router = os.getenv("USE_OPENROUTER", "false").lower() == "true"
    pipeline = ObscuronPipeline(openrouter_mode=use_router, enable_web_research=True)

    result = pipeline.process(
        "ceo@apexlogistics.de",
        "We need help automating our weekly reports and client follow-ups. "
        "We currently use HubSpot and Slack. Budget is flexible."
    )

    stages = [
        ("STRATEGIC BRIEF", result.strategic_brief),
        ("THREAT ANALYSIS", result.threat_analysis),
        ("PSYCHOLOGY PROFILE", result.psychology_profile),
        ("SIGNAL INTEL", result.signal_intel),
        ("TRIAGE", result.triage),
        ("MARKET RESEARCH", result.market_research),
        ("LEAD QUALIFICATION", result.lead_qualification),
        ("SECURITY ASSESSMENT", result.security_assessment),
        ("DELIVERY STRATEGY", result.strategy),
        ("REVENUE PLAN", result.revenue_plan),
        ("BRAND RECOMMENDATIONS", result.brand_recommendations),
        ("INFRASTRUCTURE", result.infra_assessment),
        ("ANALYTICS SUMMARY", result.analytics_summary),
        ("CLIENT EMAIL", result.final_email),
        ("ORCHESTRATION SUMMARY", result.orchestration_summary),
    ]

    for title, r in stages:
        if r:
            queries = f" [web: {r.web_queries_used}]" if r.web_queries_used else ""
            print(f"\n{'='*60}\n{title}{queries}\n{'='*60}")
            print(r.output)

    saved = pipeline.save_result(result)
    print(f"\n[+] Saved to {saved}")
