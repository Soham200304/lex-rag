from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk


class ChunkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        chunk: DocumentChunk,
    ) -> DocumentChunk:
        self.db.add(chunk)
        await self.db.commit()
        await self.db.refresh(chunk)

        return chunk

    async def create_many(
        self,
        chunks: list[DocumentChunk],
    ) -> list[DocumentChunk]:
        self.db.add_all(chunks)
        await self.db.commit()

        for chunk in chunks:
            await self.db.refresh(chunk)

        return chunks

    async def get_by_document(
        self,
        document_id: UUID,
    ) -> list[DocumentChunk]:
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )

        return list(result.scalars().all())

    async def delete_by_document(
        self,
        document_id: UUID,
    ) -> None:
        await self.db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document_id
            )
        )

        await self.db.commit()