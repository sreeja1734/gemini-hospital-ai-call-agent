"""
Unit tests for the emergency detection service.
"""
import pytest
from backend.services.emergency_detection import (
    detect_emergency_keywords,
    RiskLevel,
)


class TestKeywordDetection:
    """Test the fast keyword-based emergency detection."""

    def test_high_risk_chest_pain(self):
        result = detect_emergency_keywords("I'm having severe chest pain")
        assert result.is_emergency is True
        assert result.risk_level == RiskLevel.HIGH
        assert result.should_escalate is True
        assert "chest pain" in result.detected_keywords

    def test_high_risk_difficulty_breathing(self):
        result = detect_emergency_keywords("My mother can't breathe properly")
        assert result.is_emergency is True
        assert result.risk_level == RiskLevel.HIGH
        assert result.should_escalate is True

    def test_high_risk_stroke(self):
        result = detect_emergency_keywords("I think he's having a stroke")
        assert result.is_emergency is True
        assert result.risk_level == RiskLevel.HIGH

    def test_high_risk_hindi_keywords(self):
        result = detect_emergency_keywords("मुझे सीने में दर्द हो रहा है")
        assert result.is_emergency is True
        assert result.risk_level == RiskLevel.HIGH

    def test_medium_risk_high_fever(self):
        result = detect_emergency_keywords("My child has a very high fever")
        assert result.is_emergency is True
        assert result.risk_level == RiskLevel.MEDIUM
        assert result.should_escalate is True

    def test_medium_risk_fracture(self):
        result = detect_emergency_keywords("I think I have a broken bone in my arm")
        assert result.is_emergency is True
        assert result.risk_level == RiskLevel.MEDIUM

    def test_low_risk_appointment(self):
        result = detect_emergency_keywords("I want to book an appointment with a cardiologist")
        assert result.is_emergency is False
        assert result.risk_level == RiskLevel.LOW
        assert result.should_escalate is False
        assert result.detected_keywords == []

    def test_low_risk_general_question(self):
        result = detect_emergency_keywords("What are your hospital timings?")
        assert result.is_emergency is False
        assert result.risk_level == RiskLevel.LOW

    def test_case_insensitive(self):
        result = detect_emergency_keywords("I'M HAVING CHEST PAIN RIGHT NOW")
        assert result.is_emergency is True
        assert result.risk_level == RiskLevel.HIGH

    def test_multiple_high_keywords(self):
        result = detect_emergency_keywords("He had an accident and there is severe bleeding")
        assert result.is_emergency is True
        assert result.risk_level == RiskLevel.HIGH
        assert len(result.detected_keywords) >= 2

    def test_empty_text(self):
        result = detect_emergency_keywords("")
        assert result.is_emergency is False
        assert result.risk_level == RiskLevel.LOW
