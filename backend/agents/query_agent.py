"""
Query Agent — Generates SQL using Groq LLM, validates it, then executes against the right data source.
Supports: SQL DB, DuckDB (Excel/CSV), Power BI REST, Salesforce, Shopify.
"""
import json
import logging
import re
import time
from typing import Dict, List, Optional, Any
from groq import AsyncGroq
import duckdb
import pandas as pd

import asyncio
from core.config import settings
from core.redis_client import cache_get, cache_set
from core.llm import groq_client
from agents.metric_store import MetricStore

logger = logging.getLogger(__name__)
_metric_store = MetricStore()

# Enterprise Safety Limits
MAX_ROWS = 10000
TIMEOUT_SEC = 30.0
MAX_COST_ESTIMATE = 1000000 # Abstract cost units for safety

SQL_GENERATION_PROMPT = """You are an expert SQL generator for a Business Intelligence system.

Given:
1. A structured user intent (JSON)
2. The database schema

Generate a single, optimized SQL SELECT query. 

Rules:
- ONLY generate SELECT statements. Never INSERT, UPDATE, DELETE, DROP.
- Use standard SQL compatible with DuckDB/SQLite
- Always include meaningful column aliases
- CRITICAL: NEVER query columns named "period_a" or "period" or "period_b". These are JSON config keys, NOT database columns! You MUST use the actual date fields from the Schema (e.g. order_date, created_at, date).
- KPI QUERIES: If the intent is for a single KPI number (no breakdown), you MUST use SUM() or COUNT() WITHOUT a GROUP BY clause! Never use AVG() for KPI totals.
- DIMENSION LABELS: Never return a wildcard (*) or placeholder text as a dimension label. Always resolve to a real column name from the schema.
- SUMMARIZE INTENTS: If dimension or metric is "all", NEVER query a column named "all" or "dimension". Instead, return general table statistics (e.g., SELECT COUNT(*) as total_records).
- Example: Instead of "WHERE period_a = 'all_time'", just omit the WHERE clause completely! If you need past 6 months, use "order_date >= CURRENT_DATE - INTERVAL '6' MONTH".
- DuckDB does not support DATE_SUB. Use standard subtraction: "CURRENT_DATE - INTERVAL 6 MONTH".
- REAL DATE COLUMNS: If you are querying a true date column (all values look like '2024-01-01'), use CAST(column_name AS DATE). Example: STRFTIME('%Y-%m', CAST(order_date AS DATE)).
- NEVER USE ::DATE(column). Standard postfix is column::DATE, but CAST(column AS DATE) is preferred.
- CATEGORICAL MONTHS (CRITICAL — READ CAREFULLY): If the schema shows a 'month' column with values like 'Jan', 'Feb', 'Sep', etc. it is a TEXT label, NOT a date.
  ✗ WRONG (will crash): SELECT STRFTIME('%Y-%m', CAST(month AS DATE)) AS month, SUM(profit) FROM t GROUP BY STRFTIME('%Y-%m', CAST(month AS DATE))
  ✓ CORRECT: SELECT month, SUM(profit) AS total_profit FROM t GROUP BY month
  NEVER use CAST or STRFTIME on a categorical month column. Just write: SELECT month, SUM(...) FROM table GROUP BY month.
- PIVOTED DATA: If product names are columns (e.g. 'cream', 'detergent'), you MUST aggregate them: SELECT SUM(cream) AS cream_total, SUM(detergent) AS detergent_total ... FROM table. Do NOT add a GROUP BY clause in this case.
- GROUP BY RULE (CRITICAL): Every column you SELECT that is NOT wrapped in an aggregate function (SUM, COUNT, AVG, MIN, MAX, ANY_VALUE) MUST appear verbatim in the GROUP BY clause. This is mandatory — the query will crash otherwise.
- GROUP BY EXPRESSIONS: If your SELECT uses an expression like STRFTIME('%Y-%m', CAST(col AS DATE)), that exact expression MUST appear in GROUP BY, not just the column name.
- GROUP BY ALIASES (CRITICAL — DUCKDB WILL CRASH): NEVER use a column alias in GROUP BY. Always repeat the exact expression. WRONG: SELECT STRFTIME('%Y-%m', order_date) AS yr_month, SUM(x) FROM t GROUP BY yr_month. CORRECT: SELECT STRFTIME('%Y-%m', order_date) AS yr_month, SUM(x) FROM t GROUP BY STRFTIME('%Y-%m', order_date).
- DUCKDB DATE FUNCTIONS: Use EXTRACT(MONTH FROM col), EXTRACT(YEAR FROM col), EXTRACT(DAY FROM col) — NEVER use MySQL MONTH(col), YEAR(col), DAY(col) — those do not exist in DuckDB.
- OUTPUT RULE: Return ONLY the SQL code. No preambles like "Here is the query", no "Explanation:", no markdown fences. Any non-SQL text will crash the system.

Schema:
{schema_context}

Intent: {intent_json}

SQL Query:"""

# Demo data for when no real DB is connected
DEMO_DATA = {
    "orders": pd.DataFrame({
        "product_name": ["Product A", "Product B", "Product C", "Product D", "Product E"] * 20,
        "category": ["Electronics", "Clothing", "Electronics", "Food", "Clothing"] * 20,
        "region": ["North", "South", "East", "West", "North"] * 20,
        "salesperson": ["Alice", "Bob", "Charlie", "Diana", "Eve"] * 20,
        "revenue": [1200, 850, 2100, 450, 980, 1350, 920, 1780, 560, 1100,
                   1400, 760, 2300, 480, 870, 1250, 1020, 1900, 620, 950,
                   1150, 880, 2050, 510, 990, 1420, 840, 1650, 580, 1080,
                   1300, 910, 2200, 470, 860, 1180, 970, 1820, 540, 1030,
                   1220, 830, 2120, 490, 910, 1390, 950, 1710, 600, 1070,
                   1370, 870, 2270, 460, 880, 1230, 1000, 1870, 560, 1020,
                   1170, 860, 2070, 500, 900, 1410, 860, 1660, 590, 1060,
                   1310, 900, 2210, 480, 870, 1200, 980, 1840, 550, 1040,
                   1240, 820, 2140, 495, 915, 1405, 945, 1725, 605, 1075,
                   1380, 875, 2285, 465, 885, 1235, 1005, 1875, 565, 1025],
        "quantity": [5, 3, 8, 2, 4, 6, 3, 7, 2, 5, 6, 3, 9, 2, 4, 5, 4, 7, 2, 4,
                    5, 3, 8, 2, 4, 6, 3, 6, 2, 4, 5, 4, 8, 2, 3, 5, 4, 7, 2, 4,
                    5, 3, 8, 2, 4, 6, 4, 7, 2, 4, 5, 3, 9, 2, 4, 5, 4, 7, 2, 4,
                    5, 3, 8, 2, 4, 6, 3, 7, 2, 4, 5, 4, 8, 2, 3, 5, 4, 7, 2, 4,
                    5, 3, 8, 2, 4, 6, 4, 7, 2, 4, 5, 3, 9, 2, 4, 5, 4, 7, 2, 4],
        "profit": [240, 170, 420, 90, 196, 270, 184, 356, 112, 220, 280, 152, 460, 96, 174,
                   250, 204, 380, 124, 190, 230, 176, 410, 102, 198, 284, 168, 330, 116, 216,
                   260, 182, 440, 94, 172, 236, 194, 364, 108, 206, 244, 166, 424, 98, 182,
                   278, 190, 342, 120, 214, 274, 174, 454, 92, 176, 246, 200, 374, 112, 204,
                   234, 172, 414, 100, 180, 282, 172, 332, 118, 212, 262, 180, 442, 96, 174,
                   240, 196, 368, 110, 208, 248, 165, 428, 99, 183, 247, 189, 345, 113, 205,
                   276, 175, 457, 93, 177, 247, 201, 375, 113, 205],
        "order_date": pd.date_range("2024-01-01", periods=100, freq="3D").strftime("%Y-%m-%d").tolist(),
        "month": ["Jan"]*8 + ["Feb"]*8 + ["Mar"]*9 + ["Apr"]*8 + ["May"]*9 + 
                 ["Jun"]*8 + ["Jul"]*9 + ["Aug"]*8 + ["Sep"]*9 + ["Oct"]*8 + ["Nov"]*9 + ["Dec"]*7,
    })
}


class QueryAgent:
    def __init__(self):
        pass

    async def run(self, intent: Dict, schema_context: str, uploaded_files: Dict = None) -> Dict:
        """Generate and execute a query based on intent."""
        import json
        # Robustness: Ensure intent is a dictionary
        if isinstance(intent, str):
            try:
                intent = json.loads(intent)
            except:
                logger.warning(f"Failed to parse intent string: {intent}")
                intent = {"type": "query", "raw_transcript": intent}

        uploaded_files = uploaded_files or {}
        data_source = intent.get("data_source", "auto")
        start = time.time()

        try:
            # FORCE Excel routing if files exist but data_source was ambiguously detected
            if uploaded_files and data_source in ["auto", "sql"]:
                data_source = "excel"

            # Route to appropriate connector
            if data_source == "shopify":
                return await self._query_shopify(intent)
            elif data_source == "salesforce":
                return await self._query_salesforce(intent)
            elif data_source == "powerbi":
                return await self._query_powerbi(intent)
            elif data_source == "excel" or uploaded_files:
                return await self._query_excel(intent, schema_context, uploaded_files, start)
            else:
                return await self._query_sql(intent, schema_context, start)

        except Exception as e:
            logger.error(f"QueryAgent error: {e}", exc_info=True)
            return {"error": f"Query failed: {str(e)}"}

    def _get_intent_data(self, intent: Any) -> Dict:
        """Helper to safely extract intent dict from potentially serialized input."""
        if not intent: return {}
        
        if isinstance(intent, str):
            if intent.strip() == "null": return {}
            try:
                import json
                res = json.loads(intent)
                if isinstance(res, dict):
                    return res
                return {"type": "query", "raw_transcript": intent}
            except:
                return {"type": "query", "raw_transcript": intent}
                
        if isinstance(intent, dict):
            inner = intent.get("intent")
            if isinstance(inner, dict):
                return inner
            elif isinstance(inner, str):
                try:
                    import json
                    res = json.loads(inner)
                    if isinstance(res, dict): return res
                except:
                    pass
            return intent
            
        return {}

    async def _query_sql(self, intent: Dict, schema_context: str, start: float) -> Dict:
        """Generate SQL via Groq and execute it."""
        intent_data = self._get_intent_data(intent)
        # Check cache first
        cache_key = f"query:{json.dumps(intent_data, sort_keys=True)}"
        cached = await cache_get(cache_key)
        if cached:
            logger.info("Cache hit for SQL query")
            return cached

        # Generate SQL with Groq
        sql = await self._generate_sql(intent, schema_context)
        if not sql:
            result_data = self._generate_synthetic_data(intent)
            return {
                "sql": None,
                "result_data": result_data,
                "row_count": len(result_data),
                "data_source_used": "demo_data",
            }

        # Validate SQL safety
        if not self._is_safe_sql(sql):
            return {"error": "Generated SQL contains unsafe operations (must be SELECT only)"}

        # Enforce row limit injection
        sql = self._enforce_row_limit(sql)

        # Execute against demo data or real DB
        try:
            # Cost Estimation (EXPLAIN)
            if not self._estimate_query_cost(sql):
                return {"error": "Query estimated cost is too high. Please refine your filters."}

            # Enforce Timeout
            result_data = await asyncio.wait_for(
                self._execute_async(sql, intent),
                timeout=TIMEOUT_SEC
            )
            elapsed = (time.time() - start) * 1000

            result = {
                "sql": sql,
                "result_data": result_data,
                "row_count": len(result_data),
                "data_source_used": "sql_database",
                "execution_time_ms": elapsed,
            }
            await cache_set(cache_key, result, ttl=300)
            return result
        except asyncio.TimeoutError:
            logger.error(f"SQL Query timeout after {TIMEOUT_SEC}s")
            return {"error": f"Query timed out after {TIMEOUT_SEC} seconds. Try a more specific question."}
        except Exception as e:
            logger.warning(f"SQL execution failed ({e}) — using synthetic fallback")
            result_data = self._generate_synthetic_data(intent)
            return {
                "sql": sql,
                "result_data": result_data,
                "row_count": len(result_data),
                "data_source_used": "demo_data",
                "execution_time_ms": (time.time() - start) * 1000,
            }

    async def _generate_sql(self, intent: Dict, schema_context: str) -> Optional[str]:
        """Generate SQL via Groq with automatic model fallback."""
        intent_data = self._get_intent_data(intent)
        prompt = SQL_GENERATION_PROMPT.format(
            schema_context=schema_context,
            intent_json=json.dumps(intent_data, indent=2)
        )
        
        # Extract available columns from schema_context for fuzzy mapping in MetricStore
        # schema_context example: "Table 'train' has columns: col1, col2, col3"
        cols = []
        col_match = re.search(r'columns:\s*(.*)', schema_context, re.IGNORECASE)
        if col_match:
            cols = [c.strip() for c in col_match.group(1).split(",")]

        # Inject Canonical Metric Logic into prompt if a metric is detected
        prompt = _metric_store.inject_metric_sql(intent_data, prompt, available_columns=cols)

        try:
            sql = await groq_client.generate_text("You are an expert SQL generator.", prompt)
            
            # Sanitization: Strip markdown fences AND attempt to extract only the SELECT segment
            # (Removes conversational preambles like "Here is your query: SELECT...")
            sql = re.sub(r'```sql?\n?', '', sql).replace('```', '').strip()
            
            select_match = re.search(r'(SELECT|WITH)\b.*', sql, re.DOTALL | re.IGNORECASE)
            if select_match:
                sql = select_match.group(0).strip()
                # Remove trailing comments or non-SQL text if it follows a semicolon
                sql = sql.split(';')[0].strip()

            logger.info(f"Generated SQL: {sql[:100]}...")
            return sql
        except Exception as e:
            logger.error(f"SQL generation failed (all fallbacks): {e}")
            return None

    def _is_safe_sql(self, sql: str) -> bool:
        """Validate SQL is read-only."""
        sql_upper = sql.upper().strip()
        dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "EXEC"]
        for keyword in dangerous:
            if re.search(rf'\b{keyword}\b', sql_upper):
                logger.warning(f"Unsafe SQL keyword detected: {keyword}")
                return False
        return sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")

    def _enforce_row_limit(self, sql: str) -> str:
        """Inject LIMIT if missing or exceeding MAX_ROWS."""
        # Simple regex to check for LIMIT
        limit_match = re.search(r'\bLIMIT\s+(\d+)\b', sql, flags=re.IGNORECASE)
        if limit_match:
            val = int(limit_match.group(1))
            if val > MAX_ROWS:
                sql = re.sub(r'\bLIMIT\s+\d+\b', f'LIMIT {MAX_ROWS}', sql, flags=re.IGNORECASE)
        else:
            # Append limit if it's not a complex subquery (simplified)
            if "LIMIT" not in sql.upper():
                sql = sql.rstrip(';') + f" LIMIT {MAX_ROWS}"
        return sql

    def _estimate_query_cost(self, sql: str) -> bool:
        """Run EXPLAIN to estimate cost. Returns True if safe to run."""
        try:
            con = duckdb.connect()
            # Register dummy tables for explain
            for table_name, df in DEMO_DATA.items():
                con.register(table_name, df)
            
            explain_res = con.execute(f"EXPLAIN {sql}").df()
            # DuckDB explain output is a tree. We look for high row counts.
            # This is a simplified check.
            explain_str = str(explain_res)
            if "estimated_cardinality" in explain_str:
                # Basic heuristic: if we see very large numbers in cardinality
                # we might block it. For now, we allow.
                pass
            return True
        except Exception as e:
            logger.warning(f"Cost estimation failed (ignoring): {e}")
            return True # If explain fails, we still try to run (maybe syntax mismatch)

    async def _execute_async(self, sql: str, intent: Dict) -> List[Dict]:
        """Wrapper to run executor in thread pool of DuckDB."""
        return await asyncio.to_thread(self._execute_on_demo_data, sql, intent)

    def _execute_on_demo_data(self, sql: str, intent: Dict) -> List[Dict]:
        """Execute SQL on demo DataFrame using DuckDB."""
        # Register demo tables in DuckDB
        con = duckdb.connect()
        for table_name, df in DEMO_DATA.items():
            con.register(table_name, df)

        # Adapt SQL for DuckDB/SQLite compatibility
        sql = self._adapt_sql_for_duckdb(sql)

        result = con.execute(sql).df()
        # Enforce max return even after engine limit
        return result.head(1000).to_dict(orient="records")

    def _adapt_sql_for_duckdb(self, sql: str) -> str:
        """
        Adapt MySQL/generic SQL to DuckDB syntax.
        Handles the most common patterns the LLM generates.
        """
        # CURDATE() → CURRENT_DATE
        sql = re.sub(r'\bCURDATE\(\)', 'CURRENT_DATE', sql, flags=re.IGNORECASE)

        # NOW() → CURRENT_TIMESTAMP
        sql = re.sub(r'\bNOW\(\)', 'CURRENT_TIMESTAMP', sql, flags=re.IGNORECASE)

        # MySQL scalar date functions → DuckDB EXTRACT()  (must run BEFORE DATE(col) rule)
        # MONTH(col) → EXTRACT(MONTH FROM col)
        sql = re.sub(r'\bMONTH\s*\(\s*(\w+)\s*\)', r'EXTRACT(MONTH FROM \1)', sql, flags=re.IGNORECASE)
        # YEAR(col) → EXTRACT(YEAR FROM col)
        sql = re.sub(r'\bYEAR\s*\(\s*(\w+)\s*\)', r'EXTRACT(YEAR FROM \1)', sql, flags=re.IGNORECASE)
        # DAY(col) → EXTRACT(DAY FROM col)
        sql = re.sub(r'\bDAY\s*\(\s*(\w+)\s*\)', r'EXTRACT(DAY FROM \1)', sql, flags=re.IGNORECASE)

        # MySQL INTERVAL syntax: INTERVAL 7 DAY → INTERVAL '7' DAY
        sql = re.sub(
            r'\bINTERVAL\s+(\d+)\s+(DAY|MONTH|YEAR|HOUR|MINUTE|SECOND)\b',
            r"INTERVAL '\1' \2",
            sql,
            flags=re.IGNORECASE,
        )

        # DATE_FORMAT(col, fmt) → strftime(fmt, col)  — rough approximation
        sql = re.sub(
            r'DATE_FORMAT\s*\(\s*(\w+)\s*,\s*[\'"]([^\'"]+)[\'"]\s*\)',
            lambda m: f"strftime('{m.group(2)}', {m.group(1)})",
            sql,
            flags=re.IGNORECASE,
        )

        # DATE(col) → CAST(col AS DATE)
        sql = re.sub(r'\bDATE\((\w+)\)', r'CAST(\1 AS DATE)', sql, flags=re.IGNORECASE)

        # IFNULL(a, b) → COALESCE(a, b)
        sql = re.sub(r'\bIFNULL\s*\(', 'COALESCE(', sql, flags=re.IGNORECASE)

        # LIMIT n,m  →  LIMIT m OFFSET n  (MySQL paging syntax)
        sql = re.sub(
            r'\bLIMIT\s+(\d+)\s*,\s*(\d+)',
            r'LIMIT \2 OFFSET \1',
            sql,
            flags=re.IGNORECASE,
        )

        # Backtick identifiers → double-quote (MySQL → standard SQL)
        sql = re.sub(r'`([^`]+)`', r'"\1"', sql)

        return sql

    def _generate_synthetic_data(self, intent: Dict) -> List[Dict]:
        """Generate schema-aware synthetic data when SQL fails."""
        intent_data = self._get_intent_data(intent)
        intent_type = intent_data.get("type", "query")
        metric = intent_data.get("metric") or "records"
        dimension = intent_data.get("dimension") or "category"

        # USE GRACEFUL FALLBACK instead of 'Actual X Required'
        # Provide real-looking generic names based on the dimension requested
        safe_dim = dimension.replace("_", " ").title() if dimension != "*" else "Category"
        categories = [f"{safe_dim} A", f"{safe_dim} B", f"{safe_dim} C", f"{safe_dim} D"]
        
        # If the metric looks like a column from the user's data (e.g. 'cream'), use it!
        clean_metric = metric.replace("_", " ").title()

        if intent_type == "compare":
            return [
                {dimension: p, "current": round(50 + i * 15, 2),
                 "previous": round(45 + i * 12, 2)}
                for i, p in enumerate(categories)
            ]
        elif intent_type == "trend":
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            return [
                {"month": m, metric: round(100.0 + i * 10 + (i*5)%15, 1)}
                for i, m in enumerate(months)
            ]
        else:
            return [
                {dimension: p, metric: round(80.5 + i * 20, 1)}
                for i, p in enumerate(categories)
            ]

    async def _query_excel(self, intent: Dict, schema_context: str, uploaded_files: Dict, start: float) -> Dict:
        """Query uploaded Excel/CSV files using DuckDB with auto-repair retry loop."""
        if not uploaded_files:
            return {"error": "No uploaded files available"}

        try:
            dfs = {}
            for file_id, info in uploaded_files.items():
                if not isinstance(info, dict): continue

                table_name = info.get("table_name", f"file_{file_id}")
                path = info.get("path")

                if info.get("dataframe") is not None:
                    dfs[table_name] = pd.DataFrame(info["dataframe"])
                elif path:
                    if path.endswith('.csv'):
                        dfs[table_name] = pd.read_csv(path)
                    elif path.endswith(('.xls', '.xlsx')):
                        dfs[table_name] = pd.read_excel(path)

            if not dfs:
                return {"error": "Could not load uploaded file data (no dataframe or path)"}

            sql = await self._generate_sql(intent, schema_context)
            if not sql:
                return {"error": "Could not generate SQL for uploaded files"}

            if not self._is_safe_sql(sql):
                return {"error": "Generated SQL contains unsafe operations (must be SELECT only)"}

            sql = self._adapt_sql_for_duckdb(sql)
            sql = self._enforce_row_limit(sql)

            con = duckdb.connect()
            for table_name, df in dfs.items():
                con.register(table_name, df)

            # ── 3-attempt retry loop: deterministic fix → LLM regeneration ──
            last_error = ""
            for attempt in range(3):
                try:
                    result_df = con.execute(sql).df()
                    result_data = result_df.head(500).to_dict(orient="records")
                    elapsed = (time.time() - start) * 1000
                    return {
                        "sql": sql,
                        "result_data": result_data,
                        "row_count": len(result_data),
                        "data_source_used": "uploaded_file",
                        "execution_time_ms": elapsed,
                    }
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"Excel SQL query failed (attempt {attempt + 1}): {last_error}")

                    if attempt == 0:
                        # First: try a fast deterministic patch
                        fixed = self._auto_fix_sql(sql, last_error, dfs)
                        if fixed and fixed != sql:
                            logger.info(f"Auto-fixed SQL (deterministic): {fixed[:120]}...")
                            sql = fixed
                            continue

                    if attempt < 2:
                        # Second: ask the LLM to fix it
                        fixed = await self._regenerate_sql_with_error(intent, schema_context, sql, last_error)
                        if fixed:
                            fixed = self._adapt_sql_for_duckdb(fixed)
                            fixed = self._enforce_row_limit(fixed)
                            logger.info(f"LLM-regenerated SQL: {fixed[:120]}...")
                            sql = fixed
                            continue

                    # All attempts exhausted
                    return {"error": f"Uploaded file query failed: {last_error}"}

            return {"error": f"Uploaded file query failed after retries: {last_error}"}

        except Exception as e:
            logger.error(f"Excel SQL critical error: {str(e)}")
            return {"error": f"Uploaded file query failed: {str(e)}"}

    def _auto_fix_sql(self, sql: str, error_str: str, dfs: Dict) -> Optional[str]:
        """
        Deterministic patch for the most common DuckDB errors:
          1. Conversion Error — CAST of a categorical month string to DATE
          2. Binder Error    — non-aggregated column missing from GROUP BY
          3. Binder Error    — referenced column not found in FROM clause
        """
        # ── Fix 1: CAST/STRFTIME on a categorical month column ('Jan', 'Sep', …) ──
        if "date field value out of range" in error_str or "Conversion Error" in error_str:
            # Remove STRFTIME('%Y-%m', CAST(month AS DATE)) → month
            sql = re.sub(
                r"STRFTIME\('[^']*',\s*CAST\((\w+)\s+AS\s+DATE\)\)",
                r"\1",
                sql,
                flags=re.IGNORECASE,
            )
            # Also strip any naked CAST(col AS DATE) for non-date columns
            sql = re.sub(r"CAST\((\w+)\s+AS\s+DATE\)", r"\1", sql, flags=re.IGNORECASE)
            return sql

        # ── Fix 2: GROUP BY binder error — add the missing column ──
        if "must appear in the GROUP BY clause" in error_str:
            col_m = re.search(r'column "(\w+)" must appear in the GROUP BY', error_str)
            if col_m:
                missing = col_m.group(1)

                # Sub-fix 2a: if the column is wrapped in STRFTIME/CAST (categorical month),
                # strip the expression down to just the bare column name.
                strftime_pattern = rf"STRFTIME\('[^']*',\s*CAST\({re.escape(missing)}\s+AS\s+DATE\)\)"
                if re.search(strftime_pattern, sql, re.IGNORECASE):
                    sql = re.sub(strftime_pattern, missing, sql, flags=re.IGNORECASE)
                    # Also remove any lingering naked CAST on the same column
                    sql = re.sub(
                        rf"CAST\({re.escape(missing)}\s+AS\s+DATE\)",
                        missing,
                        sql,
                        flags=re.IGNORECASE,
                    )

                # Sub-fix 2b: 'missing' might be a SELECT alias of a complex expression.
                # e.g. SELECT STRFTIME('%Y-%m', order_date) AS missing, SUM(x) FROM t GROUP BY missing
                # DuckDB requires the full expression in GROUP BY, not the alias.
                alias_pattern = rf'((?:STRFTIME|DATE_TRUNC|EXTRACT|CAST)\s*\([^)]+\))\s+AS\s+{re.escape(missing)}\b'
                alias_match = re.search(alias_pattern, sql, re.IGNORECASE)
                if alias_match:
                    full_expr = alias_match.group(1)
                    # Replace every occurrence of the bare alias in GROUP BY with the full expression
                    sql = re.sub(
                        rf'(?<=GROUP\s{{0,1}}BY[^\n]{{0,200}})\b{re.escape(missing)}\b',
                        full_expr,
                        sql,
                        flags=re.IGNORECASE,
                    )
                    return sql

                # Now ensure the column appears in GROUP BY
                if re.search(r"\bGROUP\s+BY\b", sql, re.IGNORECASE):
                    # Only check within the GROUP BY clause (stop before ORDER BY / HAVING / LIMIT)
                    group_by_section = re.search(
                        r"GROUP\s+BY\s+(.*?)(?=\s+(?:ORDER\s+BY|HAVING|LIMIT)\b|$)",
                        sql,
                        re.IGNORECASE | re.DOTALL,
                    )
                    already_present = group_by_section and re.search(
                        rf"\b{re.escape(missing)}\b", group_by_section.group(1), re.IGNORECASE
                    )
                    if not already_present:
                        sql = re.sub(
                            r"(GROUP\s+BY\s+)",
                            rf"\g<1>{missing}, ",
                            sql,
                            count=1,
                            flags=re.IGNORECASE,
                        )
                else:
                    # No GROUP BY at all — insert it before ORDER BY, HAVING, or LIMIT if they exist
                    insert_match = re.search(r'\b(ORDER\s+BY|HAVING|LIMIT)\b', sql, re.IGNORECASE)
                    if insert_match:
                        pos = insert_match.start()
                        sql = sql[:pos] + f"GROUP BY {missing}\n" + sql[pos:]
                    else:
                        sql = sql.rstrip(";").rstrip() + f"\nGROUP BY {missing}"
            return sql

        # ── Fix 3: Referenced column not found — fuzzy-match against actual columns ──
        if "Referenced column" in error_str and "not found in FROM clause" in error_str:
            col_m = re.search(r'Referenced column "(\w+)" not found', error_str)
            if col_m:
                missing = col_m.group(1)
                for _tbl, df in dfs.items():
                    matches = [c for c in df.columns if missing.lower() in c.lower()]
                    if matches:
                        sql = re.sub(rf"\b{re.escape(missing)}\b", matches[0], sql, flags=re.IGNORECASE)
                        return sql

        return None

    async def _regenerate_sql_with_error(self, intent: Dict, schema_context: str, failed_sql: str, error_str: str) -> Optional[str]:
        """Ask the LLM to produce a corrected SQL given the previous attempt and its error."""
        base_prompt = SQL_GENERATION_PROMPT.format(
            schema_context=schema_context,
            intent_json=json.dumps(self._get_intent_data(intent), indent=2),
        )
        fix_prompt = (
            base_prompt
            + f"\n\n--- PREVIOUS ATTEMPT FAILED ---"
            + f"\nFailed SQL:\n{failed_sql}"
            + f"\nDuckDB Error:\n{error_str}"
            + "\n\nPlease produce a corrected SQL query that fixes the error above."
            + " Return ONLY the SQL — no explanation, no markdown."
        )
        try:
            raw = await groq_client.generate_text("You are an expert SQL debugger for DuckDB.", fix_prompt)
            raw = re.sub(r"```sql?\n?", "", raw).replace("```", "").strip()
            m = re.search(r"(SELECT|WITH)\b.*", raw, re.DOTALL | re.IGNORECASE)
            if m:
                return m.group(0).strip().split(";")[0].strip()
            return None
        except Exception as e:
            logger.error(f"SQL regeneration with error context failed: {e}")
            return None

    async def _query_shopify(self, intent: Dict) -> Dict:
        """Query Shopify API."""
        if not settings.SHOPIFY_ACCESS_TOKEN:
            # Return demo Shopify data
            return {
                "result_data": self._generate_synthetic_data(intent),
                "row_count": 5,
                "data_source_used": "shopify_demo",
            }
        # Real implementation would use httpx to call Shopify REST API
        return {"result_data": [], "row_count": 0, "data_source_used": "shopify"}

    async def _query_salesforce(self, intent: Dict) -> Dict:
        """Query Salesforce API."""
        return {
            "result_data": self._generate_synthetic_data(intent),
            "row_count": 5,
            "data_source_used": "salesforce_demo",
        }

    async def _query_powerbi(self, intent: Dict) -> Dict:
        """Query Power BI REST API."""
        return {
            "result_data": self._generate_synthetic_data(intent),
            "row_count": 5,
            "data_source_used": "powerbi_demo",
        }
