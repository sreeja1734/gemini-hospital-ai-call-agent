"""
Database models using SQLAlchemy ORM.
Tables: patients, calls, appointments, transcripts
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, Text,
    DateTime, ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    pass


class CallStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    MISSED = "missed"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Intent(str, enum.Enum):
    APPOINTMENT_BOOKING = "appointment_booking"
    DOCTOR_AVAILABILITY = "doctor_availability"
    HOSPITAL_TIMINGS = "hospital_timings"
    DEPARTMENT_INFO = "department_info"
    EMERGENCY = "emergency"
    GENERAL_INQUIRY = "general_inquiry"
    UNKNOWN = "unknown"


class Patient(Base):
    """Patient records — identified by phone number."""
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    preferred_language = Column(String(10), default="en-US")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    calls = relationship("Call", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")


class Call(Base):
    """Call records — one per phone session."""
    __tablename__ = "calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True)
    twilio_call_sid = Column(String(100), unique=True, nullable=True, index=True)
    caller_phone = Column(String(20), nullable=False)
    status = Column(SAEnum(CallStatus), default=CallStatus.ACTIVE)
    intent = Column(SAEnum(Intent), default=Intent.UNKNOWN)
    emergency_flag = Column(Boolean, default=False)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.LOW)
    ai_handled = Column(Boolean, default=True)
    duration_seconds = Column(Integer, nullable=True)
    language_detected = Column(String(10), default="en-US")
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="calls")
    transcript = relationship("Transcript", back_populates="call", uselist=False, cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="call")


class Appointment(Base):
    """Appointment records created during or after calls."""
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), nullable=True)
    patient_name = Column(String(255), nullable=False)
    patient_phone = Column(String(20), nullable=False)
    doctor_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=True)
    appointment_slot = Column(DateTime, nullable=False)
    confirmed = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    call = relationship("Call", back_populates="appointments")


class Transcript(Base):
    """Full conversation transcript with AI analysis results."""
    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"), unique=True, nullable=False)
    content = Column(Text, nullable=False)  # Full conversation text
    analysis = Column(JSON, nullable=True)  # Gemini analysis result
    turn_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    call = relationship("Call", back_populates="transcript")


class DoctorSchedule(Base):
    """Doctor availability slots for appointment booking."""
    __tablename__ = "doctor_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    specialization = Column(String(100), nullable=True)
    available_slot = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
