"""
Speech-to-Text helper for browser-recorded WebM/Opus audio.
"""
from __future__ import annotations

import asyncio

import structlog
from google.cloud import speech_v1 as speech

from backend.config import settings

logger = structlog.get_logger(__name__)


class BrowserSpeechToTextService:
    def __init__(self) -> None:
        self.client = speech.SpeechClient()
        logger.info("BrowserSpeechToTextService initialized")

    def _build_config(self, language_code: str) -> speech.RecognitionConfig:
        return speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code=language_code,
            alternative_language_codes=[
                candidate for candidate in ["en-US", "hi-IN", "ta-IN"] if candidate != language_code
            ],
            enable_automatic_punctuation=True,
            model="latest_short",
        )

    async def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        language_code: str = "en-US",
    ) -> tuple[str, float, str]:
        try:
            config = self._build_config(language_code)
            audio = speech.RecognitionAudio(content=audio_bytes)
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.recognize(config=config, audio=audio),
            )

            if not response.results:
                return "", 0.0, language_code

            result = response.results[0]
            alternative = result.alternatives[0]
            detected_language = getattr(result, "language_code", language_code)
            return alternative.transcript.strip(), alternative.confidence, detected_language
        except Exception as exc:
            logger.error("Browser STT transcription failed", error=str(exc))
            return "", 0.0, language_code


class MockBrowserSpeechToTextService:
    def __init__(self) -> None:
        self._responses = [
            "I need to book an appointment for tomorrow morning.",
            "Can you tell me the cardiology department timings?",
            "I have chest pain and need urgent help.",
        ]
        self._index = 0

    async def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        language_code: str = "en-US",
    ) -> tuple[str, float, str]:
        response = self._responses[self._index % len(self._responses)]
        self._index += 1
        logger.info("Mock browser STT transcript generated", transcript=response)
        return response, 0.95, language_code


def get_browser_stt_service():
    if settings.GOOGLE_CLOUD_PROJECT:
        try:
            return BrowserSpeechToTextService()
        except Exception as exc:
            logger.warning("Falling back to mock browser STT", error=str(exc))
    return MockBrowserSpeechToTextService()


browser_stt_service = get_browser_stt_service()
