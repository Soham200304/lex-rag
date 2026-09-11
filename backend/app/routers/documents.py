from uuid import UUID
from app.core.redis import create_redis_pool

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

@router.get(
    "/{document_id}",
    response_model=DocumentResponse
)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository = DocumentRepository(db)
    service = DocumentService(repository)

    document = await service.get_document(
        document_id=document_id,
        owner_id=current_user.id
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document Not found."
        )
    return document


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository = DocumentRepository(db)
    service = DocumentService(repository)

    try:
        document = await service.upload_document(
            file=file,
            owner_id=current_user.id,
        )

        redis = await create_redis_pool()

        try:
            await redis.enqueue_job(
                "process_document_task",
                str(document.id),
            )
        finally:
            await redis.close()

        return document

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

@router.get(
    "",
    response_model=DocumentListResponse,
)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository = DocumentRepository(db)
    service = DocumentService(repository)

    documents = await service.list_documents(
        owner_id=current_user.id,
    )

    return DocumentListResponse(
        documents=documents,
        total=len(documents),
    )

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repository = DocumentRepository(db)
    service = DocumentService(repository)

    deleted = await service.delete_document(
        document_id=document_id,
        owner_id=current_user.id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )