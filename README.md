# Obscuron Labs — AI Business Automation Suite
### Production v2.0

> Multi-agent email pipeline · Real lead generation · n8n Discord automation

---

## What's in this package

| File | What it does |
|---|---|
| `core/agents.py` | Three-agent AI pipeline (triage → strategy → response email) |
| `core/scraper.py` | Real B2B lead scraper — emails, phones, company names from any website |
| `main.py` | CLI entry point for all features |
| `dashboard/index.html` | Sales landing page you can deploy immediately |
| `workflows/obscuron_automation.json` | n8n workflow — imports directly into your n8n instance |
| `requirements.txt` | All Python dependencies, pinned versions |
| `.env.example` | Configuration template |

---

## Quick Start (5 minutes)

### 1. Install dependencies

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Open .env and add your API keys
```

**Minimum required:**
- `OPENAI_API_KEY` — get one at [platform.openai.com](https://platform.openai.com)
- OR `OPENROUTER_API_KEY` + `USE_OPENROUTER=true` — get one at [openrouter.ai](https://openrouter.ai)

### 3. Run the agent pipeline

```bash
python main.py pipeline \
  --email "ceo@prospect.com" \
  --message "We need help automating our weekly reports and client follow-ups."
```

Output: triage analysis, delivery strategy, and a ready-to-send email — all in under 30 seconds.

### 4. Scrape leads

```bash
# Scrape specific websites
python main.py scrape --urls stripe.com hubspot.com salesforce.com

# Search Google and scrape results (requires SERPAPI_KEY)
python main.py search --query "logistics companies Berlin" --results 20
```

Output: timestamped CSV in the `outputs/` folder.

---

## Agent Pipeline — How It Works

```
[Client Email] → Maya (triage) → Leo (strategy) → Sophia (client reply)
                    │                  │                    │
                 extracts:         produces:           writes:
                 intent            timeline            polished
                 urgency           tech stack          <250 word
                 budget            pricing             email ready
                 requirements      team plan           to send
```

Each agent uses a different model:
- **Maya** uses `gpt-4o-mini` (fast, cheap — triage is straightforward)
- **Leo** and **Sophia** use `gpt-4o` (quality matters for strategy and client-facing output)

All results saved to `outputs/<timestamp>_<email>.json`.

---

## Lead Scraper — How It Works

The scraper does four things per website:

1. Fetches the homepage
2. Extracts emails (prefers those matching the company domain) and phones
3. If no email found, auto-discovers and checks the contact/about page
4. Saves everything to a CSV

Works on any public business website. Respects server response times with configurable delays.

**With SerpAPI:** Run a Google search query and auto-scrape the top N results.

```bash
python main.py search --query "SaaS companies London hiring" --results 15 --delay 2.0
```

---

## n8n Workflow Setup

1. Open your n8n instance
2. Click **Import from file** and select `workflows/obscuron_automation.json`
3. Update the following in each HTTP Request node:
   - Replace `YOUR_OPENROUTER_API_KEY` with your key
4. Update Discord nodes:
   - Set your Guild ID and Channel IDs
5. Activate the workflow

The workflow runs hourly and posts AI-generated reports to your Discord channels:
- `#automation-reports` — operations summary
- `#client-analysis` — client pipeline report
- `#workflow-alerts` — system monitoring
- `#market-research` — AI market intelligence

---

## Configuration Reference

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | If not using OpenRouter | Your OpenAI API key |
| `OPENROUTER_API_KEY` | If not using OpenAI | Your OpenRouter API key |
| `USE_OPENROUTER` | No (default: false) | Set `true` to use OpenRouter |
| `SERPAPI_KEY` | For search-based scraping | Free tier available at serpapi.com |
| `DISCORD_BOT_TOKEN` | For Discord notifications | Your Discord bot token |
| `OUTPUT_DIR` | No (default: outputs) | Where to save results |

---

## Deploying the Sales Page

The `dashboard/index.html` is a standalone file — no server required.

**Fastest options:**
- Drag it into [Netlify Drop](https://app.netlify.com/drop) — live in 30 seconds
- Upload to GitHub Pages (free)
- Host on any static host (Vercel, Cloudflare Pages)

Update the Gumroad/buy links to point to your own product listing.

---

## Cost Estimates

| Usage | Monthly API Cost |
|---|---|
| 50 pipeline runs/month | ~$2–4 |
| 200 pipeline runs/month | ~$8–15 |
| n8n workflow (hourly, 30 days) | ~$1–3 |

Using OpenRouter with cheaper models (Mistral, Llama) can cut costs by 70%.

---

## Extending the Package

**Add a new agent:** Subclass `BaseAgent` in `core/agents.py`, define a `SYSTEM` prompt, add it to `ObscuronPipeline.process()`.

**Add a scraping source:** Add a new method to `ObscuronScraper` in `core/scraper.py`. The CSV output format stays the same.

**Add a new n8n trigger:** Import the workflow, add a Webhook node, connect it to the existing HTTP Request chain.

---

## License

See `LICENSE.txt`. For Agency tier: resale rights included, white-label permitted, attribution not required.

---

## Support

Questions? Open issues on the repo or reach out via the contact link on the landing page.

**Built by Obscuron Labs.**
