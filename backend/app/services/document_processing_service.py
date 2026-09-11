from uuid import UUID

from app.models.chunk import DocumentChunk
from app.models.document import DocumentStatus
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.services.pdf_extractor import PDFExtractor
from app.services.text_chunker import TextChunker


class DocumentProcessingService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: ChunkRepository,
        pdf_extractor: PDFExtractor,
        text_chunker: TextChunker,
    ):
        self.document_repository = document_repository
        self.chunk_repository = chunk_repository
        self.pdf_extractor = pdf_extractor
        self.text_chunker = text_chunker

    async def process_document(
        self,
        document_id: UUID,
    ) -> None:

        document = await self.document_repository.get_by_document_id(
            document_id
        )

        if document is None:
            raise ValueError(
                f"Document not found: {document_id}"
            )

        try:
            # 1. Mark document as processing
            await self.document_repository.update_status(
                document,
                DocumentStatus.PROCESSING,
            )

            # 2. Extract text from PDF
            pages = self.pdf_extractor.extract(
                document.file_path
            )

            # 3. Create chunks
            chunks: list[DocumentChunk] = []

            for page in pages:

                page_chunks = self.text_chunker.chunk(
                    page.text
                )

                for content in page_chunks:

                    chunks.append(
                        DocumentChunk(
                            document_id=document.id,
                            content=content,
                            chunk_index=len(chunks),
                            page_number=page.page_number,
                        )
                    )

            # 4. Save chunks
            if chunks:
                await self.chunk_repository.create_many(
                    chunks
                )

            # 5. Mark document as processed
            await self.document_repository.update_status(
                document,
                DocumentStatus.PROCESSED,
            )

        except Exception:

            await self.document_repository.update_status(
                document,
                DocumentStatus.FAILED,
            )

            raise