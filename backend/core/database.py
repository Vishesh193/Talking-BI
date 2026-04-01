"""Async database setup with SQLAlchemy."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, JSON, DateTime, Text, Integer, Float
from datetime import datetime
import uuid

from core.config import settings


class Base(DeclarativeBase):
    pass


class KPIRegistry(Base):
    __tablename__ = "kpi_registry"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    description = Column(Text)
    data_source = Column(String)  # sql | excel | powerbi | api
    sql_expression = Column(Text)
    api_endpoint = Column(String)
    category = Column(String)  # revenue | customer | product | ops | marketing
    unit = Column(String)  # currency | percentage | count | duration
    direction = Column(String, default="up_good")  # up_good | down_good
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column("metadata", JSON, default={})


class QueryLog(Base):
    __tablename__ = "query_log"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False)
    transcript = Column(Text)
    intent = Column(JSON)
    generated_sql = Column(Text)
    data_source = Column(String)
    execution_time_ms = Column(Float)
    row_count = Column(Integer)
    success = Column(String, default="true")
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Dashboard(Base):
    __tablename__ = "dashboards"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    layout = Column(JSON, default=[])
    kpis = Column(JSON, default=[])
    filters = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SchemaRegistry(Base):
    __tablename__ = "schema_registry"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type = Column(String)  # sql | excel
    source_name = Column(String)  # database name or filename
    table_name = Column(String)
    column_name = Column(String)
    data_type = Column(String)
    description = Column(Text)  # human-readable label
    sample_values = Column(JSON)
    is_metric = Column(String, default="false")
    is_dimension = Column(String, default="false")
    created_at = Column(DateTime, default=datetime.utcnow)


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session_maker() as session:
        yield session
