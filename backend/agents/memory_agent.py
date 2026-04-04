import json
import logging
from typing import Dict, Any, List
from core.vector_client import get_session_collection

logger = logging.getLogger(__name__)


class MemoryAgent:
    def __init__(self):
        self.collection = get_session_collection("default")

    async def save(self, session_id: str, current_state: Dict) -> None:
        """Save current state to persistent vector memory for semantic recall."""
        try:
            intent = current_state.get("intent", {})
            if not intent or current_state.get("error"):
                return

            transcript = current_state.get("transcript", "")
            
            # Store the main entry as a document in the vector store
            # This allows semantic search later: "Show me that chart about last month again"
            doc_id = f"{session_id}_{int(current_state['start_time'])}"
            
            metadata = {
                "session_id": session_id,
                "intent_type": intent.get("type", "general"),
                "metric": intent.get("metric", "unknown"),
                "dimension": intent.get("dimension", "unknown"),
                "data_source": current_state.get("data_source_used", "auto"),
                "timestamp": current_state["start_time"],
                "intent_json": json.dumps(intent)
            }
            
            self.collection.add(
                ids=[doc_id],
                documents=[transcript],
                metadatas=[metadata]
            )
            
            logger.info(f"✅ State saved to Vector Memory for session {session_id}")
        except Exception as e:
            logger.error(f"❌ MemoryAgent save error: {e}", exc_info=True)

    async def recall(self, session_id: str, query: str, limit: int = 5) -> List[Dict]:
        """Semantically recall past query context from the session."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where={"session_id": session_id}
            )
            
            parsed_results = []
            if results and results["metadatas"]:
                for meta in results["metadatas"][0]:
                    parsed_results.append({
                        **meta,
                        "intent_json": json.loads(meta["intent_json"])
                    })
            return parsed_results
        except Exception as e:
            logger.error(f"❌ MemoryAgent recall error: {e}")
            return []

    async def load(self, session_id: str) -> Dict:
        """Legacy support for basic state lookup — now pulling recent from Chroma."""
        try:
            # For backward compat with session_get, just return the most recent matching intent
            results = self.collection.get(
                where={"session_id": session_id},
                limit=1,
                # In current Chroma, sorting isn't built in to get(), 
                # but we can assume ID order for simple use cases or query for current state.
            )
            if results and results["metadatas"]:
                meta = results["metadatas"][0]
                return {
                    "last_intent": json.loads(meta["intent_json"]),
                    "last_metric": meta["metric"],
                    "session_id": session_id
                }
            return {}
        except Exception as e:
            logger.error(f"MemoryAgent load error: {e}")
            return {}
