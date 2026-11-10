import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple
from storage.database import JobDatabase

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


class MarketAnalytics:
    """Analyzes ingested job vacancies to derive market intelligence for Junior Python roles."""

    def __init__(self, db: JobDatabase | None = None):
        self.db = db or JobDatabase()
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def analyze(self) -> Dict[str, Any]:
        """Performs statistical aggregation over tracked vacancies."""
        offers = self.db.get_all_offers()
        total_offers = len(offers)
        if total_offers == 0:
            return {"error": "No vacancies currently recorded in database."}

        # 1. Technology Frequency Analysis
        tech_counter: Counter = Counter()
        for o in offers:
            reqs_raw = o.get("requirements", "[]")
            try:
                reqs = json.loads(reqs_raw) if isinstance(reqs_raw, str) else reqs_raw
            except Exception:
                reqs = []

            for tech in reqs:
                norm = self._normalize_tech(tech)
                if norm:
                    tech_counter[norm] += 1

        top_techs = [
            (tech, count, round((count / total_offers) * 100, 1))
            for tech, count in tech_counter.most_common(12)
        ]

        # 2. Work Mode Distribution
        remote_count = sum(1 for o in offers if o.get("is_remote", 0) == 1)
        hybrid_onsite_count = total_offers - remote_count
        remote_pct = round((remote_count / total_offers) * 100, 1)

        # 3. Salary Disclosures & Ranges
        salary_offers = [o for o in offers if o.get("salary") and "brak" not in str(o.get("salary")).lower()]
        disclosed_pct = round((len(salary_offers) / total_offers) * 100, 1)

        extracted_mins: List[int] = []
        extracted_maxs: List[int] = []
        for o in salary_offers:
            sal_str = o.get("salary", "")
            raw_nums = re.findall(r"\b\d{1,3}(?:[\s\xa0]*\d{3})*\b", sal_str)
            numbers = []
            for n in raw_nums:
                digits = re.sub(r"[^\d]", "", n)
                if digits:
                    val = int(digits)
                    if 1000 <= val <= 100000:
                        numbers.append(val)

            if len(numbers) >= 2:
                extracted_mins.append(min(numbers[:2]))
                extracted_maxs.append(max(numbers[:2]))
            elif len(numbers) == 1:
                extracted_mins.append(numbers[0])

        avg_min = int(sum(extracted_mins) / len(extracted_mins)) if extracted_mins else 0
        avg_max = int(sum(extracted_maxs) / len(extracted_maxs)) if extracted_maxs else 0

        # 4. Portal Breakdown
        portal_counts = Counter(o.get("portal", "unknown") for o in offers)

        return {
            "total_analyzed": total_offers,
            "top_technologies": top_techs,
            "remote_pct": remote_pct,
            "remote_count": remote_count,
            "hybrid_onsite_count": hybrid_onsite_count,
            "salary_disclosed_pct": disclosed_pct,
            "avg_salary_min": avg_min,
            "avg_salary_max": avg_max,
            "portal_distribution": dict(portal_counts),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        }

    def _normalize_tech(self, name: str) -> str:
        clean = name.strip()
        lower = clean.lower()
        if lower in ("py", "python3", "python 3"):
            return "Python"
        if lower in ("django rest framework", "drf"):
            return "Django REST Framework"
        if lower in ("postgres", "postgresql", "psql"):
            return "PostgreSQL"
        if lower in ("fast api", "fastapi"):
            return "FastAPI"
        if lower in ("docker", "containerization"):
            return "Docker"
        if lower in ("git", "github", "gitlab"):
            return "Git"
        if lower in ("rest", "rest api", "restful"):
            return "REST API"
        if lower in ("aws", "amazon web services"):
            return "AWS"
        if lower in ("react", "react.js", "reactjs"):
            return "React"
        if lower in ("ts", "typescript"):
            return "TypeScript"
        if lower in ("linux", "bash"):
            return "Linux/Bash"
        if lower in ("sql", "relational databases"):
            return "SQL"
        return clean.capitalize() if len(clean) > 2 else clean.upper()

    def generate_markdown_report(self) -> str:
        """Generates a structured analytical report and writes it to disk."""
        data = self.analyze()
        if "error" in data:
            return data["error"]

        report_lines = [
            f"# 📊 Polish IT Market Intelligence Report — Junior Python Roles",
            f"*Generated on: {data['generated_at']} | Analyzed Vacancies: {data['total_analyzed']}*",
            "",
            "## 🛠 Most In-Demand Technologies (Junior Python Vacancies)",
            "| Technology | Frequency | Market Share (%) | Relative Demand Bar |",
            "| :--- | :---: | :---: | :--- |"
        ]

        for tech, count, pct in data["top_technologies"]:
            bar_len = int(pct / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            report_lines.append(f"| **{tech}** | {count} | {pct}% | `{bar}` |")

        report_lines.extend([
            "",
            "## 💼 Work Mode Distribution",
            f"* **100% Remote:** {data['remote_pct']}% ({data['remote_count']} vacancies)",
            f"* **Hybrid / On-site (Wrocław focus):** {round(100 - data['remote_pct'], 1)}% ({data['hybrid_onsite_count']} vacancies)",
            "",
            "## 💰 Compensation Benchmarks (Disclosed Salaries)",
            f"* **Salary Transparency Rate:** {data['salary_disclosed_pct']}% of tracked postings disclose salary ranges.",
            f"* **Average Disclosed Minimum:** ~{data['avg_salary_min']:,} PLN",
            f"* **Average Disclosed Maximum:** ~{data['avg_salary_max']:,} PLN",
            "",
            "## 🌐 Data Sources & Ingestion Coverage",
        ])

        for portal, count in data["portal_distribution"].items():
            report_lines.append(f"* **{portal.upper()}:** {count} postings ingested")

        content = "\n".join(report_lines)
        output_file = REPORTS_DIR / "market_insights.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        return content

    def generate_discord_embed(self) -> Dict[str, Any]:
        """Creates a Discord Embed visualization of the market report."""
        data = self.analyze()
        if "error" in data:
            return {"title": "Błąd analityki", "description": data["error"], "color": 0xe74c3c}

        tech_text = "\n".join(
            f"• **{t}**: `{pct}%` rynkowych ofert"
            for t, _, pct in data["top_technologies"][:6]
        )

        fields = [
            {"name": "🔥 Top technologie (Junior)", "value": tech_text, "inline": False},
            {"name": "🏠 Tryb pracy", "value": f"• **Zdalnie:** `{data['remote_pct']}%`\n• **Hybryda/Biuro:** `{round(100-data['remote_pct'], 1)}%`", "inline": True},
            {"name": "💰 Średnie widełki", "value": f"• **Min:** ~`{data['avg_salary_min']:,} PLN`\n• **Max:** ~`{data['avg_salary_max']:,} PLN`", "inline": True},
        ]

        portals_str = ", ".join(f"{p.upper()}: `{c}`" for p, c in data["portal_distribution"].items())
        fields.append({"name": "🌐 Pokrycie portali", "value": portals_str, "inline": False})

        return {
            "title": f"📊 Raport Analityczny Rynku IT — Junior Python",
            "description": f"Analiza statystyczna na próbie **{data['total_analyzed']}** zebranych ofert pracy.",
            "color": 0x9b59b6,
            "fields": fields,
            "footer": {
                "text": f"Aktualizacja: {data['generated_at']} • Wygenerowano przez Job Hunter AI"
            }
        }
