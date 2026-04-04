"""
Visualization Agent — Selects the optimal chart type based on intent and data shape,
then builds a complete Recharts-compatible configuration.
"""
import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

CHART_RULES = {
    "compare": {"default": "grouped_bar"},
    "trend": {"default": "line"},
    "query": {"default": "bar"},
    "drill_down": {"default": "bar"},
    "filter": {"default": "bar"},
    "forecast": {"default": "line"},
    "summarize": {"default": "kpi_card"},
}

class VizAgent:
    async def run(self, transcript: str, intent: Dict, result_data: Optional[List[Dict]]) -> Dict:
        """Select chart type and build Recharts config with layout awareness."""
        if not result_data:
            return {"chart_config": None}

        try:
            # Extract layout metadata from transcript hint [layout: x=...,y=...,type=...]
            layout_meta = self._parse_layout_hint(transcript)
            
            # Override chart type if hint exists
            hint_type = layout_meta.get("type", "auto")
            chart_type = hint_type if hint_type != "auto" else self._select_chart_type(intent, result_data)
            
            config = self._build_config(chart_type, intent, result_data, layout_meta)
            
            # Robust Data Shape Validation
            if not self._validate_data_shape(config):
                # If explicit hint failed check (e.g. 1 row treemap), try auto-selection
                if hint_type != "auto":
                    logger.warning(f"Hinted chart type {hint_type} invalid for data shape — falling back to auto-select")
                    chart_type = self._select_chart_type(intent, result_data)
                    config = self._build_config(chart_type, intent, result_data, layout_meta)
                    if self._validate_data_shape(config):
                        return {"chart_config": config}
                
                logger.warning(f"Final data shape invalid for {chart_type} — falling back to Table")
                return {"chart_config": self._build_table_config(intent, result_data)}
                
            return {"chart_config": config}
        except Exception as e:
            logger.error(f"VizAgent error: {e}", exc_info=True)
            return {"chart_config": self._build_table_config(intent, result_data)}

    def _parse_layout_hint(self, transcript: str) -> Dict:
        """Parse [layout: x=0,y=0,w=3,h=2,type=kpi_card] from transcript."""
        meta = {}
        match = re.search(r'\[layout:\s*(.*?)\]', transcript)
        if match:
            pairs = match.group(1).split(",")
            for p in pairs:
                if "=" in p:
                    k, v = p.split("=")
                    meta[k.strip()] = v.strip()
        return meta

    def _select_chart_type(self, intent: Dict, data: List[Dict]) -> str:
        """Select the best chart type based on intent and data shape."""
        intent_type = intent.get("type", "query")
        rules = CHART_RULES.get(intent_type, {"default": "bar"})
        cols = list(data[0].keys()) if data else []
        num_rows = len(data)

        if intent_type == "compare":
            numeric_cols = [c for c in cols if any(isinstance(row.get(c), (int, float)) for row in data[:3])]
            return "grouped_bar" if len(numeric_cols) >= 2 else "bar"
        elif intent_type == "trend":
            return "stacked_area" if len(cols) > 3 else "line"
        elif intent_type in ["query", "filter"]:
             return "kpi_card" if num_rows == 1 else "bar"
        
        return rules.get("default", "bar")

    def _build_config(self, chart_type: str, intent: Dict, data: List[Dict], layout_meta: Dict = None) -> Dict:
        if not data: return {}
        layout_meta = layout_meta or {}

        cols = list(data[0].keys())
        metric = intent.get("metric", "value")
        x_key = self._find_x_key(cols, data, intent.get("dimension"))
        y_keys = self._find_y_keys(cols, data, x_key)

        colors = layout_meta.get("colors", ["#3C3489", "#854F0B", "#0F6E56", "#993C1D", "#BA7517"])
        if isinstance(colors, str):
            if "|" in colors:
                colors = [c.strip() for c in colors.split("|")]
            elif "," in colors:
                colors = [c.strip() for c in colors.split(",")]
            else:
                colors = [colors]

        config = {
            "type": chart_type,
            "title": layout_meta.get("title") or self._build_title(intent),
            "data": data,
            "x_key": x_key,
            "y_keys": y_keys[:6],
            "colors": colors,
            "show_legend": len(y_keys) > 1,
            "show_grid": True,
            "unit": self._infer_unit(metric),
            "layout": {
                "x": self._safe_int(layout_meta.get("x"), 0),
                "y": self._safe_int(layout_meta.get("y"), 0),
                "w": self._safe_int(layout_meta.get("w"), 6),
                "h": self._safe_int(layout_meta.get("h"), 4),
            } if "w" in layout_meta else None
        }

        # ── KPI card: decide WHAT value to display ──────────────────────────────
        if chart_type == "kpi_card":
            dimension = intent.get("dimension")
            has_dimension_col = dimension and any(
                dimension.lower() in c.lower() for c in cols
            )
            is_top_query = has_dimension_col and x_key  # "top X by Y" shape

            if is_top_query:
                # Show the category name (e.g. "Consumer"), not the number
                config["kpi_value_key"] = x_key          # "segment" → "Consumer"
                config["kpi_secondary_key"] = y_keys[0] if y_keys else None  # show 80.5 as subtext
            else:
                # Show the number (e.g. total sales = $2.3M)
                config["kpi_value_key"] = y_keys[0] if y_keys else x_key
                config["kpi_secondary_key"] = None

            # Pull the label from the layout hint (e.g. "TOP SEGMENT", "TOTAL SALES")
            config["kpi_label"] = layout_meta.get("label", config["title"])
            config["kpi_delta"] = layout_meta.get("delta")
            config["kpi_direction"] = layout_meta.get("direction")

        return config

    def _safe_int(self, val: Any, default: int = 0) -> int:
        if val in [None, "undefined", "null", ""]: return default
        try: return int(val)
        except: return default

    def _validate_data_shape(self, config: Dict) -> bool:
        ct = config.get("type")
        if ct in ["kpi_card", "table"]: return True
        data = config.get("data", [])
        if not data: return False
        xk = config.get("x_key")
        yk = config.get("y_keys", [])
        return bool(xk and yk and xk in data[0] and any(y in data[0] for y in yk))

    def _find_x_key(self, cols: List[str], data: List[Dict], hint: str) -> str:
        for c in cols:
            if hint and hint.lower() in c.lower(): return c
        for c in cols:
            if isinstance(data[0].get(c), str): return c
        return cols[0] if cols else "category"

    def _find_y_keys(self, cols: List[str], data: List[Dict], x_key: str) -> List[str]:
        keys = [c for c in cols if c != x_key and isinstance(data[0].get(c), (int, float))]
        return keys if keys else [c for c in cols if c != x_key]

    def _build_title(self, intent: Dict) -> str:
        metric = (intent.get("metric") or "Data").replace("_", " ").title()
        dim = (intent.get("dimension") or "").replace("_", " ").title()
        return f"{metric} by {dim}" if dim else f"{metric} Overview"

    def _infer_unit(self, metric: str) -> Optional[str]:
        m = (metric or "").lower()
        if any(k in m for k in ["rate", "percent", "margin"]): return "%"
        # Never default to $ unless explicitly confirmed by data source metadata
        return None

    def _build_table_config(self, intent: Dict, data: List[Dict]) -> Dict:
        return {
            "type": "table",
            "title": self._build_title(intent),
            "data": data,
            "x_key": list(data[0].keys())[0] if data else "id",
            "y_keys": list(data[0].keys())[1:] if data else [],
            "colors": ["#888"],
            "show_legend": False,
            "show_grid": True,
            "unit": None,
        }
