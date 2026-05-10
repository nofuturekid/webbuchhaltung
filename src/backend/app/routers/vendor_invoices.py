import uuid
from datetime import date

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.errors import ConflictError
from app.models.mandant import Mandant
from app.models.user import User
from app.schemas.vendor import (
    SepaExportRequest,
    VendorInvoiceCreate,
    VendorInvoiceListResponse,
    VendorInvoicePostRequest,
    VendorInvoiceResponse,
)
from app.services.sepa_xml import build_sepa_batch_for_due_invoices
from app.services.vendor_invoice import (
    cancel_vendor_invoice,
    create_vendor_invoice,
    get_vendor_invoice,
    list_vendor_invoices,
    mark_vendor_invoice_paid,
    post_vendor_invoice,
)

router = APIRouter(prefix="/vendor-invoices", tags=["vendor-invoices"])


async def _get_mandant(session: AsyncSession, mandant_id: uuid.UUID) -> Mandant:
    result = await session.execute(select(Mandant).where(Mandant.id == mandant_id))
    mandant = result.scalar_one_or_none()
    if mandant is None:
        raise ConflictError("Mandant not found.")
    return mandant


@router.get(
    "/",
    response_model=VendorInvoiceListResponse,
    summary="List vendor invoices",
)
async def list_vendor_invoices_endpoint(
    page: int = 1,
    page_size: int = 50,
    status: str | None = None,
    vendor_id: uuid.UUID | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> VendorInvoiceListResponse:
    return await list_vendor_invoices(
        session, mandant_id, page, page_size, status, vendor_id, due_from, due_to
    )


@router.post(
    "/",
    response_model=VendorInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create vendor invoice",
)
async def create_vendor_invoice_endpoint(
    payload: VendorInvoiceCreate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VendorInvoiceResponse:
    invoice = await create_vendor_invoice(session, mandant_id, current_user.id, payload)
    return VendorInvoiceResponse.model_validate(invoice)


@router.get(
    "/{invoice_id}",
    response_model=VendorInvoiceResponse,
    summary="Get vendor invoice",
)
async def get_vendor_invoice_endpoint(
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> VendorInvoiceResponse:
    invoice = await get_vendor_invoice(session, invoice_id, mandant_id)
    return VendorInvoiceResponse.model_validate(invoice)


@router.post(
    "/{invoice_id}/post",
    response_model=VendorInvoiceResponse,
    summary="Post vendor invoice",
)
async def post_vendor_invoice_endpoint(
    invoice_id: uuid.UUID,
    payload: VendorInvoicePostRequest,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VendorInvoiceResponse:
    mandant = await _get_mandant(session, mandant_id)
    invoice = await post_vendor_invoice(
        session,
        invoice_id,
        mandant_id,
        current_user.id,
        payload.expense_coa_id,
        mandant.skr_variant,
        payload.vat_coa_id,
    )
    return VendorInvoiceResponse.model_validate(invoice)


@router.post(
    "/{invoice_id}/pay",
    response_model=VendorInvoiceResponse,
    summary="Mark vendor invoice paid",
)
async def mark_vendor_invoice_paid_endpoint(
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VendorInvoiceResponse:
    invoice = await mark_vendor_invoice_paid(
        session, invoice_id, mandant_id, current_user.id
    )
    return VendorInvoiceResponse.model_validate(invoice)


@router.post(
    "/{invoice_id}/cancel",
    response_model=VendorInvoiceResponse,
    summary="Cancel vendor invoice",
)
async def cancel_vendor_invoice_endpoint(
    invoice_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VendorInvoiceResponse:
    invoice = await cancel_vendor_invoice(
        session, invoice_id, mandant_id, current_user.id
    )
    return VendorInvoiceResponse.model_validate(invoice)


@router.post(
    "/sepa-export",
    summary="Generate SEPA payment XML",
)
async def sepa_export_endpoint(
    payload: SepaExportRequest,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    mandant = await _get_mandant(session, mandant_id)

    if not mandant.iban:
        raise ConflictError("Mandant IBAN not configured.")
    if not mandant.bic:
        raise ConflictError("Mandant BIC not configured.")

    xml_bytes, _invoice_ids = await build_sepa_batch_for_due_invoices(
        session=session,
        mandant_id=mandant_id,
        due_on_or_before=payload.due_on_or_before,
        mandant_name=mandant.name,
        mandant_iban=mandant.iban,
        mandant_bic=mandant.bic,
    )
    due_date = payload.due_on_or_before.isoformat()
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=sepa-{due_date}.xml"},
    )
