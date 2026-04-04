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
  "thought": "Brief chain-of-thought analysis of the query",
  "type": "query|compare|trend|drill_down|filter|explain|forecast|summarize|simulate",
  "metric": "the business metric being asked about (e.g. revenue, orders, leads, churn_rate)",
  "dimension": "the grouping dimension (e.g. product, region, salesperson, category)",
  "period_a": "primary time period (e.g. current_month, last_7_days, Q1_2024, today, this_year)",
  "period_b": "comparison time period for compare intents (e.g. previous_month, last_year)",
  "filters": {"key": "value"},
  "data_source": "auto|sql|excel|powerbi|salesforce|shopify",
  "needs_clarification": false,
  "clarification_question": null
}

FEW-SHOT EXAMPLES:
1. User: "How was revenue last month?"
   JSON: {"thought": "The user wants a simple revenue query for the previous month.", "type": "query", "metric": "revenue", "period_a": "last_month", "data_source": "auto"}

2. User: "Compare sales in North vs South region"
   JSON: {"thought": "Comparing sales across two regions.", "type": "compare", "metric": "sales", "dimension": "region", "filters": {"region": ["North", "South"]}, "data_source": "auto"}

3. User: "What if price increases by 10%?"
   JSON: {"thought": "This is a what-if simulation scenario.", "type": "simulate", "metric": "price", "data_source": "auto"}

Rules:
- Use 'thought' to explain your logic before filling the fields.
- NEVER set needs_clarification=True unless the query is complete unreadable gibberish. ALWAYS confidently guess the user's intent. Do not interrogate the user.
- If no metric is explicitly stated, infer the most likely metric (e.g., "count", "revenue", "price", "records"), or default to "*" or "all".
- If no time period is specified, default period_a to "all_time", "current_year", or "current_month".
- For follow-ups like "drill into that" or "show last year", use session_memory context to fill in missing fields.
- If a `target_panel_context` is provided, and the user asks to "change", "filter", or "modify", then use that context as the base and only change the requested parts.
- Infer data_source from context: "Shopify" → shopify, "Salesforce leads" → salesforce, otherwise "auto".
"""


from core.llm import groq_client

class IntentAgent:
    def __init__(self):
        pass

    async def run(self, transcript: str, session_memory: Dict = None, target_panel_id: str = None, uploaded_files: Dict = None) -> Dict:
        """Parse transcript into structured intent."""
        session_memory = session_memory or {}
        
        # Build schema summary for better intent classification
        schema_summary = ""
        if uploaded_files:
            schema_summary = "\n\n=== AVAILABLE USER DATA FIELDS ===\n"
            for f_id, info in uploaded_files.items():
                if isinstance(info, dict):
                    cols = info.get("columns", [])
                    filename = info.get("filename", "unknown")
                    schema_summary += f"File: {filename}\nColumns: {', '.join(cols)}\n\n"
            schema_summary += "!!! USE THESE FIELDS AS THE PRIMARY METRICS/DIMENSIONS. DO NOT INVENT PRODUCT NAMES IF THEY ARE NOT IN THE COLUMNS !!!\n"

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

        user_prompt = f"Parse this query: \"{transcript}\"{schema_summary}{memory_context}"

        try:
            intent = await groq_client.generate_json(INTENT_SYSTEM_PROMPT, user_prompt, preferred_model="llama-3.1-8b-instant")
            
            logger.info(f"Intent parsed successfully: type={intent.get('type')}")

            return {
                "intent": intent,
                "needs_clarification": intent.get("needs_clarification", False),
                "clarification_question": intent.get("clarification_question"),
            }

        except Exception as e:
            import traceback
            logger.error(f"IntentAgent error: {e}\n{traceback.format_exc()}")
            # Even if all models fail, we provide a safe fallback intent to keep the UI alive.
            return {
                "intent": {
                   "type": "query",
                   "metric": None,
                   "dimension": None,
                   "period_a": "current",
                   "filters": {},
                   "data_source": "auto",
                   "needs_clarification": True,
                   "clarification_question": f"Model deprecated / unavailable. Please try again. ({str(e)})"
                },
                "needs_clarification": True,
                "clarification_question": f"Model deprecated / unavailable. Please try again. ({str(e)})"
            }
