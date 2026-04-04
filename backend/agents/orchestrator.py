"""
LangGraph Multi-Agent Orchestrator
Pipeline: Voice transcript → Intent → Schema → Query → Viz → Insight → TTS → Memory
"""
import time
import logging
from typing import TypedDict, Optional, List, Dict, Any

from langgraph.graph import StateGraph, END

from agents.intent_agent import IntentAgent
from agents.schema_agent import SchemaAgent
from agents.query_agent import QueryAgent
from agents.viz_agent import VizAgent
from agents.insight_agent import InsightAgent
from agents.strategy_agent import StrategyAgent
from agents.simulation_agent import SimulationAgent
from agents.data_quality_agent import DataQualityAgent
from agents.alert_agent import AlertAgent
from agents.memory_agent import MemoryAgent
from agents.tts_agent import TTSAgent
from models.schemas import AgentResult, Intent, ChartConfig, InsightCard, StrategyRecommendation, SimulationResult
from core.redis_client import session_get

logger = logging.getLogger(__name__)


class BIState(TypedDict, total=False):
    """
    Shared state passed through all agent nodes.
    total=False means all keys are optional — LangGraph merges partial updates.
    """
    session_id: str
    transcript: str
    intent: Optional[Dict]
    schema_context: str
    sql: Optional[str]
    data_source_used: Optional[str]
    result_data: Optional[List[Dict]]
    row_count: int
    quality: Optional[Dict]
    chart_config: Optional[Dict]
    insights: List[Dict]
    suggestions: List[str]
    strategies: List[Dict]
    alerts: List[Dict]
    simulation: Optional[Dict]
    tts_text: Optional[str]
    session_memory: Dict
    needs_clarification: bool
    clarification_question: Optional[str]
    error: Optional[str]
    start_time: float
    uploaded_files: Dict
    target_panel_id: Optional[str]


# ── Routing functions ────────────────────────────────────────────────────────

def route_after_intent(state: BIState) -> str:
    if state.get("error"):
        return "end_with_error"
    if state.get("needs_clarification"):
        return "clarify"
    return "schema"


def route_after_query(state: BIState) -> str:
    if state.get("error"):
        return "end_with_error"
    return "viz"


def route_after_viz(state: BIState) -> str:
    # Option 3: Pipeline Bypassing. Skip ALL text-heavy agents to avoid 429 limits
    # when the system is just bulk-rendering a dashboard grid natively.
    if "[layout:" in state.get("transcript", ""):
        return "memory"
    return "insight"


# ── Agent node functions (pure: receive state dict, return partial update) ───

async def run_intent(state: BIState) -> Dict:
    logger.info(f"[Intent] '{state.get('transcript', '')[:80]}'")
    agent = IntentAgent()
    result = await agent.run(
        transcript=state["transcript"],
        session_memory=state.get("session_memory", {}),
        target_panel_id=state.get("target_panel_id"),
        uploaded_files=state.get("uploaded_files", {}),
    )
    return result


async def run_schema(state: BIState) -> Dict:
    logger.info(f"[Schema] intent_type={state.get('intent', {}).get('type')}")
    agent = SchemaAgent()
    result = await agent.run(
        intent=state.get("intent", {}),
        uploaded_files=state.get("uploaded_files", {}),
    )
    return result


async def run_query(state: BIState) -> Dict:
    logger.info("[Query] generating + executing")
    agent = QueryAgent()
    result = await agent.run(
        intent=state.get("intent", {}),
        schema_context=state.get("schema_context", ""),
        uploaded_files=state.get("uploaded_files", {}),
    )
    return result


async def run_data_quality(state: BIState) -> Dict:
    try:
        logger.info("[DataQuality] profiling result set")
        agent = DataQualityAgent()
        result = await agent.run(
            result_data=state.get("result_data"),
            data_source=state.get("data_source_used"),
        )
        return result
    except Exception as e:
        logger.warning(f"DataQualityAgent failed (graceful skip): {e}")
        return {"quality": None}


async def run_viz(state: BIState) -> Dict:
    logger.info(f"[Viz] {state.get('row_count', 0)} rows")
    agent = VizAgent()
    result = await agent.run(
        transcript=state.get("transcript", ""),
        intent=state.get("intent", {}),
        result_data=state.get("result_data"),
    )
    return result


async def run_insight(state: BIState) -> Dict:
    try:
        logger.info("[Insight] generating ranked insights")
        agent = InsightAgent()
        result = await agent.run(
            intent=state.get("intent", {}),
            result_data=state.get("result_data"),
            chart_config=state.get("chart_config"),
        )
        return result
    except Exception as e:
        logger.warning(f"InsightAgent failed (graceful skip): {e}")
        return {"insights": []}


async def run_simulation(state: BIState) -> Dict:
    try:
        if state.get("intent", {}).get("type") != "simulate":
            return {"simulation": None}
        
        logger.info("[Simulation] preforming what-if analysis")
        agent = SimulationAgent()
        result = await agent.run(
            intent=state.get("intent", {}),
            result_data=state.get("result_data"),
            query=state["transcript"]
        )
        return result
    except Exception as e:
        logger.warning(f"SimulationAgent failed (graceful skip): {e}")
        return {"simulation": None}


async def run_strategy(state: BIState) -> Dict:
    try:
        if not state.get("insights") and not state.get("simulation"):
            return {"strategies": []}
        
        logger.info("[Strategy] generating prescriptive recommendations")
        agent = StrategyAgent()
        result = await agent.run(
            intent=state.get("intent", {}),
            insights=state.get("insights", []),
            result_data=state.get("result_data"),
            data_source=state.get("data_source_used", "unknown")
        )
        return result
    except Exception as e:
        logger.warning(f"StrategyAgent failed (graceful skip): {e}")
        return {"strategies": []}


async def run_alerts(state: BIState) -> Dict:
    try:
        insights = state.get("insights", [])
        anomalies = [i for i in insights if i.get("is_anomaly")]
        if not anomalies:
            return {"alerts": []}
        logger.info(f"[Alerts] checking {len(anomalies)} anomalies")
        agent = AlertAgent()
        fired = await agent.evaluate_and_alert(
            insights=insights,
            session_id=state.get("session_id", ""),
            query_context=state.get("transcript", ""),
            chart_config=state.get("chart_config"),
        )
        return {"alerts": fired}
    except Exception as e:
        logger.warning(f"AlertAgent failed (graceful skip): {e}")
        return {"alerts": []}


async def run_tts(state: BIState) -> Dict:
    try:
        logger.info("[TTS] generating spoken summary")
        agent = TTSAgent()
        result = await agent.run(
            insights=state.get("insights", []),
            intent=state.get("intent", {}),
        )
        return result
    except Exception as e:
        logger.warning(f"TTSAgent failed (graceful skip): {e}")
        return {"tts_text": None}


async def run_memory(state: BIState) -> Dict:
    logger.info(f"[Memory] saving session {state.get('session_id')}")
    agent = MemoryAgent()
    await agent.save(
        session_id=state["session_id"],
        current_state=state,
    )
    return {"session_id": state["session_id"]}


async def run_clarify(state: BIState) -> Dict:
    question = state.get("clarification_question", "Could you clarify your question?")
    logger.info(f"[Clarify] {question}")
    return {"tts_text": question}


async def handle_error(state: BIState) -> Dict:
    logger.error(f"[Error] {state.get('error')}")
    return {"tts_text": "I encountered an error. Please try again."}


# ── Build the compiled graph (done once at module load) ──────────────────────

def _build_pipeline():
    g = StateGraph(BIState)

    g.add_node("intent_node",         run_intent)
    g.add_node("schema_node",         run_schema)
    g.add_node("query_node",          run_query)
    g.add_node("data_quality_node",   run_data_quality)
    g.add_node("simulation_node",     run_simulation)
    g.add_node("viz_node",            run_viz)
    g.add_node("insight_node",        run_insight)
    g.add_node("strategy_node",       run_strategy)
    g.add_node("alerts_node",         run_alerts)
    g.add_node("tts_node",            run_tts)
    g.add_node("memory_node",         run_memory)
    g.add_node("clarify_node",        run_clarify)
    g.add_node("end_with_error_node", handle_error)

    g.set_entry_point("intent_node")

    g.add_conditional_edges("intent_node", route_after_intent, {
        "schema":         "schema_node",
        "clarify":        "clarify_node",
        "end_with_error": "end_with_error_node",
    })
    g.add_conditional_edges("query_node", route_after_query, {
        "viz":            "data_quality_node",
        "end_with_error": "end_with_error_node",
    })

    g.add_edge("schema_node",         "query_node")
    g.add_edge("data_quality_node",   "simulation_node")
    g.add_edge("simulation_node",     "viz_node")
    
    g.add_conditional_edges("viz_node", route_after_viz, {
        "insight": "insight_node",
        "memory": "memory_node"
    })
    
    g.add_edge("insight_node",        "strategy_node")
    g.add_edge("strategy_node",       "alerts_node")
    g.add_edge("alerts_node",         "tts_node")
    g.add_edge("tts_node",            "memory_node")
    g.add_edge("memory_node",         END)
    g.add_edge("clarify_node",        END)
    g.add_edge("end_with_error_node", END)

    return g.compile()


_pipeline = _build_pipeline()


# ── Public entry point ───────────────────────────────────────────────────────

async def run_pipeline(
    transcript: str,
    session_id: str,
    uploaded_files: Dict = None,
    target_panel_id: str = None,
) -> AgentResult:
    """Run the full agentic pipeline. Returns a complete AgentResult."""
    session_memory = await session_get(session_id)
    start = time.time()

    initial: BIState = {
        "session_id":           session_id,
        "transcript":           transcript,
        "intent":               None,
        "schema_context":       "",
        "sql":                  None,
        "data_source_used":     None,
        "result_data":          None,
        "row_count":            0,
        "chart_config":         None,
        "insights":             [],
        "strategies":           [],
        "suggestions":          [],
        "simulation":           None,
        "tts_text":             None,
        "session_memory":       session_memory,
        "needs_clarification":  False,
        "clarification_question": None,
        "error":                None,
        "start_time":           start,
        "uploaded_files":       uploaded_files or {},
        "target_panel_id":      target_panel_id,
    }

    try:
        final: BIState = await _pipeline.ainvoke(initial)
        elapsed = (time.time() - start) * 1000

        # Safely build Intent model
        intent_obj = None
        if final.get("intent"):
            try:
                intent_data = final["intent"]
                # If agent intent suggests a modification of the target panel
                should_update = intent_data.get("type") in ["filter", "compare", "trend", "drill_down"] or "change" in transcript.lower()
                update_id = target_panel_id if should_update else None
                
                intent_obj = Intent(**intent_data)
            except Exception:
                pass

        # Safely build ChartConfig model
        chart_obj = None
        if final.get("chart_config"):
            try:
                chart_obj = ChartConfig(**final["chart_config"])
            except Exception as e:
                logger.warning(f"ChartConfig parse error: {e}")

        # Safely build SimulationResult model
        sim_obj = None
        if final.get("simulation"):
            try:
                sim_obj = SimulationResult(**final["simulation"])
            except Exception as e:
                logger.warning(f"Simulation parse error: {e}")

        # Safely build InsightCard list
        insight_objs = []
        for i in final.get("insights", []):
            try:
                insight_objs.append(InsightCard(**i))
            except Exception:
                pass

        # Safely build StrategyRecommendation list
        strategy_objs = []
        for s in final.get("strategies", []):
            try:
                strategy_objs.append(StrategyRecommendation(**s))
            except Exception as e:
                logger.warning(f"Strategy parse error: {e}")

        return AgentResult(
            session_id=session_id,
            transcript=transcript,
            intent=intent_obj,
            sql=final.get("sql"),
            data_source_used=final.get("data_source_used"),
            row_count=final.get("row_count", 0),
            chart=chart_obj,
            insights=insight_objs,
            strategies=strategy_objs,
            simulation=sim_obj,
            suggestions=final.get("suggestions", []),
            tts_text=final.get("tts_text"),
            execution_time_ms=elapsed,
            error=final.get("error"),
            needs_clarification=final.get("needs_clarification", False),
            clarification_question=final.get("clarification_question"),
            update_panel_id=update_id if 'update_id' in locals() else None,
        )

    except Exception as e:
        logger.error(f"Pipeline fatal error: {e}", exc_info=True)
        return AgentResult(
            session_id=session_id,
            transcript=transcript,
            error=str(e),
            execution_time_ms=(time.time() - start) * 1000,
        )
