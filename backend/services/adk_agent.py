"""Backward-compatible ADK service shim."""

from backend.services.agent_service import HospitalAgentService, agent_service

AdkConversationAgent = HospitalAgentService
adk_agent = agent_service
