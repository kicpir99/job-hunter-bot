"""
Profil kandydata: Kacper Łamasz - Junior Python / Backend Developer
Plik zawiera reguły i preferencje używane przez filtr regułowy oraz model AI (Gemini).
"""

CANDIDATE_PROFILE = {
    "name": "Kacper Łamasz",
    "headline": "Junior Python / Backend Developer",
    
    # 1. DOŚWIADCZENIE KOMERCYJNE
    "max_commercial_experience_years": 1.0,
    "accept_zero_experience": True,
    "highlight_portfolio_projects": True,
    
    # 2. PROFILE STANOWISK
    "target_roles": [
        "Python Developer",
        "Backend Developer (Python)",
        "Fullstack Developer (Python + React/TS)",
        "Junior AI / LLM Engineer",
        "Junior Data Engineer",
        "Stażysta / Praktykant Python",
        "Trainee Python"
    ],
    
    # Stanowiska, które natychmiast odrzucamy
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

    # 3. TECHNOLOGIE KANDYDATA
    "core_technologies": [
        "Python 3", "AsyncIO", "OOP",
        "Django", "Django REST Framework", "FastAPI", "Flask", "REST API",
        "PostgreSQL", "SQLite", "SQL",
        "Docker", "Git", "GitHub Actions", "Linux (Bash)",
        "Celery", "Redis",
        "TypeScript", "React", "Vite", "Tailwind CSS", "HTML5", "CSS3",
        "Integracja modeli AI / LLM", "PyQt6"
    ],

    # 4. LOKALIZACJA I TRYB PRACY
    # Praca 100% zdalna: Dopuszczalna z dowolnego miejsca (Polska i świat)
    "allow_remote": True,
    
    # Praca stacjonarna / hybrydowa: WYŁĄCZNIE Wrocław i okolice
    "allowed_hybrid_onsite_cities": [
        "wrocław", "wroclaw", "smolec", "bielany wrocławskie", 
        "bielany wroclawskie", "długołęka", "dlugoleka", "kobierzyce", "siechnice"
    ],

    # 5. JĘZYKI OBCE
    "languages": {
        "polish": "C2 (Ojczysty)",
        "english": "B2 (Swobodna komunikacja i dokumentacja)"
    },
    # Jeśli oferta wymaga innych języków obcych jako koniecznych (MUST) -> odrzuć
    "disallowed_foreign_languages": [
        "niemiecki", "german", "francuski", "french", "hiszpański", "spanish"
    ],

    # 6. STATUS STUDENTA
    # Kandydat NIE posiada statusu studenta.
    # Oferty wymagające statusu studenta oznaczamy specjalną etykietą ostrzegawczą
    "has_student_status": False,
    "include_student_offers_with_tag": True  # Jeśli True: przepuszcza z ostrzeżeniem [WYMÓG STUDENTA], jeśli False: odrzuca
}

