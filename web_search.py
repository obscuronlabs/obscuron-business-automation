"""
Obscuron Labs — Web Search Engine
Real-time internet research for AI agents.
Uses DuckDuckGo (free, no API key) with SerpAPI fallback.
"""

import os
import logging
import time
from typing import Optional

logger = logging.getLogger("WebSearch")


def search(query: str, max_results: int = 5, retries: int = 3) -> str:
    """
    Search the web and return a formatted string of results.
    Returns empty string on failure (agents handle gracefully).
    """
    # Try DuckDuckGo first (free)
    for attempt in range(retries):
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if results:
                lines = [f"Web Search Results for: {query}\n"]
                for i, r in enumerate(results, 1):
                    title = r.get("title", "")
                    body = r.get("body", "")
                    href = r.get("href", "")
                    lines.append(f"[{i}] {title}\n{body}\nSource: {href}\n")
                return "\n".join(lines)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.warning(f"DuckDuckGo search failed for '{query}': {e}")

    # Fallback: SerpAPI if key available
    serpapi_key = os.getenv("SERPAPI_KEY")
    if serpapi_key:
        try:
            import requests
            resp = requests.get(
                "https://serpapi.com/search",
                params={"q": query, "num": max_results, "api_key": serpapi_key, "engine": "google"},
                timeout=15,
            )
            resp.raise_for_status()
            organic = resp.json().get("organic_results", [])
            lines = [f"Web Search Results for: {query}\n"]
            for i, r in enumerate(organic[:max_results], 1):
                lines.append(
                    f"[{i}] {r.get('title', '')}\n{r.get('snippet', '')}\nSource: {r.get('link', '')}\n"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"SerpAPI fallback failed for '{query}': {e}")

    return ""


def multi_search(queries: list[str], max_results: int = 3) -> str:
    """Run multiple searches and combine results."""
    combined = []
    for q in queries:
        result = search(q, max_results=max_results)
        if result:
            combined.append(result)
        time.sleep(0.5)
    return "\n\n---\n\n".join(combined) if combined else ""
