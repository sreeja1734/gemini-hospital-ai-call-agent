"""
Local tool implementations for the hospital receptionist ADK agent.

These tools are intentionally self-contained:
- no Gemini calls
- no speech API calls
- only local static data and local in-memory state
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import structlog

from backend.config import settings

logger = structlog.get_logger(__name__)

HOSPITAL_INFO = {
    "timings": f"{settings.HOSPITAL_NAME} is open from 8 AM to 8 PM, Monday through Saturday. Emergency care is available 24/7.",
    "departments": (
        "Available departments include Cardiology, Orthopedics, Pediatrics, "
        "General Medicine, Neurology, and Emergency."
    ),
    "contact": f"You can reach the hospital at {settings.HOSPITAL_PHONE}.",
    "emergency": "Emergency services are available 24 hours a day, 7 days a week.",
    "location": "The hospital is located at 123 Health Avenue, Medical District.",
    "general": (
        f"{settings.HOSPITAL_NAME} offers outpatient care, appointment booking, "
        "specialist consultations, and 24/7 emergency support."
    ),
}

EMERGENCY_KEYWORDS = (
    "chest pain",
    "breathing difficulty",
    "difficulty breathing",
    "shortness of breath",
    "severe bleeding",
    "unconscious",
    "unconsciousness",
)

LOCAL_APPOINTMENTS: list[dict[str, str]] = []


def _normalize_query(query: str) -> str:
    query_text = (query or "").strip().lower()
    if not query_text:
        return "general"

    if "time" in query_text or "hour" in query_text or "open" in query_text:
        return "timings"
    if "department" in query_text or "special" in query_text:
        return "departments"
    if "contact" in query_text or "phone" in query_text or "number" in query_text:
        return "contact"
    if "emergency" in query_text or "urgent" in query_text:
        return "emergency"
    if "location" in query_text or "address" in query_text or "where" in query_text:
        return "location"
    return "general"


def emergency_keyword_matches(message: str) -> list[str]:
    """Return all emergency keywords found in the message."""
    normalized_message = (message or "").lower()
    return [keyword for keyword in EMERGENCY_KEYWORDS if keyword in normalized_message]


def getHospitalInfo(query: str) -> str:
    """Return static hospital information based on the caller's query."""
    category = _normalize_query(query)
    logger.info("Hospital tool called", tool="getHospitalInfo", category=category, query=query)
    return HOSPITAL_INFO.get(category, HOSPITAL_INFO["general"])


def detectEmergency(message: str) -> bool:
    """Detect obvious emergencies using simple local keyword matching."""
    matches = emergency_keyword_matches(message)
    is_emergency = bool(matches)
    logger.info(
        "Hospital tool called",
        tool="detectEmergency",
        is_emergency=is_emergency,
        matches=matches,
    )
    return is_emergency


def bookAppointment(name: str, department: str) -> str:
    """Simulate an appointment booking using local in-memory storage."""
    patient_name = (name or "Patient").strip() or "Patient"
    department_name = (department or "General Medicine").strip() or "General Medicine"

    appointment = {
        "id": uuid4().hex[:8].upper(),
        "name": patient_name,
        "department": department_name,
        "created_at": datetime.utcnow().isoformat(),
    }
    LOCAL_APPOINTMENTS.append(appointment)

    logger.info(
        "Hospital tool called",
        tool="bookAppointment",
        appointment_id=appointment["id"],
        name=patient_name,
        department=department_name,
    )

    return (
        f"Appointment confirmed for {patient_name} with the {department_name} department. "
        f"Your local booking reference is {appointment['id']}."
    )
