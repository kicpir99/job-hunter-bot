import logging
from typing import Optional, Dict, Any
import httpx

from config import DISCORD_WEBHOOK_URL
from models import JobOffer

logger = logging.getLogger(__name__)


def create_discord_embed(offer: JobOffer, ai_summary: Optional[str] = None) -> Dict[str, Any]:
    """Constructs a Discord Embed card with candidate alignment indicators."""
    fields = [
        {"name": "🏢 Firma", "value": offer.company, "inline": True},
        {"name": "💰 Wynagrodzenie", "value": offer.salary or "Brak podanych widełek", "inline": True},
        {"name": "📍 Lokalizacja", "value": f"{offer.location} {'(100% Zdalnie)' if offer.is_remote else ''}", "inline": True},
    ]

    if offer.match_score:
        score_icon = "🔥" if offer.match_score == "Wysokie" else "⚡"
        fields.append({
            "name": f"{score_icon} Dopasowanie do profilu", 
            "value": f"**{offer.match_score}**", 
            "inline": True
        })

    if offer.matched_skills:
        matched_str = ", ".join(f"`{s}`" for s in offer.matched_skills)
        fields.append({
            "name": "✅ Zgodność ze stosem", 
            "value": matched_str, 
            "inline": True
        })

    if offer.requires_student:
        fields.append({
            "name": "🎓 Wymóg formalny", 
            "value": "⚠️ *Oferta w treści wymaga statusu studenta.*", 
            "inline": False
        })

    if offer.requirements:
        reqs_str = ", ".join(f"`{r}`" for r in offer.requirements[:8])
        fields.append({"name": "🛠 Wymagania ogłoszenia", "value": reqs_str, "inline": False})

    if ai_summary:
        fields.append({"name": "🤖 Analiza AI", "value": ai_summary.strip(), "inline": False})

    if offer.requires_student:
        color = 0xf39c12
    elif offer.is_remote:
        color = 0x2ecc71
    else:
        color = 0x3498db

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
    """Dispatches payload to Discord Webhook endpoint."""
    target_webhook = webhook_url or DISCORD_WEBHOOK_URL
    if not target_webhook:
        return False

    payload = {}
    if text:
        payload["content"] = text

    if offer:
        header = "🎓 **Nowa oferta (status studenta):**" if offer.requires_student else "🎯 **Nowa dopasowana oferta pracy!**"
        payload["content"] = payload.get("content", header)
        payload["embeds"] = [create_discord_embed(offer, ai_summary=ai_summary)]

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(target_webhook, json=payload)
            if resp.status_code in (200, 204):
                logger.info(f"Notification successfully delivered to Discord ({offer.title if offer else 'Text'}).")
                return True
            else:
                logger.error(f"Discord API returned status {resp.status_code}: {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to deliver Discord notification: {e}")
        return False
