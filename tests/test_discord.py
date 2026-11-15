from models import JobOffer
from notifier.discord import create_discord_embed, _truncate


def test_truncate_helper():
    assert _truncate("short", 10) == "short"
    assert _truncate("abcdefghijk", 8) == "abcde..."
    assert len(_truncate("x" * 300, 256)) == 256


def test_create_discord_embed_enforces_discord_limits():
    offer = JobOffer(
        id="123456",
        portal="justjoin",
        title="A" * 400,
        company="B" * 1500,
        url="https://example.com/offer",
        salary="10000 PLN",
        location="Warszawa",
        is_remote=True,
        requirements=["Python"] * 200,
        matched_skills=["Python"] * 200,
        match_score="Wysokie",
        requires_student=False,
    )
    embed = create_discord_embed(offer, ai_summary="Line\n" * 500, db_id=42)

    assert len(embed["title"]) <= 256
    assert len(embed["footer"]["text"]) <= 2048
    for field in embed["fields"]:
        assert len(field["name"]) <= 256
        assert len(field["value"]) <= 1024
