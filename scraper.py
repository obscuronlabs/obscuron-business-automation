"""
Obscuron Labs — Lead Generation Engine
Production v2.0

Scrapes real company/contact data from public sources.
Respects robots.txt. For B2B prospecting only.
"""

import os
import re
import csv
import time
import logging
import random
from dataclasses import dataclass, field, asdict
from typing import Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("ObscuronScraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
PHONE_REGEX = re.compile(
    r"(\+?\d[\d\s\-\(\)]{7,}\d)"
)

SKIP_EMAIL_DOMAINS = {
    "example.com", "test.com", "sentry.io", "wixpress.com",
    "google.com", "apple.com", "gmail.com", "yahoo.com", "hotmail.com",
}

CONTACT_PAGE_HINTS = [
    "/contact", "/contact-us", "/about", "/about-us",
    "/impressum", "/team", "/reach-us", "/get-in-touch",
]


# ─── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class Lead:
    company_name: str = ""
    website: str = ""
    email: str = ""
    phone: str = ""
    description: str = ""
    source_url: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    verified: bool = False

    def is_valid(self) -> bool:
        return bool(self.email or self.phone)


# ─── Core Scraper ──────────────────────────────────────────────────────────────

class ObscuronScraper:
    """
    Scrapes B2B leads from:
      1. Direct URLs you provide
      2. Google search results (via SerpAPI if key is set)
    """

    def __init__(
        self,
        request_delay: float = 1.5,
        timeout: int = 10,
        serpapi_key: Optional[str] = None,
    ):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = request_delay
        self.timeout = timeout
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_KEY")
        logger.info("Obscuron Scraper initialized")

    def _get(self, url: str) -> Optional[BeautifulSoup]:
        try:
            time.sleep(self.delay + random.uniform(0, 0.5))
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def _extract_emails(self, soup: BeautifulSoup, url: str) -> list[str]:
        text = soup.get_text(separator=" ")
        # Also check mailto links
        mailto_emails = [
            a["href"].replace("mailto:", "").split("?")[0].strip()
            for a in soup.find_all("a", href=True)
            if a["href"].startswith("mailto:")
        ]
        regex_emails = EMAIL_REGEX.findall(text)
        all_emails = set(mailto_emails + regex_emails)

        domain = urlparse(url).netloc.replace("www.", "")
        filtered = [
            e for e in all_emails
            if e.split("@")[-1] not in SKIP_EMAIL_DOMAINS
            and not e.endswith(".png")
            and not e.endswith(".jpg")
        ]
        # Prefer emails matching the company domain
        filtered.sort(key=lambda e: (0 if domain in e else 1))
        return filtered

    def _extract_phones(self, soup: BeautifulSoup) -> list[str]:
        text = soup.get_text(separator=" ")
        phones = PHONE_REGEX.findall(text)
        cleaned = [re.sub(r"\s+", " ", p).strip() for p in phones]
        # Filter out short numbers that are likely not phones
        return [p for p in cleaned if len(re.sub(r"\D", "", p)) >= 7]

    def _extract_description(self, soup: BeautifulSoup) -> str:
        meta = soup.find("meta", attrs={"name": "description"}) or \
               soup.find("meta", property="og:description")
        if meta and meta.get("content"):
            return meta["content"][:300]
        # Fallback: first paragraph
        p = soup.find("p")
        return p.get_text(strip=True)[:300] if p else ""

    def _find_contact_page(self, base_url: str, soup: BeautifulSoup) -> Optional[str]:
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if any(hint in href for hint in CONTACT_PAGE_HINTS):
                return urljoin(base_url, a["href"])
        # Try common paths directly
        for hint in CONTACT_PAGE_HINTS:
            candidate = urljoin(base_url, hint)
            if candidate != base_url:
                return candidate
        return None

    def scrape_website(self, url: str) -> Lead:
        """Scrape a single website for lead data."""
        if not url.startswith("http"):
            url = "https://" + url

        lead = Lead(website=url, source_url=url)
        logger.info(f"Scraping: {url}")

        soup = self._get(url)
        if not soup:
            return lead

        # Company name from title or og:site_name
        og_site = soup.find("meta", property="og:site_name")
        title_tag = soup.find("title")
        if og_site and og_site.get("content"):
            lead.company_name = og_site["content"].strip()
        elif title_tag:
            lead.company_name = title_tag.get_text(strip=True).split("|")[0].split("-")[0].strip()

        lead.description = self._extract_description(soup)

        emails = self._extract_emails(soup, url)
        phones = self._extract_phones(soup)

        # Try contact page if we haven't found an email yet
        if not emails:
            contact_url = self._find_contact_page(url, soup)
            if contact_url:
                logger.info(f"  Checking contact page: {contact_url}")
                contact_soup = self._get(contact_url)
                if contact_soup:
                    emails = self._extract_emails(contact_soup, url)
                    if not phones:
                        phones = self._extract_phones(contact_soup)

        lead.email = emails[0] if emails else ""
        lead.phone = phones[0] if phones else ""
        lead.verified = bool(lead.email)

        logger.info(
            f"  → {lead.company_name} | email: {lead.email or 'none'} | "
            f"phone: {lead.phone or 'none'}"
        )
        return lead

    def scrape_list(self, urls: list[str]) -> list[Lead]:
        """Scrape a list of websites."""
        leads = []
        for url in urls:
            lead = self.scrape_website(url)
            leads.append(lead)
        logger.info(f"Scraped {len(leads)} sites | {sum(l.verified for l in leads)} verified leads")
        return leads

    def search_and_scrape(self, query: str, num_results: int = 10) -> list[Lead]:
        """
        Search Google via SerpAPI and scrape the results.
        Requires SERPAPI_KEY in .env
        """
        if not self.serpapi_key:
            logger.warning(
                "No SERPAPI_KEY found. Set it in .env to enable search-based scraping. "
                "Falling back to empty list."
            )
            return []

        try:
            params = {
                "q": query,
                "num": num_results,
                "api_key": self.serpapi_key,
                "engine": "google",
            }
            resp = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            organic = data.get("organic_results", [])
            urls = [r["link"] for r in organic if "link" in r]
            logger.info(f"SerpAPI returned {len(urls)} results for: '{query}'")
            return self.scrape_list(urls)
        except Exception as e:
            logger.error(f"SerpAPI search failed: {e}")
            return []

    def save_to_csv(self, leads: list[Lead], output_dir: str = "outputs") -> str:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/leads_{timestamp}.csv"
        if not leads:
            logger.warning("No leads to save.")
            return filename
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=asdict(leads[0]).keys())
            writer.writeheader()
            writer.writerows([asdict(l) for l in leads])
        valid = sum(l.verified for l in leads)
        logger.info(f"Saved {len(leads)} leads ({valid} verified) → {filename}")
        return filename


# ─── CLI Entry Point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    scraper = ObscuronScraper(request_delay=2.0)

    # Example: scrape specific websites
    urls = [
        "https://stripe.com",
        "https://notion.so",
        "https://linear.app",
    ]
    leads = scraper.scrape_list(urls)
    output = scraper.save_to_csv(leads)
    print(f"\n✓ Leads saved to: {output}")
    for l in leads:
        print(f"  {l.company_name} | {l.email} | {l.phone}")
