from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from app.models.document import DocumentStatus

class DocumentResponse(BaseModel):
    id: UUID
    owner_id: UUID
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    file_path: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int