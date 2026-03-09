# 🏥 Gemini Hospital AI Call Agent

A production-ready AI voice agent designed to automatically answer hospital phone calls, understand patient requests, book appointments, detect medical emergencies, and store comprehensive call analytics.

Built for a 48-hour hackathon, this system leverages Google's **Gemini Live API** and Google Cloud AI services for real-time, multilingual, human-like voice conversations.

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
- **Voice Gateway**: Exotel WebSockets for streaming bidirectional audio
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
- Exotel Account (for actual phone numbers, optional for local testing)

### 2. Environment Variables
Copy `.env.example` to `.env` in the root folder and add your credentials:
```bash
cp .env.example .env
```
Fill in your `GOOGLE_API_KEY` and `GOOGLE_CLOUD_PROJECT`.

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

If you don't have Exotel set up, you can simulate a conversation via the REST API:

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

---

## 📜 Hackathon Judging Criteria

- **Innovation**: Uses Gemini Live API + multi-turn conversational function calling.
- **Completeness**: A fully functional End-to-End system (DB + Backend + Frontend).
- **Practicality**: Solves a real-world high-value problem (Hospital triage & scheduling).
- **Scalability**: Stateless backend design, containerized, and deployment-ready for Cloud Run.
