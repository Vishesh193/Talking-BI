"""TTS Agent — Generates concise spoken summary from insights."""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TTSAgent:
    async def run(self, insights: List[Dict], intent: Dict) -> Dict:
        """Generate a concise spoken summary from top insights."""
        if not insights:
            metric = (intent.get("metric") or "data").replace("_", " ")
            return {"tts_text": f"I've retrieved the {metric} data. No significant insights detected."}

        try:
            top_insight = insights[0]
            parts = []

            # Lead with top finding
            body = top_insight.get("body", "")
            if body:
                parts.append(body)

            # Add anomaly note
            if top_insight.get("is_anomaly"):
                parts.append("This looks unusual — worth investigating.")

            # Add action
            action = top_insight.get("action")
            if action:
                parts.append(f"I recommend: {action}.")

            # Add count if multiple insights
            if len(insights) > 1:
                parts.append(f"I found {len(insights)} total insights on your dashboard.")

            tts_text = " ".join(parts)
            # Keep it under ~25 words for natural speech
            words = tts_text.split()
            if len(words) > 40:
                tts_text = " ".join(words[:40]) + "."

            return {"tts_text": tts_text}
        except Exception as e:
            logger.error(f"TTSAgent error: {e}")
            return {"tts_text": "Your dashboard has been updated with the latest data."}
