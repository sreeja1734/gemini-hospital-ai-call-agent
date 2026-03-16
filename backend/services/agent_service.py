"""
ADK-backed agent service for hospital call conversations.

Speech services remain outside this service. This layer only manages:
- ADK session memory
- Gemini reasoning through the ADK runner
- tool-call capture for debugging
"""
from __future__ import annotations

import structlog

from backend.agents.hospital_agent import hospital_receptionist_agent
from backend.config import settings

logger = structlog.get_logger(__name__)


class HospitalAgentService:
    """Single entrypoint for the hospital receptionist ADK agent."""

    def __init__(self) -> None:
        self._app_name = "hospital_call_agent"
        self._created_sessions: set[str] = set()
        self._runner = None
        self._session_service = None
        self._content_types = None
        self._available = False

        if hospital_receptionist_agent is None:
            logger.error("Hospital receptionist ADK agent unavailable during service initialization")
            return

        try:
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai import types

            self._session_service = InMemorySessionService()
            self._runner = Runner(
                app_name=self._app_name,
                agent=hospital_receptionist_agent,
                session_service=self._session_service,
            )
            self._content_types = types
            self._available = True
            logger.info("Hospital receptionist ADK agent initialized", model=settings.GEMINI_MODEL)
        except Exception as exc:
            logger.exception("Failed to initialize hospital receptionist ADK service", error=str(exc))

    @property
    def is_available(self) -> bool:
        return self._available

    def get_greeting(self) -> str:
        return (
            f"Hello! Thank you for calling {settings.HOSPITAL_NAME}. "
            "I'm your AI assistant. How may I help you today?"
        )

    async def _ensure_session(self, call_id: str, user_id: str) -> None:
        if not self._available or call_id in self._created_sessions:
            return

        await self._session_service.create_session(
            app_name=self._app_name,
            user_id=user_id,
            session_id=call_id,
        )
        self._created_sessions.add(call_id)
        logger.info("ADK session created", call_id=call_id, user_id=user_id)

    async def initialize_session(self, call_id: str, user_id: str) -> None:
        await self._ensure_session(call_id, user_id)

    async def process_message(
        self,
        call_id: str,
        user_message: str,
        user_id: str = "anonymous",
    ) -> tuple[str, list[dict]]:
        """Run a user message through the ADK agent and return text plus tool-call metadata."""
        if not self._available:
            logger.error("ADK agent service unavailable for message processing", call_id=call_id)
            return (
                "The hospital AI assistant is temporarily unavailable. Please connect to a human receptionist.",
                [],
            )

        try:
            await self._ensure_session(call_id, user_id)
            message = self._content_types.Content(
                role="user",
                parts=[self._content_types.Part(text=user_message)],
            )

            response_parts: list[str] = []
            tool_calls: list[dict] = []

            async for event in self._runner.run_async(
                user_id=user_id,
                session_id=call_id,
                new_message=message,
            ):
                extracted_calls = self._extract_tool_calls(event)
                if extracted_calls:
                    tool_calls.extend(extracted_calls)

                if not self._is_final_response(event):
                    continue

                response_parts.extend(self._extract_text_parts(event))

            final_text = " ".join(part.strip() for part in response_parts if part and part.strip()).strip()
            if not final_text:
                final_text = "I didn't catch that clearly. Could you please repeat that?"

            return final_text, tool_calls
        except Exception as exc:
            logger.exception("Failed to process message with hospital ADK agent", error=str(exc), call_id=call_id)
            return (
                "I'm sorry, I'm having trouble right now. Please hold while I connect you to the hospital staff.",
                [],
            )

    def _extract_tool_calls(self, event) -> list[dict]:
        calls: list[dict] = []
        get_function_calls = getattr(event, "get_function_calls", None)
        if callable(get_function_calls):
            for call in get_function_calls() or []:
                calls.append(
                    {
                        "name": getattr(call, "name", ""),
                        "args": dict(getattr(call, "args", {}) or {}),
                    }
                )

        for call in calls:
            logger.info("ADK tool call observed", tool_name=call["name"], args=call["args"])

        return calls

    def _extract_text_parts(self, event) -> list[str]:
        content = getattr(event, "content", None)
        parts = getattr(content, "parts", []) or []
        return [text for part in parts if (text := getattr(part, "text", None))]

    def _is_final_response(self, event) -> bool:
        is_final_response = getattr(event, "is_final_response", None)
        if callable(is_final_response):
            return bool(is_final_response())
        return True


agent_service = HospitalAgentService()
