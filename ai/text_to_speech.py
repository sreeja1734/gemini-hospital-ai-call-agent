"""
Text-to-Speech module using Google Cloud Text-to-Speech.
Produces natural, professional-sounding voice for hospital phone calls.
"""
import asyncio
import structlog
from typing import Optional
from google.cloud import texttospeech

from backend.config import settings

logger = structlog.get_logger()

# Voice configurations per language
VOICE_CONFIG = {
    "en-US": {
        "language_code": "en-US",
        "name": "en-US-Neural2-F",  # Warm, professional female voice
        "ssml_gender": texttospeech.SsmlVoiceGender.FEMALE
    },
    "hi-IN": {
        "language_code": "hi-IN",
        "name": "hi-IN-Neural2-A",
        "ssml_gender": texttospeech.SsmlVoiceGender.FEMALE
    },
    "ta-IN": {
        "language_code": "ta-IN",
        "name": "ta-IN-Neural2-A",
        "ssml_gender": texttospeech.SsmlVoiceGender.FEMALE
    }
}

# SSML templates for better prosody
SSML_TEMPLATE = """
<speak>
  <prosody rate="medium" pitch="+0st">
    {text}
  </prosody>
</speak>
"""


class TextToSpeechService:
    """
    Google Cloud TTS wrapper optimized for telephony audio delivery.
    Output: MULAW 8kHz (Twilio-compatible) or LINEAR16.
    """

    def __init__(self):
        self.client = texttospeech.TextToSpeechClient()
        logger.info("TextToSpeechService initialized")

    async def synthesize(
        self,
        text: str,
        language_code: str = "en-US",
        use_ssml: bool = True,
        audio_format: str = "mulaw"  # "mulaw" for Twilio, "mp3" for web
    ) -> bytes:
        """
        Convert text to speech audio bytes.

        Args:
            text: Text to synthesize
            language_code: Target language (en-US, hi-IN, ta-IN)
            use_ssml: Wrap text in SSML for better prosody
            audio_format: Output format ("mulaw", "mp3", "linear16")

        Returns:
            Audio bytes
        """
        voice_cfg = VOICE_CONFIG.get(language_code, VOICE_CONFIG["en-US"])

        # Build synthesis input
        if use_ssml:
            ssml_text = SSML_TEMPLATE.format(text=text.replace("&", "&amp;"))
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)
        else:
            synthesis_input = texttospeech.SynthesisInput(text=text)

        # Voice selection
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_cfg["language_code"],
            name=voice_cfg["name"],
            ssml_gender=voice_cfg["ssml_gender"]
        )

        # Audio config based on format
        format_map = {
            "mulaw": texttospeech.AudioEncoding.MULAW,
            "mp3": texttospeech.AudioEncoding.MP3,
            "linear16": texttospeech.AudioEncoding.LINEAR16,
        }
        audio_config = texttospeech.AudioConfig(
            audio_encoding=format_map.get(audio_format, texttospeech.AudioEncoding.MULAW),
            sample_rate_hertz=8000 if audio_format == "mulaw" else 24000,
            speaking_rate=0.95,  # Slightly slower for clarity
            pitch=0.0,
            volume_gain_db=2.0  # Slightly louder for phone output
        )

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
            )
            return response.audio_content

        except Exception as e:
            logger.error("TTS synthesis failed", error=str(e), language=language_code)
            raise


class MockTextToSpeechService:
    """Mock TTS for local development (returns empty bytes)."""

    async def synthesize(
        self, text: str, language_code: str = "en-US",
        use_ssml: bool = True, audio_format: str = "mulaw"
    ) -> bytes:
        logger.info("MockTTS: synthesizing", text=text[:50], language=language_code)
        return b""  # Empty audio for testing


def get_tts_service():
    """Factory: returns real or mock TTS service."""
    if settings.GOOGLE_CLOUD_PROJECT:
        return TextToSpeechService()
    logger.warning("GOOGLE_CLOUD_PROJECT not set — using MockTTS")
    return MockTextToSpeechService()


tts_service = MockTextToSpeechService()  # Using mock service to avoid credential issues
