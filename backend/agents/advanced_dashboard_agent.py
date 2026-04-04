"""
Advanced Dashboard Agent — Layout Randomizer Edition
Generates analyst-grade executive dashboards with randomized layouts and palettes.
5 layouts × 5 palettes = 25 unique combinations before any repeat.
"""
import logging
import random
import json
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# COLOR PALETTES
# ─────────────────────────────────────────────────────────────────────────────
PALETTES = {
    "Slate & Amber": {
        "primary":    "#3C3489",
        "secondary":  "#854F0B",
        "positive":   "#0F6E56",
        "negative":   "#993C1D",
        "background": "#F5F4F0",
        "colors": ["#3C3489", "#854F0B", "#0F6E56", "#993C1D", "#BA7517"],
    },
    "Forest & Rust": {
        "primary":    "#27500A",
        "secondary":  "#712B13",
        "positive":   "#085041",
        "negative":   "#633806",
        "background": "#F4F2EE",
        "colors": ["#27500A", "#712B13", "#085041", "#633806", "#4A7C2F"],
    },
    "Navy & Gold": {
        "primary":    "#042C53",
        "secondary":  "#BA7517",
        "positive":   "#0C447C",
        "negative":   "#A32D2D",
        "background": "#F3F4F6",
        "colors": ["#042C53", "#BA7517", "#0C447C", "#A32D2D", "#1A6B8A"],
    },
    "Plum & Teal": {
        "primary":    "#26215C",
        "secondary":  "#085041",
        "positive":   "#3C3489",
        "negative":   "#993556",
        "background": "#F2F0F8",
        "colors": ["#26215C", "#085041", "#3C3489", "#993556", "#0F6E56"],
    },
    "Charcoal & Coral": {
        "primary":    "#444441",
        "secondary":  "#993C1D",
        "positive":   "#3B6D11",
        "negative":   "#791F1F",
        "background": "#F6F5F2",
        "colors": ["#444441", "#993C1D", "#3B6D11", "#791F1F", "#C47A3A"],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT DEFINITIONS
# Each panel: (label, w, h, chart_type, query_template)
# Grid is 12 columns wide.
# ─────────────────────────────────────────────────────────────────────────────
LAYOUTS = {
    "A — Executive Ribbon": {
        "description": "Full-width KPI ribbon (6 mini cards), 70/30 area+donut, 3-col waterfall+bullet+heatmap, scatter",
        "panels": [
            # Row 1 — KPI ribbon (6 × w2)
            {"label": "TOTAL UNITS",    "w": 2, "h": 2, "type": "kpi_card",      "metric": "total_units",  "dim": None,    "period": "all_time"},
            {"label": "TOTAL PROFIT",   "w": 2, "h": 2, "type": "kpi_card",      "metric": "total_profit", "dim": None,    "period": "all_time"},
            {"label": "TOP PRODUCT",    "w": 2, "h": 2, "type": "kpi_card",      "metric": "total_units",  "dim": "product","period": "all_time"},
            {"label": "AVG MONTHLY PROFIT","w":2,"h": 2, "type": "kpi_card",     "metric": "total_profit", "dim": None,    "period": "monthly_avg"},
            {"label": "BEST MONTH",     "w": 2, "h": 2, "type": "kpi_card",      "metric": "total_profit", "dim": "month", "period": "all_time"},
            {"label": "GROWTH RATE",    "w": 2, "h": 2, "type": "kpi_card",      "metric": "total_units",  "dim": None,    "period": "growth"},
            # Row 2 — 70/30
            {"label": "Profit Trend Over Time",   "w": 8, "h": 4, "type": "stacked_area", "metric": "total_profit", "dim": "month",   "period": "all_time"},
            {"label": "Units by Product",          "w": 4, "h": 4, "type": "donut",        "metric": "total_units",  "dim": "product", "period": "all_time"},
            # Row 3 — 3-col
            {"label": "Monthly Profit Waterfall", "w": 4, "h": 4, "type": "waterfall",    "metric": "total_profit", "dim": "month",   "period": "all_time"},
            {"label": "Units vs Target",           "w": 4, "h": 4, "type": "bullet",       "metric": "total_units",  "dim": "product", "period": "all_time"},
            {"label": "Month × Product Heatmap",  "w": 4, "h": 4, "type": "heatmap",      "metric": "total_profit", "dim": "product", "period": "all_time"},
            # Row 4 — scatter
            {"label": "Units vs Profit Scatter",  "w":12, "h": 4, "type": "scatter",      "metric": "total_profit", "dim": "product", "period": "all_time"},
        ]
    },

    "B — Analyst Grid": {
        "description": "2×2 large chart grid, 5-card KPI strip, full-width ranked bar",
        "panels": [
            # Row 1 — 2×2 grid
            {"label": "Profit Trend",             "w": 6, "h": 4, "type": "line",          "metric": "total_profit", "dim": "month",   "period": "all_time"},
            {"label": "Units by Product",          "w": 6, "h": 4, "type": "grouped_bar",   "metric": "total_units",  "dim": "product", "period": "all_time"},
            {"label": "Product Mix Treemap",       "w": 6, "h": 4, "type": "treemap",       "metric": "total_profit", "dim": "product", "period": "all_time"},
            {"label": "Profit Gauge",              "w": 6, "h": 4, "type": "gauge",         "metric": "total_profit", "dim": None,      "period": "all_time"},
            # Row 2 — 5-card KPI strip
            {"label": "TOTAL UNITS",    "w": 2, "h": 2, "type": "kpi_card", "metric": "total_units",  "dim": None,    "period": "all_time"},
            {"label": "TOTAL PROFIT",   "w": 3, "h": 2, "type": "kpi_card", "metric": "total_profit", "dim": None,    "period": "all_time"},
            {"label": "TOP PRODUCT",    "w": 2, "h": 2, "type": "kpi_card", "metric": "total_units",  "dim": "product","period": "all_time"},
            {"label": "BEST MONTH",     "w": 3, "h": 2, "type": "kpi_card", "metric": "total_profit", "dim": "month", "period": "all_time"},
            {"label": "AVG PROFIT/MO",  "w": 2, "h": 2, "type": "kpi_card", "metric": "total_profit", "dim": None,    "period": "monthly_avg"},
            # Row 3 — full-width ranked bar
            {"label": "Products Ranked by Total Profit", "w":12,"h":4,"type":"ranked_bar", "metric": "total_profit", "dim": "product", "period": "all_time"},
        ]
    },

    "C — Storytelling Flow": {
        "description": "Single hero KPI banner (3 large numbers), full-width stacked area, side-by-side waterfall+scatter, treemap, heatmap",
        "panels": [
            # Row 1 — hero banner (3 large KPIs)
            {"label": "TOTAL REVENUE",  "w": 4, "h": 3, "type": "kpi_card", "metric": "total_profit", "dim": None,    "period": "all_time"},
            {"label": "TOTAL UNITS",    "w": 4, "h": 3, "type": "kpi_card", "metric": "total_units",  "dim": None,    "period": "all_time"},
            {"label": "TOP PRODUCT",    "w": 4, "h": 3, "type": "kpi_card", "metric": "total_units",  "dim": "product","period": "all_time"},
            # Row 2 — full-width stacked area
            {"label": "Profit by Product Over Time", "w":12,"h":5,"type":"stacked_area",  "metric": "total_profit", "dim": "month",   "period": "all_time"},
            # Row 3 — waterfall + scatter side by side
            {"label": "Month-over-Month Waterfall",  "w": 6, "h": 4, "type": "waterfall", "metric": "total_profit", "dim": "month",   "period": "all_time"},
            {"label": "Units vs Profit by Product",  "w": 6, "h": 4, "type": "scatter",   "metric": "total_profit", "dim": "product", "period": "all_time"},
            # Row 4 — treemap full width
            {"label": "Revenue Treemap by Product",  "w":12, "h": 4, "type": "treemap",   "metric": "total_profit", "dim": "product", "period": "all_time"},
            # Row 5 — heatmap
            {"label": "Month × Product Heatmap",     "w":12, "h": 4, "type": "heatmap",   "metric": "total_units",  "dim": "product", "period": "all_time"},
        ]
    },

    "D — Command Center": {
        "description": "Left sidebar 4 vertical KPI cards, main stacked charts, right panel donut+gauge+bullet",
        "panels": [
            # Left sidebar — 4 KPI cards stacked (w=3)
            {"label": "TOTAL UNITS",    "w": 3, "h": 3, "type": "kpi_card", "metric": "total_units",  "dim": None,    "period": "all_time"},
            {"label": "TOTAL PROFIT",   "w": 3, "h": 3, "type": "kpi_card", "metric": "total_profit", "dim": None,    "period": "all_time"},
            {"label": "TOP PRODUCT",    "w": 3, "h": 3, "type": "kpi_card", "metric": "total_units",  "dim": "product","period": "all_time"},
            {"label": "BEST MONTH",     "w": 3, "h": 3, "type": "kpi_card", "metric": "total_profit", "dim": "month", "period": "all_time"},
            # Main area (center) — stacked charts (w=6)
            {"label": "Profit Trend",              "w": 6, "h": 5, "type": "line",        "metric": "total_profit", "dim": "month",   "period": "all_time"},
            # Right panel (w=3) — donut + gauge + bullet
            {"label": "Product Mix",               "w": 3, "h": 5, "type": "donut",       "metric": "total_units",  "dim": "product", "period": "all_time"},
            # Main center row 2
            {"label": "Units by Product",          "w": 6, "h": 5, "type": "grouped_bar", "metric": "total_units",  "dim": "product", "period": "all_time"},
            # Right panel row 2
            {"label": "Profit Gauge",              "w": 3, "h": 3, "type": "gauge",       "metric": "total_profit", "dim": None,      "period": "all_time"},
            {"label": "Units vs Target",           "w": 3, "h": 2, "type": "bullet",      "metric": "total_units",  "dim": "product", "period": "all_time"},
            # Bottom full width
            {"label": "Month × Product Heatmap",  "w":12, "h": 4, "type": "heatmap",     "metric": "total_profit", "dim": "product", "period": "all_time"},
        ]
    },

    "E — Mosaic": {
        "description": "Large treemap half-width paired with donut+gauge, 4-col KPI strip, full-width multi-series line, scatter+waterfall",
        "panels": [
            # Row 1 — treemap half + donut+gauge right half
            {"label": "Revenue Treemap",           "w": 6, "h": 6, "type": "treemap",     "metric": "total_profit", "dim": "product", "period": "all_time"},
            {"label": "Units by Product",          "w": 3, "h": 3, "type": "donut",       "metric": "total_units",  "dim": "product", "period": "all_time"},
            {"label": "Profit Gauge",              "w": 3, "h": 3, "type": "gauge",       "metric": "total_profit", "dim": None,      "period": "all_time"},
            {"label": "TOTAL UNITS",               "w": 3, "h": 3, "type": "kpi_card",   "metric": "total_units",  "dim": None,      "period": "all_time"},
            {"label": "TOP PRODUCT",               "w": 3, "h": 3, "type": "kpi_card",   "metric": "total_units",  "dim": "product", "period": "all_time"},
            # Row 2 — 4-col KPI strip
            {"label": "TOTAL PROFIT",  "w": 3, "h": 2, "type": "kpi_card", "metric": "total_profit", "dim": None,    "period": "all_time"},
            {"label": "BEST MONTH",    "w": 3, "h": 2, "type": "kpi_card", "metric": "total_profit", "dim": "month", "period": "all_time"},
            {"label": "AVG UNITS/MO",  "w": 3, "h": 2, "type": "kpi_card", "metric": "total_units",  "dim": None,    "period": "monthly_avg"},
            {"label": "GROWTH RATE",   "w": 3, "h": 2, "type": "kpi_card", "metric": "total_units",  "dim": None,    "period": "growth"},
            # Row 3 — full-width multi-series line
            {"label": "All Products Profit Trend Over Time", "w":12,"h":5,"type":"line",  "metric": "total_profit", "dim": "month",   "period": "all_time"},
            # Row 4 — scatter + waterfall
            {"label": "Units vs Profit Scatter",   "w": 6, "h": 4, "type": "scatter",    "metric": "total_profit", "dim": "product", "period": "all_time"},
            {"label": "Monthly Profit Waterfall",  "w": 6, "h": 4, "type": "waterfall",  "metric": "total_profit", "dim": "month",   "period": "all_time"},
        ]
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# QUERY TEMPLATES — maps (metric, dim, period) → natural language question
# ─────────────────────────────────────────────────────────────────────────────
def _build_query(metric: str, dim: Optional[str], period: str, label: str) -> str:
    period_phrase = {
        "all_time":    "across all time",
        "monthly_avg": "as a monthly average",
        "growth":      "as month-over-month growth rate",
    }.get(period, "across all time")

    metric_phrase = metric.replace("_", " ")

    if dim:
        return f"What is the {metric_phrase} by {dim} {period_phrase}?"
    else:
        if "kpi" in label.lower() or period == "monthly_avg":
            return f"What is the total {metric_phrase} {period_phrase}?"
        return f"What is the {metric_phrase} trend {period_phrase}?"


# ─────────────────────────────────────────────────────────────────────────────
# ADVANCED DASHBOARD AGENT
# ─────────────────────────────────────────────────────────────────────────────
class AdvancedDashboardAgent:
    """
    Generates a full executive dashboard config by randomly selecting
    a layout + palette combination from the 25-combination pool.
    Tracks used combinations per session to avoid repeats.
    """

    def __init__(self):
        self._used_combinations: List[str] = []  # tracks used layout+palette pairs

    async def run(
        self,
        session_id: str,
        schema_info: Dict,
        fields: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> Dict:
        """
        Returns:
            {
                "layout_chosen": str,
                "palette_chosen": str,
                "panels": List[Dict],   ← list of panel configs with query + layout hints
                "palette": Dict,        ← full palette colours for frontend theming
                "dashboard_title": str,
            }
        """
        layout_name, palette_name = self._pick_combination()
        layout = LAYOUTS[layout_name]
        palette = PALETTES[palette_name]

        logger.info(f"AdvancedDashboardAgent: Layout chosen: [{layout_name}] | Palette chosen: [{palette_name}]")

        panels = self._build_panels(layout["panels"], palette)
        dashboard_title = self._infer_title(fields, context)

        return {
            "layout_chosen":   layout_name,
            "palette_chosen":  palette_name,
            "layout_description": layout["description"],
            "panels":          panels,
            "palette":         palette,
            "dashboard_title": dashboard_title,
            "panels_per_row":  self._panels_per_row(layout["panels"]),
        }

    # ── private ───────────────────────────────────────────────────────────────

    def _pick_combination(self):
        all_combinations = [
            (l, p)
            for l in LAYOUTS
            for p in PALETTES
        ]
        available = [c for c in all_combinations if f"{c[0]}|{c[1]}" not in self._used_combinations]

        # Reset if all 25 used
        if not available:
            logger.info("AdvancedDashboardAgent: All 25 combinations used — resetting pool.")
            self._used_combinations = []
            available = all_combinations

        chosen = random.choice(available)
        self._used_combinations.append(f"{chosen[0]}|{chosen[1]}")
        return chosen

    def _build_panels(self, panel_defs: List[Dict], palette: Dict) -> List[Dict]:
        panels = []
        color_str = "|".join(palette["colors"])

        for panel in panel_defs:
            metric = panel["metric"]
            dim    = panel.get("dim")
            period = panel.get("period", "all_time")
            label  = panel["label"]
            w      = panel["w"]
            h      = panel["h"]
            ctype  = panel["type"]

            query = _build_query(metric, dim, period, label)

            # Build the layout hint string the orchestrator/viz agent understands
            layout_hint = (
                f"[layout: x=0,y=0,"
                f"w={w},h={h},"
                f"type={ctype},"
                f"label={label},"
                f"delta=0,direction=,"
                f"colors={color_str}]"
            )

            panels.append({
                "query":        f"{query} {layout_hint}",
                "label":        label,
                "chart_type":   ctype,
                "metric":       metric,
                "dimension":    dim,
                "period":       period,
                "layout": {
                    "w": w,
                    "h": h,
                    "type": ctype,
                    "label": label,
                },
            })

        logger.info(f"AdvancedDashboardAgent: panels per row = {self._panels_per_row(panel_defs)}")
        return panels

    def _panels_per_row(self, panel_defs: List[Dict]) -> Dict[int, int]:
        """Count how many panels fit per row (groups by cumulative width resets)."""
        row_map = {}
        row_num = 0
        row_width = 0
        for p in panel_defs:
            w = p["w"]
            if row_width + w > 12:
                row_num += 1
                row_width = 0
            row_map[row_num] = row_map.get(row_num, 0) + 1
            row_width += w
        return row_map

    def _infer_title(self, fields: Optional[List[str]], context: Optional[str]) -> str:
        if context:
            return context
        if fields:
            product_fields = [f for f in fields if f not in ("month", "id", "date")]
            if product_fields:
                return f"Product Sales Performance Dashboard"
        return "Executive Performance Dashboard"


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN RULES (enforced via docstring — communicate to LLM prompts)
# ─────────────────────────────────────────────────────────────────────────────
DESIGN_RULES = """
DESIGN RULES (non-negotiable every run):
- Never use default blue (#0078D4 or any Power BI default) for any fill
- Every chart must use the selected palette — no off-palette colors
- Every chart must have a title, axis labels, and data labels where appropriate
- KPI cards must show value, label, and delta with directional arrow
- No decorative gradients or shadows
- Legends must be inline and compact
- The dashboard must feel like it was built by a senior analyst at a tier-1 consulting firm
- Dashboard title should reflect the data context, not a generic name
"""
advanced_dashboard_agent = AdvancedDashboardAgent()
