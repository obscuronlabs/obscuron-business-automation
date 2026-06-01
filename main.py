#!/usr/bin/env python3
"""
Obscuron Labs — Main Entry Point
Usage:
  python main.py pipeline --email client@co.com --message "We need automation help"
  python main.py scrape --urls stripe.com notion.so linear.app
  python main.py search --query "logistics companies Berlin" --results 15
"""

import argparse
import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from dotenv import load_dotenv

load_dotenv()


def cmd_pipeline(args):
    from agents import ObscuronPipeline

    use_router = os.getenv("USE_OPENROUTER", "false").lower() == "true"
    pipeline = ObscuronPipeline(openrouter_mode=use_router)

    message = args.message or input("Paste client message (Ctrl+D to finish):\n")
    result = pipeline.process(args.email, message)

    if not result.success:
        print("\n[ERROR] Pipeline failed. Check obscuron.log for details.")
        sys.exit(1)

    print("\n" + "="*60 + "\n📋 TRIAGE\n" + "="*60)
    print(result.triage.output)

    print("\n" + "="*60 + "\n🗺  STRATEGY\n" + "="*60)
    print(result.strategy.output)

    print("\n" + "="*60 + "\n✉  CLIENT EMAIL\n" + "="*60)
    print(result.final_email.output)

    saved = pipeline.save_result(result)
    print(f"\n✅ Saved to {saved}")


def cmd_scrape(args):
    from scraper import ObscuronScraper

    scraper = ObscuronScraper(request_delay=args.delay)
    leads = scraper.scrape_list(args.urls)
    output = scraper.save_to_csv(leads)

    verified = sum(l.verified for l in leads)
    print(f"\n✅ {len(leads)} sites scraped | {verified} verified leads → {output}")
    for lead in leads:
        status = "✓" if lead.verified else "✗"
        print(f"  [{status}] {lead.company_name or lead.website} | {lead.email or 'no email'}")


def cmd_search(args):
    from scraper import ObscuronScraper

    scraper = ObscuronScraper(request_delay=args.delay)
    leads = scraper.search_and_scrape(args.query, num_results=args.results)
    output = scraper.save_to_csv(leads)

    verified = sum(l.verified for l in leads)
    print(f"\n✅ {len(leads)} leads found | {verified} with contact info → {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Obscuron Labs Automation Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py pipeline --email ceo@client.com --message "We need help with..."
  python main.py scrape --urls stripe.com notion.so
  python main.py search --query "SaaS companies London" --results 20
        """,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Pipeline command
    p = sub.add_parser("pipeline", help="Run multi-agent client response pipeline")
    p.add_argument("--email", required=True, help="Client email address")
    p.add_argument("--message", default="", help="Client message text")

    # Scrape command
    s = sub.add_parser("scrape", help="Scrape lead data from website URLs")
    s.add_argument("--urls", nargs="+", required=True, help="Websites to scrape")
    s.add_argument("--delay", type=float, default=1.5, help="Seconds between requests")

    # Search command
    sr = sub.add_parser("search", help="Search Google and scrape results for leads")
    sr.add_argument("--query", required=True, help="Google search query")
    sr.add_argument("--results", type=int, default=10, help="Number of results to scrape")
    sr.add_argument("--delay", type=float, default=2.0, help="Seconds between requests")

    args = parser.parse_args()

    if args.command == "pipeline":
        cmd_pipeline(args)
    elif args.command == "scrape":
        cmd_scrape(args)
    elif args.command == "search":
        cmd_search(args)


if __name__ == "__main__":
    main()
