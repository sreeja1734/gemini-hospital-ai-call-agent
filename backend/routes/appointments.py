"""
Appointment management routes.
"""
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.connection import get_db
from database.models import Appointment
from ..services.appointment_service import (
    check_doctor_availability, book_appointment, get_all_appointments
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])
logger = structlog.get_logger()


class BookAppointmentRequest(BaseModel):
    patient_name: str
    patient_phone: str
    doctor_name: str
    department: str = "General Medicine"
    appointment_slot: str   # ISO 8601 datetime string
    notes: str = ""
    call_id: Optional[str] = None


class AvailabilityRequest(BaseModel):
    doctor_name: Optional[str] = None
    department: Optional[str] = None
    preferred_date: Optional[str] = None   # YYYY-MM-DD


@router.get("/")
async def list_appointments(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get all recent appointments for the dashboard."""
    appointments = await get_all_appointments(limit)
    return {"appointments": appointments, "count": len(appointments)}


@router.post("/")
async def create_appointment(
    req: BookAppointmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Book an appointment directly (without a call session)."""
    result = await book_appointment(
        patient_name=req.patient_name,
        doctor_name=req.doctor_name,
        appointment_slot=req.appointment_slot,
        patient_phone=req.patient_phone,
        department=req.department,
        notes=req.notes,
        call_id=req.call_id
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Booking failed"))
    return result


@router.post("/check-availability")
async def check_availability(req: AvailabilityRequest):
    """Check doctor availability for given parameters."""
    result = await check_doctor_availability(
        doctor_name=req.doctor_name,
        department=req.department,
        preferred_date=req.preferred_date
    )
    return result


@router.get("/{appointment_id}")
async def get_appointment(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single appointment by ID."""
    import uuid
    result = await db.execute(
        select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {
        "id": str(appt.id),
        "patient_name": appt.patient_name,
        "patient_phone": appt.patient_phone,
        "doctor_name": appt.doctor_name,
        "department": appt.department,
        "appointment_slot": appt.appointment_slot.isoformat() if appt.appointment_slot else None,
        "confirmed": appt.confirmed,
        "notes": appt.notes,
        "created_at": appt.created_at.isoformat() if appt.created_at else None
    }
