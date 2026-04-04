"""
Metric Store — Single source of truth for business metric definitions.
Maps semantic metric names → SQL expressions, units, and directionality.
QueryAgent resolves these automatically so every user gets the same formula.
"""
import logging
import re
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# ── Metric Registry ───────────────────────────────────────────────────────────
# Format: "alias": {sql, unit, direction, description}
METRIC_REGISTRY: Dict[str, Dict] = {
    # Revenue
    "mrr": {
        "sql": "SUM(amount) FILTER (WHERE billing_period = 'monthly')",
        "unit": "$",
        "direction": "up_is_good",
        "description": "Monthly Recurring Revenue",
        "aliases": ["monthly recurring revenue", "monthly revenue"],
    },
    "arr": {
        "sql": "SUM(amount) FILTER (WHERE billing_period = 'monthly') * 12",
        "unit": "$",
        "direction": "up_is_good",
        "description": "Annual Recurring Revenue",
        "aliases": ["annual recurring revenue", "annual revenue"],
    },
    "revenue": {
        "sql": "SUM(sales)",
        "unit": "$",
        "direction": "up_is_good",
        "description": "Total Sales",
        "aliases": ["total revenue", "revenue", "sales", "total sales", "income"],
    },
    "gross_profit": {
        "sql": "SUM(profit)",
        "unit": "$",
        "direction": "up_is_good",
        "description": "Gross Profit",
        "aliases": ["gross profit", "gp", "profit"],
    },
    "net_profit": {
        "sql": "SUM(profit)",
        "unit": "$",
        "direction": "up_is_good",
        "description": "Net Profit",
        "aliases": ["net profit", "operating income", "net income"],
    },

    # Customer
    "cac": {
        "sql": "SUM(marketing_spend + sales_spend) / NULLIF(COUNT(DISTINCT new_customer_id), 0)",
        "unit": "$",
        "direction": "down_is_good",
        "description": "Customer Acquisition Cost",
        "aliases": ["customer acquisition cost", "acquisition cost"],
    },
    "ltv": {
        "sql": "AVG(total_revenue_per_customer)",
        "unit": "$",
        "direction": "up_is_good",
        "description": "Customer Lifetime Value",
        "aliases": ["lifetime value", "customer lifetime value", "clv"],
    },
    "churn": {
        "sql": "COUNT(DISTINCT churned_customer_id) * 1.0 / NULLIF(COUNT(DISTINCT customer_id), 0) * 100",
        "unit": "%",
        "direction": "down_is_good",
        "description": "Churn Rate (%)",
        "aliases": ["churn rate", "customer churn", "attrition"],
    },
    "nrr": {
        "sql": "(SUM(expansion_revenue) + SUM(starting_mrr) - SUM(churn_revenue)) / NULLIF(SUM(starting_mrr), 0) * 100",
        "unit": "%",
        "direction": "up_is_good",
        "description": "Net Revenue Retention (%)",
        "aliases": ["net revenue retention", "ndr", "net dollar retention"],
    },

    # Operational
    "orders": {
        "sql": "COUNT(DISTINCT order_id)",
        "unit": None,
        "direction": "up_is_good",
        "description": "Total Order Count",
        "aliases": ["order count", "number of orders", "total orders"],
    },
    "aov": {
        "sql": "SUM(order_value) / NULLIF(COUNT(DISTINCT order_id), 0)",
        "unit": "$",
        "direction": "up_is_good",
        "description": "Average Order Value",
        "aliases": ["average order value", "avg order", "aov"],
    },
    "conversion_rate": {
        "sql": "COUNT(DISTINCT converted_user_id) * 1.0 / NULLIF(COUNT(DISTINCT user_id), 0) * 100",
        "unit": "%",
        "direction": "up_is_good",
        "description": "Conversion Rate (%)",
        "aliases": ["conversion", "cvr", "conversion rate"],
    },
    "roas": {
        "sql": "SUM(sales) / NULLIF(SUM(ad_spend), 0)",
        "unit": "x",
        "direction": "up_is_good",
        "description": "Return on Ad Spend",
        "aliases": ["return on ad spend", "roas", "ad efficiency"],
    },
}


class MetricStore:
    """Resolves natural language metric mentions to verified SQL expressions."""

    def resolve(self, metric_name: str) -> Optional[Dict]:
        """
        Look up a metric by name or alias.
        Returns the full metric definition or None if not found.
        """
        name = (metric_name or "").lower().strip()
        if not name:
            return None

        # Direct key match
        if name in METRIC_REGISTRY:
            return {"key": name, **METRIC_REGISTRY[name]}

        # Alias match
        for key, info in METRIC_REGISTRY.items():
            if name in [a.lower() for a in info.get("aliases", [])]:
                return {"key": key, **info}

        return None

    def inject_metric_sql(self, intent: Dict, prompt_context: str, available_columns: List[str] = None) -> str:
        """
        Given an intent dict and available columns, look up the metric,
        dynamically map its columns to the schema, and inject the SQL.
        """
        metric_name = intent.get("metric", "")
        definition = self.resolve(metric_name)
        if not definition:
            return prompt_context

        sql_expr = definition['sql']
        # Dynamically map column names if schema is provided
        if available_columns:
            # Common mappings for metric components
            # "SUM(sales)" -> find closest to 'sales' in available_columns
            cols_to_map = ["revenue", "sales", "profit", "cogs", "operating_expenses", "amount", "order_value", "ad_spend"]
            for col in cols_to_map:
                if col in sql_expr.lower():
                    # Find closest match in available_columns
                    match = self._find_best_col_match(col, available_columns)
                    if match and match.lower() != col:
                        # Use regex for safe replacement of the column name token
                        sql_expr = re.sub(rf'\b{col}\b', match, sql_expr, flags=re.IGNORECASE)

        metric_note = (
            f"\n\n[METRIC DEFINITION]\n"
            f"'{definition['description']}' should be calculated as:\n"
            f"  SQL Expression: {sql_expr}\n"
            f"  Unit: {definition.get('unit', 'count')}\n"
            f"  Direction (good = {definition.get('direction', 'up_is_good').replace('_', ' ')})\n"
            f"Use this exact expression in the SQL query. Do not invent a different formula.\n"
        )
        logger.info(f"MetricStore: resolved '{metric_name}' → {definition['key']} (mapped SQL: {sql_expr})")
        return prompt_context + metric_note

    def _find_best_col_match(self, target: str, columns: List[str]) -> Optional[str]:
        """Fuzzy match conceptual column name to real schema columns."""
        target = target.lower()
        # 1. Exact match
        for c in columns:
            if c.lower() == target: return c
        
        # 2. Contains match
        for c in columns:
            if target in c.lower() or c.lower() in target: return c
        
        # 3. Handle 'revenue'/'sales' equivalence
        if target in ["revenue", "sales"]:
            for c in columns:
                cl = c.lower()
                if "sales" in cl or "revenue" in cl or "income" in cl or "amount" in cl:
                    return c
        
        return None

    def all_metrics(self) -> list:
        """Return a list of all registered metrics for the UI metric browser."""
        return [
            {
                "key": k,
                "description": v["description"],
                "unit": v.get("unit"),
                "direction": v.get("direction"),
                "aliases": v.get("aliases", []),
            }
            for k, v in METRIC_REGISTRY.items()
        ]
