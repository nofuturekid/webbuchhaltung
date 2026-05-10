import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, field_validator


class AssetCreate(BaseModel):
    name: str
    description: str | None = None
    purchase_date: date
    purchase_amount_cents: int
    useful_life_months: int
    depreciation_method: Literal["linear", "none"] = "linear"
    residual_value_cents: int = 0
    coa_id: uuid.UUID
    depreciation_coa_id: uuid.UUID

    @field_validator("purchase_amount_cents")
    @classmethod
    def purchase_amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("purchase_amount_cents must be > 0")
        return v

    @field_validator("useful_life_months")
    @classmethod
    def useful_life_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("useful_life_months must be > 0")
        return v

    @field_validator("residual_value_cents")
    @classmethod
    def residual_value_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("residual_value_cents must be >= 0")
        return v


class AssetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    purchase_date: date | None = None
    purchase_amount_cents: int | None = None
    useful_life_months: int | None = None
    depreciation_method: Literal["linear", "none"] | None = None
    residual_value_cents: int | None = None
    coa_id: uuid.UUID | None = None
    depreciation_coa_id: uuid.UUID | None = None

    @field_validator("purchase_amount_cents")
    @classmethod
    def purchase_amount_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("purchase_amount_cents must be > 0")
        return v

    @field_validator("useful_life_months")
    @classmethod
    def useful_life_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("useful_life_months must be > 0")
        return v

    @field_validator("residual_value_cents")
    @classmethod
    def residual_value_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("residual_value_cents must be >= 0")
        return v


class AssetResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    asset_number: str
    name: str
    description: str | None
    purchase_date: date
    purchase_amount_cents: int
    useful_life_months: int
    depreciation_method: str
    residual_value_cents: int
    disposal_date: date | None
    disposal_amount_cents: int | None
    coa_id: uuid.UUID
    depreciation_coa_id: uuid.UUID
    status: str
    created_by: uuid.UUID
    total_depreciated_cents: int = 0
    net_book_value_cents: int = 0


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int
    page: int
    page_size: int


class DepreciationScheduleEntry(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    asset_id: uuid.UUID
    period_year: int
    period_month: int
    amount_cents: int
    cumulative_depreciation_cents: int
    net_book_value_cents: int
    booking_id: uuid.UUID | None
    is_posted: bool = False

    @classmethod
    def model_validate(
        cls, obj: object, **kwargs: object
    ) -> "DepreciationScheduleEntry":  # type: ignore[override]
        instance = super().model_validate(obj, **kwargs)
        instance.is_posted = instance.booking_id is not None
        return instance


class BookDepreciationRequest(BaseModel):
    period_year: int | None = None
    period_month: int | None = None


class DisposeAssetRequest(BaseModel):
    disposal_date: date
    disposal_amount_cents: int = 0

    @field_validator("disposal_amount_cents")
    @classmethod
    def disposal_amount_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("disposal_amount_cents must be >= 0")
        return v
