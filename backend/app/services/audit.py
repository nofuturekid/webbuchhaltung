import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.period import AuditLog


async def write_audit(
    session: AsyncSession,
    table_name: str,
    record_id: uuid.UUID,
    action: str,
    change_summary: dict[str, object],
    mandant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> None:
    log = AuditLog(
        mandant_id=mandant_id,
        user_id=user_id,
        table_name=table_name,
        record_id=record_id,
        action=action,
        changed_at=datetime.now(timezone.utc),
        change_summary=change_summary,
    )
    session.add(log)


async def list_booking_audit_log(
    session: AsyncSession, booking_id: uuid.UUID
) -> list[dict[str, object]]:
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.record_id == booking_id, AuditLog.table_name == "bookings")
        .order_by(AuditLog.changed_at)
    )
    return [
        {
            "action": r.action,
            "changed_at": r.changed_at.isoformat(),
            "change_summary": r.change_summary,
        }
        for r in result.scalars().all()
    ]
