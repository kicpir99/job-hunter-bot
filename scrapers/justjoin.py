import json
import logging
import re
from typing import List, Optional
from curl_cffi import requests

from candidate_profile import CANDIDATE_PROFILE
from models import JobOffer
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class JustJoinScraper(BaseScraper):
    """Scraper pobierający oferty z portalu Just Join IT."""

    SEARCH_URL = "https://justjoin.it/job-offers/all-locations/python?experience-level=junior"
    OFFER_URL_PREFIX = "https://justjoin.it/offers/"

    @property
    def name(self) -> str:
        return "justjoin"

    def fetch_offers(self) -> List[JobOffer]:
        offers: List[JobOffer] = []
        try:
            r = requests.get(
                self.SEARCH_URL,
                impersonate="safari15_5",
                timeout=15
            )
            if r.status_code != 200:
                logger.warning(f"[{self.name}] Błąd odpowiedzi HTTP: {r.status_code}")
                return []

            # Wypakowanie danych z Next.js React Server Components (self.__next_f)
            chunks = re.findall(r'self\.__next_f\.push\(\[\d+,\s*"(.*?)"\]\)', r.text)
            full_text = "".join(chunks).replace('\\"', '"').replace('\\n', '\n')

            idx = full_text.find('{"offers":[')
            if idx == -1:
                logger.warning(f"[{self.name}] Nie znaleziono bloku 'offers' w odpowiedzi.")
                return []

            start = idx + len('{"offers":')
            depth, end = 0, -1
            for i in range(start, len(full_text)):
                if full_text[i] == '[':
                    depth += 1
                elif full_text[i] == ']':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break

            if end == -1:
                logger.warning(f"[{self.name}] Nie udało się domknąć tablicy JSON ofert.")
                return []

            raw_offers = json.loads(full_text[start:end])
            logger.info(f"[{self.name}] Znaleziono {len(raw_offers)} surowych ogłoszeń.")

            for o in raw_offers:
                offer = self._parse_offer(o)
                if not offer:
                    continue

                # Filtr lokalizacji
                if not self._is_location_valid(offer):
                    continue

                offers.append(offer)

            logger.info(f"[{self.name}] Po filtracji lokalizacji: {len(offers)} pasujących ofert.")

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

    def _parse_offer(self, o: dict) -> Optional[JobOffer]:
        slug = o.get("slug")
        if not slug:
            return None

        title = o.get("title") or o.get("body") or "Brak tytułu"
        company = o.get("companyName") or "Nieznana firma"
        full_url = f"{self.OFFER_URL_PREFIX}{slug}"

        city = o.get("city", "Polska")
        workplace_type = (o.get("workplaceType") or "").lower()
        is_remote = (workplace_type == "remote") or ("remote" in city.lower())
        location = "Zdalnie" if is_remote else city

        # Wynagrodzenie
        salary_str = None
        emp_types = o.get("employmentTypes", [])
        for emp in emp_types:
            f = emp.get("from")
            t = emp.get("to")
            curr = emp.get("currency", "PLN")
            etype = emp.get("type", "").upper()
            if f and t:
                salary_str = f"{int(f)} - {int(t)} {curr} ({etype})"
                break
            elif f:
                salary_str = f"od {int(f)} {curr} ({etype})"
                break
            elif t:
                salary_str = f"do {int(t)} {curr} ({etype})"
                break

        # Umiejętności
        reqs = o.get("requiredSkills", [])
        if isinstance(reqs, list):
            requirements = [r if isinstance(r, str) else r.get("name", "") for r in reqs if r]
        else:
            requirements = []

        return JobOffer(
            id=str(slug),
            portal=self.name,
            title=title,
            company=company,
            url=full_url,
            seniority=["Junior"],
            salary=salary_str,
            location=location,
            is_remote=is_remote,
            requirements=requirements
        )

