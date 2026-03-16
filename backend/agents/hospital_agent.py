"""
ADK hospital receptionist agent configuration.
"""
from __future__ import annotations

import structlog

from backend.config import settings
from backend.tools.hospital_tools import bookAppointment, detectEmergency, getHospitalInfo

logger = structlog.get_logger(__name__)


def _load_agent_class():
    try:
        from google.adk.agents.llm_agent import Agent

        return Agent
    except Exception:
        pass

    try:
        from google.adk.agents import LlmAgent

        return LlmAgent
    except Exception:
        pass

    try:
        from google.adk.agents import Agent

        return Agent
    except Exception:
        return None


def _load_gemini_model_class():
    try:
        from google.adk.models.google_llm import Gemini

        return Gemini
    except Exception:
        return None


def _build_model(model_name: str):
    gemini_model_class = _load_gemini_model_class()
    if gemini_model_class is None:
        raise ImportError("google-adk Gemini model class is unavailable")

    try:
        return gemini_model_class(model=model_name)
    except TypeError:
        return gemini_model_class(model_name=model_name)


def _build_hospital_receptionist_agent():
    agent_class = _load_agent_class()
    if agent_class is None:
        logger.error("Failed to initialize hospital receptionist ADK agent", error="Agent class unavailable")
        return None

    instructions = f"""
You are a hospital receptionist AI for {settings.HOSPITAL_NAME}.

Your responsibilities:
- answer hospital information queries
- guide patients to the correct department
- help book appointments
- detect emergency situations

Rules:
- All reasoning must stay inside this ADK agent.
- Use tools only for local logic and never assume tools can call external APIs.
- If detectEmergency returns true, clearly advise the caller to contact emergency services immediately.
- Keep phone-call responses concise, calm, and professional.
- If the request is about timings, departments, emergency availability, contact number, or location, use getHospitalInfo.
- If the caller wants to book an appointment, use bookAppointment once the caller name and department are known.
""".strip()

    model = _build_model(settings.GEMINI_MODEL)
    common_kwargs = {
        "name": "hospital_receptionist_agent",
        "model": model,
        "tools": [getHospitalInfo, detectEmergency, bookAppointment],
    }

    for instruction_field in ("instruction", "instructions"):
        try:
            agent = agent_class(**common_kwargs, **{instruction_field: instructions})
            logger.info(
                "Hospital receptionist ADK agent initialized",
                model=settings.GEMINI_MODEL,
                instruction_field=instruction_field,
            )
            return agent
        except Exception as exc:
            logger.warning(
                "Hospital receptionist ADK agent init attempt failed",
                error=str(exc),
                instruction_field=instruction_field,
            )

    logger.error("Failed to initialize hospital receptionist ADK agent after all constructor attempts")
    return None


hospital_receptionist_agent = _build_hospital_receptionist_agent()
