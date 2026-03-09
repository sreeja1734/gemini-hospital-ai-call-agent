"""
Post-Call Transcript Analysis using Gemini 1.5 Flash.
Extracts structured insights from full call transcripts.
"""
import json
import structlog
import google.generativeai as genai

from backend.config import settings

logger = structlog.get_logger()

ANALYSIS_PROMPT_TEMPLATE = """
You are an expert medical call center analyst. Analyze the following hospital call transcript and provide detailed structured insights.

Return ONLY a valid JSON object with this exact structure:
{{
  "intent": "appointment_booking|doctor_availability|hospital_timings|department_info|emergency|general_inquiry|unknown",
  "sentiment": "positive|neutral|negative|distressed",
  "emergency_risk": "low|medium|high",
  "patient_name": "extracted name or null",
  "summary": "2-3 sentence summary of what the call was about and its outcome",
  "key_topics": ["topic1", "topic2"],
  "follow_up_required": true/false,
  "follow_up_reason": "reason if follow_up_required is true, else null",
  "appointment_requested": true/false,
  "appointment_confirmed": true/false,
  "escalation_needed": true/false,
  "language_detected": "en-US|hi-IN|ta-IN",
  "call_outcome": "appointment_booked|transferred|resolved|unresolved|emergency_escalated"
}}

Call Transcript:
---
{transcript}
---
"""


async def analyze_transcript(call_id: str, transcript: str) -> dict:
    """
    Send transcript to Gemini for structured analysis.

    Args:
        call_id: UUID of the call record
        transcript: Full conversation text

    Returns:
        Structured analysis dict
    """
    if not transcript.strip():
        return _empty_analysis()

    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1  # Low temperature for structured output
            )
        )

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(transcript=transcript)
        response = model.generate_content(prompt)
        analysis = json.loads(response.text)

        logger.info(
            "Transcript analysis complete",
            call_id=call_id,
            intent=analysis.get("intent"),
            risk=analysis.get("emergency_risk")
        )
        return analysis

    except json.JSONDecodeError as e:
        logger.error("Gemini returned invalid JSON", error=str(e), call_id=call_id)
        return _empty_analysis()
    except Exception as e:
        logger.error("Transcript analysis failed", error=str(e), call_id=call_id)
        return _empty_analysis()


def _empty_analysis() -> dict:
    """Return a safe default analysis when processing fails."""
    return {
        "intent": "unknown",
        "sentiment": "neutral",
        "emergency_risk": "low",
        "patient_name": None,
        "summary": "Analysis unavailable for this call.",
        "key_topics": [],
        "follow_up_required": False,
        "follow_up_reason": None,
        "appointment_requested": False,
        "appointment_confirmed": False,
        "escalation_needed": False,
        "language_detected": "en-US",
        "call_outcome": "unresolved"
    }


async def batch_analyze_unprocessed_calls(db) -> int:
    """
    Background task: analyze all completed calls without analysis.
    Returns number of calls processed.
    """
    from database.models import Call, Transcript, CallStatus
    from sqlalchemy import select, and_

    try:
        result = await db.execute(
            select(Transcript)
            .join(Call)
            .where(
                and_(
                    Call.status == CallStatus.COMPLETED,
                    Transcript.analysis == None
                )
            )
            .limit(10)
        )
        transcripts = result.scalars().all()

        count = 0
        for transcript in transcripts:
            analysis = await analyze_transcript(
                str(transcript.call_id),
                transcript.content
            )
            transcript.analysis = analysis
            count += 1

        await db.commit()
        logger.info("Batch analysis complete", processed=count)
        return count

    except Exception as e:
        logger.error("Batch analysis failed", error=str(e))
        return 0
