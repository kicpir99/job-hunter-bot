import re
from typing import List, Optional
from pydantic import BaseModel, Field


def normalize_company(name: str) -> str:
    """Normalizes company names by stripping legal forms and punctuation for cross-location and cross-portal deduplication."""
    if not name:
        return ""
    n = name.lower()
    n = re.sub(r'\(poland\)', '', n)
    n = re.sub(r'sp[oó]łka z o\.?\s*o\.?', '', n)
    n = re.sub(r'sp\.\s*z\s*o\.?\s*o\.?', '', n)
    n = re.sub(r'sp\s*z\s*o\s*o', '', n)
    n = re.sub(r's\.a\.', '', n)
    n = re.sub(r'\bsa\b', '', n)
    n = re.sub(r'sp\.\s*k\.', '', n)
    n = re.sub(r'\bgmbh\b', '', n)
    n = re.sub(r'\bltd\.?\b', '', n)
    n = re.sub(r'[^\w\s]', '', n)
    return ' '.join(n.split())


def normalize_title(title: str) -> str:
    """Normalizes job titles by stripping contract types, remote tags, and noise for fuzzy deduplication."""
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r'\(b2b.*?\)', '', t)
    t = re.sub(r'\(uop.*?\)', '', t)
    t = re.sub(r'\(m/k\)', '', t)
    t = re.sub(r'\(k/m\)', '', t)
    t = re.sub(r'\(m/f/x\)', '', t)
    t = re.sub(r'\(f/m/x\)', '', t)
    t = re.sub(r'\(remote\)', '', t)
    t = re.sub(r'\(zdalnie\)', '', t)
    t = re.sub(r'[\-–—]\s*(b2b|remote|zdalnie).*', '', t)
    t = re.sub(r'[^\w\s]', '', t)
    return ' '.join(t.split())


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
