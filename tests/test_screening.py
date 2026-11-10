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

