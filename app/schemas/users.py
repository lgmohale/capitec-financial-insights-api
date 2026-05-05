from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserMetadata(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440000",
                "name": "Lucas George",
                "created_at": "2026-05-05T10:00:00Z",
                "updated_at": "2026-05-05T10:00:00Z",
            }
        },
    )

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
