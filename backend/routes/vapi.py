"""
Vapi Custom LLM integration endpoints.

Exposes an OpenAI-compatible /chat/completions endpoint that Vapi can call.
Uses Google Gemini for conversation logic and returns either:
- assistant text for Vapi TTS, or
- tool_calls to trigger Vapi call transfer (doctor / emergency).
"""
import json
import time
import structlog
from typing import Any, Dict, List

import google.generativeai as genai
from fastapi import APIRouter, Request

from ..config import settings

router = APIRouter(tags=["Vapi"])
logger = structlog.get_logger()


def _get_gemini_client() -> genai.GenerativeModel:
    """Initialize a lightweight Gemini client for Vapi conversations."""
    api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
    genai.configure(api_key=api_key)

    # Use a fast but capable model; configurable via env if needed
    model_name = settings.GEMINI_MODEL or "gemini-2.0-flash"

    system_prompt = f"""
You are an AI hospital receptionist for {settings.HOSPITAL_NAME}.

Your job:
- Greet callers: "Hello, thank you for calling our healthcare center. How can I help you today?"
- If the caller wants to book an appointment, politely ask for:
  - their full name
  - preferred date and time
- If the caller wants to talk to a doctor (non-emergency), we will transfer the call to a doctor number.
- If the caller describes an emergency (chest pain, trouble breathing, severe bleeding, accident, unconsciousness, etc.),
  we will immediately transfer the call to the emergency number.
- For general questions about the hospital, departments, timings, or services, answer as a receptionist would.

You MUST respond in STRICT JSON only, with no extra text, markdown, or code fences.
JSON shape:
{{
  "intent": "emergency" | "doctor" | "appointment" | "general",
  "replyText": "what you want spoken back to the caller"
}}

Rules:
- If any life-threatening situation or the word "emergency" is clearly mentioned → intent = "emergency".
  Keep replyText short like "I'm connecting you to emergency services now."
- If the caller explicitly asks to speak with a doctor or nurse and it is not an emergency → intent = "doctor".
- If the caller is clearly asking to book or reschedule an appointment → intent = "appointment".
- Otherwise → intent = "general".
""".strip()

    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
    )


async def get_gemini_receptionist_reply(messages: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Call Gemini with the conversation so far and return { intent, replyText }.

    `messages` is expected to be an OpenAI-style list of { role, content } items.
    """
    model = _get_gemini_client()

    # Build a single prompt summarizing the conversation
    history_text_lines: List[str] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        history_text_lines.append(f"{role.upper()}: {content}")

    history_text = "\n".join(history_text_lines)

    prompt = f"""
Conversation so far:
{history_text}

Based on the conversation, decide the next thing the receptionist should say.
Return ONLY the JSON object as described in the system instructions.
""".strip()

    response = model.generate_content(prompt)
    raw = (response.text or "").strip()

    try:
        parsed = json.loads(raw)
        intent = parsed.get("intent", "general")
        reply_text = parsed.get(
            "replyText",
            "Hello, thank you for calling our healthcare center. How can I help you today?",
        )
        return {"intent": intent, "replyText": reply_text}
    except Exception as exc:
        logger.error("Failed to parse Gemini JSON for Vapi", raw=raw, error=str(exc))
        return {
            "intent": "general",
            "replyText": "Hello, thank you for calling our healthcare center. How can I help you today?",
        }


@router.post("/chat/completions")
async def vapi_chat_completions(request: Request) -> Dict[str, Any]:
    """
    OpenAI-compatible chat completions endpoint for Vapi Custom LLM.

    Configure Vapi Custom LLM:
    - Base URL: https://<your-domain>/vapi
    - Path: /chat/completions
    """
    body = await request.json()
    messages = body.get("messages") or []
    model_name = body.get("model", "gemini-hospital-receptionist")

    try:
        result = await get_gemini_receptionist_reply(messages)
        intent = result["intent"]
        reply_text = result["replyText"]

        now = int(time.time())

        # Handle transfers via tool_calls that Vapi will execute
        if intent == "emergency":
            phone = settings.EMERGENCY_PHONE_NUMBER or settings.HOSPITAL_PHONE
            tool_call = {
                "id": "transfer_emergency_1",
                "type": "function",
                "function": {
                    "name": "transfer_to_number",
                    "arguments": json.dumps(
                        {
                            "reason": "emergency",
                            "phoneNumber": phone,
                        }
                    ),
                },
            }
            return {
                "id": "chatcmpl-emergency-transfer",
                "object": "chat.completion",
                "created": now,
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "tool_calls": [tool_call],
                        },
                    }
                ],
            }

        if intent == "doctor":
            phone = settings.DOCTOR_PHONE_NUMBER or settings.RECEPTIONIST_PHONE
            tool_call = {
                "id": "transfer_doctor_1",
                "type": "function",
                "function": {
                    "name": "transfer_to_number",
                    "arguments": json.dumps(
                        {
                            "reason": "doctor",
                            "phoneNumber": phone,
                        }
                    ),
                },
            }
            return {
                "id": "chatcmpl-doctor-transfer",
                "object": "chat.completion",
                "created": now,
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "tool_calls": [tool_call],
                        },
                    }
                ],
            }

        # Default: speak the reply back to the caller
        return {
            "id": "chatcmpl-gemini-reply",
            "object": "chat.completion",
            "created": now,
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": reply_text,
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    except Exception as exc:
        logger.error("Error in Vapi chat completions", error=str(exc))
        # Fallback error message Vapi can still speak
        now = int(time.time())
        return {
            "id": "chatcmpl-error-fallback",
            "object": "chat.completion",
            "created": now,
            "model": "error-fallback",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "I'm experiencing technical difficulties. Please hold while we connect you to a staff member or try again later.",
                    },
                }
            ],
        }

