from typing import List, Optional
from pydantic import BaseModel, Field


class JobOffer(BaseModel):
    """Standardized representation of an aggregated job posting."""
    id: str = Field(description="Unique identifier of the offer on the source portal")
    portal: str = Field(description="Source portal identifier (e.g. nofluffjobs, justjoin)")
    title: str = Field(description="Job title")
    company: str = Field(description="Hiring company name")
    url: str = Field(description="Canonical URL to the job posting")
    seniority: List[str] = Field(default_factory=list, description="Target seniority levels")
    salary: Optional[str] = Field(default=None, description="Disclosed compensation range")
    location: str = Field(default="Polska", description="Primary location or Remote")
    is_remote: bool = Field(default=False, description="Flag indicating 100% remote availability")
    requirements: List[str] = Field(default_factory=list, description="Extracted required technologies")
    description: Optional[str] = Field(default=None, description="Full job description body")
    published_at: Optional[str] = Field(default=None, description="Publication timestamp")

    # Fields enriched by AI analysis
    requires_student: bool = Field(default=False, description="Whether student status is strictly mandated")
    match_score: Optional[str] = Field(default=None, description="Candidate alignment score")
    matched_skills: List[str] = Field(default_factory=list, description="Candidate skills matching the offer")
