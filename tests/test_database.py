from storage.database import JobDatabase
from models import JobOffer


def test_database_deduplication(tmp_path):
    test_db_path = tmp_path / "test_jobs.db"
    db = JobDatabase(db_path=test_db_path)

    offer = JobOffer(
        id="test-123",
        portal="nofluffjobs",
        title="Junior Python Developer",
        company="TechCorp",
        url="https://nofluffjobs.com/job/test-123",
        seniority=["Junior"],
        location="Remote",
        is_remote=True
    )

    assert not db.is_seen("nofluffjobs", "test-123")
    db.save_offer(offer, is_notified=True, ai_summary="Test match")
    assert db.is_seen("nofluffjobs", "test-123")

    stats = db.get_stats()
    assert stats["total_tracked"] == 1
    assert stats["total_notified"] == 1
    assert stats["by_portal"].get("nofluffjobs") == 1

