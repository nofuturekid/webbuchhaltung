import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_mandant_id
from app.models.user import User
from app.schemas.vendor import (
    VendorCreate,
    VendorListResponse,
    VendorResponse,
    VendorUpdate,
)
from app.services.vendor_invoice import (
    create_vendor,
    get_vendor,
    list_vendors,
    update_vendor,
)

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("/", response_model=VendorListResponse, summary="List vendors")
async def list_vendors_endpoint(
    page: int = 1,
    page_size: int = 50,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> VendorListResponse:
    return await list_vendors(session, mandant_id, page, page_size)


@router.post(
    "/",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create vendor",
)
async def create_vendor_endpoint(
    payload: VendorCreate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VendorResponse:
    vendor = await create_vendor(session, mandant_id, current_user.id, payload)
    return VendorResponse.model_validate(vendor)


@router.get("/{vendor_id}", response_model=VendorResponse, summary="Get vendor")
async def get_vendor_endpoint(
    vendor_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> VendorResponse:
    vendor = await get_vendor(session, vendor_id, mandant_id)
    return VendorResponse.model_validate(vendor)


@router.patch("/{vendor_id}", response_model=VendorResponse, summary="Update vendor")
async def update_vendor_endpoint(
    vendor_id: uuid.UUID,
    payload: VendorUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VendorResponse:
    vendor = await update_vendor(
        session, vendor_id, mandant_id, current_user.id, payload
    )
    return VendorResponse.model_validate(vendor)
