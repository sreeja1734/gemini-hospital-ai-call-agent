"""
Emergency detection service using local keyword matching only.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


EMERGENCY_KEYWORDS_HIGH = [
    "chest pain",
    "pain in my chest",
    "heart attack",
    "cardiac arrest",
    "palpitations",
    "difficulty breathing",
    "can't breathe",
    "shortness of breath",
    "choking",
    "stroke",
    "unconscious",
    "not responding",
    "seizure",
    "convulsion",
    "accident",
    "severe bleeding",
    "blood loss",
    "deep wound",
    "overdose",
    "poisoning",
    "allergic reaction",
    "anaphylaxis",
    "सीने में दर्द",
    "सांस लेने में तकलीफ",
    "மார்பு வலி",
]

EMERGENCY_KEYWORDS_MEDIUM = [
    "high fever",
    "vomiting blood",
    "severe pain",
    "fracture",
    "broken bone",
    "head injury",
    "fainted",
    "very high temperature",
    "diabetic emergency",
    "insulin",
]


@dataclass
class EmergencyAssessment:
    is_emergency: bool
    risk_level: RiskLevel
    detected_keywords: list[str]
    recommendation: str
    should_escalate: bool


def detect_emergency_keywords(text: str) -> EmergencyAssessment:
    """Fast local emergency detection with no external API dependency."""
    normalized_text = (text or "").lower()

    high_matches = [keyword for keyword in EMERGENCY_KEYWORDS_HIGH if keyword.lower() in normalized_text]
    medium_matches = [keyword for keyword in EMERGENCY_KEYWORDS_MEDIUM if keyword.lower() in normalized_text]

    if high_matches:
        return EmergencyAssessment(
            is_emergency=True,
            risk_level=RiskLevel.HIGH,
            detected_keywords=high_matches,
            recommendation="Immediate escalation to emergency staff required. Call 911 if life-threatening.",
            should_escalate=True,
        )

    if medium_matches:
        return EmergencyAssessment(
            is_emergency=True,
            risk_level=RiskLevel.MEDIUM,
            detected_keywords=medium_matches,
            recommendation="Route to on-call doctor and monitor the situation closely.",
            should_escalate=True,
        )

    return EmergencyAssessment(
        is_emergency=False,
        risk_level=RiskLevel.LOW,
        detected_keywords=[],
        recommendation="Standard appointment booking flow.",
        should_escalate=False,
    )


async def assess_emergency_with_ai(symptoms: str, caller_phone: str = "") -> dict:
    """
    Compatibility wrapper kept for older callers.

    Despite the historical name, this now uses local-only logic to preserve the
    architecture boundary that tools and triage checks must not call Gemini.
    """
    assessment = detect_emergency_keywords(symptoms)

    if assessment.is_emergency:
        logger.warning(
            "Emergency detected via local keyword matching",
            caller=caller_phone,
            risk_level=assessment.risk_level.value,
            keywords=assessment.detected_keywords,
        )

    return {
        "is_emergency": assessment.is_emergency,
        "risk_level": assessment.risk_level.value,
        "detected_keywords": assessment.detected_keywords,
        "recommendation": assessment.recommendation,
        "should_escalate": assessment.should_escalate,
        "method": "keyword_only",
    }
