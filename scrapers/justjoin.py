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
    """Scraper extracting job postings from Just Join IT via Next.js RSC payload."""

    SEARCH_URL = "https://justjoin.it/job-offers/all-locations/python?experience-level=junior&experience-level=intern"
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
                logger.warning(f"[{self.name}] HTTP response status: {r.status_code}")
                return []

            chunks = re.findall(r'self\.__next_f\.push\(\[\d+,\s*"(.*?)"\]\)', r.text)
            full_text = "".join(chunks).replace('\\"', '"').replace('\\n', '\n')

            idx = full_text.find('{"offers":[')
            if idx == -1:
                logger.warning(f"[{self.name}] Offers payload block not found in DOM.")
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
                return []

            raw_offers = json.loads(full_text[start:end])
            logger.info(f"[{self.name}] Ingested {len(raw_offers)} raw postings.")

            for o in raw_offers:
                offer = self._parse_offer(o)
                if not offer or not self._is_location_valid(offer):
                    continue

                offers.append(offer)

            logger.info(f"[{self.name}] Filtered down to {len(offers)} matching offers.")

        except Exception as e:
            logger.error(f"[{self.name}] Error during offer ingestion: {e}")

        return offers

    def _is_location_valid(self, offer: JobOffer) -> bool:
        if offer.is_remote:
            return True
        loc_lower = offer.location.lower()
        allowed_cities = CANDIDATE_PROFILE["allowed_hybrid_onsite_cities"]
        return any(city in loc_lower for city in allowed_cities)

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

        reqs = o.get("requiredSkills", [])
        requirements = [r if isinstance(r, str) else r.get("name", "") for r in reqs if r] if isinstance(reqs, list) else []

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
