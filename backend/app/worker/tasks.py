from uuid import UUID

from app.db.database import SessionLocal
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.services.document_processing_service import (
    DocumentProcessingService,
)
from app.services.pdf_extractor import PDFExtractor
from app.services.text_chunker import TextChunker


async def process_document_task(
    ctx,
    document_id: str,
):
    async with SessionLocal() as db:

        document_repository = DocumentRepository(db)
        chunk_repository = ChunkRepository(db)

        service = DocumentProcessingService(
            document_repository=document_repository,
            chunk_repository=chunk_repository,
            pdf_extractor=PDFExtractor(),
            text_chunker=TextChunker(),
        )

        await service.process_document(
            UUID(document_id)
        )