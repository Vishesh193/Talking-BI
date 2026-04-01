"""API Routes — REST endpoints for KPI registry, file upload, connectors, dashboards."""
import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import pandas as pd
import aiofiles

from core.config import settings
from core.database import get_db, KPIRegistry, SchemaRegistry, Dashboard, QueryLog
from models.schemas import (
    KPIRegistryItem, UploadedFileInfo, ConnectorStatus,
    FileAnalysisResult,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

logger = logging.getLogger(__name__)
router = APIRouter()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


# ─── KPI REGISTRY ────────────────────────────────────────────────────────────

@router.get("/kpis", response_model=List[dict])
async def list_kpis(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KPIRegistry).order_by(KPIRegistry.category))
    kpis = result.scalars().all()
    return [
        {
            "id": k.id, "name": k.name, "display_name": k.display_name,
            "description": k.description, "data_source": k.data_source,
            "category": k.category, "unit": k.unit, "direction": k.direction,
        }
        for k in kpis
    ]


@router.post("/kpis")
async def create_kpi(kpi: KPIRegistryItem, db: AsyncSession = Depends(get_db)):
    new_kpi = KPIRegistry(
        name=kpi.name,
        display_name=kpi.display_name,
        description=kpi.description,
        data_source=kpi.data_source,
        sql_expression=kpi.sql_expression,
        category=kpi.category,
        unit=kpi.unit,
        direction=kpi.direction,
    )
    db.add(new_kpi)
    await db.commit()
    return {"id": new_kpi.id, "message": "KPI created successfully"}


@router.delete("/kpis/{kpi_id}")
async def delete_kpi(kpi_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(KPIRegistry).where(KPIRegistry.id == kpi_id))
    await db.commit()
    return {"message": "KPI deleted"}


# ─── FILE UPLOAD ─────────────────────────────────────────────────────────────

@router.post("/upload", response_model=UploadedFileInfo)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = "default",
):
    """Upload Excel/CSV file, register its schema for the session, return parsed metadata."""
    if not file.filename or not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(400, "Only CSV and Excel files (.csv, .xlsx, .xls) are supported")

    file_id = str(uuid.uuid4())
    safe_name = file.filename.replace(" ", "_")
    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}_{safe_name}")

    # Save file
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit")

    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    # Parse with pandas
    try:
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        # Clean column names
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

        preview = df.head(5).to_dict(orient="records")
        columns = list(df.columns)

        # Register with ws_manager so agents can query this file
        ws_manager = getattr(request.app.state, 'ws_manager', None)
        if ws_manager:
            ws_manager.register_file(session_id, file_id, {
                'file_id': file_id,
                'filename': file.filename,
                'table_name': os.path.splitext(safe_name)[0].lower().replace('-', '_'),
                'file_path': file_path,
                'columns': columns,
                'dataframe': df.to_dict(orient='records'),
            })

        return UploadedFileInfo(
            file_id=file_id,
            filename=file.filename,
            rows=len(df),
            columns=columns,
            preview=preview,
        )
    except Exception as e:
        logger.error(f"File parse error: {e}")
        raise HTTPException(400, f"Failed to parse file: {str(e)}")


@router.post("/upload/analyze")
async def analyze_uploaded_file(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = "default",
):
    """
    Upload + analyze a file: returns dashboard suggestions and clarifying questions.
    This is the smart entry point — call this instead of /upload for the new dashboard flow.
    """
    if not file.filename or not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(400, "Only CSV and Excel files (.csv, .xlsx, .xls) are supported")

    file_id = str(uuid.uuid4())
    safe_name = file.filename.replace(" ", "_")
    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}_{safe_name}")

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit")

    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    try:
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

        # Register with ws_manager
        ws_manager = getattr(request.app.state, 'ws_manager', None)
        if ws_manager:
            ws_manager.register_file(session_id, file_id, {
                'file_id': file_id,
                'filename': file.filename,
                'table_name': os.path.splitext(safe_name)[0].lower().replace('-', '_'),
                'file_path': file_path,
                'columns': list(df.columns),
                'dataframe': df.to_dict(orient='records'),
            })

        # Run dashboard analysis agent
        from agents.dashboard_agent import DashboardAgent
        agent = DashboardAgent()
        analysis = await agent.analyze_file(file_id, file.filename, df)
        return analysis

    except Exception as e:
        logger.error(f"File analysis error: {e}", exc_info=True)
        raise HTTPException(400, f"Failed to analyze file: {str(e)}")


# ─── CONNECTORS STATUS ───────────────────────────────────────────────────────

@router.get("/connectors", response_model=List[ConnectorStatus])
async def get_connector_status():
    """Check status of all configured data source connectors."""
    return [
        ConnectorStatus(
            type="sql",
            name="SQL Database",
            connected=bool(settings.ANALYTICS_DB_URL),
            tables_or_endpoints=["orders", "customers", "products", "marketing_campaigns"] if settings.ANALYTICS_DB_URL else ["demo_data"],
            error=None if settings.ANALYTICS_DB_URL else "Using demo data — set ANALYTICS_DB_URL to connect",
        ),
        ConnectorStatus(
            type="powerbi",
            name="Power BI",
            connected=bool(settings.POWERBI_CLIENT_ID),
            tables_or_endpoints=[],
            error=None if settings.POWERBI_CLIENT_ID else "Configure POWERBI_CLIENT_ID to connect",
        ),
        ConnectorStatus(
            type="salesforce",
            name="Salesforce",
            connected=bool(settings.SALESFORCE_USERNAME),
            tables_or_endpoints=[],
            error=None if settings.SALESFORCE_USERNAME else "Configure SALESFORCE credentials to connect",
        ),
        ConnectorStatus(
            type="shopify",
            name="Shopify",
            connected=bool(settings.SHOPIFY_ACCESS_TOKEN),
            tables_or_endpoints=[],
            error=None if settings.SHOPIFY_ACCESS_TOKEN else "Configure SHOPIFY_ACCESS_TOKEN to connect",
        ),
        ConnectorStatus(
            type="csv",
            name="CSV / Excel Upload",
            connected=True,
            tables_or_endpoints=[],
            error=None,
        ),
    ]


# ─── DASHBOARDS ──────────────────────────────────────────────────────────────

@router.get("/dashboards")
async def list_dashboards(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).order_by(Dashboard.updated_at.desc()))
    dashboards = result.scalars().all()
    return [
        {"id": d.id, "name": d.name, "kpis": d.kpis, "updated_at": d.updated_at.isoformat()}
        for d in dashboards
    ]


@router.post("/dashboards")
async def create_dashboard(data: dict, db: AsyncSession = Depends(get_db)):
    dashboard = Dashboard(
        name=data.get("name", "New Dashboard"),
        layout=data.get("layout", []),
        kpis=data.get("kpis", []),
    )
    db.add(dashboard)
    await db.commit()
    return {"id": dashboard.id, "message": "Dashboard created"}


@router.put("/dashboards/{dashboard_id}")
async def update_dashboard(dashboard_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dashboard).where(Dashboard.id == dashboard_id))
    dashboard = result.scalar_one_or_none()
    if not dashboard:
        raise HTTPException(404, "Dashboard not found")
    if "name" in data:
        dashboard.name = data["name"]
    if "layout" in data:
        dashboard.layout = data["layout"]
    if "kpis" in data:
        dashboard.kpis = data["kpis"]
    dashboard.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "Dashboard updated"}


# ─── QUERY LOG ───────────────────────────────────────────────────────────────

@router.get("/query-log")
async def get_query_log(db: AsyncSession = Depends(get_db), limit: int = 50):
    result = await db.execute(
        select(QueryLog).order_by(QueryLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": l.id, "transcript": l.transcript,
            "data_source": l.data_source, "success": l.success,
            "execution_time_ms": l.execution_time_ms,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


# ─── DEMO DATA SEED ──────────────────────────────────────────────────────────

@router.post("/seed-demo-kpis")
async def seed_demo_kpis(db: AsyncSession = Depends(get_db)):
    """Seed KPI registry with demo KPIs."""
    demo_kpis = [
        KPIRegistry(name="revenue", display_name="Total Revenue", description="Sum of all order revenue", data_source="sql", sql_expression="SUM(revenue)", category="revenue", unit="currency", direction="up_good"),
        KPIRegistry(name="orders", display_name="Total Orders", description="Count of completed orders", data_source="sql", sql_expression="COUNT(id)", category="revenue", unit="count", direction="up_good"),
        KPIRegistry(name="profit", display_name="Profit", description="Revenue minus cost", data_source="sql", sql_expression="SUM(profit)", category="revenue", unit="currency", direction="up_good"),
        KPIRegistry(name="churn_rate", display_name="Churn Rate", description="Percentage of churned customers", data_source="sql", sql_expression="AVG(is_churned)*100", category="customer", unit="percentage", direction="down_good"),
        KPIRegistry(name="average_order_value", display_name="Avg Order Value", description="Average revenue per order", data_source="sql", sql_expression="AVG(revenue)", category="revenue", unit="currency", direction="up_good"),
    ]
    for kpi in demo_kpis:
        try:
            db.add(kpi)
            await db.commit()
        except Exception:
            await db.rollback()
    return {"message": f"Seeded {len(demo_kpis)} demo KPIs"}
