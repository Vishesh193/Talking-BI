"""
Schema Agent — Retrieves relevant schema context from the registry.
Uses the intent to find the right tables/columns for NL→SQL generation.
"""
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.config import settings
from core.database import async_session_maker

logger = logging.getLogger(__name__)

# Schema Caching & Filtering Limits
SCHEMA_CACHE: Dict[str, Tuple[str, float, str]] = {} # {db_url: (schema_text, timestamp, checksum)}
CACHE_TTL = 3600 # 1 hour
MAX_TABLES_IN_CONTEXT = 15 # Top relevant tables to include

# Built-in schema descriptions for demo data
DEMO_SCHEMA = """
=== AVAILABLE TABLES ===

TABLE: orders
  - id (INTEGER) — Unique order ID
  - customer_id (INTEGER) — Customer reference
  - product_id (INTEGER) — Product reference  
  - product_name (VARCHAR) — Product name [dimension]
  - category (VARCHAR) — Product category [dimension]
  - region (VARCHAR) — Sales region [dimension]
  - salesperson (VARCHAR) — Salesperson name [dimension]
  - revenue (DECIMAL) — Order revenue in USD [metric]
  - quantity (INTEGER) — Units sold [metric]
  - cost (DECIMAL) — Cost of goods [metric]
  - profit (DECIMAL) — Profit (revenue - cost) [metric]
  - order_date (DATE) — Date of order [time dimension]
  - status (VARCHAR) — Order status: completed|pending|cancelled

TABLE: customers
  - id (INTEGER) — Unique customer ID
  - name (VARCHAR) — Customer name [dimension]
  - email (VARCHAR) — Email address
  - region (VARCHAR) — Customer region [dimension]
  - segment (VARCHAR) — Customer segment: enterprise|smb|startup [dimension]
  - created_at (DATE) — Acquisition date [time dimension]
  - is_churned (BOOLEAN) — Churn flag [metric]
  - lifetime_value (DECIMAL) — Customer LTV [metric]

TABLE: products
  - id (INTEGER) — Unique product ID
  - name (VARCHAR) — Product name [dimension]
  - category (VARCHAR) — Category [dimension]
  - price (DECIMAL) — Unit price [metric]
  - cost (DECIMAL) — Unit cost [metric]
  - inventory (INTEGER) — Stock count [metric]

TABLE: marketing_campaigns
  - id (INTEGER) — Campaign ID
  - name (VARCHAR) — Campaign name [dimension]
  - channel (VARCHAR) — Channel: email|paid|social|organic [dimension]
  - spend (DECIMAL) — Ad spend [metric]
  - clicks (INTEGER) — Click count [metric]
  - conversions (INTEGER) — Conversion count [metric]
  - revenue_attributed (DECIMAL) — Revenue attributed [metric]
  - start_date (DATE), end_date (DATE) — Campaign dates

=== DATE/TIME HELPERS (DuckDB syntax ONLY) ===
current_month: WHERE EXTRACT(MONTH FROM order_date) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE)
previous_month: WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1' MONTH) AND order_date < DATE_TRUNC('month', CURRENT_DATE)
last_7_days: WHERE order_date >= CURRENT_DATE - INTERVAL '7' DAY
this_year: WHERE EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE)
last_year: WHERE EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE) - 1
today: WHERE CAST(order_date AS DATE) = CURRENT_DATE
"""


class SchemaAgent:
    def __init__(self):
        self._analytics_engine = None
        if settings.ANALYTICS_DB_URL:
            self._analytics_engine = create_async_engine(settings.ANALYTICS_DB_URL)

    async def run(self, intent: Dict, uploaded_files: Dict = None) -> Dict:
        """Get relevant schema context for the intent, prioritizing user data."""
        try:
            data_source = intent.get("data_source", "auto")
            schema_context = ""
            has_user_data = False

            # IF UPLOADED FILES EXIST — ISOLATE TO THEM ONLY
            if uploaded_files:
                schema_context = self._get_uploaded_file_schemas(uploaded_files)
                return {"schema_context": schema_context}

            # 2. SQL database schema
            if data_source == "sql" or (data_source == "auto" and settings.ANALYTICS_DB_URL):
                if self._analytics_engine:
                    db_schema = await self._get_cached_database_schema(intent)
                    schema_context += f"\n\n=== CORPORATE DATABASE ===\n{db_schema}"
                    has_user_data = True

            # 3. KPI registry context
            kpi_context = await self._get_kpi_context(intent.get("metric"))
            if kpi_context:
                schema_context += f"\n\n=== VERIFIED METRICS ===\n{kpi_context}"

            # 4. Demo schema fallback (ONLY if no other data exists or if explicitly requested)
            if not has_user_data or data_source == "demo":
                 schema_context += f"\n\n=== DEMO DATASET (Use only if specifically asked for Sales/Revenue) ===\n{DEMO_SCHEMA}"

            return {"schema_context": schema_context}

        except Exception as e:
            logger.error(f"SchemaAgent error: {e}")
            return {"schema_context": DEMO_SCHEMA, "error": None}

    def _get_uploaded_file_schemas(self, uploaded_files: Dict) -> str:
        """Build schema description for uploaded Excel/CSV files."""
        schemas = []
        for file_id, info in uploaded_files.items():
            if isinstance(info, dict):
                cols = info.get("columns", [])
                filename = info.get("filename", "unknown file")
                table_name = info.get("table_name", f"file_{file_id}")
                
                schemas.append(
                    f"TABLE: {table_name}\n"
                    f"  Source: User uploaded file '{filename}'\n"
                    f"  Columns: {', '.join(cols)}\n"
                    f"  Description: User provided data for analysis. Use this table as the PRIMARY data source."
                )
        
        # Add a strict directive if we have user data
        if schemas:
            schemas.insert(0, "!!! IMPORTANT: PRIORITIZE THE FOLLOWING USER-UPLOADED TABLES OVER ANY OTHER DATA SOURCE !!!")
            
        return "\n\n".join(schemas)

    async def _get_cached_database_schema(self, intent: Dict) -> str:
        """Retrieve schema from cache or introspect, then filter for relevance."""
        db_key = str(settings.ANALYTICS_DB_URL)
        now = time.time()
        
        # 1. Try to get full schema from cache
        if db_key in SCHEMA_CACHE:
            full_schema, timestamp, checksum = SCHEMA_CACHE[db_key]
            if now - timestamp < CACHE_TTL:
                logger.info("Schema cache hit")
                return self._filter_relevant_tables(full_schema, intent)

        # 2. Cache miss or expired: Introspect everything
        full_schema = await self._introspect_database()
        checksum = hashlib.md5(full_schema.encode()).hexdigest()
        SCHEMA_CACHE[db_key] = (full_schema, now, checksum)
        
        return self._filter_relevant_tables(full_schema, intent)

    def _filter_relevant_tables(self, full_schema: str, intent: Dict) -> str:
        """Filter the schema to only include tables relevant to the intent."""
        if not full_schema or full_schema == DEMO_SCHEMA:
            return full_schema
            
        metric = intent.get("metric", "").lower()
        dimension = intent.get("dimension", "").lower()
        query_text = intent.get("raw_transcript", "").lower()
        keywords = {metric, dimension} | set(query_text.split())
        
        table_blocks = full_schema.split("TABLE: ")
        # The first block might be "=== SQL DATABASE ===" or empty
        header = table_blocks[0]
        tables = table_blocks[1:]
        
        scored_tables = []
        for table_content in tables:
            table_name = table_content.split("\n")[0].strip()
            score = 0
            # Higher score for direct name match
            if table_name.lower() in keywords: score += 10
            # Score for keyword mentions in columns/description
            for kw in keywords:
                if kw and len(kw) > 2 and kw in table_content.lower():
                    score += 1
            scored_tables.append((score, table_content))
            
        # Sort by score descending and take top N
        scored_tables.sort(key=lambda x: x[0], reverse=True)
        relevant_tables = [t[1] for t in scored_tables[:MAX_TABLES_IN_CONTEXT]]
        
        if not relevant_tables:
            return full_schema # Fallback to all if filtering failed
            
        return header + "\n" + "\nTABLE: ".join(relevant_tables)

    async def _introspect_database(self) -> str:
        """Introspect the connected analytics database (works with MySQL, PostgreSQL, SQLite)."""
        try:
            async with AsyncSession(self._analytics_engine) as session:
                # Try information_schema first (works for MySQL + PostgreSQL)
                try:
                    result = await session.execute(text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'sys') "
                        "AND table_type = 'BASE TABLE' LIMIT 20"
                    ))
                    tables = [row[0] for row in result.fetchall()]
                except Exception:
                    # SQLite fallback
                    result = await session.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    ))
                    tables = [row[0] for row in result.fetchall()]

                schema_parts = []
                for table in tables[:10]:
                    try:
                        # information_schema columns (PostgreSQL + MySQL)
                        cols_result = await session.execute(text(
                            "SELECT column_name, data_type FROM information_schema.columns "
                            f"WHERE table_name = '{table}' ORDER BY ordinal_position"
                        ))
                        col_info = [f"  - {row[0]} ({row[1]})" for row in cols_result.fetchall()]
                    except Exception:
                        # SQLite: PRAGMA
                        cols_result = await session.execute(text(f"PRAGMA table_info({table})"))
                        col_info = [f"  - {row[1]} ({row[2]})" for row in cols_result.fetchall()]

                    if col_info:
                        schema_parts.append(f"TABLE: {table}\n" + "\n".join(col_info))

                return "\n\n".join(schema_parts) if schema_parts else DEMO_SCHEMA
        except Exception as e:
            logger.warning(f"DB introspection failed: {e}, using demo schema")
            return DEMO_SCHEMA

    async def _get_kpi_context(self, metric: Optional[str]) -> str:
        """Get KPI definition from registry."""
        if not metric:
            return ""
        try:
            async with async_session_maker() as db:
                from sqlalchemy import select
                from core.database import KPIRegistry
                result = await db.execute(
                    select(KPIRegistry).where(KPIRegistry.name.ilike(f"%{metric}%")).limit(3)
                )
                kpis = result.scalars().all()
                if kpis:
                    return "\n".join([
                        f"KPI: {k.name} — {k.description} — SQL: {k.sql_expression or 'N/A'}"
                        for k in kpis
                    ])
        except Exception:
            pass
        return ""
