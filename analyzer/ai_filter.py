import json
import logging
import time
from typing import Tuple, Optional
from config import GEMINI_API_KEY, GEMINI_MODEL
from candidate_profile import CANDIDATE_PROFILE
from models import JobOffer

logger = logging.getLogger(__name__)


class JobOfferAnalyzer:
    """Evaluates job offers against candidate profile using Gemini LLM and deterministic rules."""

    def __init__(self, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL):
        self.api_key = api_key
        self.model = model
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

    def evaluate_offer(self, offer: JobOffer) -> Tuple[bool, str]:
        """
        Screens an offer against constraints.
        Returns: (is_recommended: bool, summary_or_rejection_reason: str)
        """
        is_valid, reason = self._fast_heuristic_check(offer)
        if not is_valid:
            return False, reason

        if not self.client:
            return self._heuristic_fallback(offer)

        prompt = f"""
Jesteś doradcą rekrutacyjnym weryfikującym dopasowanie oferty pracy do profilu kandydata.

PROFIL KANDYDATA:
- Imię: {CANDIDATE_PROFILE['name']} ({CANDIDATE_PROFILE['headline']})
- Doświadczenie komercyjne: Poziom Junior / Staż (0 lat doświadczenia komercyjnego, dopuszczalne do 1 roku).
- Projekty portfolio: Django, FastAPI, Docker, PostgreSQL, React, TypeScript, AsyncIO, integracja modeli AI/LLM.
- Stack technologiczny: {', '.join(CANDIDATE_PROFILE['core_technologies'])}
- Lokalizacja: Praca w 100% zdalna (Remote) LUB praca stacjonarna/hybrydowa we Wrocławiu i najbliższych okolicach.
- Języki: Angielski B2, Polski C2 (ojczysty). Brak znajomości języka niemieckiego, francuskiego itp.
- Status studenta: Brak statusu studenta.

OFERTA PRACY DO OCENY:
- Tytuł: {offer.title}
- Firma: {offer.company}
- Poziom (seniority): {', '.join(offer.seniority)}
- Widełki: {offer.salary or 'Nie podano'}
- Lokalizacja: {offer.location} (Zdalnie: {offer.is_remote})
- Wymagane technologie: {', '.join(offer.requirements)}
- Treść ogłoszenia: {offer.description or 'Brak dodatkowego opisu'}

ZASADY WERYFIKACJI:
1. ODRZUĆ ofertę (is_recommended = false), jeśli:
   - Wymaga powyżej 1 roku doświadczenia komercyjnego (np. min. 2-3 lata, poziom Mid/Senior/Lead).
   - Rola nie jest programistyczna lub Python jest tylko marginalnym dodatkiem.
   - Wymaga pracy stacjonarnej/hybrydowej poza Wrocławiem (i brak opcji Remote).
   - Wymaga obowiązkowej znajomości języka innego niż polski i angielski.
2. STATUS STUDENTA:
   - Jeśli oferta bezwzględnie wymaga statusu studenta, oznacz requires_student = true.
3. DOPASOWANIE TECHNOLOGICZNE:
   - Wskaż technologie pokrywające się ze skillem kandydata.
   - Oceń stopień dopasowania: 'Wysokie', 'Średnie' lub 'Niskie'.

ZWRÓĆ WYŁĄCZNIE CZYSTY JSON:
{{
  "is_recommended": true/false,
  "rejection_reason": "Powód odrzucenia (lub null)",
  "requires_student": true/false,
  "match_score": "Wysokie / Średnie / Niskie",
  "matched_skills": ["Python", "FastAPI", "Docker"],
  "summary": "Zwięzłe 2 zdania podsumowania: specyfika roli, dopasowanie do portfolio i wskazówka do aplikacji."
}}
"""

        response = None
        for current_model in [self.model, "gemini-3.5-flash"]:
            try:
                response = self.client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                )
                if response and response.text:
                    break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    logger.warning("Rate limit encountered. Backing off briefly...")
                    time.sleep(4.0)
                else:
                    logger.warning(f"Model {current_model} call failed ({e}), attempting fallback...")

        if not response or not response.text:
            return self._heuristic_fallback(offer)

        try:
            raw_text = response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()

            parsed = json.loads(raw_text)
            is_rec = parsed.get("is_recommended", True)
            requires_student = parsed.get("requires_student", False)
            match_score = parsed.get("match_score", "Średnie")
            matched_skills = parsed.get("matched_skills", [])
            summary = parsed.get("summary", "")
            rejection_reason = parsed.get("rejection_reason")

            offer.requires_student = requires_student
            offer.match_score = match_score
            offer.matched_skills = matched_skills

            if not is_rec:
                return False, rejection_reason or "Oferta nie spełnia kryteriów kandydata."

            if requires_student and not CANDIDATE_PROFILE.get("include_student_offers_with_tag", True):
                return False, "Oferta odrzucona: wymaga statusu studenta."

            return True, summary

        except Exception as e:
            logger.warning(f"Failed to parse LLM structured response ({e}), using fallback.")
            return self._heuristic_fallback(offer)

    def _fast_heuristic_check(self, offer: JobOffer) -> Tuple[bool, str]:
        title_lower = offer.title.lower()

        for bad_role in CANDIDATE_PROFILE["blacklisted_roles"]:
            if bad_role in title_lower and "python" not in title_lower:
                return False, f"Odrzucono ze względu na profil: {bad_role}"

        all_text = (offer.title + " " + " ".join(offer.requirements)).lower()
        for dis_lang in CANDIDATE_PROFILE["disallowed_foreign_languages"]:
            if f"język {dis_lang}" in all_text or f"znajomość języka {dis_lang}" in all_text:
                return False, f"Odrzucono ze względu na wymóg języka obcego ({dis_lang})."

        return True, "OK"

    def _heuristic_fallback(self, offer: JobOffer) -> Tuple[bool, str]:
        matched = []
        for tech in ["Python", "Django", "FastAPI", "Flask", "PostgreSQL", "Docker", "React", "TypeScript", "SQL"]:
            if any(tech.lower() == req.lower() for req in offer.requirements):
                matched.append(tech)

        offer.matched_skills = matched
        offer.match_score = "Wysokie" if len(matched) >= 2 else "Średnie"
        summary = f"Wymagania pokrywające się z profilem: {', '.join(matched) if matched else 'Python'}."
        return True, summary
