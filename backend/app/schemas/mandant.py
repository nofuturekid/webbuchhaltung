import uuid

from pydantic import BaseModel


class MandantCreate(BaseModel):
    name: str
    steuernummer: str | None = None
    ust_id: str | None = None
    datev_beraternummer: str | None = None
    datev_mandantennummer: str | None = None
    fiscal_year_start: int = 1
    skr_variant: str = "skr03"


class MandantUpdate(BaseModel):
    name: str | None = None
    steuernummer: str | None = None
    ust_id: str | None = None
    datev_beraternummer: str | None = None
    datev_mandantennummer: str | None = None
    fiscal_year_start: int | None = None


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
