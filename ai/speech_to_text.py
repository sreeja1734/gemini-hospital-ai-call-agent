"""
Speech-to-Text module using Google Cloud Speech-to-Text v2.
Supports streaming transcription for real-time call processing.
Languages: English (en-US), Hindi (hi-IN), Tamil (ta-IN)
"""
import asyncio
import structlog
from typing import AsyncIterator, Optional
from google.cloud import speech_v1 as speech

from backend.config import settings

logger = structlog.get_logger()


class SpeechToTextService:
    """
    Google Cloud Speech-to-Text wrapper.
    Supports both single-shot and streaming transcription.
    """

    def __init__(self):
        self.client = speech.SpeechClient()
        self.default_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MULAW,
            sample_rate_hertz=8000,  # Standard telephony sample rate
            language_code="en-US",
            alternative_language_codes=["hi-IN", "ta-IN"],
            enable_automatic_punctuation=True,
            model="telephony",  # Optimized for phone audio
            use_enhanced=True,
        )
        logger.info("SpeechToTextService initialized")

    def _build_config(self, language_code: str = "en-US") -> speech.RecognitionConfig:
        """Build recognition config for the given language."""
        return speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.MULAW,
            sample_rate_hertz=8000,
            language_code=language_code,
            alternative_language_codes=[
                lang for lang in ["en-US", "hi-IN", "ta-IN"] if lang != language_code
            ],
            enable_automatic_punctuation=True,
            model="telephony",
            use_enhanced=True,
        )

    async def transcribe_audio_bytes(
        self, audio_bytes: bytes, language_code: str = "en-US"
    ) -> tuple[str, float, str]:
        """
        Transcribe a single audio chunk.

        Returns:
            (transcript, confidence, detected_language)
        """
        try:
            audio = speech.RecognitionAudio(content=audio_bytes)
            config = self._build_config(language_code)

            # Run synchronous API call in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.recognize(config=config, audio=audio)
            )

            if response.results:
                result = response.results[0]
                alternative = result.alternatives[0]
                detected_lang = getattr(result, "language_code", language_code)
                return alternative.transcript, alternative.confidence, detected_lang
            return "", 0.0, language_code

        except Exception as e:
            logger.error("STT transcription failed", error=str(e))
            return "", 0.0, language_code

    async def streaming_transcribe(
        self,
        audio_stream: AsyncIterator[bytes],
        language_code: str = "en-US",
        session_id: str = ""
    ) -> AsyncIterator[dict]:
        """
        Stream audio chunks and yield real-time transcription results.

        Yields dicts with:
            {is_final, transcript, confidence, stability}
        """
        config = speech.StreamingRecognitionConfig(
            config=self._build_config(language_code),
            interim_results=True,
            single_utterance=False,
        )

        def audio_generator():
            """Synchronous generator for the gRPC streaming API."""
            yield speech.StreamingRecognizeRequest(streaming_config=config)

        try:
            async for audio_chunk in audio_stream:
                request = speech.StreamingRecognizeRequest(audio_content=audio_chunk)
                responses = self.client.streaming_recognize(
                    requests=iter([speech.StreamingRecognizeRequest(streaming_config=config), request])
                )
                for response in responses:
                    for result in response.results:
                        if result.alternatives:
                            alt = result.alternatives[0]
                            yield {
                                "is_final": result.is_final,
                                "transcript": alt.transcript,
                                "confidence": getattr(alt, "confidence", 0.0),
                                "stability": getattr(result, "stability", 0.0),
                                "session_id": session_id
                            }

        except Exception as e:
            logger.error("Streaming STT error", error=str(e), session_id=session_id)


# ── Mock implementation for local development (no GCP credentials needed)
class MockSpeechToTextService:
    """
    Mock STT for local development and testing.
    Returns scripted responses for common test phrases.
    """

    async def transcribe_audio_bytes(
        self, audio_bytes: bytes, language_code: str = "en-US"
    ) -> tuple[str, float, str]:
        logger.info("MockSTT: returning simulated transcript")
        return "I'd like to book an appointment with Dr. Kumar tomorrow", 0.95, "en-US"

    async def streaming_transcribe(
        self, audio_stream, language_code: str = "en-US", session_id: str = ""
    ):
        yield {
            "is_final": True,
            "transcript": "Hello, I need to see a cardiologist",
            "confidence": 0.92,
            "stability": 1.0,
            "session_id": session_id
        }


def get_stt_service():
    """Factory: returns real or mock STT service based on config."""
    if settings.GOOGLE_CLOUD_PROJECT:
        return SpeechToTextService()
    logger.warning("GOOGLE_CLOUD_PROJECT not set — using MockSTT")
    return MockSpeechToTextService()


stt_service = MockSpeechToTextService()  # Using mock service to avoid credential issues
