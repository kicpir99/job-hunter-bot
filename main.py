import argparse
import logging
import sys
from storage.database import JobDatabase
from scrapers.nofluffjobs import NoFluffJobsScraper
from scrapers.bulldogjob import BulldogJobScraper
from scrapers.justjoin import JustJoinScraper
from scrapers.pracujpl import PracujPlScraper
from analyzer.ai_filter import JobOfferAnalyzer
from notifier.telegram import format_offer_message, send_telegram_message
from notifier.discord import send_discord_message
from config import DATABASE_PATH, DISCORD_WEBHOOK_URL, TELEGRAM_BOT_TOKEN

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("JobHunter")


def dispatch_notification(offer, ai_summary: str | None = None) -> bool:
    """Wysyła powiadomienie na skonfigurowane kanały (Discord i/lub Telegram)."""
    sent_any = False

    # 1. Wysyłka na Discord (jeśli podano Webhook)
    if DISCORD_WEBHOOK_URL:
        if send_discord_message(offer=offer, ai_summary=ai_summary):
            sent_any = True

    # 2. Wysyłka na Telegram (jeśli skonfigurowano token)
    if TELEGRAM_BOT_TOKEN:
        tg_text = format_offer_message(offer, ai_summary=ai_summary)
        if send_telegram_message(tg_text):
            sent_any = True

    if not DISCORD_WEBHOOK_URL and not TELEGRAM_BOT_TOKEN:
        logger.warning("Brak skonfigurowanego kanału powiadomień! Uzupełnij DISCORD_WEBHOOK_URL lub TELEGRAM_BOT_TOKEN w .env")

    return sent_any


def run():
    parser = argparse.ArgumentParser(description="Job Hunter Bot - Automatyczny monitor ofert pracy")
    parser.add_argument("--reset-db", action="store_true", help="Usuwa dotychczasową bazę ofert i tworzy nową")
    parser.add_argument("--test-discord", action="store_true", help="Wysyła testową wiadomość na Discord")
    parser.add_argument("--test-telegram", action="store_true", help="Wysyła testową wiadomość na Telegram")
    args = parser.parse_args()

    if args.reset_db:
        if DATABASE_PATH.exists():
            DATABASE_PATH.unlink()
            logger.info(f"Baza danych {DATABASE_PATH} została zresetowana.")
        else:
            logger.info("Baza danych jeszcze nie istnieje.")
        return

    if args.test_discord:
        logger.info("Wysyłanie testowej wiadomości na Discord...")
        success = send_discord_message(text="🚀 **Job Hunter Bot:** Testowe powiadomienie Discord działa poprawnie!")
        if success:
            logger.info("Sukces! Sprawdź swój kanał na Discordzie.")
        else:
            logger.error("Błąd wysyłki. Upewnij się, że uzupełniłeś DISCORD_WEBHOOK_URL w pliku .env")
        return

    if args.test_telegram:
        logger.info("Wysyłanie testowej wiadomości na Telegram...")
        success = send_telegram_message("🚀 <b>Job Hunter Bot:</b> Testowe powiadomienie Telegram działa poprawnie!")
        if success:
            logger.info("Sukces! Sprawdź aplikację Telegram na telefonie.")
        else:
            logger.error("Błąd wysyłki. Upewnij się, że uzupełniłeś TELEGRAM_BOT_TOKEN i TELEGRAM_CHAT_ID w pliku .env")
        return

    logger.info("=== Rozpoczęcie cyklicznego sprawdzania ofert pracy ===")

    # 1. Inicjalizacja bazy danych
    db = JobDatabase()
    stats_before = db.get_stats()
    logger.info(f"Baza danych gotowa. Obecnie w bazie: {stats_before['total_tracked']} ofert (w tym {stats_before['total_notified']} wysłanych).")

    # 2. Inicjalizacja scraperów i modułu AI
    scrapers = [
        NoFluffJobsScraper(),
        JustJoinScraper(),
        PracujPlScraper(),
        BulldogJobScraper(),
    ]
    analyzer = JobOfferAnalyzer()

    total_fetched = 0
    new_offers_found = 0
    notifications_sent = 0

    # 3. Pobieranie ofert ze źródeł
    for scraper in scrapers:
        logger.info(f"Pobieranie ofert ze źródła: {scraper.name}...")
        offers = scraper.fetch_offers()
        total_fetched += len(offers)

        for offer in offers:
            # Sprawdzenie czy oferta była już wcześniej widziana
            if db.is_seen(offer.portal, offer.id):
                continue

            new_offers_found += 1
            logger.info(f"Nowa oferta! [{offer.company}] {offer.title}")

            # Analiza oferty przez AI (lub filtr regułowy)
            is_recommended, ai_summary = analyzer.evaluate_offer(offer)

            if not is_recommended:
                logger.info(f"Oferta odrzucona przez filtr: {ai_summary}")
                db.save_offer(offer, is_notified=False, ai_summary=ai_summary)
                continue

            # Wysłanie powiadomienia (Discord i/lub Telegram)
            sent_ok = dispatch_notification(offer, ai_summary=ai_summary)

            if sent_ok:
                notifications_sent += 1
                db.save_offer(offer, is_notified=True, ai_summary=ai_summary)
            else:
                db.save_offer(offer, is_notified=False, ai_summary=ai_summary)

            # Krótka pauza, by nie przekroczyć limitu 15 zapytań/min w AI
            import time
            time.sleep(1.5)

    logger.info(
        f"=== Zakończono! Pobranych: {total_fetched}, Nowych: {new_offers_found}, "
        f"Wysłanych powiadomień: {notifications_sent} ==="
    )


if __name__ == "__main__":
    run()
