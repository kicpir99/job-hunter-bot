import json
import logging
import re
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
                    time.sleep(2.0)
                    break
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    logger.warning("Rate limit encountered. Backing off 6s...")
                    time.sleep(6.0)
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
        """
        Fast deterministic screening for seniority, years of experience, blacklisted roles, and language requirements.
        Prevents wasting LLM tokens on obviously mismatched postings.
        """
        title_lower = offer.title.lower()
        sen_text = " ".join(offer.seniority).lower()
        combined_sen = f"{title_lower} {sen_text}"

        has_junior = any(k in combined_sen for k in ["junior", "trainee", "intern", "staż", "staz", "praktyk"])

        # 1. Definite Senior / Lead / Principal / Architect exclusions
        SENIOR_KEYWORDS = [
            r"\bsenior\b", r"\blead\b", r"\bprincipal\b", r"\barchitect\b",
            r"\bexpert\b", r"\bstaff\b", r"\bmanager\b", r"\bkierownik\b",
            r"\bdyrektor\b", r"\bhead\s+of\b", r"\bstarszy\b"
        ]
        for pat in SENIOR_KEYWORDS:
            if re.search(pat, combined_sen):
                return False, "Odrzucono automatycznie: rola Senior / Lead / Architect."

        # 2. Mid / Regular exclusions (unless junior is explicitly mentioned)
        MID_KEYWORDS = [r"\bmid\b", r"\bmiddle\b", r"\bregular\b", r"\bsamodzielny\b"]
        if not has_junior:
            for pat in MID_KEYWORDS:
                if re.search(pat, combined_sen):
                    return False, "Odrzucono automatycznie: rola Mid / Regular."

        # 3. Deterministic Regex for Years of Commercial Experience in description & requirements
        desc_and_reqs = f"{offer.description or ''} {' '.join(offer.requirements)}".lower()

        EXPERIENCE_EXCLUDE_PATTERNS = [
            # 1-3 years, 2-4 years, 3-5 lat
            r'(?:[1-9]\s*[\-–—]\s*[2-9]|[2-9]\+?)\s*(?:years?|lat|lata|roku|rok)\b',
            # min / minimum / co najmniej 2 lata / at least 2 years
            r'(?:min\.?|minimum|co\s+najmniej|przynajmniej|at\s+least)\s*[2-9]\s*(?:years?|lat|lata|roku|rok)\b',
            # commercial experience / doświadczenia komercyjnego
            r'(?:commercial\s+experience|do[sś]wiadczeni[ae]\s+komercyjn[a-z]*)\s*[:\-–]?\s*(?:min\.?|minimum)?\s*(?:[1-9]\s*[\-–—]\s*[2-9]|[2-9]\+?)\s*(?:years?|lat|lata|roku|rok)?\b',
            # 2+ years of commercial
            r'(?:[1-9]\s*[\-–—]\s*[2-9]|[2-9]\+?)\s*(?:years?|lat|lata)?\s*(?:of\s+)?(?:commercial\s+experience|do[sś]wiadczenia\s+komercyjnego)',
        ]

        for pat in EXPERIENCE_EXCLUDE_PATTERNS:
            match = re.search(pat, desc_and_reqs)
            if match:
                matched_snippet = match.group(0)
                if not re.search(r'0\s*[\-–—]\s*[12]', matched_snippet):
                    return False, f"Odrzucono automatycznie: wymagane doświadczenie > 1 roku ('{matched_snippet}')."

        # 4. Role blacklist
        for bad_role in CANDIDATE_PROFILE.get("blacklisted_roles", []):
            if bad_role in title_lower and "python" not in title_lower:
                return False, f"Odrzucono ze względu na profil: {bad_role}"

        # 5. Language requirements
        all_text = f"{title_lower} {' '.join(offer.requirements).lower()} {offer.description or ''}".lower()
        for dis_lang in CANDIDATE_PROFILE.get("disallowed_foreign_languages", []):
            if f"język {dis_lang}" in all_text or f"znajomość języka {dis_lang}" in all_text or f"{dis_lang} b2" in all_text or f"{dis_lang} c1" in all_text:
                return False, f"Odrzucono ze względu na wymóg języka obcego ({dis_lang})."

        return True, "OK"

    def _heuristic_fallback(self, offer: JobOffer) -> Tuple[bool, str]:
        """
        Conservative fallback used ONLY when LLM API is unavailable.
        Strictly requires explicit Junior/Intern indicators to avoid leaking ambiguous postings.
        """
        is_ok, reason = self._fast_heuristic_check(offer)
        if not is_ok:
            return False, reason

        title_and_sen = (offer.title + " " + " ".join(offer.seniority)).lower()
        is_explicit_entry = any(k in title_and_sen for k in ["junior", "trainee", "intern", "staż", "staz", "praktyk"])

        if not is_explicit_entry:
            return False, "Tryb awaryjny (brak limitu AI): odrzucono ofertę bez jednoznacznego oznaczenia Junior/Staż."

        matched = []
        for tech in ["Python", "Django", "FastAPI", "Flask", "PostgreSQL", "Docker", "React", "TypeScript", "SQL"]:
            if any(tech.lower() == req.lower() for req in offer.requirements):
                matched.append(tech)

        offer.matched_skills = matched
        offer.match_score = "Wysokie" if len(matched) >= 2 else "Średnie"
        summary = f"Wymagania pokrywające się z profilem: {', '.join(matched) if matched else 'Python'}."
        return True, summary
