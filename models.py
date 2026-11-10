from typing import List, Optional
from pydantic import BaseModel, Field


class JobOffer(BaseModel):
    """Reprezentuje pojedynczą ofertę pracy w ujednoliconym formacie."""
    id: str = Field(description="Unikalny identyfikator oferty na danym portalu")
    portal: str = Field(description="Nazwa portalu (np. nofluffjobs)")
    title: str = Field(description="Tytuł stanowiska")
    company: str = Field(description="Nazwa firmy")
    url: str = Field(description="Bezpośredni link do oferty")
    seniority: List[str] = Field(default_factory=list, description="Poziom zaawansowania (np. Junior, Trainee)")
    salary: Optional[str] = Field(default=None, description="Widełki płacowe lub informacja o braku")
    location: str = Field(default="Polska", description="Lokalizacja (miasto lub Remote)")
    is_remote: bool = Field(default=False, description="Czy praca w 100% zdalna")
    requirements: List[str] = Field(default_factory=list, description="Kluczowe technologie / wymagania")
    description: Optional[str] = Field(default=None, description="Pełny opis stanowiska")
    published_at: Optional[str] = Field(default=None, description="Data publikacji oferty")

    # Pola wzbogacane przez analizator AI
    requires_student: bool = Field(default=False, description="Czy oferta bezwzględnie wymaga statusu studenta")
    match_score: Optional[str] = Field(default=None, description="Stopień dopasowania do profilu kandydata (np. Wysokie / Średnie)")
    matched_skills: List[str] = Field(default_factory=list, description="Umiejętności kandydata pasujące do oferty")
