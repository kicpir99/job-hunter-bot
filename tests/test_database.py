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


def test_database_cleanup(tmp_path):
    test_db_path = tmp_path / "test_jobs.db"
    db = JobDatabase(db_path=test_db_path)

    offer = JobOffer(
        id="old-1",
        portal="nofluffjobs",
        title="Python Dev",
        company="OldCorp",
        url="https://example.com",
    )
    db.save_offer(offer)

    # Artificially set created_at to 90 days ago
    with db._get_connection() as conn:
        conn.execute("UPDATE seen_offers SET created_at = datetime('now', '-90 days') WHERE id = 1")
        conn.commit()

    # Offer should still exist before cleanup
    assert db.is_seen("nofluffjobs", "old-1")

    # Cleanup with 60 days retention
    deleted = db.cleanup_old_offers(retention_days=60)
    assert deleted == 1
    assert not db.is_seen("nofluffjobs", "old-1")


def test_application_tracking(tmp_path):
    test_db_path = tmp_path / "test_jobs.db"
    db = JobDatabase(db_path=test_db_path)

    offer = JobOffer(
        id="app-1",
        portal="justjoin",
        title="Junior Backend Developer",
        company="StartupSp",
        url="https://justjoin.it/offers/app-1",
    )
    db.save_offer(offer)

    # Initial state
    assert len(db.get_applied_offers()) == 0

    # Mark as applied
    res = db.mark_as_applied("StartupSp")
    assert res is not None
    assert res["company"] == "StartupSp"

    applied = db.get_applied_offers()
    assert len(applied) == 1
    assert applied[0]["company"] == "StartupSp"
    assert applied[0]["applied_at"] is not None



