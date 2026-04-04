import base64
import io
import json
import logging
import asyncio
from typing import Dict, Optional
from fastapi import WebSocket

from agents.orchestrator import run_pipeline
from core.config import settings
from core.database import async_session_maker, QueryLog

logger = logging.getLogger(__name__)


from core.auth import decode_token

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        # session_id → {user_id, email, role, ...}
        self.connection_auth: Dict[str, Dict] = {}
        # session_id → {file_id: {filename, columns, dataframe, ...}}
        self.uploaded_files: Dict[str, Dict] = {}

    # ── Connection lifecycle ─────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, session_id: str, token: Optional[str] = None) -> None:
        user_info = None
        if token:
            try:
                user_info = decode_token(token)
                logger.info(f"Auth success for {user_info.get('email')} on session {session_id}")
            except Exception as e:
                logger.warning(f"Auth failed on session {session_id}: {e}")
                # We could close the socket here, but keeping it open for now for dev flexibility
        
        await websocket.accept()
        self.active_connections[session_id] = websocket
        if user_info:
            self.connection_auth[session_id] = user_info
            
        logger.info(f"WebSocket connected: {session_id}")
        await self._send(session_id, {
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to Talking BI agent pipeline",
        })

    def disconnect(self, session_id: str) -> None:
        self.active_connections.pop(session_id, None)
        logger.info(f"WebSocket disconnected: {session_id}")

    # ── Message dispatch ─────────────────────────────────────────────────

    async def handle_message(self, websocket: WebSocket, session_id: str, message: dict) -> None:
        msg_type = message.get("type", "")

        if msg_type == "text_query":
            await self._handle_text_query(session_id, message.get("query", ""), message.get("selected_panel_id"))

        elif msg_type == "voice_audio":
            await self._handle_voice_audio(session_id, message.get("audio", ""), message.get("selected_panel_id"))

        elif msg_type == "clarification":
            await self._handle_text_query(session_id, message.get("response", ""), message.get("selected_panel_id"))

        elif msg_type == "ping":
            await self._send(session_id, {"type": "pong"})

        else:
            logger.debug(f"Unknown message type '{msg_type}' from {session_id}")

    # ── Text query pipeline ──────────────────────────────────────────────

    async def _handle_text_query(self, session_id: str, query: str, selected_panel_id: Optional[str] = None) -> None:
        query = query.strip()
        if not query:
            return

        await self._send(session_id, {
            "type": "agent_thinking",
            "stage": "intent",
            "message": "Analyzing your query...",
        })

        session_files = self.uploaded_files.get(session_id, {})

        # Thinking Ping Loop (keeps socket alive + UI fresh)
        async def thinking_pings():
            stages = ["Analyzing...", "Generating SQL...", "Fetching Data...", "Processing Insights...", "Crafting Recommendations..."]
            idx = 0
            while True:
                await asyncio.sleep(5)
                await self._send(session_id, {
                    "type": "agent_thinking",
                    "stage": "processing",
                    "message": stages[idx % len(stages)]
                })
                idx += 1

        ping_task = asyncio.create_task(thinking_pings())
        try:
            result = await run_pipeline(
                transcript=query,
                session_id=session_id,
                uploaded_files=session_files,
                target_panel_id=selected_panel_id,
            )

            # FIX: write to QueryLog (audit trail)
            await self._log_query(session_id, query, result)

            if result.needs_clarification:
                await self._send(session_id, {
                    "type": "clarification_needed",
                    "question": result.clarification_question,
                    "tts_text": result.clarification_question,
                })
                return

            await self._send(session_id, {
                "type": "agent_result",
                "data": {
                    "session_id":        result.session_id,
                    "transcript":        result.transcript,
                    "intent":            result.intent.model_dump() if result.intent else None,
                    "sql":               result.sql,
                    "data_source_used":  result.data_source_used,
                    "row_count":         result.row_count,
                    "chart":             result.chart.model_dump() if result.chart else None,
                    "insights":          [i.model_dump() for i in result.insights],
                    "tts_text":          result.tts_text,
                    "execution_time_ms": round(result.execution_time_ms, 1),
                    "error":             result.error,
                    "update_panel_id":   getattr(result, 'update_panel_id', None),
                },
            })

        except Exception as e:
            logger.error(f"Pipeline error for {session_id}: {e}", exc_info=True)
            await self._send(session_id, {
                "type": "error",
                "message": f"Pipeline error: {str(e)}",
            })
        finally:
            ping_task.cancel()

    # ── Voice audio pipeline ─────────────────────────────────────────────

    async def _handle_voice_audio(self, session_id: str, audio_b64: str, selected_panel_id: Optional[str] = None) -> None:
        if not audio_b64:
            return

        await self._send(session_id, {
            "type": "agent_thinking",
            "stage": "transcribing",
            "message": "Transcribing your voice...",
        })

        transcript = await self._transcribe_audio(audio_b64)

        if not transcript:
            await self._send(session_id, {
                "type": "transcription_failed",
                "message": "Could not transcribe audio. Please try again or type your query.",
            })
            return

        # Echo transcript so the frontend can show "Heard: ..."
        await self._send(session_id, {
            "type": "transcription",
            "transcript": transcript,
        })

        # Run the full agent pipeline on the transcript
        await self._handle_text_query(session_id, transcript, selected_panel_id)

    async def _transcribe_audio(self, audio_b64: str) -> Optional[str]:
        """Transcribe audio using Groq Whisper (free) or OpenAI Whisper (fallback)."""
        # Try Groq Whisper first (free with existing GROQ_API_KEY)
        if settings.GROQ_API_KEY:
            result = await self._transcribe_with_groq(audio_b64)
            if result:
                return result

        # Fallback to OpenAI Whisper if Groq fails or unavailable
        if settings.OPENAI_API_KEY:
            return await self._transcribe_with_openai(audio_b64)

        logger.warning("No API key available for voice transcription (need GROQ_API_KEY or OPENAI_API_KEY)")
        return None

    async def _transcribe_with_groq(self, audio_b64: str) -> Optional[str]:
        """Transcribe audio using Groq Whisper (free tier)."""
        try:
            from groq import AsyncGroq
            audio_bytes = base64.b64decode(audio_b64)
            client = AsyncGroq(api_key=settings.GROQ_API_KEY)

            response = await client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=("audio.webm", audio_bytes),
                language="en",
                prompt="Business intelligence query about sales, revenue, customers, or products.",
            )
            transcript = response.text.strip()
            if not transcript:
                return None
            logger.info(f"Groq Whisper transcribed: '{transcript}'")
            return transcript

        except Exception as e:
            logger.error(f"Groq Whisper transcription error: {e}")
            return None

    async def _transcribe_with_openai(self, audio_b64: str) -> Optional[str]:
        """Transcribe audio using OpenAI Whisper (fallback)."""
        try:
            import openai
            audio_bytes = base64.b64decode(audio_b64)
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.webm", audio_bytes),
                language="en",
                prompt="Business intelligence query about sales, revenue, customers, or products.",
            )
            transcript = response.text.strip()
            if not transcript:
                return None
            logger.info(f"OpenAI Whisper transcribed: '{transcript}'")
            return transcript

        except Exception as e:
            logger.error(f"OpenAI Whisper transcription error: {e}")
            return None

    # ── File registration (called from upload route) ─────────────────────

    def register_file(self, session_id: str, file_id: str, file_info: dict) -> None:
        """Register an uploaded file so agents can query it for this session."""
        if session_id not in self.uploaded_files:
            self.uploaded_files[session_id] = {}
        self.uploaded_files[session_id][file_id] = file_info
        logger.info(f"File registered for session {session_id}: {file_info.get('filename')}")

    def get_session_files(self, session_id: str) -> Dict:
        """Return all uploaded files for a session."""
        return self.uploaded_files.get(session_id, {})

    # ── Query log writer ─────────────────────────────────────────────────

    async def _log_query(self, session_id: str, transcript: str, result) -> None:
        """Write query result to QueryLog for audit trail."""
        try:
            async with async_session_maker() as db:
                log_entry = QueryLog(
                    session_id=session_id,
                    transcript=transcript,
                    intent=result.intent.model_dump() if result.intent else None,
                    generated_sql=result.sql,
                    data_source=result.data_source_used,
                    execution_time_ms=result.execution_time_ms,
                    row_count=result.row_count,
                    success="false" if result.error else "true",
                    error_message=result.error,
                )
                db.add(log_entry)
                await db.commit()
        except Exception as e:
            logger.warning(f"QueryLog write failed (non-critical): {e}")

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _send(self, session_id: str, data: dict) -> None:
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data, default=str))
            except Exception as e:
                logger.warning(f"Send failed to {session_id}: {e}")
                self.disconnect(session_id)
