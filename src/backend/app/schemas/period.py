import uuid

from pydantic import AwareDatetime, BaseModel


class PeriodResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    year: int
    month: int
    status: str
    locked_at: AwareDatetime | None
