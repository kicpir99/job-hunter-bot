import logging
from typing import Optional
import httpx

from config import DISCORD_WEBHOOK_URL
from models import JobOffer

logger = logging.getLogger(__name__)


def create_discord_embed(offer: JobOffer, ai_summary: Optional[str] = None) -> dict:
    """Tworzy bogatą wizualnie kartę (Embed) w Discordzie z danymi dopasowanymi do profilu."""
    fields = [
        {"name": "🏢 Firma", "value": offer.company, "inline": True},
        {"name": "💰 Wynagrodzenie", "value": offer.salary or "Brak podanych widełek", "inline": True},
        {"name": "📍 Lokalizacja", "value": f"{offer.location} {'(100% Zdalnie)' if offer.is_remote else ''}", "inline": True},
    ]

    # Informacja o dopasowaniu i technologiach
    if offer.match_score:
        score_icon = "🔥" if offer.match_score == "Wysokie" else "⚡"
        fields.append({
            "name": f"{score_icon} Dopasowanie do Twojego CV", 
            "value": f"**{offer.match_score}**", 
            "inline": True
        })

    if offer.matched_skills:
        matched_str = ", ".join(f"`{s}`" for s in offer.matched_skills)
        fields.append({
            "name": "✅ Pokrycie z Twoim stackiem", 
            "value": matched_str, 
            "inline": True
        })

    # Ostrzeżenie o statusie studenta
    if offer.requires_student:
        fields.append({
            "name": "🎓 Uwaga: Status studenta", 
            "value": "⚠️ *Ta oferta w treści wymaga posiadania statusu studenta.*", 
            "inline": False
        })

    if offer.requirements:
        reqs_str = ", ".join(f"`{r}`" for r in offer.requirements[:8])
        fields.append({"name": "🛠 Wymagania oferty", "value": reqs_str, "inline": False})

    if ai_summary:
        fields.append({"name": "🤖 Analiza AI (Gemini)", "value": ai_summary.strip(), "inline": False})

    # Kolor paska:
    # Żółty/pomarańczowy, jeśli wymaga studenta; Zielony jeśli 100% zdalnie; Niebieski jeśli Wrocław
    if offer.requires_student:
        color = 0xf39c12  # Pomarańczowy
    elif offer.is_remote:
        color = 0x2ecc71  # Zielony
    else:
        color = 0x3498db  # Niebieski

    badge_title = f"🎓 [DLA STUDENTA] {offer.title}" if offer.requires_student else f"💼 {offer.title}"

    return {
        "title": badge_title,
        "url": offer.url,
        "color": color,
        "fields": fields,
        "footer": {
            "text": f"Źródło: {offer.portal.upper()} • Kliknij tytuł, aby otworzyć ofertę"
        }
    }


def send_discord_message(
    offer: Optional[JobOffer] = None,
    text: Optional[str] = None,
    ai_summary: Optional[str] = None,
    webhook_url: Optional[str] = None
) -> bool:
    """Wysyła powiadomienie przez Discord Webhook."""
    target_webhook = webhook_url or DISCORD_WEBHOOK_URL

    if not target_webhook:
        logger.warning("Brak skonfigurowanego DISCORD_WEBHOOK_URL w pliku .env.")
        return False

    payload = {}
    if text:
        payload["content"] = text

    if offer:
        header = "🎓 **Nowa oferta (wymaga statusu studenta):**" if offer.requires_student else "🎯 **Nowa dopasowana oferta pracy!**"
        payload["content"] = payload.get("content", header)
        payload["embeds"] = [create_discord_embed(offer, ai_summary=ai_summary)]

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(target_webhook, json=payload)
            if resp.status_code in (200, 204):
                logger.info("Powiadomienie na Discord wysłane pomyślnie!")
                return True
            else:
                logger.error(f"Discord API zwróciło błąd {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Nie udało się wysłać powiadomienia na Discord: {e}")
        return False
