"""
Appointment management routes.
"""
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Appointment

from ..auth import UserInfo, require_role
from ..services.appointment_service import book_appointment, check_doctor_availability

router = APIRouter(prefix="/appointments", tags=["Appointments"])
logger = structlog.get_logger()

STAFF_APPOINTMENT_ROLES = ["admin", "doctor", "receptionist"]


class BookAppointmentRequest(BaseModel):
    patient_name: str
    patient_phone: str
    doctor_name: str
    department: str = "General Medicine"
    appointment_slot: str
    notes: str = ""
    call_id: Optional[str] = None


class AvailabilityRequest(BaseModel):
    doctor_name: Optional[str] = None
    department: Optional[str] = None
    preferred_date: Optional[str] = None


class RescheduleRequest(BaseModel):
    new_slot: str
    notes: Optional[str] = None


@router.get("/")
async def list_appointments(
    limit: int = 50,
    patient_phone: Optional[str] = None,
    doctor_name: Optional[str] = None,
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(require_role(STAFF_APPOINTMENT_ROLES)),
):
    """View or search appointments for staff users."""
    query = select(Appointment).order_by(Appointment.created_at.desc()).limit(limit)

    if patient_phone:
        query = query.where(Appointment.patient_phone.ilike(f"%{patient_phone}%"))
    if doctor_name:
        query = query.where(Appointment.doctor_name.ilike(f"%{doctor_name}%"))
    if department:
        query = query.where(Appointment.department.ilike(f"%{department}%"))

    result = await db.execute(query)
    appointments = [_serialize_appointment(appointment) for appointment in result.scalars().all()]
    return {"appointments": appointments, "count": len(appointments)}


@router.post("/")
async def create_appointment(
    req: BookAppointmentRequest,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(require_role(STAFF_APPOINTMENT_ROLES)),
):
    """Book an appointment directly for staff workflows."""
    result = await book_appointment(
        patient_name=req.patient_name,
        doctor_name=req.doctor_name,
        appointment_slot=req.appointment_slot,
        patient_phone=req.patient_phone,
        department=req.department,
        notes=req.notes,
        call_id=req.call_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Booking failed"))
    return result


@router.post("/check-availability")
async def check_availability(
    req: AvailabilityRequest,
    user: UserInfo = Depends(require_role(STAFF_APPOINTMENT_ROLES)),
):
    """Check doctor availability for staff workflows."""
    return await check_doctor_availability(
        doctor_name=req.doctor_name,
        department=req.department,
        preferred_date=req.preferred_date,
    )


@router.get("/by-phone/{phone_number}")
async def get_appointments_by_phone(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Public patient lookup for appointment details by phone number."""
    result = await db.execute(
        select(Appointment)
        .where(Appointment.patient_phone == phone_number)
        .order_by(Appointment.created_at.desc())
    )
    appointments = result.scalars().all()
    return {
        "appointments": [_serialize_appointment(appointment) for appointment in appointments],
        "count": len(appointments),
    }


@router.get("/by-booking/{appointment_id}")
async def get_appointment_by_booking_id(appointment_id: str, db: AsyncSession = Depends(get_db)):
    """Public patient lookup for appointment details by booking ID."""
    return await _get_single_appointment(appointment_id, db)


@router.get("/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(require_role(STAFF_APPOINTMENT_ROLES)),
):
    """Get a single appointment by ID for authenticated staff."""
    return await _get_single_appointment(appointment_id, db)


@router.patch("/{appointment_id}")
async def reschedule_appointment(
    appointment_id: str,
    req: RescheduleRequest,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(require_role(STAFF_APPOINTMENT_ROLES)),
):
    """Reschedule an existing appointment to a new time slot."""
    import uuid
    from datetime import datetime

    result = await db.execute(
        select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    try:
        new_slot = datetime.fromisoformat(req.new_slot)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    appointment.appointment_slot = new_slot
    if req.notes:
        appointment.notes = (appointment.notes or "") + f"\nRescheduled: {req.notes}"
    await db.flush()

    return {
        "id": str(appointment.id),
        "new_slot": new_slot.isoformat(),
        "message": f"Appointment rescheduled to {new_slot.strftime('%A, %B %d at %I:%M %p')}",
    }


@router.delete("/{appointment_id}")
async def cancel_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(require_role(STAFF_APPOINTMENT_ROLES)),
):
    """Cancel an existing appointment."""
    import uuid

    result = await db.execute(
        select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    await db.delete(appointment)
    await db.flush()

    return {
        "id": appointment_id,
        "message": "Appointment cancelled successfully",
    }


async def _get_single_appointment(appointment_id: str, db: AsyncSession) -> dict:
    import uuid

    result = await db.execute(
        select(Appointment).where(Appointment.id == uuid.UUID(appointment_id))
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _serialize_appointment(appointment)


def _serialize_appointment(appointment: Appointment) -> dict:
    return {
        "id": str(appointment.id),
        "patient_name": appointment.patient_name,
        "patient_phone": appointment.patient_phone,
        "doctor_name": appointment.doctor_name,
        "department": appointment.department,
        "appointment_slot": appointment.appointment_slot.isoformat() if appointment.appointment_slot else None,
        "confirmed": appointment.confirmed,
        "notes": appointment.notes,
        "created_at": appointment.created_at.isoformat() if appointment.created_at else None,
    }
