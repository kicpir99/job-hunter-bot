"""Candidate profile definition and screening constraints."""

CANDIDATE_PROFILE = {
    "name": "Kacper Łamasz",
    "headline": "Junior Python / Backend Developer",
    
    # Experience thresholds
    "max_commercial_experience_years": 1.0,
    "accept_zero_experience": True,
    
    # Target positions
    "target_roles": [
        "Python Developer",
        "Backend Developer (Python)",
        "Fullstack Developer (Python + React/TS)",
        "Junior AI / LLM Engineer",
        "Junior Data Engineer",
        "Stażysta / Praktykant Python",
        "Trainee Python"
    ],
    
    # Blacklisted roles
    "blacklisted_roles": [
        "administrator",
        "devops engineer",
        "manual tester",
        "qa engineer",
        "helpdesk",
        "support",
        "c++ developer",
        "java developer",
        ".net developer",
        "php developer",
        "scrum master",
        "product owner"
    ],

    # Core tech stack
    "core_technologies": [
        "Python 3", "AsyncIO", "OOP",
        "Django", "Django REST Framework", "FastAPI", "Flask", "REST API",
        "PostgreSQL", "SQLite", "SQL",
        "Docker", "Git", "GitHub Actions", "Linux (Bash)",
        "Celery", "Redis",
        "TypeScript", "React", "Vite", "Tailwind CSS", "HTML5", "CSS3",
        "AI / LLM Integration", "PyQt6"
    ],

    # Work mode & locations
    "allow_remote": True,
    "allowed_hybrid_onsite_cities": [
        "wrocław", "wroclaw", "smolec", "bielany wrocławskie", 
        "bielany wroclawskie", "długołęka", "dlugoleka", "kobierzyce", "siechnice"
    ],

    # Languages
    "languages": {
        "polish": "C2 (Native)",
        "english": "B2"
    },
    "disallowed_foreign_languages": [
        "niemiecki", "german", "francuski", "french", "hiszpański", "spanish"
    ],

    # Student requirements
    "has_student_status": False,
    "include_student_offers_with_tag": True
}
