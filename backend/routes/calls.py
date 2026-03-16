"""
FastAPI routes for call handling and ADK-powered hospital conversations.
Handles: Exotel webhooks, WebSocket streaming, speech processing.
"""
import base64
import json
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.conversation_manager import conversation_manager
from ai.speech_to_text import stt_service
from ai.text_to_speech import tts_service
from ai.transcript_analysis import analyze_transcript
from database.connection import get_db
from database.models import Call, CallStatus, Intent, RiskLevel, Transcript

from ..config import settings
from ..services.agent_service import agent_service
from ..tools.hospital_tools import detectEmergency

router = APIRouter(tags=["Calls"])
logger = structlog.get_logger()


class StartConversationRequest(BaseModel):
    caller_phone: str
    twilio_call_sid: str = ""
    language: str = "en-US"


class ProcessSpeechRequest(BaseModel):
    call_id: str
    audio_base64: str = ""
    text_input: str = ""
    language: str = "en-US"


class AnalyzeTranscriptRequest(BaseModel):
    call_id: str
    transcript: str = ""


class EndCallRequest(BaseModel):
    call_id: str
    twilio_call_sid: str = ""


@router.post("/incoming-call")
async def incoming_call(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Exotel webhook for incoming calls.
    Returns Exotel Custom XML to connect call to WebSocket stream.
    """
    form_data = await request.form()
    caller_phone = form_data.get("From", "Unknown")
    exotel_sid = form_data.get("CallSid", str(uuid.uuid4()))

    ctx = conversation_manager.create_session(caller_phone)

    call = Call(
        id=uuid.UUID(ctx.call_id),
        twilio_call_sid=exotel_sid,
        caller_phone=caller_phone,
        status=CallStatus.ACTIVE,
    )
    db.add(call)
    await db.flush()

    logger.info("Incoming call", phone=caller_phone, call_id=ctx.call_id)

    ws_url = f"{settings.WS_BASE_URL}/ws/call/{ctx.call_id}"
    exotel_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}">
      <Parameter name="callId" value="{ctx.call_id}" />
    </Stream>
  </Connect>
</Response>"""

    return Response(content=exotel_xml, media_type="application/xml")


@router.post("/start-conversation")
async def start_conversation(
    req: StartConversationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Initialize a new call session and return the greeting.
    Use this for testing or non-Exotel call initiation.
    """
    ctx = conversation_manager.create_session(req.caller_phone)
    ctx.language = req.language

    await agent_service.initialize_session(ctx.call_id, req.caller_phone)
    greeting = agent_service.get_greeting()
    conversation_manager.add_assistant_turn(ctx.call_id, greeting)

    try:
        audio_bytes = await tts_service.synthesize(greeting, req.language)
        audio_b64 = base64.b64encode(audio_bytes).decode() if audio_bytes else ""
    except Exception:
        audio_b64 = ""

    return {
        "call_id": ctx.call_id,
        "greeting_text": greeting,
        "greeting_audio_base64": audio_b64,
        "session_started": True,
    }


@router.post("/process-user-speech")
async def process_user_speech(
    req: ProcessSpeechRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Process a user's speech turn:
    1. STT if audio provided
    2. ADK agent reasoning with local tools
    3. TTS audio output
    """
    ctx = conversation_manager.get_session(req.call_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Call session not found")

    if req.audio_base64:
        audio_bytes = base64.b64decode(req.audio_base64)
        user_text, confidence, detected_lang = await stt_service.transcribe_audio_bytes(
            audio_bytes, req.language
        )
        ctx.language = detected_lang
    else:
        user_text = req.text_input

    if not user_text:
        return {"response_text": "I didn't catch that. Could you please repeat?"}

    conversation_manager.add_user_turn(req.call_id, user_text)

    if detectEmergency(user_text):
        conversation_manager.set_emergency(req.call_id, "high")

    response_text, fn_calls = await agent_service.process_message(
        call_id=req.call_id,
        user_message=user_text,
        user_id=ctx.caller_phone,
    )

    conversation_manager.add_assistant_turn(req.call_id, response_text, fn_calls)

    audio_bytes = await tts_service.synthesize(response_text, ctx.language)
    audio_b64 = base64.b64encode(audio_bytes).decode() if audio_bytes else ""

    return {
        "call_id": req.call_id,
        "user_text": user_text,
        "response_text": response_text,
        "response_audio_base64": audio_b64,
        "is_emergency": ctx.is_emergency,
        "risk_level": ctx.risk_level,
        "function_calls": fn_calls,
        "turn_count": ctx.turn_count,
    }


@router.post("/end-call")
async def end_call(req: EndCallRequest, db: AsyncSession = Depends(get_db)):
    """
    End a call session, save transcript, and trigger analysis.
    """
    ctx = conversation_manager.close_session(req.call_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Call session not found")

    call_result = await db.execute(select(Call).where(Call.id == uuid.UUID(req.call_id)))
    call = call_result.scalar_one_or_none()

    if call:
        call.status = CallStatus.ESCALATED if not ctx.ai_handled else CallStatus.COMPLETED
        call.emergency_flag = ctx.is_emergency
        call.risk_level = RiskLevel(ctx.risk_level)
        call.ai_handled = ctx.ai_handled
        call.duration_seconds = ctx.duration_seconds
        call.ended_at = datetime.now(timezone.utc)
        if ctx.detected_intent:
            try:
                call.intent = Intent(ctx.detected_intent)
            except ValueError:
                call.intent = Intent.UNKNOWN

    transcript_text = ctx.get_transcript()
    if transcript_text and call:
        existing = await db.execute(
            select(Transcript).where(Transcript.call_id == uuid.UUID(req.call_id))
        )
        if not existing.scalar_one_or_none():
            transcript = Transcript(
                call_id=uuid.UUID(req.call_id),
                content=transcript_text,
                turn_count=ctx.turn_count,
            )
            db.add(transcript)

    analysis = await analyze_transcript(req.call_id, transcript_text)
    if call and analysis:
        result = await db.execute(
            select(Transcript).where(Transcript.call_id == uuid.UUID(req.call_id))
        )
        tr = result.scalar_one_or_none()
        if tr:
            tr.analysis = analysis

    await db.flush()

    return {
        "call_id": req.call_id,
        "duration_seconds": ctx.duration_seconds,
        "turn_count": ctx.turn_count,
        "is_emergency": ctx.is_emergency,
        "ai_handled": ctx.ai_handled,
        "analysis": analysis,
    }


@router.post("/analyze-transcript")
async def analyze_transcript_endpoint(
    req: AnalyzeTranscriptRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger transcript analysis for a completed call."""
    transcript_text = req.transcript

    if not transcript_text:
        tr_result = await db.execute(
            select(Transcript).where(Transcript.call_id == uuid.UUID(req.call_id))
        )
        tr = tr_result.scalar_one_or_none()
        if not tr:
            raise HTTPException(status_code=404, detail="Transcript not found")
        transcript_text = tr.content

    analysis = await analyze_transcript(req.call_id, transcript_text)
    return {"call_id": req.call_id, "analysis": analysis}


@router.websocket("/ws/call/{call_id}")
async def websocket_call_stream(websocket: WebSocket, call_id: str):
    """
    WebSocket endpoint for Exotel media streams.
    Handles bidirectional audio streaming for live calls.
    """
    await websocket.accept()
    logger.info("WebSocket call stream connected", call_id=call_id)

    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event_type = data.get("event")

            if event_type == "start":
                logger.info("Exotel stream started", call_id=call_id)
                ctx = conversation_manager.get_session(call_id)
                if ctx:
                    await agent_service.initialize_session(call_id, ctx.caller_phone)
                    greeting = agent_service.get_greeting()
                    conversation_manager.add_assistant_turn(call_id, greeting)

                    try:
                        audio_out = await tts_service.synthesize(greeting, ctx.language)
                    except Exception:
                        audio_out = b""

                    if audio_out:
                        await websocket.send_json(
                            {
                                "event": "media",
                                "media": {
                                    "payload": base64.b64encode(audio_out).decode(),
                                },
                            }
                        )

            elif event_type == "media":
                audio_payload = data.get("media", {}).get("payload", "")
                if audio_payload:
                    audio_bytes = base64.b64decode(audio_payload)
                    text, confidence, _ = await stt_service.transcribe_audio_bytes(audio_bytes)
                    if text and confidence > 0.5:
                        conversation_manager.add_user_turn(call_id, text)
                        if detectEmergency(text):
                            conversation_manager.set_emergency(call_id, "high")

                        ctx = conversation_manager.get_session(call_id)
                        if ctx:
                            response_text, _ = await agent_service.process_message(
                                call_id=call_id,
                                user_message=text,
                                user_id=ctx.caller_phone,
                            )
                            conversation_manager.add_assistant_turn(call_id, response_text)

                            audio_out = await tts_service.synthesize(response_text, ctx.language)
                            if audio_out:
                                await websocket.send_json(
                                    {
                                        "event": "media",
                                        "media": {
                                            "payload": base64.b64encode(audio_out).decode(),
                                        },
                                    }
                                )

            elif event_type == "stop":
                logger.info("Exotel stream stopped", call_id=call_id)
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", call_id=call_id)
    except Exception as exc:
        logger.error("WebSocket error", error=str(exc), call_id=call_id)
