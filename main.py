#!/usr/bin/env python3
"""
Obscuron Labs — Main Entry Point
Usage:
  python main.py pipeline --email client@co.com --message "We need automation help"
  python main.py scrape --urls stripe.com notion.so linear.app
  python main.py search --query "logistics companies Berlin" --results 15
  python main.py report --email client@co.com --message "..." --discord
"""

import argparse
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()


def cmd_pipeline(args):
    from agents import ObscuronPipeline
    from discord_reporter import report_pipeline_result, get_webhooks_from_env

    use_router = os.getenv("USE_OPENROUTER", "false").lower() == "true"
    pipeline = ObscuronPipeline(openrouter_mode=use_router)

    message = args.message or input("Paste client message:\n")
    result = pipeline.process(args.email, message)

    if not result.success:
        print("\n[ERROR] Pipeline failed. Check obscuron.log for details.")
        sys.exit(1)

    sections = [
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

    for title, r in sections:
        if r:
            print(f"\n{'='*60}\n{title}\n{'='*60}")
            print(r.output)

    saved = pipeline.save_result(result)
    print(f"\n[+] Saved to {saved}")

    if args.discord:
        webhooks = get_webhooks_from_env()
        if webhooks:
            sent = report_pipeline_result(result, webhooks)
            ok = sum(1 for v in sent.values() if v)
            print(f"[+] Discord: {ok}/{len(sent)} channels notified")
        else:
            print("[!] No Discord webhooks configured. Add DISCORD_WEBHOOK_* vars to .env")


def cmd_scrape(args):
    from scraper import ObscuronScraper

    scraper = ObscuronScraper(request_delay=args.delay)
    leads = scraper.scrape_list(args.urls)
    output = scraper.save_to_csv(leads)

    verified = sum(l.verified for l in leads)
    print(f"\n[+] {len(leads)} sites scraped | {verified} verified leads -> {output}")
    for lead in leads:
        status = "+" if lead.verified else "-"
        print(f"  [{status}] {lead.company_name or lead.website} | {lead.email or 'no email'}")


def cmd_search(args):
    from scraper import ObscuronScraper

    scraper = ObscuronScraper(request_delay=args.delay)
    leads = scraper.search_and_scrape(args.query, num_results=args.results)
    output = scraper.save_to_csv(leads)

    verified = sum(l.verified for l in leads)
    print(f"\n[+] {len(leads)} leads found | {verified} with contact info -> {output}")
    for lead in leads:
        status = "+" if lead.verified else "-"
        print(f"  [{status}] {lead.company_name or lead.website} | {lead.email or 'no email'}")


def main():
    parser = argparse.ArgumentParser(
        description="Obscuron Labs Automation Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py pipeline --email ceo@client.com --message "We need help with..."
  python main.py pipeline --email ceo@client.com --message "..." --discord
  python main.py scrape --urls stripe.com notion.so
  python main.py search --query "SaaS companies London" --results 20
        """,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Pipeline command
    p = sub.add_parser("pipeline", help="Run 15-agent client response pipeline")
    p.add_argument("--email", required=True, help="Client email address")
    p.add_argument("--message", default="", help="Client message text")
    p.add_argument("--discord", action="store_true", help="Post results to Discord webhooks")

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
