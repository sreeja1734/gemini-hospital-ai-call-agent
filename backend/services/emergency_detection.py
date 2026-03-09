"""
Emergency Detection Service.

Uses keyword matching + Gemini AI to assess medical emergency risk
from caller descriptions. HIGH priority calls trigger human escalation.
"""
import structlog
from enum import Enum
from dataclasses import dataclass
import google.generativeai as genai

from backend.config import settings

logger = structlog.get_logger()


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# High-priority emergency keywords (immediate escalation)
EMERGENCY_KEYWORDS_HIGH = [
    # Cardiac
    "chest pain", "heart attack", "cardiac arrest", "palpitations",
    # Respiratory
    "difficulty breathing", "can't breathe", "shortness of breath", "choking",
    # Neurological
    "stroke", "unconscious", "not responding", "seizure", "convulsion",
    # Trauma
    "accident", "severe bleeding", "blood loss", "deep wound",
    # Other critical
    "overdose", "poisoning", "allergic reaction", "anaphylaxis",
    "सीने में दर्द",  # Hindi: chest pain
    "सांस लेने में तकलीफ",  # Hindi: difficulty breathing
    "மார்பு வலி",  # Tamil: chest pain
]

# Medium priority keywords (monitor but may not escalate immediately)
EMERGENCY_KEYWORDS_MEDIUM = [
    "high fever", "vomiting blood", "severe pain", "fracture",
    "broken bone", "head injury", "unconscious", "fainted",
    "very high temperature", "diabetic emergency", "insulin",
]


@dataclass
class EmergencyAssessment:
    is_emergency: bool
    risk_level: RiskLevel
    detected_keywords: list[str]
    recommendation: str
    should_escalate: bool


def detect_emergency_keywords(text: str) -> EmergencyAssessment:
    """
    Fast keyword-based emergency detection (no API call needed).
    Used as a first pass before Gemini analysis.
    """
    text_lower = text.lower()

    high_matches = [kw for kw in EMERGENCY_KEYWORDS_HIGH if kw.lower() in text_lower]
    medium_matches = [kw for kw in EMERGENCY_KEYWORDS_MEDIUM if kw.lower() in text_lower]

    if high_matches:
        return EmergencyAssessment(
            is_emergency=True,
            risk_level=RiskLevel.HIGH,
            detected_keywords=high_matches,
            recommendation="Immediate escalation to emergency staff required. Call 911 if life-threatening.",
            should_escalate=True
        )
    elif medium_matches:
        return EmergencyAssessment(
            is_emergency=True,
            risk_level=RiskLevel.MEDIUM,
            detected_keywords=medium_matches,
            recommendation="Route to on-call doctor. Monitor situation.",
            should_escalate=True
        )
    else:
        return EmergencyAssessment(
            is_emergency=False,
            risk_level=RiskLevel.LOW,
            detected_keywords=[],
            recommendation="Standard appointment booking flow.",
            should_escalate=False
        )


async def assess_emergency_with_ai(symptoms: str, caller_phone: str = "") -> dict:
    """
    AI-enhanced emergency assessment using Gemini.
    Combines keyword detection with semantic understanding.
    """
    # Fast keyword check first
    keyword_result = detect_emergency_keywords(symptoms)

    # Skip AI call for clear HIGH risk (speed is critical in emergencies)
    if keyword_result.risk_level == RiskLevel.HIGH:
        logger.warning(
            "HIGH PRIORITY emergency detected",
            keywords=keyword_result.detected_keywords,
            caller=caller_phone
        )
        return {
            "is_emergency": True,
            "risk_level": "high",
            "detected_keywords": keyword_result.detected_keywords,
            "recommendation": keyword_result.recommendation,
            "should_escalate": True,
            "method": "keyword"
        }

    # Use Gemini for nuanced assessment on ambiguous cases
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
You are a medical triage assistant. Assess the emergency level of this caller's description:

"{symptoms}"

Reply ONLY with JSON:
{{
  "is_emergency": true/false,
  "risk_level": "low|medium|high",
  "reason": "brief explanation",
  "recommended_action": "action to take"
}}
"""
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(response_mime_type="application/json")
        )
        import json
        ai_result = json.loads(response.text)

        # Merge keyword and AI results (take the higher risk)
        final_risk = _merge_risk_levels(
            keyword_result.risk_level,
            RiskLevel(ai_result.get("risk_level", "low"))
        )

        return {
            "is_emergency": ai_result.get("is_emergency", False) or keyword_result.is_emergency,
            "risk_level": final_risk.value,
            "detected_keywords": keyword_result.detected_keywords,
            "recommendation": ai_result.get("recommended_action", keyword_result.recommendation),
            "should_escalate": final_risk in [RiskLevel.MEDIUM, RiskLevel.HIGH],
            "method": "ai+keyword"
        }

    except Exception as e:
        logger.error("AI emergency assessment failed, using keyword result", error=str(e))
        return {
            "is_emergency": keyword_result.is_emergency,
            "risk_level": keyword_result.risk_level.value,
            "detected_keywords": keyword_result.detected_keywords,
            "recommendation": keyword_result.recommendation,
            "should_escalate": keyword_result.should_escalate,
            "method": "keyword_fallback"
        }


def _merge_risk_levels(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    """Return the higher of two risk levels."""
    order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
    return a if order[a] >= order[b] else b
