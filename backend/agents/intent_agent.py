"""
Intent Agent — Uses Groq LLM to parse natural language into structured intent JSON.
Handles follow-up queries using session memory context.
"""
import json
import logging
from typing import Dict, Any, Optional
from groq import AsyncGroq

from core.config import settings

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = """You are an Intent Parser for a Business Intelligence system.

Your job is to analyze a user's natural language query (from voice) and extract structured intent.

Always respond with ONLY a valid JSON object. No explanation, no markdown, just JSON.

JSON Schema:
{
  "type": "query|compare|trend|drill_down|filter|explain|forecast|summarize",
  "metric": "the business metric being asked about (e.g. revenue, orders, leads, churn_rate)",
  "dimension": "the grouping dimension (e.g. product, region, salesperson, category)",
  "period_a": "primary time period (e.g. current_month, last_7_days, Q1_2024, today, this_year)",
  "period_b": "comparison time period for compare intents (e.g. previous_month, last_year)",
  "filters": {"key": "value"},
  "data_source": "auto|sql|excel|powerbi|salesforce|shopify",
  "needs_clarification": false,
  "clarification_question": null
}

Rules:
- NEVER set needs_clarification=True unless the query is complete unreadable gibberish. ALWAYS confidently guess the user's intent. Do not interrogate the user.
- If no metric is explicitly stated, infer the most likely metric (e.g., "count", "revenue", "price", "records"), or default to "*" or "all".
- If no time period is specified, default period_a to "all_time", "current_year", or "current_month".
- For follow-ups like "drill into that" or "show last year", use session_memory context to fill in missing fields.
- If a `target_panel_context` is provided, and the user asks to "change", "filter", or "modify", then use that context as the base and only change the requested parts.
- Infer data_source from context: "Shopify" → shopify, "Salesforce leads" → salesforce, otherwise "auto".
"""


class IntentAgent:
    def __init__(self):
        self.client = AsyncGroq(
            api_key=settings.GROQ_API_KEY,
            timeout=15.0,
            max_retries=1
        )

    async def run(self, transcript: str, session_memory: Dict = None, target_panel_id: str = None) -> Dict:
        """Parse transcript into structured intent."""
        session_memory = session_memory or {}

        # Build context from session memory or target panel
        memory_context = ""
        if target_panel_id:
            # If we have a target panel, find its context in memory
            panel_history = session_memory.get("panel_history", {})
            panel_ctx = panel_history.get(target_panel_id)
            if panel_ctx:
                memory_context = f"\n\nTarget Panel Context (this is the chart the user is looking at): {json.dumps(panel_ctx)}"
        elif session_memory.get("last_intent"):
            memory_context = f"\n\nSession context (previous query): {json.dumps(session_memory['last_intent'])}"
            memory_context += f"\nPrevious metric: {session_memory.get('last_metric', 'unknown')}"

        user_prompt = f"Parse this query: \"{transcript}\"{memory_context}"

        try:
            response = await self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=500,
                messages=[
                    {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
            )

            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            intent = json.loads(raw)

            logger.info(f"Intent parsed: type={intent.get('type')}, metric={intent.get('metric')}")

            return {
                "intent": intent,
                "needs_clarification": intent.get("needs_clarification", False),
                "clarification_question": intent.get("clarification_question"),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent JSON: {e}")
            return {
                "intent": {
                    "type": "query",
                    "metric": None,
                    "dimension": None,
                    "period_a": "current_month",
                    "period_b": None,
                    "filters": {},
                    "data_source": "auto",
                    "needs_clarification": True,
                    "clarification_question": "I didn't quite understand that. Could you rephrase your question?",
                },
                "needs_clarification": True,
                "clarification_question": "I didn't quite understand that. Could you rephrase your question?",
            }
        except Exception as e:
            logger.error(f"IntentAgent error: {e}")
            return {"error": f"Intent parsing failed: {str(e)}"}
