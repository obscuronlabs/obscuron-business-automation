"""
Influencer AI Hub — Music & Lifestyle Edition
Caption generator, hashtag optimizer, brand outreach, media kit
"""

import os
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Influencer AI Hub")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")

SYSTEM_PROMPT = """You are an expert Instagram growth strategist specializing in music and lifestyle influencers.
You help creators with 20K+ engaged followers monetize their content through brand deals, affiliate marketing, and UGC.
Always be specific, actionable, and tailor content to the music/lifestyle niche.
Write in a natural, human tone — never salesy or generic."""


async def ask_ai(prompt: str) -> str:
    if not OPENROUTER_KEY:
        return "ERROR: OPENROUTER_API_KEY not set"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000
            }
        )
    if resp.status_code != 200:
        return f"AI error: {resp.text}"
    return resp.json()["choices"][0]["message"]["content"].strip()


class CaptionRequest(BaseModel):
    topic: str
    mood: str = "authentic"
    include_cta: bool = True
    language: str = "turkish"  # turkish or english


class HashtagRequest(BaseModel):
    topic: str
    reach: str = "mixed"  # small, mixed, viral


class OutreachRequest(BaseModel):
    brand_name: str
    brand_niche: str
    your_name: str = "Influencer"
    followers: str = "20K"
    platform: str = "email"  # email or dm


class MediaKitRequest(BaseModel):
    name: str
    followers: str = "20K"
    avg_likes: str = "800"
    avg_comments: str = "60"
    engagement_rate: str = "4.3"
    niche: str = "Music & Lifestyle"
    location: str = "Turkey"
    audience_age: str = "18-34"
    audience_gender: str = "60% Female, 40% Male"
    previous_brands: str = ""


class PricingRequest(BaseModel):
    followers: int = 20000
    engagement_rate: float = 4.3
    content_type: str = "post"  # post, story, reel, package


@app.get("/")
async def index():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/caption")
async def generate_caption(req: CaptionRequest):
    lang_note = "Write in Turkish." if req.language == "turkish" else "Write in English."
    cta_note = "End with a soft call-to-action (ask a question or invite comments)." if req.include_cta else ""

    prompt = f"""Generate 3 Instagram caption options for a music & lifestyle influencer.

Topic/Context: {req.topic}
Mood: {req.mood}
{lang_note}
{cta_note}

Requirements:
- Natural, conversational tone
- 100-180 words each
- First line must be a hook that stops the scroll
- Include 1-2 relevant emojis per caption (not excessive)
- No generic influencer clichés

Format:
CAPTION 1:
[caption text]

CAPTION 2:
[caption text]

CAPTION 3:
[caption text]"""

    result = await ask_ai(prompt)
    return {"captions": result, "topic": req.topic}


@app.post("/api/hashtags")
async def generate_hashtags(req: HashtagRequest):
    prompt = f"""Generate the optimal Instagram hashtag set for a music & lifestyle influencer post about: {req.topic}

Strategy: {req.reach} reach (mix of niche, medium, and broad hashtags)

Provide:
1. 5 NICHE hashtags (under 100K posts) — high chance of being found
2. 8 MEDIUM hashtags (100K-1M posts) — good engagement
3. 5 BROAD hashtags (1M+ posts) — visibility boost
3. 2 TRENDING hashtags relevant right now for music/lifestyle

Also explain WHY this combination works.

Format as a ready-to-copy block at the end."""

    result = await ask_ai(prompt)
    return {"hashtags": result, "topic": req.topic}


@app.post("/api/outreach")
async def brand_outreach(req: OutreachRequest):
    platform_note = "Write a professional email" if req.platform == "email" else "Write a concise Instagram DM (max 150 words)"

    prompt = f"""{platform_note} pitching a brand collaboration.

Brand: {req.brand_name} ({req.brand_niche})
Influencer: {req.your_name}, {req.followers} followers, Music & Lifestyle niche
Platform: Instagram

Requirements:
- Subject line (if email): compelling, not spammy
- Open with a genuine compliment about the brand
- Mention your audience overlap with their target customer
- Propose 2-3 specific collaboration ideas
- Include your engagement stats naturally
- End with a clear, low-pressure next step
- Tone: confident but not desperate
- Sound like a real person, not a template

Also provide:
- FOLLOW-UP version (send after 5 days if no reply)
- NEGOTIATION tip: what to say if they offer free product only (no money)"""

    result = await ask_ai(prompt)
    return {"outreach": result, "brand": req.brand_name}


@app.post("/api/mediakit")
async def generate_media_kit(req: MediaKitRequest):
    brands_line = f"Previous collaborations: {req.previous_brands}" if req.previous_brands else "Building first brand partnerships"

    prompt = f"""Create a complete Instagram Media Kit text for an influencer.

Name: {req.name}
Niche: {req.niche}
Followers: {req.followers}
Avg Likes: {req.avg_likes}
Avg Comments: {req.avg_comments}
Engagement Rate: {req.engagement_rate}%
Location: {req.location}
Audience: {req.audience_age} | {req.audience_gender}
{brands_line}

Create a professional media kit with these sections:
1. BIO — 3 sentences, who you are, what you create, your audience
2. AUDIENCE INSIGHTS — demographics formatted nicely
3. CONTENT PILLARS — 4 content categories you cover
4. COLLABORATION PACKAGES — 3 tiers with what's included
5. RATE CARD — suggested prices for: story, post, reel, full package
6. WHY PARTNER WITH ME — 3 bullet points of value proposition
7. CONTACT — placeholder for email/DM

Make it professional enough to send to real brands today."""

    result = await ask_ai(prompt)
    return {"media_kit": result, "name": req.name}


@app.post("/api/pricing")
async def calculate_pricing(req: PricingRequest):
    prompt = f"""Calculate fair Instagram influencer pricing.

Stats:
- Followers: {req.followers:,}
- Engagement Rate: {req.engagement_rate}%
- Content Type: {req.content_type}
- Niche: Music & Lifestyle (Turkey-based, but open to international brands)

Provide:
1. MINIMUM price (don't go below this)
2. STANDARD price (what to ask for)
3. PREMIUM price (for long-term or exclusive deals)
4. HOW TO JUSTIFY your rate to brands
5. RED FLAGS — deals to avoid
6. NEGOTIATION script when brand says "our budget is lower"

Base on current 2024-2025 influencer market rates."""

    result = await ask_ai(prompt)
    return {"pricing": result, "followers": req.followers, "engagement": req.engagement_rate}


@app.get("/api/brands")
async def get_target_brands():
    prompt = """List the top 30 brands that actively pay music & lifestyle Instagram influencers (20K followers range) for collaborations.

Organize by category:
- Music gear & instruments (5 brands)
- Headphones & audio (5 brands)
- Fashion & streetwear (5 brands)
- Lifestyle & wellness (5 brands)
- Apps & digital products (5 brands)
- Turkish/regional brands that work with influencers (5 brands)

For each brand include:
- Brand name
- What they pay for (posts, stories, UGC)
- How to contact them (email/platform)
- Average pay range for 20K tier

Focus on brands known to work with micro/mid influencers."""

    result = await ask_ai(prompt)
    return {"brands": result}


@app.get("/api/strategy")
async def weekly_strategy():
    prompt = """Create a 4-week Instagram monetization action plan for a music & lifestyle influencer with 20K followers starting from zero brand deals.

Week by week, day by day priorities:

WEEK 1: Foundation
WEEK 2: Outreach begins
WEEK 3: Content optimization
WEEK 4: Close first deal

Include:
- Daily time commitment (realistic, max 1-2 hours)
- Which platforms to join (LTK, Amazon, etc.)
- First 5 brands to contact and WHY
- Content calendar template
- KPIs to track

Be specific and actionable. No fluff."""

    result = await ask_ai(prompt)
    return {"strategy": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
