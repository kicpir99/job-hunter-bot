from abc import ABC, abstractmethod
from typing import List
from models import JobOffer


class BaseScraper(ABC):
    """Abstrakcyjna klasa bazowa dla scraperów portali pracy."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Zwraca unikalną nazwę portalu (np. 'nofluffjobs')."""
        pass

    @abstractmethod
    def fetch_offers(self) -> List[JobOffer]:
        """Pobiera i parsuje listę najnowszych ofert pracy spełniających kryteria."""
        pass

