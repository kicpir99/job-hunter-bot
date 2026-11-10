import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List

from storage.database import JobDatabase
from scrapers import (
    BaseScraper,
    NoFluffJobsScraper,
    BulldogJobScraper,
    JustJoinScraper,
    PracujPlScraper,
)
from analyzer.ai_filter import JobOfferAnalyzer
from analyzer.cover_letter import CoverLetterGenerator
from analytics.market_report import MarketAnalytics
from notifier.telegram import format_offer_message, send_telegram_message
from notifier.discord import send_discord_message
from config import DATABASE_PATH, DISCORD_WEBHOOK_URL, TELEGRAM_BOT_TOKEN
from models import JobOffer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("JobHunter")


def dispatch_notification(offer: JobOffer, ai_summary: str | None = None) -> bool:
    """Dispatches notifications across configured messaging backends."""
    dispatched = False

    if DISCORD_WEBHOOK_URL:
        if send_discord_message(offer=offer, ai_summary=ai_summary):
            dispatched = True

    if TELEGRAM_BOT_TOKEN:
        tg_text = format_offer_message(offer, ai_summary=ai_summary)
        if send_telegram_message(tg_text):
            dispatched = True

    if not DISCORD_WEBHOOK_URL and not TELEGRAM_BOT_TOKEN:
        logger.warning("No notification backend configured. Check DISCORD_WEBHOOK_URL or TELEGRAM_BOT_TOKEN.")

    return dispatched


def run() -> None:
    parser = argparse.ArgumentParser(description="Job Hunter Agent - Career Operations & Market Intelligence Engine")
    parser.add_argument("--reset-db", action="store_true", help="Purges database and reinitializes empty schema")
    parser.add_argument("--test-discord", action="store_true", help="Dispatches test card to Discord webhook")
    parser.add_argument("--test-telegram", action="store_true", help="Dispatches test message to Telegram bot")
    parser.add_argument("--stats", action="store_true", help="Displays current database tracking metrics")
    parser.add_argument("--report", action="store_true", help="Generates comprehensive IT market intelligence report")
    parser.add_argument("--cleanup", type=int, default=None, metavar="DAYS", help="Purges database records older than DAYS (default: 60 days in automated cycle)")
    parser.add_argument("--cover-letter", type=str, metavar="QUERY", help="Generates bespoke cover letter and LinkedIn pitch for company or offer ID")
    args = parser.parse_args()

    db = JobDatabase()

    if args.reset_db:
        if DATABASE_PATH.exists():
            DATABASE_PATH.unlink()
            logger.info(f"Database at {DATABASE_PATH} successfully reset.")
        return

    if args.stats:
        stats = db.get_stats()
        logger.info(f"Total postings tracked: {stats['total_tracked']}")
        logger.info(f"Total dispatched: {stats['total_notified']}")
        logger.info(f"Breakdown by portal: {stats['by_portal']}")
        return

    if args.cleanup is not None:
        pruned = db.cleanup_old_offers(retention_days=args.cleanup)
        logger.info(f"Database hygiene complete: purged {pruned} offers older than {args.cleanup} days.")
        return

    if args.report:
        analytics = MarketAnalytics(db=db)
        report_md = analytics.generate_markdown_report()
        logger.info("Market Intelligence Report successfully generated:\n")
        print(report_md)
        logger.info("Saved to reports/market_insights.md")
        return

    if args.cover_letter:
        generator = CoverLetterGenerator(db=db)
        logger.info(f"Generating personalized application artifacts for: '{args.cover_letter}'...")
        res = generator.generate(args.cover_letter)
        if "error" in res:
            logger.error(res["error"])
            return

        company_safe = res["company"].replace(" ", "_").lower()
        out_path = Path("reports") / f"cover_letter_{company_safe}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        full_doc = f"# Application Kit: {res['company']} — {res['title']}\n\n"
        full_doc += f"**Offer URL:** {res['offer_url']}\n\n"
        full_doc += f"## 📨 LinkedIn InMail Pitch\n```text\n{res['linkedin_pitch']}\n```\n\n"
        full_doc += f"## 📄 Full Cover Letter\n\n{res['cover_letter_markdown']}\n"

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_doc)

        logger.info(f"Artifacts successfully created at {out_path}!\n")
        print(full_doc)
        return

    if args.test_discord:
        success = send_discord_message(text="🚀 **Job Hunter Engine:** Notification test successful.")
        if success:
            logger.info("Test payload delivered to Discord.")
        else:
            logger.error("Failed to deliver payload. Check DISCORD_WEBHOOK_URL.")
        return

    if args.test_telegram:
        success = send_telegram_message("🚀 <b>Job Hunter Engine:</b> Notification test successful.")
        if success:
            logger.info("Test payload delivered to Telegram.")
        else:
            logger.error("Failed to deliver payload. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return

    logger.info("=== Starting job aggregation and screening cycle ===")
    pruned = db.cleanup_old_offers(retention_days=60)
    if pruned > 0:
        logger.info(f"Retention policy applied: purged {pruned} stale vacancies older than 60 days.")

    initial_stats = db.get_stats()
    logger.info(f"Database initialized. Currently tracking {initial_stats['total_tracked']} offers.")

    scrapers: List[BaseScraper] = [
        NoFluffJobsScraper(),
        JustJoinScraper(),
        PracujPlScraper(),
        BulldogJobScraper(),
    ]
    analyzer = JobOfferAnalyzer()

    total_fetched = 0
    new_offers_found = 0
    notifications_sent = 0

    for scraper in scrapers:
        logger.info(f"Scraping source: {scraper.name}...")
        offers = scraper.fetch_offers()
        total_fetched += len(offers)

        for offer in offers:
            if db.is_seen(offer.portal, offer.id):
                continue

            new_offers_found += 1
            logger.info(f"New posting detected: [{offer.company}] {offer.title} ({offer.portal})")

            is_recommended, ai_summary = analyzer.evaluate_offer(offer)

            if not is_recommended:
                logger.info(f"Rejected by screener: {ai_summary}")
                db.save_offer(offer, is_notified=False, ai_summary=ai_summary)
                continue

            dispatched = dispatch_notification(offer, ai_summary=ai_summary)
            if dispatched:
                notifications_sent += 1
                db.save_offer(offer, is_notified=True, ai_summary=ai_summary)
            else:
                db.save_offer(offer, is_notified=False, ai_summary=ai_summary)

            time.sleep(1.5)

    logger.info(
        f"=== Cycle completed! Ingested: {total_fetched}, New: {new_offers_found}, "
        f"Dispatched: {notifications_sent} ==="
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.exception("Critical pipeline failure encountered.")
        if DISCORD_WEBHOOK_URL:
            try:
                send_discord_message(
                    text=f"🚨 **[Job Hunter Engine Alert]** Wystąpił błąd krytyczny w cyklu:\n```{str(e)[:300]}```"
                )
            except Exception:
                pass
        sys.exit(1)
