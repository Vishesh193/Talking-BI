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
from agents.memory_agent import MemoryAgent
from agents.tts_agent import TTSAgent
from models.schemas import AgentResult, Intent, ChartConfig, InsightCard
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
    chart_config: Optional[Dict]
    insights: List[Dict]
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


# ── Agent node functions (pure: receive state dict, return partial update) ───

async def run_intent(state: BIState) -> Dict:
    logger.info(f"[Intent] '{state.get('transcript', '')[:80]}'")
    agent = IntentAgent()
    result = await agent.run(
        transcript=state["transcript"],
        session_memory=state.get("session_memory", {}),
        target_panel_id=state.get("target_panel_id"),
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


async def run_viz(state: BIState) -> Dict:
    logger.info(f"[Viz] {state.get('row_count', 0)} rows")
    agent = VizAgent()
    result = await agent.run(
        intent=state.get("intent", {}),
        result_data=state.get("result_data"),
    )
    return result


async def run_insight(state: BIState) -> Dict:
    logger.info("[Insight] generating ranked insights")
    agent = InsightAgent()
    result = await agent.run(
        intent=state.get("intent", {}),
        result_data=state.get("result_data"),
        chart_config=state.get("chart_config"),
    )
    return result


async def run_tts(state: BIState) -> Dict:
    logger.info("[TTS] generating spoken summary")
    agent = TTSAgent()
    result = await agent.run(
        insights=state.get("insights", []),
        intent=state.get("intent", {}),
    )
    return result


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
    g.add_node("viz_node",            run_viz)
    g.add_node("insight_node",        run_insight)
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
        "viz":            "viz_node",
        "end_with_error": "end_with_error_node",
    })

    g.add_edge("schema_node",         "query_node")
    g.add_edge("viz_node",            "insight_node")
    g.add_edge("insight_node",        "tts_node")
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

        # Safely build InsightCard list
        insight_objs = []
        for i in final.get("insights", []):
            try:
                insight_objs.append(InsightCard(**i))
            except Exception:
                pass

        return AgentResult(
            session_id=session_id,
            transcript=transcript,
            intent=intent_obj,
            sql=final.get("sql"),
            data_source_used=final.get("data_source_used"),
            row_count=final.get("row_count", 0),
            chart=chart_obj,
            insights=insight_objs,
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
