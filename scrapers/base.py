from abc import ABC, abstractmethod
from typing import List
from models import JobOffer


class BaseScraper(ABC):
    """Abstract interface for portal scrapers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns portal identifier."""
        pass

    @abstractmethod
    def fetch_offers(self) -> List[JobOffer]:
        """Fetches and parses matching postings into JobOffer domain models."""
        pass
