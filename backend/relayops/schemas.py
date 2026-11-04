"""Strict input schemas and canonical payload hashing."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class ShipmentInput(StrictModel):
    reference: str = Field(pattern=r"^SHIP-[A-Z0-9-]{3,32}$", max_length=48)
    partner: str = Field(min_length=2, max_length=100)

class EventInput(StrictModel):
    source: str = Field(min_length=2, max_length=80, pattern=r"^[a-z][a-z0-9_-]+$")
    event_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.:-]+$")
    shipment_ref: str = Field(pattern=r"^SHIP-[A-Z0-9-]{3,32}$")
    status: str = Field(pattern=r"^(PICKED_UP|IN_TRANSIT|DELIVERED|CANCELLED)$")
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def must_be_aware(cls, value: datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone (for example Z)")
        return value
