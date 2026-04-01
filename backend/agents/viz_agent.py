"""
Visualization Agent — Selects the optimal chart type based on intent and data shape,
then builds a complete Recharts-compatible configuration.
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

CHART_COLORS = ["#00d4ff", "#ff6b35", "#7fff6b", "#c77dff", "#ffd60a", "#ff8fab", "#06d6a0"]

# Chart selection rules
CHART_RULES = {
    "compare": {
        "default": "grouped_bar",
        "if_many_items": "bar",  # >6 items
        "if_two_periods": "grouped_bar",
    },
    "trend": {
        "default": "line",
        "if_multiple_metrics": "area",
        "if_stacked": "stacked_area",
    },
    "query": {
        "default": "bar",
        "if_single_number": "kpi_card",
        "if_many_columns": "table",
    },
    "drill_down": {
        "default": "bar",
        "if_hierarchical": "bar",
    },
    "filter": {
        "default": "bar",
    },
    "summarize": {
        "default": "kpi_card",
    },
    "forecast": {
        "default": "line",
    },
}


class VizAgent:
    async def run(self, intent: Dict, result_data: Optional[List[Dict]]) -> Dict:
        """Select chart type and build Recharts config."""
        if not result_data:
            return {"chart_config": None}

        try:
            chart_type = self._select_chart_type(intent, result_data)
            config = self._build_config(chart_type, intent, result_data)
            return {"chart_config": config}
        except Exception as e:
            logger.error(f"VizAgent error: {e}")
            # Fallback to table
            return {
                "chart_config": self._build_table_config(intent, result_data)
            }

    def _select_chart_type(self, intent: Dict, data: List[Dict]) -> str:
        """Select the best chart type based on intent and data shape."""
        intent_type = intent.get("type", "query")
        rules = CHART_RULES.get(intent_type, {"default": "bar"})
        num_rows = len(data)
        num_cols = len(data[0].keys()) if data else 0

        if intent_type == "compare":
            # Check if we have two period columns
            cols = list(data[0].keys()) if data else []
            numeric_cols = [c for c in cols if any(
                isinstance(row.get(c), (int, float)) for row in data[:3]
            )]
            if len(numeric_cols) >= 2:
                return "grouped_bar"
            if num_rows > 8:
                return "bar"
            return "grouped_bar"

        elif intent_type == "trend":
            if num_cols > 3:
                return "stacked_area"
            return "line"

        elif intent_type in ["query", "filter"]:
            if num_rows == 1 and num_cols <= 3:
                return "kpi_card"
            if num_rows > 15 or num_cols > 5:
                return "table"
            return "bar"

        elif intent_type == "summarize":
            if num_rows <= 2:
                return "kpi_card"
            return "bar"

        elif intent_type == "forecast":
            return "line"

        return rules.get("default", "bar")

    def _build_config(self, chart_type: str, intent: Dict, data: List[Dict]) -> Dict:
        """Build Recharts-compatible chart configuration."""
        if not data:
            return {}

        cols = list(data[0].keys())
        metric = intent.get("metric", "value")
        dimension = intent.get("dimension") or cols[0]
        period_a = intent.get("period_a", "current")
        period_b = intent.get("period_b")

        # Find x key (string/dimension column)
        x_key = self._find_x_key(cols, data, dimension)

        # Find y keys (numeric columns)
        y_keys = self._find_y_keys(cols, data, x_key)

        # Build title
        title = self._build_title(intent)

        base = {
            "type": chart_type,
            "title": title,
            "data": data,
            "x_key": x_key,
            "y_keys": y_keys[:6],  # Max 6 series
            "colors": CHART_COLORS[:len(y_keys)],
            "show_legend": len(y_keys) > 1,
            "show_grid": True,
            "unit": self._infer_unit(metric),
        }

        if chart_type == "kpi_card":
            base["kpi_value"] = data[0].get(y_keys[0]) if y_keys else 0
            base["kpi_label"] = metric.replace("_", " ").title()

        return base

    def _find_x_key(self, cols: List[str], data: List[Dict], hint: str) -> str:
        """Find the best X-axis (categorical/time) column."""
        # Try hint first
        for col in cols:
            if hint and hint.lower() in col.lower():
                return col
        # Look for string columns
        for col in cols:
            if data and isinstance(data[0].get(col), str):
                return col
        return cols[0] if cols else "category"

    def _find_y_keys(self, cols: List[str], data: List[Dict], x_key: str) -> List[str]:
        """Find numeric columns to use as Y-axis values."""
        y_keys = []
        for col in cols:
            if col == x_key:
                continue
            if data and isinstance(data[0].get(col), (int, float)):
                y_keys.append(col)
        return y_keys if y_keys else [c for c in cols if c != x_key]

    def _build_title(self, intent: Dict) -> str:
        """Generate a human-readable chart title."""
        intent_type = intent.get("type", "query")
        metric = (intent.get("metric") or "Data").replace("_", " ").title()
        dimension = (intent.get("dimension") or "").replace("_", " ").title()
        period_a = (intent.get("period_a") or "").replace("_", " ").title()
        period_b = (intent.get("period_b") or "").replace("_", " ").title()

        titles = {
            "compare": f"{metric} by {dimension}: {period_a} vs {period_b}" if period_b else f"{metric} Comparison",
            "trend": f"{metric} Trend Over Time",
            "query": f"{metric} by {dimension}" if dimension else f"{metric} Overview",
            "drill_down": f"{metric} Breakdown by {dimension}",
            "filter": f"Filtered {metric} View",
            "summarize": f"{metric} Summary",
            "forecast": f"{metric} Forecast",
        }
        return titles.get(intent_type, f"{metric} Analysis")

    def _infer_unit(self, metric: str) -> Optional[str]:
        """Infer the display unit from metric name."""
        metric_lower = (metric or "").lower()
        if any(k in metric_lower for k in ["revenue", "sales", "cost", "profit", "spend", "value", "price"]):
            return "$"
        if any(k in metric_lower for k in ["rate", "ratio", "percentage", "pct", "margin", "roas"]):
            return "%"
        if any(k in metric_lower for k in ["count", "quantity", "orders", "customers", "clicks"]):
            return None
        return None

    def _build_table_config(self, intent: Dict, data: List[Dict]) -> Dict:
        return {
            "type": "table",
            "title": self._build_title(intent),
            "data": data,
            "x_key": list(data[0].keys())[0] if data else "id",
            "y_keys": list(data[0].keys())[1:] if data else [],
            "colors": CHART_COLORS,
            "show_legend": False,
            "show_grid": True,
            "unit": None,
        }
