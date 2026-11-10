import json
import logging
from typing import Tuple
from config import GEMINI_API_KEY, GEMINI_MODEL
from candidate_profile import CANDIDATE_PROFILE
from models import JobOffer

logger = logging.getLogger(__name__)


class JobOfferAnalyzer:
    """Moduł AI oceniający dopasowanie oferty pod kątem profilu Kacpra Łamasza."""

    def __init__(self, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL):
        self.api_key = api_key
        self.model = model
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Nie udało się zainicjalizować klienta Gemini: {e}")

    def evaluate_offer(self, offer: JobOffer) -> Tuple[bool, str]:
        """
        Ocenia ofertę pracy pod kątem profilu kandydata.
        Zwraca: (is_recommended: bool, summary_or_reason: str)
        Wzbogaca również obiekt `offer` o pola: match_score, matched_skills, requires_student.
        """
        # 1. Szybki filtr regułowy (odrzucenie oczywistych pomyłek bez kosztu AI)
        is_valid, reason = self._fast_heuristic_check(offer)
        if not is_valid:
            return False, reason

        # 2. Jeśli brak klucza API Gemini, polegamy na analizie regułowej
        if not self.client:
            return self._heuristic_fallback(offer)

        # 3. Pełna analiza kontekstowa przez model AI (Gemini Flash)
        prompt = f"""
Jesteś osobistym doradcą rekrutacyjnym dla kandydata na programistę:

PROFIL KANDYDATA:
- Imię: {CANDIDATE_PROFILE['name']} ({CANDIDATE_PROFILE['headline']})
- Doświadczenie komercyjne: Stażysta / Junior (0 lat expa komercyjnego, dopuszczalne do 1 roku komercyjnego). Posiada solidne projekty portfolio (Django, FastAPI, Docker, PostgreSQL, React/TypeScript, PyQt6, asynchroniczność, modele AI/LLM).
- Technologie: {', '.join(CANDIDATE_PROFILE['core_technologies'])}
- Lokalizacja: Praca zdalna (dowolne miejsce) LUB praca stacjonarna/hybrydowa we Wrocławiu i najbliższych okolicach.
- Języki: Angielski B2, Polski C2 (ojczysty). Brak znajomości niemieckiego, francuskiego itp.
- Status studenta: Kandydat NIE POSIADA statusu studenta.

OFERTA PRACY DO OCENY:
- Tytuł: {offer.title}
- Firma: {offer.company}
- Poziom (seniority): {', '.join(offer.seniority)}
- Widełki: {offer.salary or 'Brak podanych'}
- Lokalizacja: {offer.location} (Zdalnie: {offer.is_remote})
- Wymagane technologie: {', '.join(offer.requirements)}
- Treść ogłoszenia: {offer.description or 'Brak dodatkowego opisu'}

ZADANIE DLA CIEBIE:
Oceń, czy ta oferta pracy jest odpowiednia dla kandydata wg poniższych zasad:
1. ODRZUĆ ofertę (is_recommended = false), jeśli:
   - Wymaga powyżej 1 roku twardego doświadczenia komercyjnego (np. min. 2-3 lata jako Junior/Mid).
   - Python NIE jest jednym z głównych języków (np. oferta na C++, Java, PHP z Pythonem tylko pobocznie).
   - Wymaga pracy stacjonarnej lub hybrydowej w innym mieście niż Wrocław i okolice (gdy brak opcji 100% Remote).
   - Wymaga obowiązkowej znajomości języka niemieckiego, francuskiego itp. (angielski B2 jest w porządku).
2. STATUS STUDENTA:
   - Sprawdź, czy oferta BEZWZGLĘDNIE wymaga statusu studenta (np. "tylko dla studentów", "umowa zlecenie dla studenta").
   - Jeśli tak, oznacz requires_student = true.
3. DOPASOWANIE TECHNOLOGICZNE:
   - Wypisz technologie z oferty, które pokrywają się ze skillem kandydata (np. Python, Django, FastAPI, Docker, PostgreSQL, React).
   - Oceń dopasowanie (match_score): "Wysokie", "Średnie" lub "Niskie".

Odpowiedz WYŁĄCZNIE w poprawnym formacie JSON:
{{
  "is_recommended": true/false,
  "rejection_reason": "Dlaczego odrzucono (jeśli is_recommended=false, w przeciwnym razie null)",
  "requires_student": true/false,
  "match_score": "Wysokie / Średnie / Niskie",
  "matched_skills": ["Python", "FastAPI", "Docker"],
  "summary": "Krótkie 2 zdania podsumowania po polsku: co to za projekt, dlaczego pasuje do kandydata i na co zwrócić uwagę przy aplikacji."
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
                    logger.warning(f"Osiągnięto limit zapytań (15/min). Chwilowe odczekanie...")
                    import time
                    time.sleep(4.0)
                else:
                    logger.warning(f"Model {current_model} napotkał problem ({e}), próbuję alternatywę...")

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

            # Wzbogacenie obiektu offer
            offer.requires_student = requires_student
            offer.match_score = match_score
            offer.matched_skills = matched_skills

            if not is_rec:
                return False, rejection_reason or "Oferta nie spełnia kryteriów kandydata."

            # Obsługa statusu studenta wg preferencji kandydata
            if requires_student and not CANDIDATE_PROFILE.get("include_student_offers_with_tag", True):
                return False, "Oferta odrzucona: wymaga statusu studenta."

            return True, summary

        except Exception as e:
            logger.warning(f"Błąd podczas parsowania odpowiedzi AI ({e}), używam analizy regułowej.")
            return self._heuristic_fallback(offer)

    def _fast_heuristic_check(self, offer: JobOffer) -> Tuple[bool, str]:
        """Szybkie reguły eliminacyjne sprawdzane jeszcze przed modelem AI."""
        title_lower = offer.title.lower()

        # 1. Czarna lista ról
        for bad_role in CANDIDATE_PROFILE["blacklisted_roles"]:
            if bad_role in title_lower and "python" not in title_lower:
                return False, f"Odrzucono ze względu na rolę: {bad_role}"

        # 2. Języki obce (jeśli w tytule lub tagach widnieje język niemiecki/francuski)
        all_text = (offer.title + " " + " ".join(offer.requirements)).lower()
        for dis_lang in CANDIDATE_PROFILE["disallowed_foreign_languages"]:
            if f"język {dis_lang}" in all_text or f"znajomość języka {dis_lang}" in all_text:
                return False, f"Odrzucono ze względu na wymóg języka obcego ({dis_lang})."

        return True, "OK"

    def _heuristic_fallback(self, offer: JobOffer) -> Tuple[bool, str]:
        """Klasyczny filtr regułowy używany, gdy Gemini API nie jest dostępne."""
        matched = []
        for tech in ["Python", "Django", "FastAPI", "Flask", "PostgreSQL", "Docker", "React", "TypeScript", "SQL"]:
            if any(tech.lower() == req.lower() for req in offer.requirements):
                matched.append(tech)

        offer.matched_skills = matched
        offer.match_score = "Wysokie" if len(matched) >= 2 else "Średnie"

        summary = f"Pasujące umiejętności z portfolio: {', '.join(matched) if matched else 'Python'}."
        return True, summary
