import structlog

logger = structlog.get_logger(__name__)

# Placeholder tools

def checkDoctorAvailability(specialty: str) -> str:
    """Check doctor availability for a given medical specialty."""
    logger.info(f"Checking availability for {specialty}")
    return f"Doctors for {specialty} are available this week."

def bookAppointment(patient_name: str, specialty: str, preferred_time: str) -> str:
    """Book an appointment for a patient."""
    logger.info(f"Booking appointment for {patient_name} with {specialty} at {preferred_time}")
    return f"Appointment booked for {patient_name} in {specialty} at {preferred_time}."

def getHospitalInfo(query: str) -> str:
    """Get general information about the hospital."""
    logger.info(f"Getting hospital info for query: {query}")
    return "The hospital is open 24/7. Visiting hours are from 9 AM to 8 PM."

def detectEmergency(symptoms: str) -> str:
    """Detect if the patient symptoms indicate an emergency."""
    logger.warning(f"Evaluating emergency for symptoms: {symptoms}")
    symptoms_lower = symptoms.lower()
    if any(keyword in symptoms_lower for keyword in ["chest pain", "breathing", "bleeding", "unconscious"]):
        return "EMERGENCY_DETECTED: Please call emergency services immediately or go to the nearest emergency room."
    return "No immediate emergency detected, but please consult a doctor."

def storeCallTranscript(transcript: str) -> str:
    """Store the call transcript for record keeping."""
    logger.info(f"Storing transcript of length {len(transcript)}")
    return "Transcript stored successfully."

tools = [
    checkDoctorAvailability,
    bookAppointment,
    getHospitalInfo,
    detectEmergency,
    storeCallTranscript
]

# We use google_adk to define the agent
try:
    from google_adk import Agent
    
    hospital_receptionist_agent = Agent(
        name="hospital_receptionist_agent",
        model="gemini-1.5-flash",
        instructions="You are an AI hospital receptionist helping patients with appointments, hospital information, and medical concerns.",
        tools=tools,
    )
except ImportError:
    logger.error("google-adk is not installed. Please install it using `pip install google-adk`.")
    hospital_receptionist_agent = None
