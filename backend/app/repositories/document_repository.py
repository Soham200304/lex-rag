from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, document: Document) -> Document:
        self.db.add(document)

        await self.db.commit()
        await self.db.refresh(document)

        return document

    async def get_by_id(
        self,
        document_id: UUID,
        owner_id: UUID,
    ) -> Document | None:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.owner_id == owner_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_document_id(
        self,
        document_id: UUID,
    ) -> Document | None:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id
            )
        )

        return result.scalar_one_or_none()

    async def get_all_by_owner(
        self,
        owner_id: UUID,
    ) -> list[Document]:
        result = await self.db.execute(
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
        )

        return list(result.scalars().all())

    async def delete(
        self,
        document: Document,
    ) -> None:
        await self.db.delete(document)
        await self.db.commit()

    async def update_status(
        self,
        document: Document,
        status,
    ) -> Document:
        document.status = status

        await self.db.commit()
        await self.db.refresh(document)

        return document

    