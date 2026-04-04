import json
import logging
from typing import List, Dict, Any, Optional
from groq import AsyncGroq
from core.config import settings

logger = logging.getLogger(__name__)

SIMULATION_PROMPT = """
You are a Business Simulation Engine. Your goal is to predict the outcome of a "What-If" scenario based on baseline data.

Scenario: {query}
Baseline Metric: {metric}
Baseline Value: {baseline_total}
Baseline Data Sample (5 rows): {data_sample}

Instructions:
1. Analyze the requested change (e.g., +10% price, -5% churn).
2. Calculate a "Simulated Value" by applying the change to the baseline. 
3. If the change implies a trade-off (e.g., higher price might lower volume), take a reasonable guess at the elasticity.
4. Provide a "Confidence Score" (0-1).
5. Explain the logic briefly.

Output format (Strict JSON):
{{
  "scenario": "Short title of the scenario",
  "baseline_value": 1234.5,
  "simulated_value": 1357.9,
  "net_change_pct": 10.0,
  "confidence": 0.85,
  "reasoning": "Explain why you chose this simulation result.",
  "impact_level": "Positive | Negative | Neutral"
}}
"""

class SimulationAgent:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def run(
        self,
        intent: Dict[str, Any],
        result_data: Optional[List[Dict[str, Any]]],
        query: str
    ) -> Dict[str, Any]:
        """
        Preform a what-if simulation based on the intent and current data.
        """
        if not result_data or intent.get("type") != "simulate":
            return {"simulation": None}

        metric = intent.get("metric", "value")
        
        # Calculate baseline total (assuming the first numeric column if metric is fuzzy)
        baseline_total = 0.0
        try:
            # Try to find a numeric column that matches or contains the metric name
            numeric_col = None
            for row in result_data:
                for k, v in row.items():
                    if isinstance(v, (int, float)) and (metric.lower() in k.lower() or not numeric_col):
                        numeric_col = k
                        break
                if numeric_col: break
            
            if numeric_col:
                baseline_total = sum(row.get(numeric_col, 0) for row in result_data)
        except Exception:
            baseline_total = 100.0 # fallback

        data_sample = result_data[:5]

        prompt = SIMULATION_PROMPT.format(
            query=query,
            metric=metric,
            baseline_total=baseline_total,
            data_sample=json.dumps(data_sample)
        )

        try:
            chat_completion = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            
            raw_content = chat_completion.choices[0].message.content
            simulation_result = json.loads(raw_content)
            
            logger.info(f"SimulationAgent completed: {simulation_result.get('scenario')}")
            return {"simulation": simulation_result}

        except Exception as e:
            logger.error(f"SimulationAgent error: {e}", exc_info=True)
            return {"simulation": None}
