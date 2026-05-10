import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_mandant_id
from app.models.invoice import InvoiceSequence, InvoiceTemplate
from app.schemas.invoice import (
    InvoiceSequenceResponse,
    InvoiceSequenceUpdate,
    InvoiceTemplateResponse,
    InvoiceTemplateUpdate,
)
from app.services.invoice_sequence import get_or_create_sequence, update_sequence

router = APIRouter(tags=["invoice-settings"])


@router.get("/invoice-template", response_model=InvoiceTemplateResponse)
async def get_invoice_template(
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> InvoiceTemplate:
    result = await session.execute(
        select(InvoiceTemplate).where(InvoiceTemplate.mandant_id == mandant_id)
    )
    tmpl = result.scalar_one_or_none()
    if tmpl is None:
        tmpl = InvoiceTemplate(mandant_id=mandant_id)
        session.add(tmpl)
        await session.flush()
        await session.refresh(tmpl)
    return tmpl


@router.put("/invoice-template", response_model=InvoiceTemplateResponse)
async def update_invoice_template(
    payload: InvoiceTemplateUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> InvoiceTemplate:
    result = await session.execute(
        select(InvoiceTemplate).where(InvoiceTemplate.mandant_id == mandant_id)
    )
    tmpl = result.scalar_one_or_none()
    if tmpl is None:
        tmpl = InvoiceTemplate(mandant_id=mandant_id)
        session.add(tmpl)
        await session.flush()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tmpl, field, value)
    await session.flush()
    await session.refresh(tmpl)
    return tmpl


@router.get("/invoice-sequences", response_model=InvoiceSequenceResponse)
async def get_invoice_sequence(
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> InvoiceSequence:
    return await get_or_create_sequence(session, mandant_id)


@router.put("/invoice-sequences", response_model=InvoiceSequenceResponse)
async def update_invoice_sequence(
    payload: InvoiceSequenceUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> InvoiceSequence:
    return await update_sequence(
        session, mandant_id, payload.prefix, payload.year_reset
    )
