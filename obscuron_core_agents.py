import os
import time
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# API Anahtarı Doğrulaması
os.environ["OPENAI_API_KEY"] = "SİZİN_OPENAI_API_KEYİNİZ"

class ObscuronNeuralMatrix:
    def __init__(self):
        # Akıl yürütme kalitesi yüksek model (Strateji ve QA için)
        self.premium_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        # Hızlı ve operasyonel model
        self.fast_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        print("[Obscuron Labs] Neural Matrix Core Online.")

    def process_incoming_mission(self, client_email, payload_text):
        print(f"\n[SYSTEM] Inbound Transmission Detected from: {client_email}")
        print("-" * 60)
        time.sleep(1)

        # ------------------------------------------------------------------
        # PHASE 1: MAYA SERRIN (Client Relations AI)
        # ------------------------------------------------------------------
        print("[Maya Serrin] Triage initiating. Parsing semantic payload...")
        maya_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are Maya Serrin, Client Relations AI at Obscuron Labs. Your unyielding focus is triage. "
                "Extract the following from the client's email: 1. Core Intent, 2. Budget Signals, 3. Technical Requirements. "
                "Maintain an ultra-professional, secure, and corporate linguistic tone."
            )),
            ("human", "Inbound Payload from {client}:\n\n{payload}")
        ])
        maya_chain = maya_prompt | self.fast_llm
        maya_analysis = maya_chain.invoke({"client": client_email, "payload": payload_text}).content
        print("[Maya Serrin] Triage locked. Forwarding vectors to Operations.")
        print(f"\n>> Maya's Logs:\n{maya_analysis}\n")
        print("-" * 60)
        time.sleep(1)

        # ------------------------------------------------------------------
        # PHASE 2: LEO MERCER (Operations Director)
        # ------------------------------------------------------------------
        print("[Leo Mercer] Ingesting triage report. Mapping resource allocation...")
        leo_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are Leo Mercer, the Operations Director at Obscuron Labs. You don't write client emails; "
                "you manage the deployment matrix. Based on Maya's triage report, decide which technical assets "
                "need to deploy (e.g., Cain Holloway for Backend, Orion Blackthorne for n8n infrastructure, Vanta Crowe for Scraping). "
                "Draft an internal technical strategy detailing exactly how Obscuron Labs will build this solution."
            )),
            ("human", "Maya's Triage Vector Report:\n\n{triage_report}")
        ])
        leo_chain = leo_prompt | self.premium_llm
        leo_strategy = leo_chain.invoke({"triage_report": maya_analysis}).content
        print("[Leo Mercer] Strategy locked. Technical routing finalized.")
        print(f"\n>> Leo's Tactical Directive:\n{leo_strategy}\n")
        print("-" * 60)
        time.sleep(1)

        # ------------------------------------------------------------------
        # PHASE 3: SOPHIA EVERDAIN (QA & Linguistic Control)
        # ------------------------------------------------------------------
        print("[Sophia Everdain] Reviewing operational directive. Constructing outbound payload...")
        sophia_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are Sophia Everdain, Chief of QA & Linguistic Control at Obscuron Labs. "
                "Your word is absolute law before any external deployment. Take Leo's internal strategy and "
                "write a flawless, boardroom-ready, elite B2B response email to the client. "
                "The email must sound like it was crafted by a high-tier 15-person research institution. "
                "Sign it as 'The Systems Engineering Matrix, Obscuron Labs'."
            )),
            ("human", "Original Client Email: {raw_email}\n\nLeo's Tactical Blueprint:\n{strategy}")
        ])
        sophia_chain = sophia_prompt | self.premium_llm
        final_outbound_email = sophia_chain.invoke({"raw_email": payload_text, "strategy": leo_strategy}).content
        print("[Sophia Everdain] Semantic verification complete. Output cleared for deployment.")
        print(f"\n>> Final Outbound Transmission:\n{final_outbound_email}\n")
        print("-" * 60)

        return final_outbound_email

# ---- LOCAL TESTING MATRIX ----
if __name__ == "__main__":
    matrix = ObscuronNeuralMatrix()
    
    # Gerçek bir müşteriden gelmiş gibi simüle ettiğimiz mail payload'u
    TEST_EMAIL = "operations@apexlogistics.de"
    TEST_PAYLOAD = (
        "Hello Obscuron Labs, We need an elite data infrastructure. We want to automatically scrape "
        "our competitors' supply chain pricing across 40 European vectors weekly, and feed it directly into "
        "our custom ERP via webhooks. We run on local hardware. What is your architectural capacity for this?"
    )
    
    # Ajan matrisini ateşle
    final_response = matrix.process_incoming_mission(TEST_EMAIL, TEST_PAYLOAD)
