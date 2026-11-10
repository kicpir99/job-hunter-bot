import json
import logging
from typing import Optional, Dict, Any, List
import httpx

from config import GEMINI_API_KEY, GEMINI_MODEL
from candidate_profile import CANDIDATE_PROFILE
from storage.database import JobDatabase

logger = logging.getLogger(__name__)


class CoverLetterGenerator:
    """Generates highly customized, project-grounded cover letters and outreach pitches."""

    GITHUB_USERNAME = "kicpir99"
    GITHUB_REPOS_API = f"https://api.github.com/users/{GITHUB_USERNAME}/repos"

    def __init__(self, db: Optional[JobDatabase] = None, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL):
        self.db = db or JobDatabase()
        self.api_key = api_key
        self.model = model
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

    def fetch_live_github_projects(self) -> List[Dict[str, str]]:
        """Fetches public repositories from candidate's GitHub account."""
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.get(self.GITHUB_REPOS_API, headers={"User-Agent": "JobHunterBot"})
                if res.status_code == 200:
                    repos = res.json()
                    projects = []
                    for r in repos:
                        if not r.get("fork") and r.get("name") not in ("kicpir99", "inpost-reklamacja"):
                            projects.append({
                                "name": r.get("name"),
                                "url": r.get("html_url"),
                                "description": r.get("description") or "Repository",
                                "language": r.get("language") or "Python"
                            })
                    return projects
        except Exception as e:
            logger.debug(f"Could not fetch GitHub repos ({e}), falling back to CV portfolio.")

        # Fallback to static CV portfolio
        return [
            {
                "name": "BeatHub",
                "url": f"https://github.com/{self.GITHUB_USERNAME}/BeatHub",
                "description": "Platforma streamingowa audio (SPA UX / Hotwired Turbo), backend Django, PostgreSQL/SQLite, konteneryzacja Docker.",
                "language": "Python"
            },
            {
                "name": "KuzenBot",
                "url": f"https://github.com/{self.GITHUB_USERNAME}/KuzenBot",
                "description": "Wielowątkowa aplikacja analityczna desktopowa (PyQt6, QThread), asynchroniczne zapytania HTTP REST API, auto-updater.",
                "language": "Python"
            },
            {
                "name": "pasieka-wedrowna-usza",
                "url": f"https://github.com/{self.GITHUB_USERNAME}/pasieka-wedrowna-usza",
                "description": "Platforma e-commerce Headless z React, TypeScript, WooCommerce REST API i automatyzacją wdrożeń w Pythonie.",
                "language": "TypeScript / Python"
            }
        ]

    def generate(self, offer_query: str) -> Dict[str, Any]:
        """
        Locates the offer in SQLite and crafts a bespoke cover letter and LinkedIn pitch.
        """
        offer = self.db.find_offer_by_id_or_company(offer_query)
        if not offer:
            return {"error": f"Nie znaleziono oferty pasującej do zapytania: '{offer_query}'."}

        if not self.client:
            return {"error": "Brak skonfigurowanego GEMINI_API_KEY."}

        github_projects = self.fetch_live_github_projects()
        projects_context = "\n".join(
            f"- **{p['name']}** ({p['url']}): {p['description']} [Tech: {p['language']}]"
            for p in github_projects
        )

        prompt = f"""
Jesteś profesjonalnym mentorem inżynierii oprogramowania. Twoim zadaniem jest napisać **wybitny, inżynierski list motywacyjny** oraz **krótki pitch na LinkedIn** dla kandydata aplikującego na poniższe stanowisko.

DANE KANDYDATA:
- Imię i nazwisko: {CANDIDATE_PROFILE['name']} ({CANDIDATE_PROFILE['headline']})
- Doświadczenie: Poziom Junior / Staż. Zamiast wieloletniego stażu komercyjnego, kandydat wyróżnia się solidnymi, wdrożonymi projektami w portfolio, kulturą czystego kodu oraz ponad 4-letnim doświadczeniem inżynierskim/analitycznym (optymalizacja procesów, systemy ERP/CRM).
- GitHub: https://github.com/{self.GITHUB_USERNAME}
- Realne projekty w portfolio:
{projects_context}

DANE OFERTY PRACY:
- Stanowisko: {offer['title']}
- Firma: {offer['company']}
- Lokalizacja: {offer['location']}
- Widełki: {offer['salary']}
- URL: {offer['url']}
- Wymagania / technologie: {offer.get('requirements', 'Python')}
- Wstępna analiza: {offer.get('ai_summary', '')}

ZASADY TWORZENIA:
1. Pisz konkretnym językiem technicznym. UNIKAJ pustych banałów typu "jestem ambitny i szybko się uczę".
2. Połącz wymagania firmy z REALNYMI rozwiązaniami z projektów Kacpra (np. jeśli firma wymaga baz danych/Dockera -> powołaj się na BeatHub i optymalizację ORM w Django; jeśli REST API/asynchroniczności -> powołaj się na KuzenBot z QThread; jeśli fullstack/React -> powołaj się na Pasiekę Usza).
3. W treści listu podaj naturalnie 1-2 bezpośrednie linki markdown do konkretnych repozytoriów na GitHubie kandydata.
4. List powinien mieć 3-4 zwięzłe akapity (format gotowy do wysłania mailem lub przez formularz).
5. Wygeneruj także **"Krótki pitch na LinkedIn"** (maksymalnie 4-5 zdań do bezpośredniej wiadomości do rekrutera lub Tech Leada).

ZWRÓĆ WYŁĄCZNIE CZYSTY JSON:
{{
  "company": "{offer['company']}",
  "title": "{offer['title']}",
  "offer_url": "{offer['url']}",
  "cover_letter_markdown": "Pełna treść listu w formacie Markdown z nagłówkiem, danymi kontaktowymi i linkami",
  "linkedin_pitch": "Krótka, konkretna wiadomość do rekrutera na LinkedIn"
}}
"""

        response = None
        models_to_try = [self.model]
        for candidate in ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]:
            if candidate not in models_to_try:
                models_to_try.append(candidate)

        for current_model in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                )
                if response and response.text:
                    break
            except Exception as e:
                logger.warning(f"Cover letter generation on {current_model} failed ({e}), attempting next model...")

        if not response or not response.text:
            return {"error": "Wyczerpano limity lub wszystkie modele Gemini są chwilowo niedostępne."}

        try:
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:].strip()

            parsed = json.loads(raw)
            return parsed

        except Exception as e:
            logger.error(f"Failed to parse cover letter payload: {e}")
            return {"error": f"Błąd parsowania odpowiedzi od Gemini AI: {e}"}

