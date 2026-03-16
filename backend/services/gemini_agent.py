"""
Backward-compatible wrapper around the ADK hospital agent service.

This module intentionally avoids direct `google.generativeai` usage.
"""
from __future__ import annotations

import structlog

from backend.services.agent_service import agent_service

logger = structlog.get_logger(__name__)


class GeminiAgent:
    """Compatibility layer for older imports that expected a Gemini agent service."""

    def get_greeting(self) -> str:
        return agent_service.get_greeting()

    async def process_message(
        self,
        call_id: str,
        user_message: str,
        history: list[dict] | None = None,
        function_handler=None,
        user_id: str = "anonymous",
    ) -> tuple[str, list[dict]]:
        if history:
            logger.info("Ignoring legacy history argument in GeminiAgent compatibility wrapper", call_id=call_id)
        if function_handler:
            logger.info(
                "Ignoring legacy function handler in GeminiAgent compatibility wrapper",
                call_id=call_id,
            )
        return await agent_service.process_message(
            call_id=call_id,
            user_message=user_message,
            user_id=user_id,
        )

    async def analyze_transcript(self, transcript: str) -> dict:
        logger.warning("Transcript analysis is no longer handled by GeminiAgent compatibility wrapper")
        return {
            "intent": "unknown",
            "sentiment": "neutral",
            "emergency_risk": "low",
            "summary": "Transcript analysis moved out of the conversational agent.",
            "key_topics": [],
            "follow_up_required": False,
        }


gemini_agent = GeminiAgent()
