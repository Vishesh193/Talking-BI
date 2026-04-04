"""
Proactive Alert Agent — Scheduled insight scanning with anomaly detection.
Runs the InsightAgent on a schedule and pushes alerts via webhook/Slack/email
when anomalies exceed configured thresholds.
"""
import json
import logging
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.config import settings

logger = logging.getLogger(__name__)


# ── Alert Rules Registry ─────────────────────────────────────────────────────
# Each rule defines a query to watch and a threshold to trigger on
ALERT_RULES: List[Dict] = [
    {
        "id": "revenue_drop",
        "name": "Daily Revenue Drop",
        "metric": "revenue",
        "condition": "pct_change < -10",  # Alert if revenue drops > 10%
        "schedule": "daily",
        "channels": ["webhook"],
    },
    {
        "id": "churn_spike",
        "name": "Churn Rate Spike",
        "metric": "churn",
        "condition": "value > 5",         # Alert if churn rate > 5%
        "schedule": "daily",
        "channels": ["webhook"],
    },
    {
        "id": "anomaly_any",
        "name": "Data Anomaly Detected",
        "metric": "*",
        "condition": "is_anomaly == true",
        "schedule": "hourly",
        "channels": ["webhook"],
    },
]


class AlertAgent:
    """Evaluates insight results against alert rules and fires notifications."""

    async def evaluate_and_alert(
        self,
        insights: List[Dict],
        session_id: str,
        query_context: str = "",
        chart_config: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Check insights for alert conditions and fire configured channels.
        Returns list of alerts that were fired.
        """
        fired = []

        for insight in insights:
            for rule in ALERT_RULES:
                if self._matches_rule(insight, rule):
                    alert = self._build_alert(insight, rule, query_context)
                    await self._dispatch(alert, rule["channels"], chart_config)
                    fired.append(alert)
                    logger.info(f"Alert fired: {rule['name']} — {insight.get('title')}")

        return fired

    def _matches_rule(self, insight: Dict, rule: Dict) -> bool:
        """Check if an insight satisfies a rule condition."""
        metric = rule.get("metric", "*")
        condition = rule.get("condition", "")

        # Metric filter
        if metric != "*" and insight.get("metric") != metric:
            return False

        # Condition evaluation
        try:
            if "is_anomaly == true" in condition:
                return bool(insight.get("is_anomaly", False))

            if "pct_change <" in condition:
                threshold = float(condition.split("<")[-1].strip())
                change = insight.get("change_pct")
                return change is not None and change < threshold

            if "value >" in condition:
                threshold = float(condition.split(">")[-1].strip())
                # Use change_pct as a proxy for current value
                change = insight.get("change_pct", 0) or 0
                return change > threshold

        except Exception as e:
            logger.warning(f"Alert condition eval failed: {e}")

        return False

    def _build_alert(self, insight: Dict, rule: Dict, context: str) -> Dict:
        return {
            "alert_id": rule["id"],
            "alert_name": rule["name"],
            "fired_at": datetime.utcnow().isoformat(),
            "insight_title": insight.get("title"),
            "insight_body": insight.get("body"),
            "metric": insight.get("metric"),
            "change_pct": insight.get("change_pct"),
            "is_anomaly": insight.get("is_anomaly", False),
            "action": insight.get("action"),
            "query_context": context,
            "severity": "critical" if insight.get("is_anomaly") else "warning",
        }

    async def _dispatch(self, alert: Dict, channels: List[str], chart_config: Optional[Dict]) -> None:
        """Send alert to configured channels."""
        for channel in channels:
            try:
                if channel == "webhook" and settings.ALERT_WEBHOOK_URL:
                    await self._send_webhook(alert, chart_config)
                elif channel == "slack" and settings.SLACK_WEBHOOK_URL:
                    await self._send_slack(alert)
            except Exception as e:
                logger.error(f"Alert dispatch failed [{channel}]: {e}")

    async def _send_webhook(self, alert: Dict, chart_config: Optional[Dict]) -> None:
        """POST alert payload to a generic webhook URL."""
        payload = {
            **alert,
            "chart_snapshot": chart_config,
            "source": "TalkingBI-AlertAgent",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                settings.ALERT_WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            logger.info(f"Webhook alert sent: {resp.status_code}")

    async def _send_slack(self, alert: Dict) -> None:
        """Post a formatted Slack message via incoming webhook."""
        emoji = "🚨" if alert["severity"] == "critical" else "⚠️"
        pct = f" ({alert['change_pct']:+.1f}%)" if alert.get("change_pct") is not None else ""
        blocks = {
            "text": f"{emoji} *Talking BI Alert: {alert['alert_name']}*",
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": f"{emoji} {alert['alert_name']}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{alert['insight_title']}*{pct}\n{alert['insight_body']}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*Recommended Action:* {alert.get('action', 'N/A')}"}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Fired at {alert['fired_at']} | Severity: {alert['severity'].upper()}"}]},
            ],
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.SLACK_WEBHOOK_URL, json=blocks)
            resp.raise_for_status()
