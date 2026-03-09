"""
Dashboard analytics routes.
Provides aggregated call, appointment, and emergency data for the admin UI.
"""
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta

from database.connection import get_db
from database.models import Call, Appointment, Transcript, Patient, CallStatus, RiskLevel

router = APIRouter(prefix="", tags=["Dashboard"])
logger = structlog.get_logger()


@router.get("/get-dashboard-data")
async def get_dashboard_data(db: AsyncSession = Depends(get_db)):
    """
    Aggregated analytics for the admin dashboard.
    Returns call stats, appointment stats, and emergency summary.
    """
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        # ── Call statistics
        total_calls = await _count(db, Call)
        calls_today = await _count_where(db, Call, Call.started_at >= today_start)
        calls_this_week = await _count_where(db, Call, Call.started_at >= week_start)
        ai_handled = await _count_where(db, Call, Call.ai_handled == True)
        escalated = await _count_where(db, Call, Call.ai_handled == False)
        emergency_calls = await _count_where(db, Call, Call.emergency_flag == True)
        completed_calls = await _count_where(db, Call, Call.status == CallStatus.COMPLETED)

        # Average duration
        avg_duration_result = await db.execute(
            select(func.avg(Call.duration_seconds)).where(Call.duration_seconds != None)
        )
        avg_duration = avg_duration_result.scalar() or 0

        # ── Appointment statistics
        total_appointments = await _count(db, Appointment)
        appts_today = await _count_where(db, Appointment, Appointment.created_at >= today_start)
        appts_this_week = await _count_where(db, Appointment, Appointment.created_at >= week_start)

        # Doctor-wise appointment counts
        doctor_stats_result = await db.execute(
            select(Appointment.doctor_name, func.count(Appointment.id).label("count"))
            .group_by(Appointment.doctor_name)
            .order_by(func.count(Appointment.id).desc())
            .limit(10)
        )
        doctor_stats = [
            {"doctor": row.doctor_name, "appointments": row.count}
            for row in doctor_stats_result
        ]

        # ── Intent breakdown
        intent_result = await db.execute(
            select(Call.intent, func.count(Call.id).label("count"))
            .where(Call.intent != None)
            .group_by(Call.intent)
        )
        intent_breakdown = [
            {"intent": row.intent.value if row.intent else "unknown", "count": row.count}
            for row in intent_result
        ]

        # ── Call volume by hour (last 24h)
        hourly_result = await db.execute(
            select(
                func.date_trunc("hour", Call.started_at).label("hour"),
                func.count(Call.id).label("count")
            )
            .where(Call.started_at >= now - timedelta(hours=24))
            .group_by(func.date_trunc("hour", Call.started_at))
            .order_by(func.date_trunc("hour", Call.started_at))
        )
        hourly_volume = [
            {"hour": row.hour.isoformat() if row.hour else "", "count": row.count}
            for row in hourly_result
        ]

        # ── Recent emergency alerts
        emergency_result = await db.execute(
            select(Call)
            .where(Call.emergency_flag == True)
            .order_by(Call.started_at.desc())
            .limit(10)
        )
        emergencies = emergency_result.scalars().all()
        emergency_alerts = [
            {
                "call_id": str(c.id),
                "phone": c.caller_phone,
                "risk_level": c.risk_level.value if c.risk_level else "high",
                "time": c.started_at.isoformat() if c.started_at else "",
                "status": c.status.value if c.status else "unknown"
            }
            for c in emergencies
        ]

        return {
            "calls": {
                "total": total_calls,
                "today": calls_today,
                "this_week": calls_this_week,
                "ai_handled": ai_handled,
                "escalated": escalated,
                "emergency": emergency_calls,
                "completed": completed_calls,
                "avg_duration_seconds": round(float(avg_duration), 1),
                "ai_handle_rate": round(ai_handled / total_calls * 100, 1) if total_calls else 0
            },
            "appointments": {
                "total": total_appointments,
                "today": appts_today,
                "this_week": appts_this_week,
                "by_doctor": doctor_stats
            },
            "intents": intent_breakdown,
            "hourly_volume": hourly_volume,
            "emergency_alerts": emergency_alerts,
            "active_calls": 0,  # From in-memory session manager
            "generated_at": now.isoformat()
        }

    except Exception as e:
        logger.error("Dashboard data fetch failed", error=str(e))
        # Return demo data for hackathon presentation
        return _demo_dashboard_data()


@router.get("/emergency-alerts")
async def get_emergency_alerts(db: AsyncSession = Depends(get_db)):
    """Get all high-priority emergency calls."""
    result = await db.execute(
        select(Call)
        .where(Call.emergency_flag == True)
        .order_by(Call.started_at.desc())
        .limit(50)
    )
    calls = result.scalars().all()
    return {
        "alerts": [
            {
                "call_id": str(c.id),
                "phone": c.caller_phone,
                "risk_level": c.risk_level.value if c.risk_level else "high",
                "time": c.started_at.isoformat() if c.started_at else "",
                "status": c.status.value if c.status else "unknown",
                "ai_handled": c.ai_handled
            }
            for c in calls
        ]
    }


@router.get("/transcripts")
async def get_transcripts(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Get recent transcripts with analysis for the dashboard."""
    result = await db.execute(
        select(Transcript, Call)
        .join(Call, Transcript.call_id == Call.id)
        .order_by(Transcript.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return {
        "transcripts": [
            {
                "id": str(tr.id),
                "call_id": str(tr.call_id),
                "phone": call.caller_phone,
                "content_preview": tr.content[:200] + "..." if len(tr.content) > 200 else tr.content,
                "analysis": tr.analysis,
                "turn_count": tr.turn_count,
                "created_at": tr.created_at.isoformat() if tr.created_at else ""
            }
            for tr, call in rows
        ]
    }


# Helpers
async def _count(db, model) -> int:
    result = await db.execute(select(func.count(model.id)))
    return result.scalar() or 0


async def _count_where(db, model, *conditions) -> int:
    query = select(func.count(model.id))
    for condition in conditions:
        query = query.where(condition)
    result = await db.execute(query)
    return result.scalar() or 0


def _demo_dashboard_data() -> dict:
    """Return realistic demo data when DB is unavailable."""
    from datetime import datetime
    now = datetime.utcnow()
    return {
        "calls": {
            "total": 142, "today": 18, "this_week": 87,
            "ai_handled": 127, "escalated": 15, "emergency": 8,
            "completed": 134, "avg_duration_seconds": 187.4,
            "ai_handle_rate": 89.4
        },
        "appointments": {
            "total": 89, "today": 12, "this_week": 52,
            "by_doctor": [
                {"doctor": "Dr. Priya Kumar", "appointments": 28},
                {"doctor": "Dr. Vikram Singh", "appointments": 22},
                {"doctor": "Dr. Rahul Sharma", "appointments": 18},
                {"doctor": "Dr. Ananya Iyer", "appointments": 13},
                {"doctor": "Dr. Meena Nair", "appointments": 8}
            ]
        },
        "intents": [
            {"intent": "appointment_booking", "count": 72},
            {"intent": "doctor_availability", "count": 31},
            {"intent": "general_inquiry", "count": 22},
            {"intent": "emergency", "count": 8},
            {"intent": "hospital_timings", "count": 9}
        ],
        "hourly_volume": [
            {"hour": f"{now.strftime('%Y-%m-%dT')}{h:02d}:00:00", "count": v}
            for h, v in [(9,8),(10,12),(11,15),(12,9),(13,6),(14,11),(15,18),(16,14),(17,10),(18,7)]
        ],
        "emergency_alerts": [
            {"call_id": "demo-001", "phone": "+91-9876543210", "risk_level": "high",
             "time": now.isoformat(), "status": "escalated"},
            {"call_id": "demo-002", "phone": "+91-8765432109", "risk_level": "medium",
             "time": now.isoformat(), "status": "completed"},
        ],
        "active_calls": 3,
        "generated_at": now.isoformat(),
        "demo_mode": True
    }
