import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import DATABASE_PATH
from models import JobOffer


class JobDatabase:
    """Zarządza lokalną bazą SQLite do deduplikacji i śledzenia statusu ofert."""

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._ensure_dir()
        self.init_db()

    def _ensure_dir(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Inicjalizuje schemat tabeli, jeśli jeszcze nie istnieje."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS seen_offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portal TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    url TEXT NOT NULL,
                    salary TEXT,
                    is_notified INTEGER DEFAULT 0,
                    ai_summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(portal, external_id)
                )
            """)
            conn.commit()

    def is_seen(self, portal: str, external_id: str) -> bool:
        """Sprawdza, czy oferta o danym ID z danego portalu została już wcześniej zapisana."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM seen_offers WHERE portal = ? AND external_id = ?",
                (portal, external_id)
            )
            return cursor.fetchone() is not None

    def save_offer(self, offer: JobOffer, is_notified: bool = False, ai_summary: Optional[str] = None):
        """Zapisuje nową ofertę w bazie danych."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO seen_offers 
                (portal, external_id, title, company, url, salary, is_notified, ai_summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                offer.portal,
                offer.id,
                offer.title,
                offer.company,
                offer.url,
                offer.salary or "Brak podanych widełek",
                1 if is_notified else 0,
                ai_summary,
                datetime.utcnow().isoformat()
            ))
            conn.commit()

    def mark_as_notified(self, portal: str, external_id: str):
        """Oznacza ofertę jako wysłaną w powiadomieniu."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE seen_offers SET is_notified = 1 WHERE portal = ? AND external_id = ?",
                (portal, external_id)
            )
            conn.commit()

    def get_stats(self) -> dict:
        """Zwraca podstawowe statystyki z bazy."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(is_notified) FROM seen_offers")
            row = cursor.fetchone()
            total = row[0] or 0
            notified = row[1] or 0
            return {"total_tracked": total, "total_notified": notified}

