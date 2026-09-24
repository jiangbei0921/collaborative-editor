import asyncio

from app.database.repository import OperationRepository
from app.document.service import DocumentService
from app.types.models import (
    AckMessage,
    ConflictMessage,
    Document,
    Operation,
    WebSocketMessage,
)


class OperationManager:
    _locks: dict[str, asyncio.Lock] = {}

    @classmethod
    def _get_lock(cls, doc_id: str) -> asyncio.Lock:
        if doc_id not in cls._locks:
            cls._locks[doc_id] = asyncio.Lock()
        return cls._locks[doc_id]

    @classmethod
    async def process(
        cls, client_id: str, doc_id: str, op: Operation
    ) -> WebSocketMessage:
        if await OperationRepository.exists(op.id):
            return AckMessage(
                type="ack",
                operation_id=op.id,
                document_id=doc_id,
                version=op.version,
                status="duplicate",
            )

        async with cls._get_lock(doc_id):
            doc = await DocumentService.get_document(doc_id)
            if doc is None:
                return ConflictMessage(
                    type="conflict",
                    operation_id=op.id,
                    document_id=doc_id,
                    current_version=0,
                    reason="Document not found",
                )

            if op.version != doc.version + 1:
                return ConflictMessage(
                    type="conflict",
                    operation_id=op.id,
                    document_id=doc_id,
                    current_version=doc.version,
                    reason=f"Version mismatch: expected {doc.version + 1}, got {op.version}",
                )

            try:
                new_doc, new_version = await DocumentService.apply_operation(doc_id, op)
            except ValueError as e:
                return ConflictMessage(
                    type="conflict",
                    operation_id=op.id,
                    document_id=doc_id,
                    current_version=doc.version,
                    reason=str(e),
                )

            await OperationRepository.create(op)

        return AckMessage(
            type="ack",
            operation_id=op.id,
            document_id=doc_id,
            version=new_version,
            status="applied",
        )