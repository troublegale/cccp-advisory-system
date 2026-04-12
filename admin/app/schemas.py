from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IngestResponse(BaseModel):
    status: str
    chunks_count: int


class KBFileResponse(BaseModel):
    filename: str
    s3_key: str
    size_bytes: int | None
    sha256: str | None


class KBVersionResponse(BaseModel):
    id: UUID
    version_num: int
    created_at: datetime
    status: str
    s3_prefix: str
    qdrant_collection: str | None
    file_count: int | None
    comment: str | None
    files: list[KBFileResponse]

    model_config = ConfigDict(from_attributes=True)
