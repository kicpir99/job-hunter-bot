from analytics.market_report import MarketAnalytics
from storage.database import JobDatabase
from models import JobOffer


def test_market_analytics_aggregation(tmp_path):
    test_db = JobDatabase(db_path=tmp_path / "test_analytics.db")
    
    test_db.save_offer(
        JobOffer(
            id="offer-1",
            portal="nofluffjobs",
            title="Junior Python Dev",
            company="Company A",
            url="https://example.com/1",
            salary="8000 - 10000 PLN",
            location="Remote",
            is_remote=True,
            requirements=["Python", "FastAPI", "Docker"]
        )
    )

    analytics = MarketAnalytics(db=test_db)
    data = analytics.analyze()

    assert data["total_analyzed"] == 1
    assert data["remote_pct"] == 100.0
    assert data["avg_salary_min"] == 8000
    assert data["avg_salary_max"] == 10000
    assert len(data["top_technologies"]) == 3
