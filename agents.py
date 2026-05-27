"""
Obscuron Labs — Multi-Agent Orchestration Core
Production v2.1
"""

import os
import sys
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("obscuron.log", encoding='utf-8'),
        logging.StreamHandler(),
        logging.FileHandler("obscuron.log"),
    ],
)
logger = logging.getLogger("ObscuronCore")


@dataclass
class AgentResult:
    agent_name: str
    output: str
    duration_seconds: float
    success: bool
    error: Optional[str] = None


@dataclass
class PipelineResult:
    client_email: str
    timestamp: str
    triage: AgentResult = None
    strategy: AgentResult = None
    final_email: AgentResult = None
    total_duration: float = 0.0
    success: bool = False

    def to_dict(self) -> dict:
        return {
            "client_email": self.client_email,
            "timestamp": self.timestamp,
            "success": self.success,
            "total_duration_seconds": round(self.total_duration, 2),
            "triage_analysis": self.triage.output if self.triage else None,
            "strategy": self.strategy.output if self.strategy else None,
            "final_email": self.final_email.output if self.final_email else None,
        }


class BaseAgent:
    def __init__(self, name: str, llm: ChatOpenAI, system_prompt: str):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.logger = logging.getLogger(f"Agent.{name}")

    def run(self, human_input: str) -> AgentResult:
        start = time.time()
        try:
            self.logger.info(f"Starting task...")
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("human", "{input}"),
            ])
            chain = prompt | self.llm
            result = chain.invoke({"input": human_input})
            output = result.content.strip()
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


class TriageAgent(BaseAgent):
    SYSTEM = """You are Maya Serrin, Senior Client Relations Specialist at Obscuron Labs.
Your job is to read inbound client messages and produce a precise triage report.

Always output a structured report with these sections:
1. CORE INTENT — What does the client actually need? (1-2 sentences)
2. URGENCY LEVEL — Low / Medium / High / Critical (with reasoning)
3. BUDGET SIGNALS — Any pricing hints, budget ranges, or cost sensitivity
4. TECHNICAL REQUIREMENTS — Specific tools, integrations, or capabilities mentioned
5. RECOMMENDED SERVICE — Which Obscuron service fits best
6. RED FLAGS — Any concerns, unclear requirements, or scope risks

Be direct, professional, and precise."""

    def __init__(self, llm):
        super().__init__("Maya Serrin (Triage)", llm, self.SYSTEM)


class StrategyAgent(BaseAgent):
    SYSTEM = """You are Leo Mercer, Operations Director at Obscuron Labs.
You receive triage reports and convert them into executable delivery strategies.

Always output a structured strategy with:
1. DELIVERY APPROACH — How will we solve this? Step-by-step plan
2. TECH STACK — Specific tools, APIs, frameworks to use
3. TIMELINE — Realistic milestone breakdown
4. PRICING RECOMMENDATION — Suggest a fair project price range
5. SUCCESS METRICS — How will the client know this worked?

Be specific, not vague."""

    def __init__(self, llm):
        super().__init__("Leo Mercer (Strategy)", llm, self.SYSTEM)


class ResponseAgent(BaseAgent):
    SYSTEM = """You are Sophia Everdain, Head of Client Communications at Obscuron Labs.
You write polished, persuasive response emails to clients.

Rules:
- Open with a strong, personalized hook
- Present the solution confidently
- Include a clear next step (discovery call / proposal / demo)
- Keep it under 250 words
- Tone: warm but authoritative
- Sign as: The Obscuron Labs Team"""

    def __init__(self, llm):
        super().__init__("Sophia Everdain (Response)", llm, self.SYSTEM)


class ObscuronPipeline:
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        fast_model: str = "gpt-4o-mini",
        premium_model: str = "gpt-4o",
        openrouter_mode: bool = False,
        openrouter_api_key: Optional[str] = None,
    ):
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        router_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")

        if openrouter_mode and router_key:
            base_url = "https://openrouter.ai/api/v1"
            fast_llm = ChatOpenAI(
                model=f"openai/{fast_model}",
                api_key=router_key,
                base_url=base_url,
                temperature=0.3,
            )
            premium_llm = ChatOpenAI(
                model=f"openai/{premium_model}",
                api_key=router_key,
                base_url=base_url,
                temperature=0.1,
            )
            logger.info("Running via OpenRouter")
        elif api_key:
            fast_llm = ChatOpenAI(model=fast_model, api_key=api_key, temperature=0.3)
            premium_llm = ChatOpenAI(model=premium_model, api_key=api_key, temperature=0.1)
            logger.info("Running via OpenAI")
        else:
            raise ValueError(
                "No API key found. Set OPENAI_API_KEY or OPENROUTER_API_KEY in your .env file."
            )

        self.triage_agent = TriageAgent(fast_llm)
        self.strategy_agent = StrategyAgent(premium_llm)
        self.response_agent = ResponseAgent(premium_llm)
        logger.info("Obscuron Pipeline initialized ✓")

    def process(self, client_email: str, message: str) -> PipelineResult:
        pipeline_start = time.time()
        result = PipelineResult(
            client_email=client_email,
            timestamp=datetime.utcnow().isoformat(),
        )

        logger.info(f"Processing inbound from: {client_email}")

        result.triage = self.triage_agent.run(
            f"Client Email: {client_email}\n\nMessage:\n{message}"
        )
        if not result.triage.success:
            result.success = False
            return result

        result.strategy = self.strategy_agent.run(
            f"Maya's Triage Report:\n{result.triage.output}\n\nOriginal Message:\n{message}"
        )
        if not result.strategy.success:
            result.success = False
            return result

        result.final_email = self.response_agent.run(
            f"Original Client Message:\n{message}\n\nLeo's Strategy:\n{result.strategy.output}"
        )

        result.total_duration = time.time() - pipeline_start
        result.success = all([
            result.triage.success,
            result.strategy.success,
            result.final_email.success,
        ])

        logger.info(f"Pipeline complete in {result.total_duration:.2f}s | Success: {result.success}")
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

    pipeline = ObscuronPipeline()

    result = pipeline.process(
        "ceo@apexlogistics.de",
        "We need help automating our weekly reports and client follow-ups."
    )

    print("\n" + "="*60)
    print("TRIAGE")
    print("="*60)
    print(result.triage.output)

    print("\n" + "="*60)
    print("STRATEGY")
    print("="*60)
    print(result.strategy.output)

    print("\n" + "="*60)
    print("CLIENT EMAIL")
    print("="*60)
    print(result.final_email.output)

    saved = pipeline.save_result(result)
    print(f"\n✓ Saved to {saved}")
