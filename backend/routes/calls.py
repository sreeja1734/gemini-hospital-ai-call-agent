"""
FastAPI routes for call handling and Gemini AI conversation.
Handles: Twilio webhooks, WebSocket streaming, speech processing.
"""
import json
import uuid
import base64
import structlog
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..config import settings
from database.connection import get_db
from database.models import Call, Patient, Transcript, CallStatus, Intent, RiskLevel
from ..services.gemini_agent import gemini_agent
from ..services.appointment_service import check_doctor_availability, book_appointment
from ..services.emergency_detection import assess_emergency_with_ai
from ai.conversation_manager import conversation_manager
from ai.speech_to_text import stt_service
from ai.text_to_speech import tts_service
from ai.transcript_analysis import analyze_transcript

router = APIRouter(tags=["Calls"])
logger = structlog.get_logger()


# ── Request/Response models
class StartConversationRequest(BaseModel):
    caller_phone: str
    twilio_call_sid: str = ""
    language: str = "en-US"


class ProcessSpeechRequest(BaseModel):
    call_id: str
    audio_base64: str = ""   # Base64-encoded MULAW audio
    text_input: str = ""     # Alternative: direct text (for testing)
    language: str = "en-US"


class AnalyzeTranscriptRequest(BaseModel):
    call_id: str
    transcript: str = ""     # If empty, uses stored transcript


class EndCallRequest(BaseModel):
    call_id: str
    twilio_call_sid: str = ""


# ── Gemini function call handler
async def handle_function_call(fn_name: str, fn_args: dict, session) -> dict:
    """Dispatch Gemini function calls to backend services."""
    logger.info("Handling function call", function=fn_name)

    if fn_name == "checkDoctorAvailability":
        return await check_doctor_availability(
            doctor_name=fn_args.get("doctor_name"),
            department=fn_args.get("department"),
            preferred_date=fn_args.get("preferred_date")
        )

    elif fn_name == "bookAppointment":
        result = await book_appointment(
            patient_name=fn_args.get("patient_name", "Patient"),
            doctor_name=fn_args.get("doctor_name"),
            appointment_slot=fn_args.get("appointment_slot"),
            patient_phone=session.caller_phone,
            department=fn_args.get("department", "General Medicine"),
            notes=fn_args.get("notes", ""),
            call_id=session.call_id
        )
        return result

    elif fn_name == "getHospitalInfo":
        return get_hospital_info(fn_args.get("query_type", "general"))

    elif fn_name == "detectEmergency":
        result = await assess_emergency_with_ai(
            symptoms=fn_args.get("symptoms", ""),
            caller_phone=session.caller_phone
        )
        if result.get("is_emergency"):
            ctx = conversation_manager.get_session(session.call_id)
            if ctx:
                conversation_manager.set_emergency(session.call_id, result["risk_level"])
        return result

    elif fn_name == "escalateToHuman":
        ctx = conversation_manager.get_session(session.call_id)
        if ctx:
            ctx.ai_handled = False
        return {
            "escalated": True,
            "message": f"Transferring to human receptionist. Reason: {fn_args.get('reason')}",
            "wait_message": "Please hold while I connect you to our team."
        }

    return {"error": f"Unknown function: {fn_name}"}


def get_hospital_info(query_type: str) -> dict:
    """Return static hospital information."""
    info = {
        "departments": {
            "available": ["Cardiology", "Orthopedics", "Pediatrics", "General Medicine", "Neurology", "Emergency"],
            "emergency": "Emergency department is open 24/7"
        },
        "timings": {
            "weekdays": "Monday to Saturday: 8:00 AM - 8:00 PM",
            "emergency": "Emergency: 24 hours, 7 days",
            "pharmacy": "Pharmacy: 8:00 AM - 10:00 PM"
        },
        "emergency": {
            "number": settings.HOSPITAL_PHONE,
            "location": "Ground Floor, Emergency Block",
            "note": "For life-threatening emergencies, please call 911 immediately"
        },
        "location": {
            "address": "123 Health Avenue, Medical District",
            "parking": "Free parking available for patients",
            "public_transport": "Metro station 5 minutes walk"
        },
        "general": {
            "name": settings.HOSPITAL_NAME,
            "specialties": "Multi-specialty hospital with 500+ beds",
            "contact": settings.HOSPITAL_PHONE
        }
    }
    return info.get(query_type, info["general"])


# ── Routes

@router.post("/incoming-call")
async def incoming_call(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Exotel webhook for incoming calls.
    Returns Exotel Custom XML to connect call to WebSocket stream.
    """
    form_data = await request.form()
    caller_phone = form_data.get("From", "Unknown")
    # Exotel CallSid
    exotel_sid = form_data.get("CallSid", str(uuid.uuid4()))

    # Create conversation session
    ctx = conversation_manager.create_session(caller_phone)
    gemini_session = gemini_agent.create_session(caller_phone)

    # Store call in DB
    call = Call(
        id=uuid.UUID(ctx.call_id),
        twilio_call_sid=exotel_sid,  # Sticking to the DB column name for the third-party SID
        caller_phone=caller_phone,
        status=CallStatus.ACTIVE
    )
    db.add(call)
    await db.flush()

    logger.info("Incoming call", phone=caller_phone, call_id=ctx.call_id)

    # Return Exotel XML to stream audio to our WebSocket
    # Note: Replace 'your-domain.com' with the actual ngrok/production domain
    ws_url = f"wss://your-domain.com/ws/call/{ctx.call_id}"
    
    # Exotel uses standard XML for WebSockets
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
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize a new call session and return the greeting.
    Use this for testing or non-Twilio call initiation.
    """
    ctx = conversation_manager.create_session(req.caller_phone)
    ctx.language = req.language

    gemini_session = gemini_agent.create_session(req.caller_phone)
    greeting = await gemini_agent.get_greeting(gemini_session)

    conversation_manager.add_assistant_turn(ctx.call_id, greeting)

    # Synthesize greeting audio
    audio_bytes = await tts_service.synthesize(greeting, req.language)
    audio_b64 = base64.b64encode(audio_bytes).decode() if audio_bytes else ""

    return {
        "call_id": ctx.call_id,
        "greeting_text": greeting,
        "greeting_audio_base64": audio_b64,
        "session_started": True
    }


@router.post("/process-user-speech")
async def process_user_speech(
    req: ProcessSpeechRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a user's speech turn:
    1. STT if audio provided
    2. Emergency detection
    3. Gemini response generation
    4. TTS audio output
    """
    ctx = conversation_manager.get_session(req.call_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Call session not found")

    gemini_session = gemini_agent.get_session(req.call_id)

    # Step 1: Speech to Text
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

    # Step 2: Quick emergency check
    emergency_result = await assess_emergency_with_ai(user_text, ctx.caller_phone)
    if emergency_result["is_emergency"] and emergency_result["risk_level"] == "high":
        conversation_manager.set_emergency(req.call_id, "high")

    # Step 3: Gemini generates response (with function calling)
    if not gemini_session:
        gemini_session = gemini_agent.create_session(ctx.caller_phone)

    response_text, fn_calls = await gemini_agent.process_message(
        gemini_session, user_text,
        function_handler=lambda fn, args, sess: handle_function_call(fn, args, ctx)
    )

    conversation_manager.add_assistant_turn(req.call_id, response_text, fn_calls)

    # Step 4: TTS
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
        "turn_count": ctx.turn_count
    }


@router.post("/end-call")
async def end_call(req: EndCallRequest, db: AsyncSession = Depends(get_db)):
    """
    End a call session, save transcript, and trigger analysis.
    """
    ctx = conversation_manager.close_session(req.call_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Call session not found")

    # Update call record
    call_result = await db.execute(
        select(Call).where(Call.id == uuid.UUID(req.call_id))
    )
    call = call_result.scalar_one_or_none()

    if call:
        call.status = CallStatus.ESCALATED if not ctx.ai_handled else CallStatus.COMPLETED
        call.emergency_flag = ctx.is_emergency
        call.risk_level = RiskLevel(ctx.risk_level)
        call.ai_handled = ctx.ai_handled
        call.duration_seconds = ctx.duration_seconds
        call.ended_at = datetime.utcnow()
        if ctx.detected_intent:
            try:
                call.intent = Intent(ctx.detected_intent)
            except ValueError:
                call.intent = Intent.UNKNOWN

    # Save transcript
    transcript_text = ctx.get_transcript()
    if transcript_text and call:
        existing = await db.execute(
            select(Transcript).where(Transcript.call_id == uuid.UUID(req.call_id))
        )
        if not existing.scalar_one_or_none():
            transcript = Transcript(
                call_id=uuid.UUID(req.call_id),
                content=transcript_text,
                turn_count=ctx.turn_count
            )
            db.add(transcript)

    # Async analysis (fire and forget)
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
        "analysis": analysis
    }


@router.post("/analyze-transcript")
async def analyze_transcript_endpoint(
    req: AnalyzeTranscriptRequest,
    db: AsyncSession = Depends(get_db)
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

            elif event_type == "media":
                # Receive audio chunk from Exotel
                audio_payload = data.get("media", {}).get("payload", "")
                if audio_payload:
                    audio_bytes = base64.b64decode(audio_payload)

                    # Transcribe
                    text, confidence, _ = await stt_service.transcribe_audio_bytes(audio_bytes)
                    if text and confidence > 0.5:
                        conversation_manager.add_user_turn(call_id, text)

                        # Get Gemini response
                        ctx = conversation_manager.get_session(call_id)
                        gemini_session = gemini_agent.get_session(call_id)
                        if ctx and gemini_session:
                            response_text, _ = await gemini_agent.process_message(
                                gemini_session, text,
                                function_handler=lambda fn, args, sess: handle_function_call(fn, args, ctx)
                            )
                            # Synthesize and send back
                            audio_out = await tts_service.synthesize(response_text, ctx.language)
                            if audio_out:
                                await websocket.send_json({
                                    "event": "media",
                                    "media": {
                                        "payload": base64.b64encode(audio_out).decode()
                                    }
                                })

            elif event_type == "stop":
                logger.info("Exotel stream stopped", call_id=call_id)
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", call_id=call_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), call_id=call_id)
