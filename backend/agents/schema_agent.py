"""
Schema Agent — Retrieves relevant schema context from the registry.
Uses the intent to find the right tables/columns for NL→SQL generation.
"""
import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.config import settings
from core.database import async_session_maker

logger = logging.getLogger(__name__)

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

=== DATE/TIME HELPERS ===
current_month: WHERE MONTH(order_date) = MONTH(CURDATE()) AND YEAR(order_date) = YEAR(CURDATE())
previous_month: WHERE MONTH(order_date) = MONTH(CURDATE() - INTERVAL 1 MONTH)
last_7_days: WHERE order_date >= CURDATE() - INTERVAL 7 DAY
this_year: WHERE YEAR(order_date) = YEAR(CURDATE())
last_year: WHERE YEAR(order_date) = YEAR(CURDATE()) - 1
today: WHERE DATE(order_date) = CURDATE()
"""


class SchemaAgent:
    def __init__(self):
        self._analytics_engine = None
        if settings.ANALYTICS_DB_URL:
            self._analytics_engine = create_async_engine(settings.ANALYTICS_DB_URL)

    async def run(self, intent: Dict, uploaded_files: Dict = None) -> Dict:
        """Get relevant schema context for the intent."""
        try:
            data_source = intent.get("data_source", "auto")
            schema_context = ""

            # Excel/CSV uploaded files
            if uploaded_files and (data_source in ["excel", "auto"]):
                file_schemas = self._get_uploaded_file_schemas(uploaded_files)
                if file_schemas:
                    schema_context += f"\n\n=== UPLOADED FILES ===\n{file_schemas}"

            # SQL database schema
            if data_source in ["sql", "auto"]:
                if self._analytics_engine:
                    db_schema = await self._introspect_database()
                    schema_context += f"\n\n=== SQL DATABASE ===\n{db_schema}"
                else:
                    # Use demo schema
                    schema_context += DEMO_SCHEMA

            # KPI registry context
            kpi_context = await self._get_kpi_context(intent.get("metric"))
            if kpi_context:
                schema_context += f"\n\n=== KPI REGISTRY ===\n{kpi_context}"

            return {"schema_context": schema_context}

        except Exception as e:
            logger.error(f"SchemaAgent error: {e}")
            return {"schema_context": DEMO_SCHEMA, "error": None}  # Fallback to demo

    def _get_uploaded_file_schemas(self, uploaded_files: Dict) -> str:
        """Build schema description for uploaded Excel/CSV files."""
        schemas = []
        for file_id, info in uploaded_files.items():
            if isinstance(info, dict):
                cols = info.get("columns", [])
                table_name = info.get("table_name", f"file_{file_id}")
                schemas.append(f"TABLE: {table_name} (uploaded file)\n  Columns: {', '.join(cols)}")
        return "\n".join(schemas)

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
