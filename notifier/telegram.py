import html
import logging
from typing import Optional
import httpx

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from models import JobOffer

logger = logging.getLogger(__name__)


def format_offer_message(offer: JobOffer, ai_summary: Optional[str] = None) -> str:
    """Tworzy estetyczną wiadomość HTML do wysłania na Telegram z dopasowaniem do profilu."""
    title_escaped = html.escape(offer.title)
    company_escaped = html.escape(offer.company)
    location_escaped = html.escape(offer.location)
    salary_escaped = html.escape(offer.salary) if offer.salary else "Brak podanych widełek"

    reqs_str = ", ".join(offer.requirements[:6]) if offer.requirements else "Brak danych"
    reqs_escaped = html.escape(reqs_str)

    header = "🎓 <b>Nowa oferta (wymaga statusu studenta):</b>" if offer.requires_student else "🎯 <b>Nowa dopasowana oferta pracy!</b>"

    msg_lines = [
        f"{header}\n",
        f"💼 <b>Stanowisko:</b> {title_escaped}",
        f"🏢 <b>Firma:</b> {company_escaped}",
        f"💰 <b>Wynagrodzenie:</b> {salary_escaped}",
        f"📍 <b>Lokalizacja:</b> {location_escaped} {'(100% Zdalnie)' if offer.is_remote else ''}",
        f"🛠 <b>Wymagania:</b> <code>{reqs_escaped}</code>",
    ]

    if offer.match_score:
        score_icon = "🔥" if offer.match_score == "Wysokie" else "⚡"
        msg_lines.append(f"{score_icon} <b>Dopasowanie do CV:</b> <b>{offer.match_score}</b>")

    if offer.matched_skills:
        skills_str = ", ".join(offer.matched_skills)
        msg_lines.append(f"✅ <b>Twój stack w ofercie:</b> <code>{html.escape(skills_str)}</code>")

    if offer.requires_student:
        msg_lines.append("\n⚠️ <i>Uwaga: oferta w treści wymaga statusu studenta.</i>")

    if ai_summary:
        msg_lines.append(f"\n🤖 <b>Analiza AI:</b>\n<i>{html.escape(ai_summary.strip())}</i>")

    msg_lines.append(f"\n🔗 <a href=\"{offer.url}\">👉 Kliknij tutaj, aby zobaczyć i aplikować</a>")

    return "\n".join(msg_lines)


def send_telegram_message(
    message: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None
) -> bool:
    """Wysyła wiadomość HTML na podany czat Telegrama."""
    token = bot_token or TELEGRAM_BOT_TOKEN
    target_chat = chat_id or TELEGRAM_CHAT_ID

    if not token or not target_chat:
        logger.warning("Brak skonfigurowanego TELEGRAM_BOT_TOKEN lub TELEGRAM_CHAT_ID. Wiadomość nie została wysłana.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                logger.info("Powiadomienie na Telegram wysłane pomyślnie!")
                return True
            else:
                logger.error(f"Telegram API zwróciło błąd {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Nie udało się wysłać wiadomości na Telegram: {e}")
        return False
