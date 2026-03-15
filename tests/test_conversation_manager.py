"""
Unit tests for the ConversationManager.
"""
import pytest
from ai.conversation_manager import ConversationManager, CallContext, Turn


class TestConversationManager:
    """Tests for the centralized ConversationManager."""

    def setup_method(self):
        self.manager = ConversationManager()

    def test_create_session(self):
        ctx = self.manager.create_session("+1234567890")
        assert ctx.caller_phone == "+1234567890"
        assert ctx.call_id is not None
        assert ctx.is_emergency is False
        assert ctx.risk_level == "low"
        assert ctx.ai_handled is True
        assert ctx.turns == []
        assert ctx.gemini_history == []
        assert self.manager.active_count() == 1

    def test_get_session(self):
        ctx = self.manager.create_session("+1111111111")
        retrieved = self.manager.get_session(ctx.call_id)
        assert retrieved is ctx

    def test_get_nonexistent_session(self):
        result = self.manager.get_session("nonexistent-id")
        assert result is None

    def test_add_user_turn(self):
        ctx = self.manager.create_session("+2222222222")
        self.manager.add_user_turn(ctx.call_id, "Hello, I need help")
        assert len(ctx.turns) == 1
        assert ctx.turns[0].role == "user"
        assert ctx.turns[0].text == "Hello, I need help"
        assert len(ctx.gemini_history) == 1
        assert ctx.gemini_history[0] == {"role": "user", "parts": ["Hello, I need help"]}

    def test_add_assistant_turn(self):
        ctx = self.manager.create_session("+3333333333")
        self.manager.add_assistant_turn(ctx.call_id, "How can I help?")
        assert len(ctx.turns) == 1
        assert ctx.turns[0].role == "assistant"
        assert len(ctx.gemini_history) == 1
        assert ctx.gemini_history[0] == {"role": "model", "parts": ["How can I help?"]}

    def test_add_assistant_turn_with_function_calls(self):
        ctx = self.manager.create_session("+4444444444")
        fn_calls = [{"name": "bookAppointment", "args": {"doctor": "Dr. Kumar"}}]
        self.manager.add_assistant_turn(ctx.call_id, "Booking appointment.", fn_calls)
        assert ctx.turns[0].function_calls == fn_calls

    def test_get_gemini_history(self):
        ctx = self.manager.create_session("+5555555555")
        self.manager.add_user_turn(ctx.call_id, "User message")
        self.manager.add_assistant_turn(ctx.call_id, "Agent response")
        history = self.manager.get_gemini_history(ctx.call_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "model"

    def test_get_gemini_history_nonexistent(self):
        history = self.manager.get_gemini_history("bad-id")
        assert history == []

    def test_update_intent(self):
        ctx = self.manager.create_session("+6666666666")
        self.manager.update_intent(ctx.call_id, "appointment_booking")
        assert ctx.detected_intent == "appointment_booking"

    def test_set_emergency(self):
        ctx = self.manager.create_session("+7777777777")
        self.manager.set_emergency(ctx.call_id, "high")
        assert ctx.is_emergency is True
        assert ctx.risk_level == "high"

    def test_set_patient_name(self):
        ctx = self.manager.create_session("+8888888888")
        self.manager.set_patient_name(ctx.call_id, "Karun")
        assert ctx.patient_name == "Karun"

    def test_close_session(self):
        ctx = self.manager.create_session("+9999999999")
        call_id = ctx.call_id
        closed = self.manager.close_session(call_id)
        assert closed is ctx
        assert closed.ended_at is not None
        assert closed.duration_seconds is not None
        assert self.manager.active_count() == 0
        assert self.manager.get_session(call_id) is None

    def test_close_nonexistent_session(self):
        result = self.manager.close_session("does-not-exist")
        assert result is None

    def test_turn_count(self):
        ctx = self.manager.create_session("+1010101010")
        self.manager.add_user_turn(ctx.call_id, "Hello")
        self.manager.add_assistant_turn(ctx.call_id, "Hi there")
        self.manager.add_user_turn(ctx.call_id, "Book me")
        assert ctx.turn_count == 2  # Only user turns count

    def test_get_transcript(self):
        ctx = self.manager.create_session("+1212121212")
        self.manager.add_user_turn(ctx.call_id, "Hello")
        self.manager.add_assistant_turn(ctx.call_id, "Welcome!")
        transcript = ctx.get_transcript()
        assert "Patient: Hello" in transcript
        assert "AI Assistant: Welcome!" in transcript

    def test_get_all_active(self):
        self.manager.create_session("+1111")
        self.manager.create_session("+2222")
        self.manager.create_session("+3333")
        active = self.manager.get_all_active()
        assert len(active) == 3

    def test_multiple_sessions_isolated(self):
        ctx1 = self.manager.create_session("+1111")
        ctx2 = self.manager.create_session("+2222")
        self.manager.add_user_turn(ctx1.call_id, "Session 1 msg")
        assert len(ctx1.turns) == 1
        assert len(ctx2.turns) == 0
