import json
import logging
from typing import List, Optional
import httpx

from config import TARGET_KEYWORDS, TARGET_CATEGORY
from candidate_profile import CANDIDATE_PROFILE
from models import JobOffer
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class BulldogJobScraper(BaseScraper):
    """Scraper wyciągający oferty z portalu BulldogJob (parsowanie stanu Next.js)."""

    BASE_URL = "https://bulldogjob.pl"
    SEARCH_URL = "https://bulldogjob.pl/companies/jobs/s/role,backend/experienceLevel,junior/language,python"

    @property
    def name(self) -> str:
        return "bulldogjob"

    def fetch_offers(self) -> List[JobOffer]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://bulldogjob.pl/"
        }

        offers: List[JobOffer] = []

        try:
            with httpx.Client(headers=headers, timeout=15.0, follow_redirects=True) as client:
                resp = client.get(self.SEARCH_URL)
                if resp.status_code != 200:
                    logger.warning(f"[{self.name}] Błąd odpowiedzi HTTP: {resp.status_code}")
                    return []

                idx = resp.text.find('__NEXT_DATA__')
                if idx == -1:
                    logger.warning(f"[{self.name}] Nie znaleziono obiektu __NEXT_DATA__ w HTML.")
                    return []

                start = resp.text.find('>', idx) + 1
                end = resp.text.find('</script>', start)
                data = json.loads(resp.text[start:end])
                
                raw_jobs = data.get("props", {}).get("pageProps", {}).get("jobs", [])
                logger.info(f"[{self.name}] Znaleziono {len(raw_jobs)} surowych ogłoszeń.")

                for j in raw_jobs:
                    offer = self._parse_job(j)
                    if not offer:
                        continue

                    # Weryfikacja lokalizacji (Remote lub Wrocław/okolice)
                    if not self._is_location_valid(offer):
                        continue

                    # Weryfikacja, czy w tagach lub tytule faktycznie jest Python
                    all_text = (offer.title + " " + " ".join(offer.requirements)).lower()
                    if "python" not in all_text:
                        continue

                    offers.append(offer)

                logger.info(f"[{self.name}] Po filtracji lokalizacji i Pythona: {len(offers)} unikalnych ofert.")

        except Exception as e:
            logger.error(f"[{self.name}] Błąd podczas pobierania ofert: {e}")

        return offers

    def _is_location_valid(self, offer: JobOffer) -> bool:
        if offer.is_remote:
            return True
        loc_lower = offer.location.lower()
        for city in CANDIDATE_PROFILE["allowed_hybrid_onsite_cities"]:
            if city in loc_lower:
                return True
        return False

    def _parse_job(self, j: dict) -> Optional[JobOffer]:
        job_id = j.get("id")
        if not job_id:
            return None

        title = j.get("position") or "Brak tytułu"
        company = j.get("company", {}).get("name") or "Nieznana firma"
        full_url = f"{self.BASE_URL}/companies/jobs/{job_id}"

        # Seniority
        exp = j.get("experienceLevel", "junior")
        seniority = [exp.capitalize()] if isinstance(exp, str) else ["Junior"]

        # Wynagrodzenie
        salary_str = None
        sal_data = j.get("denominatedSalaryLong")
        if sal_data and isinstance(sal_data, dict):
            money = sal_data.get("money")
            curr = sal_data.get("currency", "PLN")
            if money:
                salary_str = f"{money} {curr}"

        # Lokalizacja
        is_remote = bool(j.get("remote", False))
        city = j.get("city") or ("Zdalnie" if is_remote else "Polska")
        location = "Zdalnie" if is_remote else city

        # Tagi technologiczne
        requirements = j.get("technologyTags", [])

        return JobOffer(
            id=str(job_id),
            portal=self.name,
            title=title,
            company=company,
            url=full_url,
            seniority=seniority,
            salary=salary_str,
            location=location,
            is_remote=is_remote,
            requirements=requirements
        )

