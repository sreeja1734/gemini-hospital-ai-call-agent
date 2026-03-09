"""
Appointment Service — handles doctor availability checks and booking.
Integrates with the database and is called by Gemini function calling.
"""
import structlog
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Appointment, DoctorSchedule, Patient, Call
from database.connection import get_db_context

logger = structlog.get_logger()

# Fallback mock data for demo when DB has no schedules
DEMO_DOCTORS = [
    {"doctor_name": "Dr. Priya Kumar",  "department": "Cardiology",      "specialization": "Cardiologist"},
    {"doctor_name": "Dr. Rahul Sharma", "department": "Orthopedics",     "specialization": "Orthopedic Surgeon"},
    {"doctor_name": "Dr. Ananya Iyer",  "department": "Pediatrics",      "specialization": "Pediatrician"},
    {"doctor_name": "Dr. Vikram Singh", "department": "General Medicine", "specialization": "General Physician"},
    {"doctor_name": "Dr. Meena Nair",   "department": "Neurology",       "specialization": "Neurologist"},
]


async def check_doctor_availability(
    doctor_name: Optional[str] = None,
    department: Optional[str] = None,
    preferred_date: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> dict:
    """
    Check available doctor slots.
    Returns a structured dict with available slots for Gemini to format.
    """
    try:
        async with get_db_context() as session:
            query = select(DoctorSchedule).where(
                DoctorSchedule.is_booked == False,
                DoctorSchedule.available_slot >= datetime.utcnow()
            )
            if doctor_name:
                query = query.where(DoctorSchedule.doctor_name.ilike(f"%{doctor_name}%"))
            if department:
                query = query.where(DoctorSchedule.department.ilike(f"%{department}%"))
            if preferred_date:
                try:
                    date = datetime.strptime(preferred_date, "%Y-%m-%d")
                    query = query.where(
                        and_(
                            DoctorSchedule.available_slot >= date,
                            DoctorSchedule.available_slot < date + timedelta(days=1)
                        )
                    )
                except ValueError:
                    pass

            result = await session.execute(query.order_by(DoctorSchedule.available_slot).limit(5))
            schedules = result.scalars().all()

            if schedules:
                slots = [
                    {
                        "schedule_id": str(s.id),
                        "doctor_name": s.doctor_name,
                        "department": s.department,
                        "specialization": s.specialization,
                        "slot": s.available_slot.strftime("%A, %B %d at %I:%M %p"),
                        "slot_iso": s.available_slot.isoformat()
                    }
                    for s in schedules
                ]
                return {"available": True, "slots": slots, "count": len(slots)}
            else:
                # Return demo slots for hackathon
                return _generate_demo_slots(doctor_name, department)

    except Exception as e:
        logger.error("DB error checking availability", error=str(e))
        return _generate_demo_slots(doctor_name, department)


def _generate_demo_slots(doctor_name: Optional[str], department: Optional[str]) -> dict:
    """Generate demo availability slots when DB is empty."""
    now = datetime.utcnow()
    doctor = DEMO_DOCTORS[0]

    if doctor_name:
        matches = [d for d in DEMO_DOCTORS if doctor_name.lower() in d["doctor_name"].lower()]
        if matches:
            doctor = matches[0]
    elif department:
        matches = [d for d in DEMO_DOCTORS if department.lower() in d["department"].lower()]
        if matches:
            doctor = matches[0]

    slots = []
    for i, hour in enumerate([9, 11, 14, 16]):
        slot_time = (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
        slots.append({
            "schedule_id": f"demo-{i}",
            "doctor_name": doctor["doctor_name"],
            "department": doctor["department"],
            "specialization": doctor["specialization"],
            "slot": slot_time.strftime("%A, %B %d at %I:%M %p"),
            "slot_iso": slot_time.isoformat()
        })

    return {"available": True, "slots": slots, "count": len(slots), "demo": True}


async def book_appointment(
    patient_name: str,
    doctor_name: str,
    appointment_slot: str,
    patient_phone: str = "Unknown",
    department: str = "General Medicine",
    notes: str = "",
    call_id: Optional[str] = None,
) -> dict:
    """
    Create an appointment record in the database.
    Also marks the doctor schedule slot as booked.
    """
    try:
        # Parse the appointment slot
        slot_dt = datetime.fromisoformat(appointment_slot) if "T" in appointment_slot else \
                  datetime.strptime(appointment_slot, "%Y-%m-%d %H:%M")

        async with get_db_context() as session:
            # Find or create patient
            patient_result = await session.execute(
                select(Patient).where(Patient.phone == patient_phone)
            )
            patient = patient_result.scalar_one_or_none()
            if not patient:
                patient = Patient(name=patient_name, phone=patient_phone)
                session.add(patient)
                await session.flush()

            # Create appointment
            appointment = Appointment(
                patient_id=patient.id,
                call_id=call_id,
                patient_name=patient_name,
                patient_phone=patient_phone,
                doctor_name=doctor_name,
                department=department,
                appointment_slot=slot_dt,
                confirmed=True,
                notes=notes
            )
            session.add(appointment)

            # Mark schedule slot as booked
            await session.execute(
                update(DoctorSchedule)
                .where(
                    and_(
                        DoctorSchedule.doctor_name.ilike(f"%{doctor_name}%"),
                        DoctorSchedule.available_slot == slot_dt,
                        DoctorSchedule.is_booked == False
                    )
                )
                .values(is_booked=True)
            )
            await session.flush()

            logger.info(
                "Appointment booked",
                patient=patient_name,
                doctor=doctor_name,
                slot=slot_dt.isoformat()
            )

            return {
                "success": True,
                "appointment_id": str(appointment.id),
                "confirmation": (
                    f"Appointment confirmed! {patient_name} is booked with {doctor_name} "
                    f"on {slot_dt.strftime('%A, %B %d at %I:%M %p')}. "
                    "Please arrive 15 minutes early with a valid photo ID."
                ),
                "slot": slot_dt.strftime("%A, %B %d at %I:%M %p")
            }

    except Exception as e:
        logger.error("Failed to book appointment", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "confirmation": "I'm sorry, there was an issue booking the appointment. Please call back or visit the front desk."
        }


async def get_all_appointments(limit: int = 50) -> list[dict]:
    """Fetch recent appointments for the dashboard."""
    try:
        async with get_db_context() as session:
            result = await session.execute(
                select(Appointment).order_by(Appointment.created_at.desc()).limit(limit)
            )
            appointments = result.scalars().all()
            return [
                {
                    "id": str(a.id),
                    "patient_name": a.patient_name,
                    "patient_phone": a.patient_phone,
                    "doctor_name": a.doctor_name,
                    "department": a.department,
                    "appointment_slot": a.appointment_slot.isoformat() if a.appointment_slot else None,
                    "confirmed": a.confirmed,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
                for a in appointments
            ]
    except Exception as e:
        logger.error("Failed to fetch appointments", error=str(e))
        return []
