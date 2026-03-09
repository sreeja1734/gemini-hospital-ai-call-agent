# Gemini Hospital AI Call Agent — Architecture

## Component Flow Diagram

```mermaid
sequenceDiagram
    participant Caller
    participant Exotel as Exotel (Phone Carrier)
    
    box Backend System
        participant API as FastAPI Server
        participant STT as Google STT (Speech-to-Text)
        participant AI as Gemini Live API
        participant TTS as Google TTS (Text-to-Speech)
    end
    
    box Data & Storage
        participant Functions as Function Tools
        participant DB as PostgreSQL DB
        participant Admin as Next.js Dashboard
    end

    %% Call Initiation
    Caller->>Exotel: Dials Hospital Number
    Exotel->>API: HTTP POST /incoming-call (Webhook)
    API-->>Exotel: Exotel XML (Connect WebSocket Stream)
    
    %% Streaming Audio Loop
    rect rgba(20, 184, 166, 0.1)
        note over Caller, TTS: Real-Time Birectional Audio Stream (8kHz MULAW)
        Exotel->>API: WSS /ws/call (Incoming Audio Bytes)
        API->>STT: Stream Audio
        STT-->>API: Transcribed Text + Language Conf
        
        API->>AI: Send Text + Context History
        
        %% Function Calling (if needed)
        opt AI needs data or action
            AI->>Functions: Call tool (bookAppointment/detectEmergency)
            Functions->>DB: Read/Write Data
            DB-->>Functions: Result Status
            Functions-->>AI: Return Tool Response
        end
        
        AI-->>API: Generate Text Response
        API->>TTS: Transliterate Text to Speech (SSML)
        TTS-->>API: Base64 Audio Bytes
        API-->>Exotel: WSS (Outgoing Audio Bytes)
        Exotel-->>Caller: Plays Audio
    end
    
    %% Post Call Analysis
    Caller->>Exotel: Hangs Up
    Exotel->>API: HTTP POST /end-call
    API->>DB: Save Full Conversation Transcript
    
    API->>AI: POST /analyze-transcript (Gemini 1.5 Flash)
    AI-->>API: JSON {intent, risk, summary, sentiment}
    API->>DB: Update Transcript Record
    
    %% Admin View
    Admin->>API: GET /get-dashboard-data
    API->>DB: Query Aggregated Stats
    DB-->>API: Return Metrics
    API-->>Admin: Display Charts & Emergency Alerts
```

## System Components

1. **Voice Gateway (Exotel)**: Handles the physical SIP/telephony connection and streams audio over WebSockets to the backend.
2. **Speech Engine (Google Cloud)**: 
   - **STT v2**: Optimized for telephony, supports en-US, hi-IN, ta-IN simultaneously.
   - **TTS**: Neural2 voices using SSML for warm, natural prosody.
3. **Core Intelligence (Gemini 2.0 Flash)**: Acts as the reasoning engine and conversational agent, leveraging function calling to interact with hospital systems.
4. **Analysis Engine (Gemini 1.5 Flash)**: Processes completed transcripts to extract structured JSON insights for the admin dashboard.
5. **Database (PostgreSQL)**: Stores patient profiles, call logs, transcripts, and doctor schedules securely using SQLAlchemy ORM.
6. **Admin Dashboard (Next.js)**: A real-time monitoring interface for hospital staff to manage appointments, track AI escalation metrics, and view emergency flags.
