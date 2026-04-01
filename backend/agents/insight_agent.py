"""
Insight Agent — Analyzes query results to generate ranked, actionable business insights.
Uses statistical analysis + Groq LLM for narrative generation.
"""
import json
import logging
import statistics
from typing import Dict, List, Optional, Any
from groq import AsyncGroq

from core.config import settings

logger = logging.getLogger(__name__)

INSIGHT_PROMPT = """You are a senior business analyst. Analyze this data and generate 2-3 sharp, actionable insights.

Intent: {intent}
Data: {data_sample}
Statistical Summary: {stats}

Return ONLY a JSON array of insight objects:
[
  {{
    "title": "Short compelling headline (max 10 words)",
    "body": "One sentence explanation with specific numbers from the data",
    "metric": "the metric this insight is about",
    "change_pct": null or a number like 34.5 or -12.3,
    "direction": "up" or "down" or "neutral",
    "confidence": 0.85,
    "action": "One concrete recommended action",
    "is_anomaly": false
  }}
]

Rules:
- Always include specific numbers from the data
- Rank by business impact (most impactful first)
- Keep body under 25 words
- action should be specific and actionable
- Set is_anomaly=true if a value deviates more than 20% from the average
"""


class InsightAgent:
    def __init__(self):
        self.client = AsyncGroq(
            api_key=settings.GROQ_API_KEY,
            timeout=15.0,
            max_retries=1
        )

    async def run(self, intent: Dict, result_data: Optional[List[Dict]], chart_config: Optional[Dict]) -> Dict:
        """Generate ranked business insights from query results."""
        if not result_data:
            return {"insights": []}

        try:
            stats = self._compute_stats(result_data)
            insights = await self._generate_insights(intent, result_data, stats)
            return {"insights": insights}
        except Exception as e:
            logger.error(f"InsightAgent error: {e}")
            # Fallback to statistical insights
            return {"insights": self._fallback_insights(intent, result_data)}

    def _compute_stats(self, data: List[Dict]) -> Dict:
        """Compute basic statistics on numeric columns."""
        if not data:
            return {}

        stats = {}
        numeric_cols = [
            col for col in data[0].keys()
            if isinstance(data[0].get(col), (int, float))
        ]

        for col in numeric_cols:
            values = [row.get(col, 0) for row in data if isinstance(row.get(col), (int, float))]
            if not values:
                continue
            stats[col] = {
                "min": min(values),
                "max": max(values),
                "mean": round(statistics.mean(values), 2),
                "total": round(sum(values), 2),
                "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
            }
        return stats

    async def _generate_insights(self, intent: Dict, data: List[Dict], stats: Dict) -> List[Dict]:
        """Use Groq to generate narrative insights."""
        try:
            # Sample data (first 10 rows for context window efficiency)
            data_sample = data[:10]
            prompt = INSIGHT_PROMPT.format(
                intent=json.dumps(intent),
                data_sample=json.dumps(data_sample, default=str),
                stats=json.dumps(stats),
            )

            response = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )

            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            insights = json.loads(raw)

            # Add anomaly detection
            insights = self._detect_anomalies(insights, data, stats)
            return insights[:3]  # Max 3 insights

        except Exception as e:
            logger.error(f"Groq insight generation failed: {e}")
            return self._fallback_insights(intent, data)

    def _detect_anomalies(self, insights: List[Dict], data: List[Dict], stats: Dict) -> List[Dict]:
        """Flag insights where values deviate significantly from mean."""
        for insight in insights:
            metric = insight.get("metric")
            if metric and metric in stats:
                mean = stats[metric].get("mean", 0)
                stdev = stats[metric].get("stdev", 0)
                if stdev > 0:
                    # Check if max value is anomalous (>2 standard deviations)
                    max_val = stats[metric].get("max", 0)
                    if abs(max_val - mean) > 2 * stdev:
                        insight["is_anomaly"] = True
        return insights

    def _fallback_insights(self, intent: Dict, data: List[Dict]) -> List[Dict]:
        """Generate basic statistical insights without LLM."""
        insights = []
        if not data:
            return insights

        # Find numeric columns
        numeric_cols = [
            col for col in data[0].keys()
            if isinstance(data[0].get(col), (int, float))
        ]

        if not numeric_cols:
            return [{"title": "Data retrieved", "body": f"Found {len(data)} records", "confidence": 1.0, "direction": "neutral", "is_anomaly": False}]

        for col in numeric_cols[:2]:
            values = [row.get(col, 0) for row in data if isinstance(row.get(col), (int, float))]
            if not values:
                continue

            max_val = max(values)
            min_val = min(values)
            total = sum(values)
            mean = total / len(values)

            # Find which dimension has highest value
            str_cols = [c for c in data[0].keys() if isinstance(data[0].get(c), str)]
            if str_cols:
                max_row = max(data, key=lambda r: r.get(col, 0))
                top_label = max_row.get(str_cols[0], "unknown")
                pct_above_avg = round(((max_val - mean) / mean) * 100, 1) if mean else 0

                insights.append({
                    "title": f"Top {col.replace('_', ' ').title()}: {top_label}",
                    "body": f"{top_label} leads with {col} of {self._format_value(max_val)}, {abs(pct_above_avg)}% {'above' if pct_above_avg > 0 else 'below'} average.",
                    "metric": col,
                    "change_pct": pct_above_avg,
                    "direction": "up" if pct_above_avg > 0 else "down",
                    "confidence": 0.95,
                    "action": f"Investigate what drives {top_label}'s performance",
                    "is_anomaly": abs(pct_above_avg) > 30,
                })

        return insights[:3]

    def _format_value(self, val: float) -> str:
        if val >= 1_000_000:
            return f"${val/1_000_000:.1f}M"
        if val >= 1_000:
            return f"${val/1_000:.1f}K"
        return f"${val:.0f}"
