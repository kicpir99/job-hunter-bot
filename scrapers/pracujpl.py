import json
import logging
from typing import List, Optional
from curl_cffi import requests

from candidate_profile import CANDIDATE_PROFILE
from models import JobOffer
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class PracujPlScraper(BaseScraper):
    """Scraper pobierający oferty IT z portalu Pracuj.pl (obejmujący również TheProtocol)."""

    SEARCH_URL = "https://it.pracuj.pl/praca/python;kw/junior;et"

    @property
    def name(self) -> str:
        return "pracujpl"

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

            idx = r.text.find('__NEXT_DATA__')
            if idx == -1:
                logger.warning(f"[{self.name}] Nie znaleziono __NEXT_DATA__.")
                return []

            start = r.text.find('>', idx) + 1
            end = r.text.find('</script>', start)
            data = json.loads(r.text[start:end])

            queries = data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])
            raw_offers = []
            for q in queries:
                q_data = q.get("state", {}).get("data", {})
                if isinstance(q_data, dict) and "groupedOffers" in q_data:
                    raw_offers = q_data["groupedOffers"]
                    break

            logger.info(f"[{self.name}] Znaleziono {len(raw_offers)} surowych ogłoszeń.")

            for o in raw_offers:
                offer = self._parse_offer(o)
                if not offer:
                    continue

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
        sub_offers = o.get("offers", [])
        if not sub_offers:
            return None

        primary_sub = sub_offers[0]
        full_url = primary_sub.get("offerAbsoluteUri")
        if not full_url:
            return None

        offer_id = str(o.get("groupId") or o.get("commonOfferId") or full_url.split(",")[-1])
        title = o.get("jobTitle") or "Brak tytułu"
        company = o.get("companyName") or "Nieznana firma"

        # Lokalizacja i praca zdalna
        work_modes = o.get("workModes", [])
        is_remote = o.get("isRemoteWorkAllowed", False) or any("zdalna" in str(m).lower() for m in work_modes)
        workplace = primary_sub.get("displayWorkplace") or "Polska"
        location = "Zdalnie" if is_remote else workplace

        # Wynagrodzenie
        salary_str = o.get("salaryDisplayText") or None

        # Poziom
        levels = o.get("positionLevels", ["Junior"])

        # Technologie
        reqs = o.get("technologies", [])

        return JobOffer(
            id=offer_id,
            portal=self.name,
            title=title,
            company=company,
            url=full_url,
            seniority=levels,
            salary=salary_str,
            location=location,
            is_remote=is_remote,
            requirements=reqs
        )

