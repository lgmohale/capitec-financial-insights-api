from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LinkBankAccountRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Lucas George",
                "bank_name": "Capitec",
            }
        }
    )

    name: str = Field(examples=["Lucas George"])
    bank_name: str = Field(examples=["Capitec"])


class UserMetadata(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "uuid": "650e8400-e29b-41d4-a716-446655440000",
                "name": "Lucas George",
                "created_at": "2026-05-05T10:00:00Z",
                "updated_at": "2026-05-05T10:00:00Z",
            }
        },
    )

    uuid: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class LinkedAccountMetadata(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user_id": "650e8400-e29b-41d4-a716-446655440000",
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "bank_name": "Capitec",
                "created_at": "2026-05-05T10:00:00Z",
            }
        },
    )

    user_id: UUID
    uuid: UUID
    bank_name: str
    created_at: datetime


class LinkBankAccountResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user": {
                    "uuid": "650e8400-e29b-41d4-a716-446655440000",
                    "name": "Lucas George",
                    "created_at": "2026-05-05T10:00:00Z",
                    "updated_at": "2026-05-05T10:00:00Z",
                },
                "linked_account": {
                    "user_id": "650e8400-e29b-41d4-a716-446655440000",
                    "uuid": "550e8400-e29b-41d4-a716-446655440000",
                    "bank_name": "Capitec",
                    "created_at": "2026-05-05T10:00:00Z",
                },
            }
        },
    )

    user: UserMetadata
    linked_account: LinkedAccountMetadata
