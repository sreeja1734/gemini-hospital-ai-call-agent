"""
Conversation Manager — maintains call session state and context.
Bridges the Gemini agent, STT, TTS, and DB persistence layers.
"""
import uuid
import structlog
from datetime import datetime
from typing import Optional, AsyncIterator
from dataclasses import dataclass, field

from backend.config import settings

logger = structlog.get_logger()


@dataclass
class Turn:
    """A single conversation turn (user or assistant)."""
    role: str  # "user" | "assistant"
    text: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    function_calls: list = field(default_factory=list)


@dataclass
class CallContext:
    """Full context for an active call session."""
    call_id: str
    caller_phone: str
    language: str = "en-US"
    patient_name: Optional[str] = None
    detected_intent: Optional[str] = None
    is_emergency: bool = False
    risk_level: str = "low"
    ai_handled: bool = True
    turns: list[Turn] = field(default_factory=list)
    pending_appointment: Optional[dict] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    @property
    def turn_count(self) -> int:
        return len([t for t in self.turns if t.role == "user"])

    @property
    def duration_seconds(self) -> Optional[int]:
        if self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return None

    def get_transcript(self) -> str:
        """Build a readable full transcript."""
        lines = []
        for turn in self.turns:
            prefix = "Patient" if turn.role == "user" else "AI Assistant"
            lines.append(f"[{turn.timestamp.strftime('%H:%M:%S')}] {prefix}: {turn.text}")
        return "\n".join(lines)


class ConversationManager:
    """
    Central session manager for all active call contexts.
    Manages lifecycle: create → add turns → close → serialize.
    """

    def __init__(self):
        self._sessions: dict[str, CallContext] = {}
        logger.info("ConversationManager initialized")

    def create_session(self, caller_phone: str) -> CallContext:
        """Create a new call context and return it."""
        call_id = str(uuid.uuid4())
        context = CallContext(call_id=call_id, caller_phone=caller_phone)
        self._sessions[call_id] = context
        logger.info("Call session created", call_id=call_id, phone=caller_phone)
        return context

    def get_session(self, call_id: str) -> Optional[CallContext]:
        return self._sessions.get(call_id)

    def add_user_turn(self, call_id: str, text: str) -> None:
        ctx = self._sessions.get(call_id)
        if ctx:
            ctx.turns.append(Turn(role="user", text=text))

    def add_assistant_turn(
        self, call_id: str, text: str, function_calls: list = None
    ) -> None:
        ctx = self._sessions.get(call_id)
        if ctx:
            ctx.turns.append(Turn(role="assistant", text=text, function_calls=function_calls or []))

    def update_intent(self, call_id: str, intent: str) -> None:
        ctx = self._sessions.get(call_id)
        if ctx:
            ctx.detected_intent = intent

    def set_emergency(self, call_id: str, risk_level: str = "high") -> None:
        ctx = self._sessions.get(call_id)
        if ctx:
            ctx.is_emergency = True
            ctx.risk_level = risk_level
            logger.warning("Emergency flagged on call", call_id=call_id, risk=risk_level)

    def set_patient_name(self, call_id: str, name: str) -> None:
        ctx = self._sessions.get(call_id)
        if ctx:
            ctx.patient_name = name

    def close_session(self, call_id: str) -> Optional[CallContext]:
        """End a session and return the final context for persistence."""
        ctx = self._sessions.pop(call_id, None)
        if ctx:
            ctx.ended_at = datetime.utcnow()
            logger.info(
                "Call session closed",
                call_id=call_id,
                duration=ctx.duration_seconds,
                turns=ctx.turn_count
            )
        return ctx

    def get_all_active(self) -> list[str]:
        """Return IDs of all active call sessions."""
        return list(self._sessions.keys())

    def active_count(self) -> int:
        return len(self._sessions)


# Singleton
conversation_manager = ConversationManager()
