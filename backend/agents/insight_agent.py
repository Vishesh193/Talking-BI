"""
Insight Agent — Analyzes query results to generate ranked, actionable business insights.
Uses statistical analysis + Groq LLM for narrative generation.
"""
import json
import logging
import statistics
from typing import Dict, List, Optional, Any, Tuple
from groq import AsyncGroq

from core.config import settings
from core.llm import groq_client

logger = logging.getLogger(__name__)

INSIGHT_PROMPT = """You are a senior business analyst. Analyze this data and generate:
1. 2-3 sharp, actionable insights.
2. 3-4 suggested follow-up natural language queries to further explore this data.

Intent: {intent}
Data: {data_sample}
Statistical Summary: {stats}

Return ONLY a JSON object:
{{
  "insights": [
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
  ],
  "suggestions": [
     "Drill down by [dimension]", 
     "Compare [metric] to previous period",
     "What if [metric] increases by 10%?"
  ]
}}

Rules:
- insights: Always include specific numbers. Rank by business impact. Body under 25 words.
- suggestions: Be specific to the current data. e.g. if looking at 'Revenue', suggests 'Revenue by region'.
- suggestions: Include at least one 'What if' simulation query.
- CRITICAL — NO CURRENCY SYMBOLS: Never use $, £, €, or any currency symbols in insight text. The data units are unknown. Write numbers as plain numerals only (e.g. "118,810 total" NOT "$118,810 total").
- CRITICAL — USE ACTUAL DATA VALUES: Copy numbers directly from the data sample. Do not invent or estimate values.
"""


class InsightAgent:
    def __init__(self):
        pass

    async def run(self, intent: Dict, result_data: Optional[List[Dict]] = None, chart_config: Optional[Dict] = None) -> Dict:
        """Generate ranked business insights and follow-up suggestions from query results."""
        if not result_data:
            return {"insights": [], "suggestions": []}

        try:
            stats = self._compute_stats(result_data)
            data_sample = result_data[:20]

            user_prompt = INSIGHT_PROMPT.format(
                intent=json.dumps(intent),
                data_sample=json.dumps(data_sample, default=str),
                stats=json.dumps(stats),
            )

            parsed = await groq_client.generate_json("You are an expert data analyst.", user_prompt)

            # Support both {insights: [...]} format and legacy bare array format
            if isinstance(parsed, list):
                insights = parsed
                suggestions = []
            else:
                insights = parsed.get("insights", [])
                suggestions = parsed.get("suggestions", [])

            insights = self._detect_anomalies(insights, result_data, stats)
            return {"insights": insights[:3], "suggestions": suggestions[:4]}

        except Exception as e:
            logger.error(f"Insight generation failed (all fallbacks): {e}")
            return {"insights": self._fallback_insights(intent, result_data), "suggestions": []}

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
        """Format numbers nicely without assuming currency."""
        if val >= 1_000_000:
            return f"{val/1_000_000:.1f}M"
        if val >= 1_000:
            return f"{val/1_000:.1f}K"
        return f"{val:,.0f}"
