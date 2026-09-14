# ObscuronLabs™ — AI Automation Suite

> Multi-agent email pipeline · B2B lead scraper · n8n Discord automation

ObscuronLabs™ builds AI agents, automation systems, and digital intelligence infrastructure for businesses. This repository contains the open-source automation toolkit that powers our backend pipelines.

**Website:** [obscuronlabs.com](https://obscuronlabs.com)

---

## What's in this repository

| File | Description |
|---|---|
| `core/agents.py` | Three-agent AI pipeline (triage → strategy → response) |
| `core/scraper.py` | B2B lead scraper — extracts emails, phones, and company names from public websites |
| `main.py` | CLI entry point |
| `workflows/obscuron_automation.json` | n8n workflow — imports directly into your n8n instance |
| `requirements.txt` | Python dependencies, pinned versions |
| `.env.example` | Configuration template |

---

## Quick Start

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Add your API keys to .env
```

**Required (choose one):**
- `OPENAI_API_KEY` — [platform.openai.com](https://platform.openai.com)
- `OPENROUTER_API_KEY` + `USE_OPENROUTER=true` — [openrouter.ai](https://openrouter.ai)

### 3. Run the agent pipeline

```bash
python main.py pipeline \
  --email "contact@example.com" \
  --message "We need help automating our weekly reports."
```

Output: triage analysis, delivery strategy, and a draft email response.

### 4. Scrape leads

```bash
# Scrape specific websites
python main.py scrape --urls stripe.com hubspot.com

# Search and scrape (requires SERPAPI_KEY)
python main.py search --query "logistics companies Berlin" --results 20
```

Output: timestamped CSV in the `outputs/` folder.

---

## Agent Pipeline

```
[Input Email] → Maya (triage) → Leo (strategy) → Sophia (response draft)
```

Each agent uses a different model:
- **Maya** — `gpt-4o-mini` (triage)
- **Leo** and **Sophia** — `gpt-4o` (strategy and client-facing output)

Results saved to `outputs/<timestamp>_<email>.json`.

---

## Lead Scraper

Per website, the scraper:

1. Fetches the homepage
2. Extracts emails and phones
3. Auto-discovers contact/about pages if no email found
4. Saves everything to CSV

Works on any public business website. Respects configurable request delays.

**With SerpAPI:** Search Google and auto-scrape the top N results.

```bash
python main.py search --query "SaaS companies London" --results 15 --delay 2.0
```

---

## n8n Workflow Setup

1. Open your n8n instance
2. Click **Import from file** → select `workflows/obscuron_automation.json`
3. In each HTTP Request node, replace `YOUR_OPENROUTER_API_KEY` with your key
4. Update Discord nodes with your Guild ID and Channel IDs
5. Activate the workflow

The workflow posts AI-generated reports to Discord channels on a schedule.

---

## Configuration Reference

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | If not using OpenRouter | OpenAI API key |
| `OPENROUTER_API_KEY` | If not using OpenAI | OpenRouter API key |
| `USE_OPENROUTER` | No (default: false) | Set `true` to route through OpenRouter |
| `SERPAPI_KEY` | For search-based scraping | Free tier at serpapi.com |
| `DISCORD_BOT_TOKEN` | For Discord notifications | Discord bot token |
| `OUTPUT_DIR` | No (default: outputs) | Output directory for results |

---

## Extending the Toolkit

**Add an agent:** Subclass `BaseAgent` in `core/agents.py`, define a `SYSTEM` prompt, add it to `ObscuronPipeline.process()`.

**Add a scraping source:** Add a method to `ObscuronScraper` in `core/scraper.py`. CSV output format stays the same.

**Add an n8n trigger:** Import the workflow, add a Webhook node, connect it to the existing HTTP Request chain.

---

## License

See `LICENSE.txt`.

---

## Contact

For custom AI solutions, automation engagements, or questions about this toolkit, reach out via [obscuronlabs.com](https://obscuronlabs.com).

**Built by ObscuronLabs™.**
