import os
import time
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

# API Key Check (Placeholder)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")

class ObscuronNeuralMatrix:
    def __init__(self):
        try:
            self.premium_llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
            self.fast_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        except Exception:
            # Fallback if no API key is set during initialization
            self.premium_llm = None
            self.fast_llm = None
        print("[Obscuron Labs] Neural Matrix Core Online.")

    def process_incoming_mission(self, client_email, payload_text):
        print(f"\n[SYSTEM] Inbound Transmission Detected from: {client_email}")
        print("-" * 60)
        
        if not self.premium_llm:
            print("[ERROR] OpenAI API Key missing. Please set the OPENAI_API_KEY environment variable.")
            return "Execution halted: API Key missing."

        # PHASE 1: MAYA SERRIN (Client Relations AI)
        print("[Maya Serrin] Triage initiating. Parsing semantic payload...")
        maya_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are Maya Serrin, Client Relations AI at Obscuron Labs. Your focus is triage. "
                "Extract: 1. Core Intent, 2. Budget Signals, 3. Technical Requirements. Tone: Corporate, elite."
            )),
            ("human", "Inbound Payload from {client}:\n\n{payload}")
        ])
        maya_chain = maya_prompt | self.fast_llm
        maya_analysis = maya_chain.invoke({"client": client_email, "payload": payload_text}).content
        print("[Maya Serrin] Triage locked. Forwarding vectors to Operations.")
        
        # PHASE 2: LEO MERCER (Operations Director)
        print("[Leo Mercer] Ingesting triage report. Mapping resource allocation...")
        leo_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are Leo Mercer, Operations Director at Obscuron Labs. Manage the deployment matrix. "
                "Decide technical assets (Cain, Orion, Vanta) and draft an internal technical strategy."
            )),
            ("human", "Maya's Triage Vector Report:\n\n{triage_report}")
        ])
        leo_chain = leo_prompt | self.premium_llm
        leo_strategy = leo_chain.invoke({"triage_report": maya_analysis}).content
        print("[Leo Mercer] Strategy locked. Technical routing finalized.")
        
        # PHASE 3: SOPHIA EVERDAIN (QA & Linguistic Control)
        print("[Sophia Everdain] Reviewing operational directive. Constructing outbound payload...")
        sophia_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are Sophia Everdain, Chief of QA at Obscuron Labs. Take Leo's strategy and "
                "write a flawless, boardroom-ready, elite B2B response email to the client. "
                "Sign as 'The Systems Engineering Matrix, Obscuron Labs'."
            )),
            ("human", "Original Client Email: {raw_email}\n\nLeo's Tactical Blueprint:\n{strategy}")
        ])
        sophia_chain = sophia_prompt | self.premium_llm
        final_outbound_email = sophia_chain.invoke({"raw_email": payload_text, "strategy": leo_strategy}).content
        print("[Sophia Everdain] Semantic verification complete. Output cleared.")
        
        return final_outbound_email

if __name__ == "__main__":
    matrix = ObscuronNeuralMatrix()
    TEST_EMAIL = "operations@apexlogistics.de"
    TEST_PAYLOAD = "Hello Obscuron Labs, We need an elite data infrastructure to scrape competitors supply chain pricing."
    # To run this successfully, ensure OPENAI_API_KEY is set in your environment
    # final_response = matrix.process_incoming_mission(TEST_EMAIL, TEST_PAYLOAD)
