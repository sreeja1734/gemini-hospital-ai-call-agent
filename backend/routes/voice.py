"""
WebSocket voice route for browser-based AI calls.

Protocol:
- client sends JSON messages: `session.start`, `audio.chunk`, `audio.commit`, `session.stop`
- server sends JSON messages: `state`, `session.ready`, `assistant.response`, `error`
"""
from __future__ import annotations

import base64
import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.voice_call_service import voice_call_service

router = APIRouter(tags=["Voice"])
logger = structlog.get_logger(__name__)


@router.websocket("/ws/voice-call")
async def websocket_voice_call(websocket: WebSocket) -> None:
    await websocket.accept()
    active_call_id: str | None = None

    try:
        await websocket.send_json({"type": "state", "state": "connecting"})

        while True:
            raw_message = await websocket.receive()

            if raw_message.get("type") == "websocket.disconnect":
                break

            text_data = raw_message.get("text")
            if not text_data:
                continue

            payload = json.loads(text_data)
            message_type = payload.get("type")

            if message_type == "session.start":
                session = await voice_call_service.start_session(
                    caller_phone=payload.get("callerPhone") or "browser-user",
                    language=payload.get("language") or "en-US",
                )
                active_call_id = session["call_id"]
                await websocket.send_json(
                    {
                        "type": "session.ready",
                        "callId": session["call_id"],
                        "greetingText": session["greeting_text"],
                        "greetingAudioBase64": session["greeting_audio_base64"],
                        "state": "ai-speaking",
                    }
                )
                continue

            if message_type == "audio.chunk":
                call_id = payload.get("callId")
                audio_b64 = payload.get("audio")
                if call_id and audio_b64:
                    voice_call_service.append_audio(call_id, base64.b64decode(audio_b64))
                continue

            if message_type == "audio.commit":
                call_id = payload.get("callId")
                if not call_id:
                    await websocket.send_json({"type": "error", "message": "Missing call id for audio commit."})
                    continue

                await websocket.send_json({"type": "state", "state": "connecting"})
                response = await voice_call_service.process_audio_turn(call_id)
                if response is None:
                    await websocket.send_json({"type": "state", "state": "listening"})
                    continue

                await websocket.send_json(
                    {
                        "type": "assistant.response",
                        "callId": call_id,
                        "transcript": response["user_text"],
                        "responseText": response["response_text"],
                        "responseAudioBase64": response["response_audio_base64"],
                        "isEmergency": response["is_emergency"],
                        "state": "ai-speaking",
                    }
                )
                continue

            if message_type == "session.stop":
                call_id = payload.get("callId")
                if call_id:
                    await voice_call_service.end_session(call_id)
                await websocket.close()
                return

            await websocket.send_json({"type": "error", "message": f"Unsupported message type: {message_type}"})

    except WebSocketDisconnect:
        logger.info("Voice websocket disconnected", call_id=active_call_id)
    except Exception as exc:
        logger.exception("Voice websocket error", error=str(exc), call_id=active_call_id)
        try:
            await websocket.send_json({"type": "error", "message": "Voice call failed unexpectedly."})
        except Exception:
            pass
    finally:
        if active_call_id:
            await voice_call_service.end_session(active_call_id)
