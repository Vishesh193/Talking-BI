"""
Dashboard Agent — Analyzes uploaded file schema to suggest dashboard templates
and generate clarifying questions about the user's analytical goals.
"""
import json
import logging
import uuid
from typing import Dict, List, Optional, Any
import pandas as pd
from groq import AsyncGroq

from core.config import settings

logger = logging.getLogger(__name__)

DASHBOARD_ANALYSIS_PROMPT = """You are a senior BI analyst. A user uploaded a dataset. Analyze the schema and sample data to:
1. Suggest 4-5 distinct dashboard templates that would be most useful
2. Generate up to 3 clarifying questions to better understand their goals

Dataset info:
- Filename: {filename}
- Rows: {rows}
- Columns: {columns_info}
- Sample data (first 3 rows): {sample}

Return ONLY valid JSON in this exact format:
{{
  "suggestions": [
    {{
      "id": "s1",
      "title": "Dashboard title (max 5 words)",
      "description": "What this dashboard reveals (1 sentence)",
      "chart_types": ["bar", "line", "kpi_card"],
      "focus": "e.g. Sales Performance",
      "preview_kpis": ["column1", "column2"]
    }}
  ],
  "clarifying_questions": [
    {{
      "id": "q1",
      "question": "Short, specific question",
      "options": ["Option A", "Option B", "Option C"],
      "allow_custom": true,
      "skippable": true
    }}
  ]
}}

Rules:
- Suggestions should cover different analytical angles: performance, trend, comparison, distribution, KPI summary
- Questions should help identify: time period focus, primary metric, comparison dimension
- Max 5 suggestions, max 3 questions
- Options in questions should be actual column values or realistic choices based on the data
- Make titles and descriptions specific to the actual columns, not generic
"""


class DashboardAgent:
    def __init__(self):
        self.client = AsyncGroq(
            api_key=settings.GROQ_API_KEY,
            timeout=20.0,
            max_retries=1
        )

    async def analyze_file(self, file_id: str, filename: str, df: pd.DataFrame) -> Dict:
        """Analyze a DataFrame and return dashboard suggestions + clarifying questions."""
        try:
            # Build column info
            columns_info = []
            column_types = {}
            for col in df.columns:
                dtype = str(df[col].dtype)
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_type = "numeric"
                    sample_vals = df[col].dropna().describe().to_dict()
                    sample_str = f"min={sample_vals.get('min', 0):.1f}, max={sample_vals.get('max', 0):.1f}, mean={sample_vals.get('mean', 0):.1f}"
                elif pd.api.types.is_datetime64_any_dtype(df[col]):
                    col_type = "date"
                    sample_str = f"date range: {df[col].min()} to {df[col].max()}"
                else:
                    col_type = "categorical"
                    unique_vals = df[col].dropna().unique()[:5].tolist()
                    sample_str = f"unique values: {unique_vals}"

                column_types[col] = col_type
                columns_info.append(f"  - {col} ({col_type}): {sample_str}")

            # Sample rows
            sample = df.head(3).to_dict(orient="records")

            prompt = DASHBOARD_ANALYSIS_PROMPT.format(
                filename=filename,
                rows=len(df),
                columns_info="\n".join(columns_info),
                sample=json.dumps(sample, default=str)[:2000],
            )

            response = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )

            raw = response.choices[0].message.content.strip()
            # Strip markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip().rstrip("```").strip()

            result = json.loads(raw)

            return {
                "file_id": file_id,
                "filename": filename,
                "rows": len(df),
                "columns": list(df.columns),
                "column_types": column_types,
                "suggestions": result.get("suggestions", []),
                "clarifying_questions": result.get("clarifying_questions", []),
            }

        except Exception as e:
            logger.error(f"DashboardAgent.analyze_file error: {e}", exc_info=True)
            # Fallback: generate basic suggestions without LLM
            return self._fallback_suggestions(file_id, filename, df)

    def _fallback_suggestions(self, file_id: str, filename: str, df: pd.DataFrame) -> Dict:
        """Generate basic suggestions without LLM."""
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        cat_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
        column_types = {c: ("numeric" if pd.api.types.is_numeric_dtype(df[c]) else "categorical") for c in df.columns}

        suggestions = [
            {
                "id": "s1",
                "title": "Summary KPI Dashboard",
                "description": f"Key metrics overview showing totals and averages for {', '.join(numeric_cols[:3])}",
                "chart_types": ["kpi_card", "bar"],
                "focus": "KPI Summary",
                "preview_kpis": numeric_cols[:3],
            },
            {
                "id": "s2",
                "title": "Comparative Analysis",
                "description": f"Compare {numeric_cols[0] if numeric_cols else 'values'} across different {cat_cols[0] if cat_cols else 'categories'}",
                "chart_types": ["bar", "grouped_bar"],
                "focus": "Comparison",
                "preview_kpis": numeric_cols[:2],
            },
            {
                "id": "s3",
                "title": "Distribution Overview",
                "description": "Breakdown of data distribution across categories",
                "chart_types": ["pie", "bar"],
                "focus": "Distribution",
                "preview_kpis": numeric_cols[:1],
            },
        ]

        questions = [
            {
                "id": "q1",
                "question": "What is your primary analytical goal?",
                "options": ["Track performance over time", "Compare categories", "Identify top performers", "Spot anomalies"],
                "allow_custom": True,
                "skippable": True,
            },
        ]

        return {
            "file_id": file_id,
            "filename": filename,
            "rows": len(df),
            "columns": list(df.columns),
            "column_types": column_types,
            "suggestions": suggestions,
            "clarifying_questions": questions,
        }
