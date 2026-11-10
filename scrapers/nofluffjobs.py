import logging
import re
from datetime import datetime
from typing import List, Optional
import httpx

from config import TARGET_KEYWORDS, TARGET_SENIORITY, TARGET_CATEGORY
from candidate_profile import CANDIDATE_PROFILE
from models import JobOffer
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class NoFluffJobsScraper(BaseScraper):
    """Scraper korzystający z wewnętrznego API serwisu NoFluffJobs z grupowaniem i filtrem lokalizacji."""

    SEARCH_URL = "https://nofluffjobs.com/api/search/posting?salaryCurrency=PLN&salaryPeriod=month&region=pl"
    JOB_URL_PREFIX = "https://nofluffjobs.com/pl/job/"
    POSTING_DETAILS_URL = "https://nofluffjobs.com/api/posting/"

    @property
    def name(self) -> str:
        return "nofluffjobs"

    def fetch_offers(self) -> List[JobOffer]:
        seniorities = ",".join(TARGET_SENIORITY)
        raw_search = f"{TARGET_KEYWORDS} category={TARGET_CATEGORY} seniority={seniorities}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Referer": "https://nofluffjobs.com/pl"
        }

        payload = {"rawSearch": raw_search}

        offers: List[JobOffer] = []
        grouped: dict[str, JobOffer] = {}

        try:
            with httpx.Client(headers=headers, timeout=15.0) as client:
                response = client.post(self.SEARCH_URL, json=payload)
                response.raise_for_status()
                data = response.json()

                postings = data.get("postings", [])
                logger.info(f"[{self.name}] Znaleziono {len(postings)} surowych ogłoszeń.")

                for p in postings:
                    offer = self._parse_posting_summary(p)
                    if not offer:
                        continue

                    # Sprawdzenie wstępnego filtra lokalizacji w Pythonie
                    if not self._is_location_valid(offer):
                        continue

                    # Klucz deduplikacji: firma + tytuł
                    group_key = f"{offer.company.lower().strip()}_{offer.title.lower().strip()}"

                    if group_key not in grouped:
                        grouped[group_key] = offer
                    else:
                        existing = grouped[group_key]
                        if offer.is_remote and not existing.is_remote:
                            grouped[group_key] = offer

                offers = list(grouped.values())
                logger.info(f"[{self.name}] Po scaleniu i filtracji lokalizacji: {len(offers)} unikalnych ofert. Pobieranie szczegółów...")

                # Pobranie szczegółów tylko dla unikalnych ofert
                for o in offers:
                    self._populate_offer_details(o, client)

        except Exception as e:
            logger.error(f"[{self.name}] Błąd podczas pobierania ofert: {e}")

        return offers

    def _is_location_valid(self, offer: JobOffer) -> bool:
        """
        Sprawdza regułę lokalizacji:
        - Praca 100% zdalna (Remote) jest zawsze akceptowana.
        - Praca stacjonarna / hybrydowa musi dotyczyć Wrocławia i okolic.
        """
        if offer.is_remote:
            return True

        location_lower = offer.location.lower()
        allowed_cities = CANDIDATE_PROFILE["allowed_hybrid_onsite_cities"]
        for city in allowed_cities:
            if city in location_lower:
                return True

        logger.info(f"[{self.name}] Odrzucono ofertę poza Wrocławiem bez opcji Remote: {offer.title} ({offer.location})")
        return False

    def _parse_posting_summary(self, p: dict) -> Optional[JobOffer]:
        offer_id = p.get("id") or p.get("url")
        if not offer_id:
            return None

        title = p.get("title", "Brak tytułu")
        company = p.get("name", "Nieznana firma")
        url_slug = p.get("url", offer_id)
        full_url = f"{self.JOB_URL_PREFIX}{url_slug}"

        # Parsowanie poziomu doświadczenia
        seniority = p.get("seniority", [])
        if isinstance(seniority, str):
            seniority = [seniority]

        # Parsowanie wynagrodzenia
        salary_str = None
        sal = p.get("salary")
        if sal and isinstance(sal, dict):
            s_from = sal.get("from")
            s_to = sal.get("to")
            currency = sal.get("currency", "PLN")
            s_type = sal.get("type", "").upper()
            if s_from and s_to:
                salary_str = f"{int(s_from)} - {int(s_to)} {currency} ({s_type})"
            elif s_from:
                salary_str = f"od {int(s_from)} {currency} ({s_type})"
            elif s_to:
                salary_str = f"do {int(s_to)} {currency} ({s_type})"

        # Lokalizacja i praca zdalna
        location_data = p.get("location", {})
        is_remote = p.get("fullyRemote", False) or location_data.get("fullyRemote", False)
        
        cities = []
        for place in location_data.get("places", []):
            city = place.get("city")
            if city and city not in cities:
                cities.append(city)

        if is_remote and "Remote" not in cities:
            cities.insert(0, "Zdalnie")

        location = ", ".join(cities[:3]) if cities else ("Zdalnie" if is_remote else "Polska")

        # Wymagania / technologie z kafelków
        requirements = []
        tiles = p.get("tiles", {}).get("values", [])
        for tile in tiles:
            val = tile.get("value")
            if val and val not in requirements:
                requirements.append(val)

        # Data publikacji
        published_at = None
        posted_ts = p.get("posted") or p.get("renewed")
        if posted_ts:
            try:
                published_at = datetime.fromtimestamp(posted_ts / 1000.0).strftime("%Y-%m-%d %H:%M")
            except Exception:
                published_at = None

        return JobOffer(
            id=str(offer_id),
            portal=self.name,
            title=title,
            company=company,
            url=full_url,
            seniority=seniority,
            salary=salary_str,
            location=location,
            is_remote=is_remote,
            requirements=requirements,
            published_at=published_at
        )

    def _populate_offer_details(self, offer: JobOffer, client: httpx.Client):
        """Pobiera pełny opis i wymagania dla wyselekcjonowanej oferty."""
        url_slug = offer.url.split("/")[-1]
        try:
            detail_res = client.get(f"{self.POSTING_DETAILS_URL}{url_slug}", timeout=5.0)
            if detail_res.status_code == 200:
                det = detail_res.json()
                req_obj = det.get("requirements", {})
                raw_desc = req_obj.get("description", "")
                clean_desc = re.sub(r"<[^>]+>", " ", raw_desc)
                offer.description = " ".join(clean_desc.split())
                
                # Dodatkowe technologie z sekcji musts/nices jeśli dostępne
                for must in req_obj.get("musts", []):
                    v = must.get("value")
                    if v and v not in offer.requirements:
                        offer.requirements.append(v)
        except Exception as e:
            logger.debug(f"Nie udało się pobrać szczegółów dla {offer.id}: {e}")
