import uuid
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.models.user import User
from app.services.datev import generate_datev_export

router = APIRouter(prefix="/datev", tags=["datev"])


class DatevExportRequest(BaseModel):
    date_from: date
    date_to: date


@router.post("/export")
async def export(
    body: DatevExportRequest,
    _current_user: User = Depends(get_current_user),
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> Response:
    content = await generate_datev_export(
        session, mandant_id, body.date_from, body.date_to
    )
    filename = f"EXTF_{body.date_from}_{body.date_to}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
