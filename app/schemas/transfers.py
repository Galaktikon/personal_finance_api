from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransferMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_transaction_id: UUID
    destination_transaction_id: UUID


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_transaction_id: UUID
    destination_transaction_id: UUID
    status: str
    created_at: datetime
