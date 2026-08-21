from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.repositories.document_repository import DocumentRepository


class DocumentService:
    def __init__(self, repository: DocumentRepository):
        self.repository = repository

    async def upload_document(
        self,
        file: UploadFile,
        owner_id: UUID,
    ) -> Document:

        # 1. Validate filename
        if not file.filename:
            raise ValueError("Filename is required.")

        # 2. Validate content type
        if file.content_type != "application/pdf":
            raise ValueError("Only PDF files are allowed.")

        # 3. Generate unique filename
        document_id = uuid4()

        original_filename = Path(file.filename).name

        stored_filename = (
            f"{document_id}_{original_filename}"
        )

        # 4. Create storage directory
        storage_directory = Path(settings.storage_path)
        storage_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = storage_directory / stored_filename

        # 5. Save file
        file_size = 0

        with file_path.open("wb") as buffer:

            while chunk := await file.read(1024 * 1024):

                file_size += len(chunk)

                if file_size > settings.max_file_size:
                    buffer.close()

                    if file_path.exists():
                        file_path.unlink()

                    raise ValueError(
                        "File size exceeds the maximum allowed size."
                    )

                buffer.write(chunk)

        # 6. Create database record
        document = Document(
            id=document_id,
            owner_id=owner_id,
            filename=stored_filename,
            original_filename=original_filename,
            content_type=file.content_type,
            file_size=file_size,
            file_path=str(file_path),
            status=DocumentStatus.UPLOADED,
        )

        try:
            return await self.repository.create(document)

        except Exception:
            if file_path.exists():
                file_path.unlink()

            raise

    async def list_documents(
        self,
        owner_id: UUID,
    ) -> list[Document]:

        return await self.repository.get_all_by_owner(owner_id)

    async def get_document(
        self,
        document_id: UUID,
        owner_id: UUID,
    ) -> Document | None:

        return await self.repository.get_by_id(
            document_id=document_id,
            owner_id=owner_id,
        )

    async def delete_document(
        self,
        document_id: UUID,
        owner_id: UUID,
    ) -> bool:

        document = await self.repository.get_by_id(
            document_id=document_id,
            owner_id=owner_id,
        )

        if document is None:
            return False

        file_path = Path(document.file_path)

        if file_path.exists():
            file_path.unlink()

        await self.repository.delete(document)

        return True