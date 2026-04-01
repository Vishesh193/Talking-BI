"""Memory Agent — persists session context for follow-up queries."""
import logging
from typing import Dict, Any
from core.redis_client import session_set, session_get

logger = logging.getLogger(__name__)


class MemoryAgent:
    async def save(self, session_id: str, current_state: Dict) -> None:
        """Save current state to session memory for follow-up queries."""
        try:
            existing = await session_get(session_id)
            intent = current_state.get("intent", {})
            panel_history = existing.get("panel_history", {})
            # If this result targets a specific panel (update) OR is a new panel, store it
            # From orchestrator.py, we have 'target_panel_id' in the final state if it was an update attempt.
            tid = current_state.get("target_panel_id")
            if tid and intent and not current_state.get("error"):
                panel_history[tid] = intent

            memory = {
                **existing,
                "last_intent": intent,
                "last_metric": intent.get("metric") if intent else None,
                "last_dimension": intent.get("dimension") if intent else None,
                "last_period": intent.get("period_a") if intent else None,
                "last_data_source": current_state.get("data_source_used"),
                "query_count": existing.get("query_count", 0) + 1,
                "last_chart_type": current_state.get("chart_config", {}).get("type") if current_state.get("chart_config") else None,
                "panel_history": panel_history,
            }
            await session_set(session_id, memory, ttl=3600)
            logger.info(f"Session {session_id} memory saved. Query #{memory['query_count']}")
        except Exception as e:
            logger.error(f"MemoryAgent save error: {e}")

    async def load(self, session_id: str) -> Dict:
        return await session_get(session_id)
