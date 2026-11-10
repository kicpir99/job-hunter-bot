import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from config import DATABASE_PATH
from models import JobOffer


class JobDatabase:
    """Manages SQLite storage for deduplication, state tracking, and analytical reporting."""

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._ensure_dir()
        self.init_db()

    def _ensure_dir(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initializes database schema, indexes, and applies automatic migrations."""
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
                    location TEXT DEFAULT 'Polska',
                    is_remote INTEGER DEFAULT 0,
                    requirements TEXT DEFAULT '[]',
                    is_notified INTEGER DEFAULT 0,
                    ai_summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(portal, external_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_seen_portal_id ON seen_offers (portal, external_id)")

            # Migration: Ensure location, is_remote, and requirements columns exist in legacy databases
            cursor.execute("PRAGMA table_info(seen_offers)")
            existing_cols = [row[1] for row in cursor.fetchall()]
            if "location" not in existing_cols:
                cursor.execute("ALTER TABLE seen_offers ADD COLUMN location TEXT DEFAULT 'Polska'")
            if "is_remote" not in existing_cols:
                cursor.execute("ALTER TABLE seen_offers ADD COLUMN is_remote INTEGER DEFAULT 0")
            if "requirements" not in existing_cols:
                cursor.execute("ALTER TABLE seen_offers ADD COLUMN requirements TEXT DEFAULT '[]'")

            conn.commit()

    def is_seen(self, portal: str, external_id: str) -> bool:
        """Checks whether a given offer has already been processed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM seen_offers WHERE portal = ? AND external_id = ?",
                (portal, external_id)
            )
            return cursor.fetchone() is not None

    def save_offer(self, offer: JobOffer, is_notified: bool = False, ai_summary: Optional[str] = None) -> None:
        """Persists a new job offer record with its metadata."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO seen_offers 
                (portal, external_id, title, company, url, salary, location, is_remote, requirements, is_notified, ai_summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                offer.portal,
                offer.id,
                offer.title,
                offer.company,
                offer.url,
                offer.salary or "Brak podanych widełek",
                offer.location,
                1 if offer.is_remote else 0,
                json.dumps(offer.requirements),
                1 if is_notified else 0,
                ai_summary,
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()

    def mark_as_notified(self, portal: str, external_id: str) -> None:
        """Updates offer dispatch status to notified."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE seen_offers SET is_notified = 1 WHERE portal = ? AND external_id = ?",
                (portal, external_id)
            )
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Calculates tracking metrics and breakdown by portal."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(is_notified), 0) FROM seen_offers")
            row = cursor.fetchone()
            total = row[0] or 0
            notified = row[1] or 0

            cursor.execute("SELECT portal, COUNT(*) FROM seen_offers GROUP BY portal")
            by_portal = {r[0]: r[1] for r in cursor.fetchall()}

            return {
                "total_tracked": total,
                "total_notified": notified,
                "by_portal": by_portal
            }

    def get_recent_notified_offers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns the most recent offers dispatched to the candidate."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, portal, external_id, title, company, url, salary, location, is_remote, requirements, ai_summary, created_at
                FROM seen_offers
                WHERE is_notified = 1
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def find_offer_by_id_or_company(self, query: str) -> Optional[Dict[str, Any]]:
        """Finds an offer by numeric DB id, external_id slug, or company name substring."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # If query is digit, try by primary key
            if query.isdigit():
                cursor.execute("SELECT * FROM seen_offers WHERE id = ?", (int(query),))
                res = cursor.fetchone()
                if res:
                    return dict(res)

            # Try by exact external_id
            cursor.execute("SELECT * FROM seen_offers WHERE external_id = ?", (query,))
            res = cursor.fetchone()
            if res:
                return dict(res)

            # Try by company or title substring
            cursor.execute("""
                SELECT * FROM seen_offers 
                WHERE company LIKE ? OR title LIKE ?
                ORDER BY is_notified DESC, id DESC
                LIMIT 1
            """, (f"%{query}%", f"%{query}%"))
            res = cursor.fetchone()
            return dict(res) if res else None

    def get_all_offers(self) -> List[Dict[str, Any]]:
        """Retrieves all tracked offers for analytical aggregation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM seen_offers")
            return [dict(r) for r in cursor.fetchall()]

    def cleanup_old_offers(self, retention_days: int = 60) -> int:
        """Purges vacancies older than retention_days to maintain relevance and compact size."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM seen_offers WHERE created_at < datetime('now', ?)",
                (f"-{retention_days} days",)
            )
            deleted = cursor.rowcount
            conn.commit()

        if deleted > 0:
            vacuum_conn = self._get_connection()
            try:
                vacuum_conn.isolation_level = None
                vacuum_conn.execute("VACUUM")
            finally:
                vacuum_conn.close()

        return deleted
