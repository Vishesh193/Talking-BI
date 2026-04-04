import json
import logging
from typing import List, Dict, Any, Optional
from groq import AsyncGroq
from core.config import settings

logger = logging.getLogger(__name__)

STRATEGY_PROMPT = """
You are a Senior Strategic Business Consultant. You have been provided with data results and automated insights from a BI platform. Your goal is to provide 2-3 **high-level, actionable business recommendations** or "next steps" (prescriptive actions) based on the findings.

Guidelines:
1. Be specific and data-driven.
2. Focus on "What should we do now?" or "How can we optimize this?".
3. Keep each recommendation short and professional (max 20 words).
4. Categorize each recommendation (e.g., Marketing, Operations, Product, Sales).

Current Analysis Context:
- Intent: {intent_type}
- Core Findings: {insight_summaries}
- Data Shape: {row_count} records from {data_source}

Input Data Result (Sample if large):
{result_sample}

Output format (Strict JSON list):
[
  {{
    "title": "Short title",
    "recommendation": "Detailed actionable text",
    "category": "Category name",
    "impact": "High/Medium/Low"
  }},
  ...
]
"""

class StrategyAgent:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def run(
        self,
        intent: Dict[str, Any],
        insights: List[Dict[str, Any]],
        result_data: Optional[List[Dict[str, Any]]],
        data_source: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Generate prescriptive business recommendations based on findings.
        """
        if not insights:
            return {"strategies": []}

        # Prepare context
        intent_type = intent.get("type", "general query")
        insight_summaries = " | ".join([i.get("insight", "") for i in insights])
        row_count = len(result_data) if result_data else 0
        result_sample = json.dumps(result_data[:5] if result_data else [], indent=2)

        prompt = STRATEGY_PROMPT.format(
            intent_type=intent_type,
            insight_summaries=insight_summaries,
            row_count=row_count,
            data_source=data_source,
            result_sample=result_sample
        )

        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.4,
                response_format={"type": "json_object"},
            )
            
            raw_content = chat_completion.choices[0].message.content
            # The model might return a wrap in a key like "recommendations" or just the list
            data = json.loads(raw_content)
            
            # Robust extraction of the list
            strategies = []
            if isinstance(data, list):
                strategies = data
            elif isinstance(data, dict):
                # Search for lists within the dict
                for val in data.values():
                    if isinstance(val, list):
                        strategies = val
                        break
                else:
                    # If it's a single dict, wrap it
                    strategies = [data]

            logger.info(f"StrategyAgent generated {len(strategies)} recommendations")
            return {"strategies": strategies[:3]} # Max 3 for UI clarity

        except Exception as e:
            logger.error(f"StrategyAgent error: {e}", exc_info=True)
            return {"strategies": []}
