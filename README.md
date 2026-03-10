# 🏥 Gemini Hospital AI Call Agent

A production-ready AI voice agent designed to automatically answer hospital phone calls, understand patient requests, book appointments, detect medical emergencies, and store comprehensive call analytics.

Built for a 48-hour hackathon, this system leverages Google's **Gemini APIs** and Google Cloud AI services for real-time, multilingual, human-like voice conversations, with **Vapi AI** handling phone calls, speech recognition, and text-to-speech.

![Hospital AI Banner](https://placehold.co/1200x400/134e4a/ffffff?text=Gemini+Hospital+AI+Call+Agent)

## 🌟 Key Features

1. **Real-time Conversational AI**: Fluid, interruptible voice conversations powered by Gemini 2.0 Flash.
2. **Multilingual Support**: Automatically detects and responds in English, Hindi, and Tamil.
3. **Smart Appointment Booking**: Checks doctor availability and books time slots autonomously using Gemini Function Calling.
4. **Emergency Detection**: Evaluates caller symptoms using keyword matching + Gemini AI to flag high-risk calls (e.g., chest pain) for immediate human escalation.
5. **Post-Call Analysis**: Automatically analyzes full transcripts using Gemini 1.5 Flash to extract intent, sentiment, and summary JSON.
6. **Next.js Admin Dashboard**: Real-time web UI for hospital administrators to view call volume, manage appointments, and track emergency alerts.

---

## 🏗️ Architecture Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Voice Gateway**: Vapi AI (phone numbers, STT, TTS, dynamic call transfers)
- **Database**: PostgreSQL with SQLAlchemy ORM + asyncpg

### Google AI Services
- **Conversational Agent**: Gemini 2.0 Flash Live API
- **Transcript Analysis**: Gemini 1.5 Flash
- **Speech Processing**: Google Cloud Speech-to-Text v2 & Text-to-Speech

### Frontend Dashboard
- **Framework**: Next.js 14 (App Router)
- **Styling**: TailwindCSS
- **Charts**: Recharts & Lucide Icons

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL container (or local instance)
- Google Cloud Project with API keys enabled
- Vapi AI account (for phone numbers and call routing)

### 2. Environment Variables
Copy `.env.example` to `.env` in the root folder and add your credentials:
```bash
cp .env.example .env
```
At minimum, set:
- `GOOGLE_API_KEY` / `GEMINI_API_KEY` – for Gemini models  
- `DATABASE_URL` – for PostgreSQL  
- `DOCTOR_PHONE_NUMBER` – Vapi transfer destination for talking to a doctor  
- `EMERGENCY_PHONE_NUMBER` – Vapi transfer destination for emergencies  
- `VAPI_API_KEY` – for authenticated calls to Vapi APIs (optional for Custom LLM)

### 3. Run with Docker Compose (Recommended)
You can launch the entire stack (PostgreSQL + FastAPI + Next.js) using Docker:
```bash
docker-compose up --build
```
- Admin Dashboard available at: `http://localhost:3000`
- FastAPI Backend available at: `http://localhost:8000/docs`

### 4. Run Locally (Manual)

**Start Database:**
```bash
docker run --name hospital_db -e POSTGRES_PASSWORD=password -e POSTGRES_DB=hospital_ai -p 5432:5432 -d postgres:15-alpine
```

**Start Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Start Frontend:**
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

---

## ☁️ Google Cloud Deployment Guide

The project is structured to deploy smoothly on Google Cloud Run.

### 1. Deploy the Backend
```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"

# Build and push the container
gcloud builds submit --tag gcr.io/$PROJECT_ID/hospital-ai-backend -f deployment/Dockerfile.backend .

# Deploy to Cloud Run
gcloud run deploy hospital-ai-backend \
  --image gcr.io/$PROJECT_ID/hospital-ai-backend \
  --set-env-vars="GOOGLE_API_KEY=your_key,DATABASE_URL=your_cloud_sql_url" \
  --region us-central1 \
  --allow-unauthenticated
```

### 2. Deploy the Frontend
```bash
# Build and push the frontend container
gcloud builds submit --tag gcr.io/$PROJECT_ID/hospital-ai-frontend -f deployment/Dockerfile.frontend .

# Deploy to Cloud Run
gcloud run deploy hospital-ai-frontend \
  --image gcr.io/$PROJECT_ID/hospital-ai-frontend \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 📞 Testing the Call Flow Locally

You can test both the **REST conversation API** and the **Vapi phone flow**.

### A. Using the REST Conversation API (no phone required)

**1. Start a Conversation:**
```bash
curl -X POST http://localhost:8000/start-conversation \
  -H "Content-Type: application/json" \
  -d '{"caller_phone": "+1234567890", "language": "en-US"}'
```
*(Save the `call_id` returned)*

**2. Send a user speech command:**
```bash
curl -X POST http://localhost:8000/process-user-speech \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "YOUR_CALL_ID", 
    "text_input": "I have severe chest pain and difficulty breathing.",
    "language": "en-US"
  }'
```
*(The AI will detect an emergency, flag the risk level to HIGH, and return an escalation response.)*

**3. End the Call:**
```bash
curl -X POST http://localhost:8000/end-call \
  -H "Content-Type: application/json" \
  -d '{"call_id": "YOUR_CALL_ID"}'
```
*(This triggers Gemini 1.5 Flash to automatically analyze the transcript and tag it for the dashboard.)*

### B. Testing the Vapi Phone Integration

1. **Run the backend locally**:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **Expose it via ngrok (or similar)**:
   ```bash
   ngrok http 8000
   ```
   Note the HTTPS URL, e.g. `https://abc123.ngrok.io`.
3. **Configure a Custom LLM in Vapi**:
   - Base URL: `https://abc123.ngrok.io/vapi`
   - Path: `/chat/completions`
4. **Create a Vapi assistant**:
   - Use the Custom LLM from step 3 as the model.
   - First message: `Hello, thank you for calling our healthcare center. How can I help you today?`
   - Add a `transfer_to_number` tool so the model can trigger call transfers.
5. **Attach a phone number in Vapi** to this assistant and call it from your phone.

On each turn, Vapi will:
- Stream audio from the caller  
- Transcribe it and send the transcript to `/vapi/chat/completions`  
- Use the Gemini-powered receptionist logic to decide whether to answer, book an appointment, or transfer the call to `DOCTOR_PHONE_NUMBER` / `EMERGENCY_PHONE_NUMBER`.

---

## 📜 Hackathon Judging Criteria

- **Innovation**: Uses Gemini APIs + multi-turn conversational function calling.
- **Completeness**: A fully functional End-to-End system (DB + Backend + Frontend).
- **Practicality**: Solves a real-world high-value problem (Hospital triage & scheduling).
- **Scalability**: Stateless backend design, containerized, and deployment-ready for Cloud Run.
