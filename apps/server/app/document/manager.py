import time
from typing import Optional

from app.database.repository import BlockRepository, DocumentRepository
from app.types.models import Document, Operation, DEFAULT_DOCUMENT_TITLE
from app.operation.apply import apply_operation


class DocumentManager:
    _cache: dict[str, Document] = {}

    @classmethod
    async def get_or_load(cls, doc_id: str) -> Optional[Document]:
        if doc_id in cls._cache:
            return cls._cache[doc_id]

        doc = await DocumentRepository.get_by_id(doc_id)
        if doc is None:
            return None

        blocks = await BlockRepository.get_by_document(doc_id)
        doc.blocks = blocks
        cls._cache[doc_id] = doc
        return doc

    @classmethod
    async def create(cls, doc_id: str, title: str = DEFAULT_DOCUMENT_TITLE) -> Document:
        doc = await DocumentRepository.create(doc_id, title)
        cls._cache[doc_id] = doc
        return doc

    @classmethod
    async def update_title(cls, doc_id: str, title: str) -> bool:
        success = await DocumentRepository.update_title(doc_id, title)
        if success and doc_id in cls._cache:
            cls._cache[doc_id].title = title
        return success

    @classmethod
    async def apply_and_persist(
        cls, doc_id: str, op: Operation
    ) -> tuple[Document, int]:
        doc = await cls.get_or_load(doc_id)
        if doc is None:
            raise ValueError(f"Document '{doc_id}' not found")

        new_doc = apply_operation(doc.model_copy(deep=True), op)
        new_version = doc.version + 1

        await DocumentRepository.update_version(doc_id, new_version)

        if op.type == "create_block":
            sort_order = await BlockRepository.get_next_sort_order(doc_id)
            await BlockRepository.create(new_doc.blocks[-1], doc_id, sort_order)
        elif op.type == "delete_block":
            if op.block_id:
                await BlockRepository.delete(op.block_id)
        elif op.type in ("insert", "delete", "update_block"):
            if op.block_id:
                block = next((b for b in new_doc.blocks if b.id == op.block_id), None)
                if block:
                    await BlockRepository.update(op.block_id, block.content)

        new_doc.version = new_version
        new_doc.updated_at = int(time.time() * 1000)
        cls._cache[doc_id] = new_doc
        return new_doc, new_version

    @classmethod
    def evict(cls, doc_id: str) -> None:
        cls._cache.pop(doc_id, None)