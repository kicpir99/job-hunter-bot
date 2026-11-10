import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx

from config import DISCORD_WEBHOOK_URL
from models import JobOffer

logger = logging.getLogger(__name__)


def create_discord_embed(offer: JobOffer, ai_summary: Optional[str] = None) -> Dict[str, Any]:
    """Constructs an ultra-readable, symmetrical Discord Embed card with candidate alignment indicators."""
    
    # 1. Location and mode formatting
    loc_display = offer.location
    if offer.is_remote:
        loc_display = f"{offer.location} (🌐 Remote)"
    else:
        loc_display = f"{offer.location} (🏢 Biuro)"

    # 2. Row 1: Core Job Metrics (3 inline columns)
    fields = [
        {"name": "🏢 Firma", "value": f"**{offer.company}**", "inline": True},
        {"name": "💰 Wynagrodzenie", "value": f"**{offer.salary or 'Brak podanych widełek'}**", "inline": True},
        {"name": "📍 Lokalizacja", "value": loc_display, "inline": True},
    ]

    # 3. Row 2: Candidate Alignment & Source Grid (3 inline columns)
    score_val = f"🔥 **{offer.match_score}**" if offer.match_score == "Wysokie" else f"⚡ **{offer.match_score or 'Średnie'}**"
    student_val = "⚠️ **Wymagany**" if offer.requires_student else "✅ **Brak wymogu**"
    portal_val = f"[{offer.portal.upper()} ↗]({offer.url})"

    fields.extend([
        {"name": "🎯 Dopasowanie (AI)", "value": score_val, "inline": True},
        {"name": "🎓 Status studenta", "value": student_val, "inline": True},
        {"name": "🌐 Portal", "value": portal_val, "inline": True},
    ])

    # 4. Tech Stack Breakdown (Candidate Match vs Additional)
    if offer.matched_skills:
        matched_str = " • ".join(f"`{s}`" for s in offer.matched_skills)
        fields.append({
            "name": "\u200b\n🟢 Pokryte technologie z Twojego profilu",
            "value": matched_str,
            "inline": False
        })

    if offer.requirements:
        matched_lower = {s.lower() for s in (offer.matched_skills or [])}
        additional = [r for r in offer.requirements if r.lower() not in matched_lower]
        if additional:
            add_str = " • ".join(f"`{r}`" for r in additional[:8])
            fields.append({
                "name": "\u200b\n📌 Dodatkowe wymagania roli",
                "value": add_str,
                "inline": False
            })
        elif not offer.matched_skills:
            reqs_str = " • ".join(f"`{r}`" for r in offer.requirements[:8])
            fields.append({"name": "\u200b\n🛠 Wymagania ogłoszenia", "value": reqs_str, "inline": False})

    # 5. AI Executive Summary & Application Insights (Blockquote format)
    if ai_summary:
        quoted_summary = "\n".join(f"> {line}" for line in ai_summary.strip().split("\n") if line.strip())
        fields.append({
            "name": "\u200b\n🤖 Analiza AI & Wskazówki rekrutacyjne",
            "value": quoted_summary,
            "inline": False
        })

    # 6. Dynamic Color Scheme
    if offer.requires_student:
        color = 0xF1C40F  # Warning Amber
    elif offer.match_score == "Wysokie" or offer.is_remote:
        color = 0x2ECC71  # Vibrant Emerald Green
    else:
        color = 0x3498DB  # Tech Blue

    badge_title = f"🎓 [DLA STUDENTA] {offer.title}" if offer.requires_student else f"💼 {offer.title}"

    return {
        "title": badge_title,
        "url": offer.url,
        "color": color,
        "fields": fields,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {
            "text": f"ID: {offer.id} • Użyj /list na czacie, aby przygotować aplikację"
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
        payload["components"] = [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": f"👉 Aplikuj na {offer.portal.upper()}",
                        "url": offer.url
                    }
                ]
            }
        ]

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
