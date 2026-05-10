from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth import create_access_token, create_refresh_token
from app.services.bootstrap import bootstrap_first_admin, system_needs_bootstrap

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])


class SetupRequest(BaseModel):
    email: EmailStr
    password: str
    mandant_name: str = "Meine Firma"
    skr_variant: Literal["skr03", "skr04", "skr07"] = "skr03"

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class SetupResponse(BaseModel):
    access_token: str
    refresh_token: str


class SetupStatusResponse(BaseModel):
    needs_setup: bool


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(
    db: AsyncSession = Depends(get_db),
) -> SetupStatusResponse:
    """Check whether the system still needs initial setup."""
    needs = await system_needs_bootstrap(db)
    return SetupStatusResponse(needs_setup=needs)


@router.post("", response_model=SetupResponse, status_code=status.HTTP_200_OK)
async def post_setup(
    body: SetupRequest,
    db: AsyncSession = Depends(get_db),
) -> SetupResponse:
    """Bootstrap the first admin user and mandant.

    Returns HTTP 404 when setup has already been completed (users exist).
    """
    needs = await system_needs_bootstrap(db)
    if not needs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setup already completed",
        )

    user, _mandant = await bootstrap_first_admin(
        db,
        email=str(body.email),
        password=body.password,
        mandant_name=body.mandant_name,
        skr_variant=body.skr_variant,
    )
    # Capture user_id before commit so the expired instance is not re-loaded.
    user_id = user.id
    await db.commit()

    access_token = create_access_token(user_id, mandant_id=None)
    refresh_token = create_refresh_token(user_id)
    return SetupResponse(access_token=access_token, refresh_token=refresh_token)
