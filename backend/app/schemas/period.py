import uuid
from datetime import datetime

from pydantic import BaseModel


class PeriodResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    mandant_id: uuid.UUID
    year: int
    month: int
    status: str
    locked_at: datetime | None
