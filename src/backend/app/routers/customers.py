import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_mandant_id
from app.errors import ConflictError, NotFoundError
from app.models.invoice import Customer, Invoice
from app.schemas.invoice import CustomerCreate, CustomerResponse, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


async def _get_customer(
    session: AsyncSession, customer_id: uuid.UUID, mandant_id: uuid.UUID
) -> Customer:
    result = await session.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.mandant_id == mandant_id
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise NotFoundError(f"Customer {customer_id} not found.")
    return customer


@router.get("/", response_model=list[CustomerResponse])
async def list_customers(
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> list[Customer]:
    result = await session.execute(
        select(Customer)
        .where(Customer.mandant_id == mandant_id)
        .order_by(Customer.name)
    )
    return list(result.scalars().all())


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> Customer:
    customer = Customer(mandant_id=mandant_id, **payload.model_dump())
    session.add(customer)
    await session.flush()
    await session.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> Customer:
    return await _get_customer(session, customer_id, mandant_id)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID,
    payload: CustomerUpdate,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> Customer:
    customer = await _get_customer(session, customer_id, mandant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    await session.flush()
    await session.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: uuid.UUID,
    mandant_id: uuid.UUID = Depends(get_mandant_id),
    session: AsyncSession = Depends(get_db),
) -> None:
    customer = await _get_customer(session, customer_id, mandant_id)
    invoice_check = await session.execute(
        select(Invoice.id).where(Invoice.customer_id == customer_id).limit(1)
    )
    if invoice_check.scalar_one_or_none():
        raise ConflictError("Customer has invoices and cannot be deleted.")
    await session.delete(customer)
    await session.flush()
