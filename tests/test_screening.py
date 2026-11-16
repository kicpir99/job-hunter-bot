from models import JobOffer
from analyzer.ai_filter import JobOfferAnalyzer


def test_heuristic_rejection_of_blacklisted_roles():
    analyzer = JobOfferAnalyzer()

    admin_offer = JobOffer(
        id="admin-1",
        portal="pracujpl",
        title="Administrator Systemów IT",
        company="AdminCorp",
        url="https://pracuj.pl/test",
        seniority=["Junior"],
        location="Wrocław",
        is_remote=False,
        requirements=["Linux", "Bash", "Networking"]
    )

    is_rec, reason = analyzer._fast_heuristic_check(admin_offer)
    assert not is_rec
    assert "administrator" in reason.lower()


def test_heuristic_pass_for_python_developer():
    analyzer = JobOfferAnalyzer()

    dev_offer = JobOffer(
        id="dev-1",
        portal="nofluffjobs",
        title="Junior Python Developer",
        company="CodeMasters",
        url="https://nofluffjobs.com/test",
        seniority=["Junior"],
        location="Remote",
        is_remote=True,
        requirements=["Python", "FastAPI", "Docker", "PostgreSQL"]
    )

    is_rec, reason = analyzer._fast_heuristic_check(dev_offer)
    assert is_rec
    assert reason == "OK"


def test_heuristic_rejection_of_commercial_experience_over_one_year():
    analyzer = JobOfferAnalyzer()

    exp_offer = JobOffer(
        id="mindpal-1",
        portal="nofluffjobs",
        title="Python Developer – Engineering Calculations",
        company="MindPal",
        url="https://nofluffjobs.com/test",
        seniority=["Junior"],
        location="Remote",
        is_remote=True,
        requirements=["Python", "QA"],
        description="We are looking for someone with 1–3 years of commercial experience with Python to join our calculations team."
    )

    is_rec, reason = analyzer._fast_heuristic_check(exp_offer)
    assert not is_rec
    assert "doświadczenie > 1 roku" in reason


def test_heuristic_rejection_of_senior_and_mid():
    analyzer = JobOfferAnalyzer()

    senior_offer = JobOffer(
        id="senior-1",
        portal="pracujpl",
        title="Senior Python Backend Developer",
        company="BigCorp",
        url="https://pracuj.pl/test",
        seniority=["Senior"],
        location="Remote",
        is_remote=True
    )
    is_rec, reason = analyzer._fast_heuristic_check(senior_offer)
    assert not is_rec
    assert "senior" in reason.lower()

    mid_offer = JobOffer(
        id="mid-1",
        portal="pracujpl",
        title="Mid Python Developer",
        company="MidCorp",
        url="https://pracuj.pl/test",
        seniority=["Mid"],
        location="Remote",
        is_remote=True
    )
    is_rec, reason = analyzer._fast_heuristic_check(mid_offer)
    assert not is_rec
    assert "mid" in reason.lower()


def test_heuristic_rejection_of_fluent_english_c2_and_degree():
    analyzer = JobOfferAnalyzer()

    toyota_like = JobOffer(
        id="toyota-1",
        portal="nofluffjobs",
        title="Infotainment Software Engineer / Graduate",
        company="Toyota Digital HUB",
        url="https://nofluffjobs.com/test",
        seniority=["Junior"],
        location="Wrocław",
        is_remote=False,
        requirements=["C++", "Python", "Rust"],
        description="Language Skills: Fluent in English (TME business language). Education: Master’s degree in Computer Science."
    )
    is_rec, reason = analyzer._fast_heuristic_check(toyota_like)
    assert not is_rec
    assert "fluent" in reason.lower() or "c1" in reason.lower()

    degree_only = JobOffer(
        id="deg-1",
        portal="pracujpl",
        title="Junior Python Developer",
        company="Corp",
        url="https://pracuj.pl/test",
        seniority=["Junior"],
        location="Remote",
        is_remote=True,
        requirements=["Python", "Django"],
        description="Wymagane wykształcenie wyższe informatyczne."
    )
    is_rec_deg, reason_deg = analyzer._fast_heuristic_check(degree_only)
    assert not is_rec_deg
    assert "wykształcenie wyższe" in reason_deg.lower()


def test_heuristic_allows_english_c1_for_python_role():
    analyzer = JobOfferAnalyzer()

    c1_offer = JobOffer(
        id="c1-1",
        portal="nofluffjobs",
        title="Junior Python Backend Developer",
        company="GoodCorp",
        url="https://nofluffjobs.com/test",
        seniority=["Junior"],
        location="Remote",
        is_remote=True,
        requirements=["Python", "FastAPI"],
        description="Required: English C1 level and experience with FastAPI."
    )
    is_rec, reason = analyzer._fast_heuristic_check(c1_offer)
    assert is_rec
    assert reason == "OK"


def test_heuristic_rejection_of_embedded_and_non_python_primary():
    analyzer = JobOfferAnalyzer()

    embedded_offer = JobOffer(
        id="emb-1",
        portal="nofluffjobs",
        title="Junior Embedded Software Engineer",
        company="AutoCorp",
        url="https://nofluffjobs.com/test",
        seniority=["Junior"],
        location="Wrocław",
        is_remote=False,
        requirements=["C++", "Rust", "Python"]
    )
    is_rec, reason = analyzer._fast_heuristic_check(embedded_offer)
    assert not is_rec
    assert "embedded" in reason.lower()


def test_heuristic_allows_python_or_other_language_choice():
    analyzer = JobOfferAnalyzer()

    dual_title_offer = JobOffer(
        id="dual-1",
        portal="nofluffjobs",
        title="Junior C++ / Python Developer",
        company="FlexCorp",
        url="https://nofluffjobs.com/test",
        seniority=["Junior"],
        location="Remote",
        is_remote=True,
        requirements=["Python", "C++"]
    )
    is_rec_title, reason_title = analyzer._fast_heuristic_check(dual_title_offer)
    assert is_rec_title
    assert reason_title == "OK"

    dual_desc_offer = JobOffer(
        id="dual-2",
        portal="pracujpl",
        title="Junior Software Engineer",
        company="FlexCorp",
        url="https://pracuj.pl/test",
        seniority=["Junior"],
        location="Wrocław",
        is_remote=False,
        requirements=["Python", "C++", "Git"],
        description="Wymagana znajomość jednego z języków: Python lub C++."
    )
    is_rec_desc, reason_desc = analyzer._fast_heuristic_check(dual_desc_offer)
    assert is_rec_desc
    assert reason_desc == "OK"



