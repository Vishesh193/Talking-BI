"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict
from enum import Enum


class IntentType(str, Enum):
    QUERY = "query"
    COMPARE = "compare"
    TREND = "trend"
    DRILL_DOWN = "drill_down"
    FILTER = "filter"
    EXPLAIN = "explain"
    FORECAST = "forecast"
    SUMMARIZE = "summarize"
    SIMULATE = "simulate"


class DataSourceType(str, Enum):
    SQL = "sql"
    EXCEL = "excel"
    POWERBI = "powerbi"
    SALESFORCE = "salesforce"
    SHOPIFY = "shopify"
    AUTO = "auto"


class Intent(BaseModel):
    type: IntentType
    metric: Optional[str] = None
    dimension: Optional[str] = None
    period_a: Optional[str] = None   # e.g. "current_month"
    period_b: Optional[str] = None   # e.g. "previous_month"
    filters: Dict[str, Any] = {}
    data_source: DataSourceType = DataSourceType.AUTO
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    raw_transcript: str = ""


class ChartType(str, Enum):
    BAR = "bar"
    LINE = "line"
    AREA = "area"
    PIE = "pie"
    DONUT = "donut"
    SCATTER = "scatter"
    GROUPED_BAR = "grouped_bar"
    STACKED_BAR = "stacked_bar"
    STACKED_AREA = "stacked_area"
    KPI_CARD = "kpi_card"
    TABLE = "table"
    HEATMAP = "heatmap"
    SANKEY = "sankey"
    GEOMAP = "geomap"
    TREEMAP = "treemap"
    WATERFALL = "waterfall"
    GAUGE = "gauge"
    BULLET = "bullet"


class SimulationResult(BaseModel):
    scenario: str
    baseline_value: float
    simulated_value: float
    net_change_pct: float
    confidence: float = 0.5
    reasoning: str
    impact_level: str = "Neutral" # Positive | Negative | Neutral


class StrategyRecommendation(BaseModel):
    title: str
    recommendation: str
    category: str
    impact: str = "Medium" # High | Medium | Low


class InsightCard(BaseModel):
    title: str
    body: str
    metric: Optional[str] = None
    change_pct: Optional[float] = None
    direction: Optional[str] = None  # up | down | neutral
    confidence: float = Field(default=0.8, ge=0, le=1)
    action: Optional[str] = None
    is_anomaly: bool = False


class ChartConfig(BaseModel):
    type: ChartType
    title: str
    data: List[Dict[str, Any]]
    x_key: str
    y_keys: List[str]
    colors: List[str] = ["#3C3489", "#854F0B", "#0F6E56", "#993C1D", "#BA7517"]
    unit: Optional[str] = None
    show_legend: bool = True
    show_grid: bool = True
    # KPI card fields
    kpi_value: Optional[float] = None
    kpi_label: Optional[str] = None
    kpi_delta: Optional[float] = None
    kpi_direction: Optional[str] = None  # up | down | neutral


class AgentResult(BaseModel):
    session_id: str
    transcript: str
    intent: Optional[Intent] = None
    sql: Optional[str] = None
    data_source_used: Optional[str] = None
    row_count: int = 0
    chart: Optional[ChartConfig] = None
    insights: List[InsightCard] = []
    strategies: List[StrategyRecommendation] = []
    simulation: Optional[SimulationResult] = None
    suggestions: List[str] = []
    tts_text: Optional[str] = None
    execution_time_ms: float = 0
    error: Optional[str] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    update_panel_id: Optional[str] = None


class TextQueryRequest(BaseModel):
    query: str
    session_id: str
    data_source: DataSourceType = DataSourceType.AUTO


class KPIRegistryItem(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    data_source: str
    sql_expression: Optional[str] = None
    category: str = "general"
    unit: str = "count"
    direction: str = "up_good"


class UploadedFileInfo(BaseModel):
    file_id: str
    filename: str
    rows: int
    columns: List[str]
    preview: List[Dict[str, Any]]


class ConnectorStatus(BaseModel):
    type: str
    name: str
    connected: bool
    tables_or_endpoints: List[str] = []
    error: Optional[str] = None


class ClarifyingQuestion(BaseModel):
    id: str
    question: str
    options: List[str] = []  # Suggested answer chips
    allow_custom: bool = True
    skippable: bool = True


class DashboardSuggestion(BaseModel):
    id: str
    title: str
    description: str
    chart_types: List[str]  # e.g. ["bar", "line", "kpi_card"]
    focus: str  # e.g. "Sales Performance", "Trend Analysis"
    preview_kpis: List[str] = []  # column names that will be KPIs


class FileAnalysisResult(BaseModel):
    file_id: str
    filename: str
    rows: int
    columns: List[str]
    column_types: Dict[str, str]  # column -> "numeric"|"categorical"|"date"
    suggestions: List[DashboardSuggestion]
    clarifying_questions: List[ClarifyingQuestion]
