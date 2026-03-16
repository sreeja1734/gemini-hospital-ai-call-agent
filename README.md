# AI Hospital Call Agent - Voice AI Receptionist for Healthcare

## Project Overview
AI Hospital Call Agent is a FastAPI-based backend that simulates an AI hospital receptionist for voice-driven patient interactions.

The system is designed to:
- handle patient calls
- detect medical emergencies
- book appointments
- store call transcripts
- provide a dashboard for hospital staff

The backend is built with FastAPI and integrates with Google Gemini for LLM capabilities through the hospital AI agent layer. The current implementation is structured around a conversational AI workflow for patient interactions and a separate authenticated dashboard workflow for hospital staff.

## Architecture Overview
High-level flow:

`Patient Call`
-> `Speech/Text Processing`
-> `Gemini AI Agent`
-> `Intent Detection (appointment / emergency / general inquiry)`
-> `Emergency Detection Service`
-> `Database Storage`
-> `Staff Dashboard APIs`

### System Separation
- Public patient interaction endpoints are used by callers and do not require login.
- Staff dashboard endpoints are protected with JWT authentication and role-based access control.

### Request Boundaries
- Patients interact only with the AI call APIs.
- Receptionists, doctors, and admins authenticate to view operational data.
- Staff permissions are enforced at the API layer using JWT role checks.

## Features Implemented
### AI Call Processing
- Process patient speech or text input
- Identify user intent
- Generate AI responses

### Emergency Detection
- Detect keywords such as chest pain, heart attack, stroke, and breathing difficulty
- Assign risk levels such as low, medium, and high
- Flag emergencies for staff review

### Appointment Management
- Check doctor availability
- Create appointment bookings
- Reschedule appointments
- Cancel appointments

### Call Transcripts
- Store conversation logs between patient and AI
- Allow staff to review call history

### Dashboard APIs
- View call statistics
- View emergency alerts
- View transcripts
- Monitor AI performance metrics

### JWT Authentication for Staff
- Role-based access control
- Supported roles:
  - Admin
  - Doctor
  - Receptionist

## API Endpoints
### Public (Patient) APIs
- `POST /start-conversation`
- `POST /process-user-speech`
- `POST /end-call`
- `GET /appointments/by-phone/{phone_number}`

Example:

```bash
curl -X POST http://127.0.0.1:8000/start-conversation \
  -H "Content-Type: application/json" \
  -d '{
    "caller_phone": "+1234567890",
    "language": "en-US"
  }'
```

### Staff (Authenticated) APIs
- `POST /auth/login`
- `GET /dashboard-data`
- `GET /emergency-alerts`
- `GET /calls/transcripts`
- `GET /appointments`

Example login:

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

### Appointment APIs
- `POST /appointments`
- `GET /appointments`
- `PATCH /appointments/{appointment_id}`
- `DELETE /appointments/{appointment_id}`

Example appointment lookup by phone:

```bash
curl http://127.0.0.1:8000/appointments/by-phone/+1234567890
```

## Authentication
Staff users authenticate using JWT access tokens.

Example development credentials:

- `admin / admin123`
- `doctor1 / doctor123`
- `reception1 / recep123`

JWT payload includes:

```json
{
  "sub": "username",
  "role": "admin|doctor|receptionist",
  "exp": "expiration timestamp"
}
```

Use the token in Swagger or API clients as:

```text
Authorization: Bearer <access_token>
```

## Running the Project
### 1. Clone the repository

```bash
git clone <your-repo-url>
cd gemini-hospital-ai-call-agent
```

### 2. Install dependencies

If you are installing backend dependencies from the backend folder:

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 3. Run the backend server

```bash
uvicorn backend.main:app --reload
```

If you see reload loops on Windows because `venv` is being watched, use:

```bash
uvicorn backend.main:app --reload --reload-dir backend --reload-dir ai --reload-dir database --reload-exclude "venv" --reload-exclude "__pycache__"
```

### 4. Open API documentation

```text
http://127.0.0.1:8000/docs
```

## Example Workflow
Patient says:

```text
I have severe chest pain
```

System flow:

`Speech`
-> `AI`
-> `Emergency Detection`
-> `Emergency Flagged`
-> `Stored`
-> `Visible in Staff Dashboard`

## Future Improvements
- real voice call integration with providers such as Twilio
- real hospital database integration
- AI triage prioritization
- real-time emergency notifications
- frontend dashboard UI enhancements

## Technologies Used
- Python
- FastAPI
- Google Gemini / Vertex AI
- SQLAlchemy
- JWT Authentication
- Uvicorn
- Swagger / OpenAPI
