"""
Service layer for browser voice calls over WebSocket.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field

import structlog

from ai.browser_speech_to_text import browser_stt_service
from ai.conversation_manager import conversation_manager
from ai.text_to_speech import tts_service
from backend.tools.hospital_tools import detectEmergency

from .agent_service import agent_service

logger = structlog.get_logger(__name__)


@dataclass
class VoiceCallSession:
    call_id: str
    caller_phone: str
    language: str
    audio_buffer: bytearray = field(default_factory=bytearray)


class VoiceCallService:
    def __init__(self) -> None:
        self._sessions: dict[str, VoiceCallSession] = {}

    async def start_session(self, caller_phone: str, language: str = "en-US") -> dict[str, str]:
        context = conversation_manager.create_session(caller_phone)
        context.language = language
        await agent_service.initialize_session(context.call_id, caller_phone)

        greeting = agent_service.get_greeting()
        conversation_manager.add_assistant_turn(context.call_id, greeting)

        audio_bytes = await self._synthesize_mp3(greeting, language)
        self._sessions[context.call_id] = VoiceCallSession(
            call_id=context.call_id,
            caller_phone=caller_phone,
            language=language,
        )

        logger.info("Voice call session started", call_id=context.call_id, caller_phone=caller_phone)
        return {
            "call_id": context.call_id,
            "greeting_text": greeting,
            "greeting_audio_base64": base64.b64encode(audio_bytes).decode() if audio_bytes else "",
        }

    def append_audio(self, call_id: str, audio_bytes: bytes) -> None:
        session = self._sessions.get(call_id)
        if not session:
            return
        session.audio_buffer.extend(audio_bytes)

    async def process_audio_turn(self, call_id: str) -> dict[str, str | bool] | None:
        session = self._sessions.get(call_id)
        context = conversation_manager.get_session(call_id)
        if not session or not context:
            logger.warning("Voice call session not found during audio processing", call_id=call_id)
            return None

        audio_bytes = bytes(session.audio_buffer)
        session.audio_buffer.clear()
        if not audio_bytes:
            return None

        user_text, _, detected_language = await browser_stt_service.transcribe_audio_bytes(
            audio_bytes=audio_bytes,
            language_code=session.language,
        )
        if not user_text:
            logger.info("Voice STT returned empty transcript", call_id=call_id)
            return None

        session.language = detected_language
        context.language = detected_language
        conversation_manager.add_user_turn(call_id, user_text)

        if detectEmergency(user_text):
            conversation_manager.set_emergency(call_id, "high")

        response_text, function_calls = await agent_service.process_message(
            call_id=call_id,
            user_message=user_text,
            user_id=session.caller_phone,
        )
        conversation_manager.add_assistant_turn(call_id, response_text, function_calls)

        audio_response = await self._synthesize_mp3(response_text, detected_language)
        return {
            "user_text": user_text,
            "response_text": response_text,
            "response_audio_base64": base64.b64encode(audio_response).decode() if audio_response else "",
            "is_emergency": context.is_emergency,
        }

    async def end_session(self, call_id: str) -> None:
        self._sessions.pop(call_id, None)
        if conversation_manager.get_session(call_id):
            conversation_manager.close_session(call_id)
        logger.info("Voice call session ended", call_id=call_id)

    async def _synthesize_mp3(self, text: str, language: str) -> bytes:
        try:
            return await tts_service.synthesize(text, language_code=language, audio_format="mp3")
        except Exception as exc:
            logger.warning("Voice response synthesis failed", error=str(exc), language=language)
            return b""


voice_call_service = VoiceCallService()
