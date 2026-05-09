import uuid
from typing import Literal

from pydantic import BaseModel, field_validator


class MandantCreate(BaseModel):
    name: str
    steuernummer: str | None = None
    ust_id: str | None = None
    datev_beraternummer: str | None = None
    datev_mandantennummer: str | None = None
    fiscal_year_start: int = 1
    skr_variant: Literal["skr03", "skr04", "skr07"] = "skr03"

    @field_validator("fiscal_year_start")
    @classmethod
    def validate_fiscal_year_start(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("fiscal_year_start must be between 1 and 12")
        return v


class MandantUpdate(BaseModel):
    name: str | None = None
    steuernummer: str | None = None
    ust_id: str | None = None
    datev_beraternummer: str | None = None
    datev_mandantennummer: str | None = None
    fiscal_year_start: int | None = None

    @field_validator("fiscal_year_start")
    @classmethod
    def validate_fiscal_year_start(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= 12:
            raise ValueError("fiscal_year_start must be between 1 and 12")
        return v


class MandantResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    steuernummer: str | None
    ust_id: str | None
    datev_beraternummer: str | None
    datev_mandantennummer: str | None
    fiscal_year_start: int
    skr_variant: str
    is_active: bool
