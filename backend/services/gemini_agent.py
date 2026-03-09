"""
Gemini AI Agent — Core intelligence of the Hospital AI Call Agent.

Integrates with:
- Google Gemini 2.0 Flash for conversational responses
- Function calling for backend integrations
- Session management for multi-turn conversations
"""
import json
import uuid
import structlog
from datetime import datetime
from typing import Optional, AsyncIterator
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

from backend.config import settings

logger = structlog.get_logger()

# ── System prompt for the hospital receptionist AI
SYSTEM_PROMPT = """
You are an intelligent AI receptionist for {hospital_name}. Your role is to:

1. Greet callers warmly and professionally
2. Understand patient needs accurately
3. Help with appointment bookings, doctor availability, and hospital information
4. Detect health emergencies and escalate immediately
5. Respond in the caller's language (English, Hindi, or Tamil)
6. Collect required information (name, concern, preferred time) naturally

Guidelines:
- Always be empathetic, calm, and professional
- Confirm all details before booking appointments
- For emergencies (chest pain, difficulty breathing, accidents), immediately trigger escalation
- Keep responses concise — this is a phone call, not a chat
- If unsure, escalate to a human receptionist rather than guessing

Hospital Information:
- Name: {hospital_name}
- Hours: Mon-Sat 8:00 AM - 8:00 PM, Emergency 24/7
- Departments: Cardiology, Orthopedics, Pediatrics, General Medicine, Neurology, Emergency
- Emergency line: {hospital_phone}

Begin every call with: "Hello! Thank you for calling {hospital_name}. I'm your AI assistant. How may I help you today?"
""".strip()

# ── Gemini Function declarations for tool use
HOSPITAL_TOOLS = [
    Tool(function_declarations=[
        FunctionDeclaration(
            name="checkDoctorAvailability",
            description="Check available appointment slots for a specific doctor or department",
            parameters={
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "Doctor's name (optional)"},
                    "department": {"type": "string", "description": "Medical department"},
                    "preferred_date": {"type": "string", "description": "Preferred date in YYYY-MM-DD format"},
                },
                "required": []
            }
        ),
        FunctionDeclaration(
            name="bookAppointment",
            description="Book an appointment for a patient with a doctor",
            parameters={
                "type": "object",
                "properties": {
                    "patient_name": {"type": "string", "description": "Patient's full name"},
                    "patient_phone": {"type": "string", "description": "Patient's phone number"},
                    "doctor_name": {"type": "string", "description": "Doctor's name"},
                    "department": {"type": "string", "description": "Medical department"},
                    "appointment_slot": {"type": "string", "description": "ISO 8601 datetime for appointment"},
                    "notes": {"type": "string", "description": "Additional notes or symptoms"}
                },
                "required": ["patient_name", "doctor_name", "appointment_slot"]
            }
        ),
        FunctionDeclaration(
            name="getHospitalInfo",
            description="Get information about hospital departments, timings, or services",
            parameters={
                "type": "object",
                "properties": {
                    "query_type": {
                        "type": "string",
                        "enum": ["departments", "timings", "emergency", "location", "general"],
                        "description": "Type of information requested"
                    }
                },
                "required": ["query_type"]
            }
        ),
        FunctionDeclaration(
            name="detectEmergency",
            description="Assess if the caller's described symptoms indicate a medical emergency",
            parameters={
                "type": "object",
                "properties": {
                    "symptoms": {"type": "string", "description": "Caller's described symptoms"},
                    "caller_phone": {"type": "string", "description": "Caller's phone number"}
                },
                "required": ["symptoms"]
            }
        ),
        FunctionDeclaration(
            name="escalateToHuman",
            description="Transfer the call to a human receptionist",
            parameters={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for escalation"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "emergency"],
                        "description": "Escalation priority level"
                    }
                },
                "required": ["reason", "priority"]
            }
        )
    ])
]


class ConversationSession:
    """Manages state for a single call conversation."""

    def __init__(self, call_id: str, caller_phone: str):
        self.call_id = call_id
        self.caller_phone = caller_phone
        self.history: list[dict] = []
        self.patient_name: Optional[str] = None
        self.detected_intent: Optional[str] = None
        self.is_emergency: bool = False
        self.language: str = "en-US"
        self.turn_count: int = 0
        self.pending_appointment: Optional[dict] = None
        self.started_at = datetime.utcnow()


class GeminiAgent:
    """
    Hospital AI Agent powered by Google Gemini.
    Handles multi-turn conversations with function calling.
    """

    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            tools=HOSPITAL_TOOLS,
            system_instruction=SYSTEM_PROMPT.format(
                hospital_name=settings.HOSPITAL_NAME,
                hospital_phone=settings.HOSPITAL_PHONE
            )
        )
        self._sessions: dict[str, ConversationSession] = {}
        logger.info("GeminiAgent initialized", model=settings.GEMINI_MODEL)

    def create_session(self, caller_phone: str) -> ConversationSession:
        """Create a new conversation session for an incoming call."""
        call_id = str(uuid.uuid4())
        session = ConversationSession(call_id=call_id, caller_phone=caller_phone)
        self._sessions[call_id] = session
        logger.info("Session created", call_id=call_id, caller=caller_phone)
        return session

    def get_session(self, call_id: str) -> Optional[ConversationSession]:
        """Retrieve an existing session by call ID."""
        return self._sessions.get(call_id)

    def end_session(self, call_id: str) -> Optional[ConversationSession]:
        """End and remove a session, returning it for persistence."""
        return self._sessions.pop(call_id, None)

    async def get_greeting(self, session: ConversationSession) -> str:
        """Generate the initial greeting for a new call."""
        greeting = (
            f"Hello! Thank you for calling {settings.HOSPITAL_NAME}. "
            "I'm your AI assistant. How may I help you today?"
        )
        session.history.append({"role": "model", "parts": [greeting]})
        return greeting

    async def process_message(
        self,
        session: ConversationSession,
        user_message: str,
        function_handler=None
    ) -> tuple[str, list[dict]]:
        """
        Process a user message and return (response_text, function_calls).

        Args:
            session: Active conversation session
            user_message: Transcribed user speech
            function_handler: Async callable to handle function calls

        Returns:
            Tuple of (text_response, list_of_function_calls_made)
        """
        session.history.append({"role": "user", "parts": [user_message]})
        session.turn_count += 1

        try:
            chat = self.model.start_chat(history=session.history[:-1])
            response = chat.send_message(user_message)

            function_calls_made = []
            final_text = ""

            # Process response parts — may include text and/or function calls
            for part in response.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    fn_name = fc.name
                    fn_args = dict(fc.args)

                    logger.info("Function call detected", function=fn_name, args=fn_args)
                    function_calls_made.append({"name": fn_name, "args": fn_args})

                    # Execute function handler if provided
                    if function_handler:
                        fn_result = await function_handler(fn_name, fn_args, session)

                        # Send function result back to Gemini
                        tool_response = chat.send_message(
                            genai.protos.Content(
                                parts=[genai.protos.Part(
                                    function_response=genai.protos.FunctionResponse(
                                        name=fn_name,
                                        response={"result": fn_result}
                                    )
                                )]
                            )
                        )
                        if tool_response.text:
                            final_text += tool_response.text

            # Update session history with model response
            if final_text:
                session.history.append({"role": "model", "parts": [final_text]})

            return final_text or "I'm sorry, I didn't quite get that. Could you please repeat?", function_calls_made

        except Exception as e:
            logger.error("Gemini processing error", error=str(e), call_id=session.call_id)
            fallback = "I'm experiencing a technical issue. Please hold while I connect you to our staff."
            return fallback, []

    async def analyze_transcript(self, transcript: str) -> dict:
        """
        Post-call analysis: extract intent, sentiment, risk, and summary.
        Returns structured JSON analysis.
        """
        analysis_prompt = f"""
Analyze this hospital call transcript and return ONLY a valid JSON object with these fields:
{{
  "intent": "appointment_booking|doctor_availability|emergency|general_inquiry|unknown",
  "sentiment": "positive|neutral|negative|distressed",
  "emergency_risk": "low|medium|high",
  "summary": "2-3 sentence summary of the call",
  "key_topics": ["list", "of", "topics"],
  "follow_up_required": true/false
}}

Transcript:
{transcript}
"""
        try:
            analysis_model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            response = analysis_model.generate_content(
                analysis_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            logger.error("Transcript analysis failed", error=str(e))
            return {
                "intent": "unknown",
                "sentiment": "neutral",
                "emergency_risk": "low",
                "summary": "Analysis unavailable",
                "key_topics": [],
                "follow_up_required": False
            }


# Singleton instance
gemini_agent = GeminiAgent()
