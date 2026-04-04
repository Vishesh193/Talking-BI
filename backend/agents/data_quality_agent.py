"""
Data Quality Agent — Profiles tables before QueryAgent runs.
Reports: null %, outlier count, row count, freshness, and a quality score.
Results surface as a quality badge on every chart panel.
"""
import logging
import statistics
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DataQualityAgent:
    """Profiles query result data for quality signals before display."""

    async def run(
        self,
        result_data: Optional[List[Dict]],
        data_source: Optional[str] = None,
        freshness_ts: Optional[datetime] = None,
    ) -> Dict:
        """
        Profile the result set and return a quality report.
        Returns: {quality_badge, score, signals}
        """
        if not result_data:
            return {"quality": None}

        try:
            report = self._profile(result_data, freshness_ts)
            return {"quality": report}
        except Exception as e:
            logger.warning(f"DataQualityAgent error (non-critical): {e}")
            return {"quality": None}

    def _profile(self, data: List[Dict], freshness_ts: Optional[datetime]) -> Dict:
        total_rows = len(data)
        if total_rows == 0:
            return self._empty_report()

        cols = list(data[0].keys())
        signals = []
        score = 100  # Start at 100, deduct for issues

        # ── Null / Missing % ──────────────────────────────────────────────────
        null_counts: Dict[str, int] = {}
        for col in cols:
            nulls = sum(1 for row in data if row.get(col) is None or row.get(col) == "")
            null_counts[col] = nulls

        total_cells = total_rows * len(cols)
        total_nulls = sum(null_counts.values())
        null_pct = round(total_nulls / total_cells * 100, 1) if total_cells else 0

        if null_pct > 10:
            score -= 25
            signals.append({"type": "warning", "message": f"{null_pct}% null values across dataset"})
        elif null_pct > 2:
            score -= 10
            signals.append({"type": "info", "message": f"{null_pct}% null values"})

        # ── Outlier Detection (IQR method on numeric cols) ────────────────────
        outlier_count = 0
        for col in cols:
            values = [row[col] for row in data if isinstance(row.get(col), (int, float))]
            if len(values) < 4:
                continue
            values.sort()
            q1 = values[len(values) // 4]
            q3 = values[3 * len(values) // 4]
            iqr = q3 - q1
            if iqr == 0:
                continue
            low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            col_outliers = sum(1 for v in values if v < low or v > high)
            outlier_count += col_outliers

        outlier_pct = round(outlier_count / total_rows * 100, 1) if total_rows > 0 else 0
        if outlier_pct > 5:
            score -= 15
            signals.append({"type": "warning", "message": f"{outlier_count} outliers detected ({outlier_pct}%)"})
        elif outlier_pct > 0:
            signals.append({"type": "info", "message": f"{outlier_count} potential outliers"})

        # ── Duplicate Rows ────────────────────────────────────────────────────
        seen = set()
        dupes = 0
        for row in data:
            key = str(sorted(row.items()))
            if key in seen:
                dupes += 1
            seen.add(key)

        if dupes > 0:
            score -= 10
            dupe_pct = round(dupes / total_rows * 100, 1)
            signals.append({"type": "warning", "message": f"{dupes} duplicate rows ({dupe_pct}%)"})

        # ── Data Freshness ────────────────────────────────────────────────────
        freshness_label = "Unknown"
        if freshness_ts:
            age = datetime.utcnow() - freshness_ts
            if age < timedelta(hours=1):
                freshness_label = f"{int(age.seconds / 60)}m ago"
            elif age < timedelta(days=1):
                freshness_label = f"{int(age.seconds / 3600)}h ago"
            else:
                freshness_label = f"{age.days}d ago"
                if age.days > 7:
                    score -= 20
                    signals.append({"type": "warning", "message": f"Data is {age.days} days old"})

        # ── Score → Grade ─────────────────────────────────────────────────────
        score = max(0, min(100, score))
        if score >= 90:
            grade, color = "Excellent", "#107C10"
        elif score >= 75:
            grade, color = "Good", "#498205"
        elif score >= 50:
            grade, color = "Fair", "#FF8C00"
        else:
            grade, color = "Poor", "#D13438"

        return {
            "score": score,
            "grade": grade,
            "grade_color": color,
            "row_count": total_rows,
            "null_pct": null_pct,
            "outlier_count": outlier_count,
            "duplicate_count": dupes,
            "freshness": freshness_label,
            "signals": signals,
        }

    def _empty_report(self) -> Dict:
        return {
            "score": 0, "grade": "No Data", "grade_color": "#605E5C",
            "row_count": 0, "null_pct": 0.0, "outlier_count": 0,
            "duplicate_count": 0, "freshness": "N/A", "signals": [],
        }
