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
