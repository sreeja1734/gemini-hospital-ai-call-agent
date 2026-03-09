-- ============================================================
-- Gemini Hospital AI Call Agent — PostgreSQL Schema
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- --------------------------------------------------------
-- PATIENTS
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255),
    phone               VARCHAR(20) UNIQUE NOT NULL,
    email               VARCHAR(255),
    date_of_birth       VARCHAR(20),
    preferred_language  VARCHAR(10) DEFAULT 'en-US',
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone);

-- --------------------------------------------------------
-- CALLS
-- --------------------------------------------------------
CREATE TYPE call_status AS ENUM ('active', 'completed', 'escalated', 'missed');
CREATE TYPE risk_level   AS ENUM ('low', 'medium', 'high');
CREATE TYPE call_intent  AS ENUM (
    'appointment_booking', 'doctor_availability', 'hospital_timings',
    'department_info', 'emergency', 'general_inquiry', 'unknown'
);

CREATE TABLE IF NOT EXISTS calls (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id          UUID REFERENCES patients(id) ON DELETE SET NULL,
    twilio_call_sid     VARCHAR(100) UNIQUE,
    caller_phone        VARCHAR(20) NOT NULL,
    status              call_status DEFAULT 'active',
    intent              call_intent DEFAULT 'unknown',
    emergency_flag      BOOLEAN DEFAULT FALSE,
    risk_level          risk_level DEFAULT 'low',
    ai_handled          BOOLEAN DEFAULT TRUE,
    duration_seconds    INTEGER,
    language_detected   VARCHAR(10) DEFAULT 'en-US',
    started_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at            TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_calls_patient_id     ON calls(patient_id);
CREATE INDEX IF NOT EXISTS idx_calls_status         ON calls(status);
CREATE INDEX IF NOT EXISTS idx_calls_emergency_flag ON calls(emergency_flag);
CREATE INDEX IF NOT EXISTS idx_calls_started_at     ON calls(started_at DESC);

-- --------------------------------------------------------
-- APPOINTMENTS
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS appointments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id          UUID REFERENCES patients(id) ON DELETE SET NULL,
    call_id             UUID REFERENCES calls(id) ON DELETE SET NULL,
    patient_name        VARCHAR(255) NOT NULL,
    patient_phone       VARCHAR(20) NOT NULL,
    doctor_name         VARCHAR(255) NOT NULL,
    department          VARCHAR(100),
    appointment_slot    TIMESTAMP WITH TIME ZONE NOT NULL,
    confirmed           BOOLEAN DEFAULT FALSE,
    notes               TEXT,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_appointments_patient_id    ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor_name   ON appointments(doctor_name);
CREATE INDEX IF NOT EXISTS idx_appointments_slot          ON appointments(appointment_slot);

-- --------------------------------------------------------
-- TRANSCRIPTS
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS transcripts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    call_id             UUID UNIQUE NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    content             TEXT NOT NULL,
    analysis            JSONB,
    turn_count          INTEGER DEFAULT 0,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transcripts_call_id ON transcripts(call_id);

-- --------------------------------------------------------
-- DOCTOR SCHEDULES
-- --------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctor_schedules (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_name         VARCHAR(255) NOT NULL,
    department          VARCHAR(100) NOT NULL,
    specialization      VARCHAR(100),
    available_slot      TIMESTAMP WITH TIME ZONE NOT NULL,
    is_booked           BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_doctor_schedules_name      ON doctor_schedules(doctor_name);
CREATE INDEX IF NOT EXISTS idx_doctor_schedules_slot      ON doctor_schedules(available_slot);
CREATE INDEX IF NOT EXISTS idx_doctor_schedules_booked    ON doctor_schedules(is_booked);

-- --------------------------------------------------------
-- SEED DOCTOR SCHEDULES (Demo data)
-- --------------------------------------------------------
INSERT INTO doctor_schedules (doctor_name, department, specialization, available_slot) VALUES
    ('Dr. Priya Kumar',   'Cardiology',     'Cardiologist',      CURRENT_TIMESTAMP + INTERVAL '1 day 9 hours'),
    ('Dr. Priya Kumar',   'Cardiology',     'Cardiologist',      CURRENT_TIMESTAMP + INTERVAL '1 day 11 hours'),
    ('Dr. Priya Kumar',   'Cardiology',     'Cardiologist',      CURRENT_TIMESTAMP + INTERVAL '1 day 15 hours'),
    ('Dr. Rahul Sharma',  'Orthopedics',    'Orthopedic Surgeon',CURRENT_TIMESTAMP + INTERVAL '2 days 10 hours'),
    ('Dr. Rahul Sharma',  'Orthopedics',    'Orthopedic Surgeon',CURRENT_TIMESTAMP + INTERVAL '2 days 14 hours'),
    ('Dr. Ananya Iyer',   'Pediatrics',     'Pediatrician',      CURRENT_TIMESTAMP + INTERVAL '1 day 10 hours'),
    ('Dr. Ananya Iyer',   'Pediatrics',     'Pediatrician',      CURRENT_TIMESTAMP + INTERVAL '1 day 16 hours'),
    ('Dr. Vikram Singh',  'General Medicine','General Physician', CURRENT_TIMESTAMP + INTERVAL '3 hours'),
    ('Dr. Vikram Singh',  'General Medicine','General Physician', CURRENT_TIMESTAMP + INTERVAL '5 hours'),
    ('Dr. Meena Nair',    'Neurology',      'Neurologist',       CURRENT_TIMESTAMP + INTERVAL '3 days 9 hours')
ON CONFLICT DO NOTHING;
