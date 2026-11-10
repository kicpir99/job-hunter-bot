import logging
import sys
import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_BOT_TOKEN
from storage.database import JobDatabase
from analytics.market_report import MarketAnalytics
from analyzer.cover_letter import CoverLetterGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DiscordBot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

db = JobDatabase()
analytics = MarketAnalytics(db=db)
cover_letter_gen = CoverLetterGenerator(db=db)


@bot.event
async def on_ready():
    logger.info(f"Bot connected as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} application slash commands.")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")


@bot.tree.command(name="raport", description="Generuje raport analityczny rynku pracy IT dla Junior Python")
async def cmd_raport(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        embed_data = analytics.generate_discord_embed()
        embed = discord.Embed.from_dict(embed_data)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Wystąpił błąd podczas generowania raportu: {e}")


@bot.tree.command(name="oferty", description="Wyświetla ostatnio dopasowane oferty pracy z bazy")
@app_commands.describe(limit="Liczba ofert do wyświetlenia (1-10)")
async def cmd_oferty(interaction: discord.Interaction, limit: int = 5):
    limit = max(1, min(limit, 10))
    offers = db.get_recent_notified_offers(limit=limit)
    if not offers:
        await interaction.response.send_message("ℹ️ Brak zarejestrowanych dopasowanych ofert w bazie danych.")
        return

    embed = discord.Embed(
        title="🎯 Ostatnio dopasowane oferty pracy (Junior Python)",
        description=f"Oto ostatnie {len(offers)} ofert zakwalifikowanych przez filtr AI:",
        color=0x3498db
    )

    for o in offers:
        val = f"**Firma:** {o['company']}\n**Widełki:** {o['salary'] or 'Nie podano'}\n**Lokalizacja:** {o['location']}\n[👉 Aplikuj]({o['url']})"
        embed.add_field(name=f"#{o['id']} • {o['title']} ({o['portal'].upper()})", value=val, inline=False)

    embed.set_footer(text="Użyj /list id:<numer_lub_firma>, aby wygenerować list motywacyjny.")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="list", description="Generuje spersonalizowany list motywacyjny i pitch na LinkedIn")
@app_commands.describe(oferta="ID oferty lub nazwa firmy (np. 1, MasterBorn, Cloudfide)")
async def cmd_list(interaction: discord.Interaction, oferta: str):
    await interaction.response.defer(thinking=True)
    try:
        res = cover_letter_gen.generate(oferta)
        if "error" in res:
            await interaction.followup.send(f"❌ {res['error']}")
            return

        embed = discord.Embed(
            title=f"📄 Spersonalizowany List Motywacyjny: {res['company']}",
            description=f"**Stanowisko:** {res['title']}\n**Oferta:** [Link do ogłoszenia]({res['offer_url']})",
            color=0x2ecc71
        )

        # Discord embed fields limit is 1024 chars, cover letter might be slightly longer -> split or send in chunks
        pitch = res.get("linkedin_pitch", "")
        if pitch:
            embed.add_field(name="📨 Krótki Pitch do wiadomości na LinkedIn", value=f"```text\n{pitch}\n```", inline=False)

        letter = res.get("cover_letter_markdown", "")
        if len(letter) <= 1024:
            embed.add_field(name="📝 Treść listu motywacyjnego", value=letter, inline=False)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(embed=embed)
            # Send full cover letter as formatted follow-up message
            await interaction.followup.send(f"**Pełna treść listu motywacyjnego:**\n\n{letter}")

    except Exception as e:
        await interaction.followup.send(f"❌ Błąd podczas generowania: {e}")


@bot.tree.command(name="aplikowano", description="Oznacza ofertę jako wysłaną aplikację w Twoim prywatnym ATS")
@app_commands.describe(oferta="ID oferty lub nazwa firmy (np. 1, MasterBorn)")
async def cmd_aplikowano(interaction: discord.Interaction, oferta: str):
    updated = db.mark_as_applied(oferta)
    if not updated:
        await interaction.response.send_message(f"❌ Nie znaleziono oferty pasującej do: '{oferta}'.")
        return

    embed = discord.Embed(
        title="🎉 Aplikacja zarejestrowana!",
        description=f"Oznaczono ofertę **{updated['company']}** jako wysłaną w Twoim systemie ATS.",
        color=0x2ecc71
    )
    embed.add_field(name="Stanowisko", value=updated["title"], inline=True)
    embed.add_field(name="Portal", value=updated["portal"].upper(), inline=True)
    embed.add_field(name="Link do oferty", value=f"[Otwórz ogłoszenie]({updated['url']})", inline=False)
    embed.set_footer(text="Wpisz /aplikacje, aby zobaczyć całą historię swoich wysłanych CV.")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="aplikacje", description="Wyświetla listę wszystkich firm, do których wysłałeś CV")
async def cmd_aplikacje(interaction: discord.Interaction):
    applied = db.get_applied_offers()
    if not applied:
        await interaction.response.send_message("ℹ️ Nie masz jeszcze oznaczonych żadnych wysłanych aplikacji. Użyj `/aplikowano <id>`, gdy wyślesz CV!")
        return

    embed = discord.Embed(
        title=f"📋 Twoje aktywne aplikacje ({len(applied)})",
        description="Oto lista stanowisk, na które wysłałeś swoje zgłoszenie:",
        color=0x9b59b6
    )

    for a in applied[:15]:
        date_str = a.get("applied_at", "")[:10] if a.get("applied_at") else "Niedawno"
        val = f"**Firma:** {a['company']}\n**Widełki:** {a['salary'] or 'Brak'}\n**Data:** {date_str}\n[🔗 Przejdź do oferty]({a['url']})"
        embed.add_field(name=f"#{a['id']} • {a['title']}", value=val, inline=False)

    await interaction.response.send_message(embed=embed)


def main():
    if not DISCORD_BOT_TOKEN:
        logger.error("Brak skonfigurowanego DISCORD_BOT_TOKEN w pliku .env.")
        logger.info("Aby uruchomić interaktywnego bota:")
        logger.info("1. Wejdź na https://discord.com/developers/applications")
        logger.info("2. Stwórz aplikację bota i skopiuj 'Bot Token' do .env jako DISCORD_BOT_TOKEN.")
        logger.info("3. Zaproś bota na swój serwer z uprawnieniem 'applications.commands'.")
        return

    bot.run(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()

