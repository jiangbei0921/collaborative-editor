from app.document.manager import DocumentManager
from app.types.models import Document, Operation, DEFAULT_DOCUMENT_TITLE


class DocumentService:
    @staticmethod
    async def create_document(doc_id: str, title: str = DEFAULT_DOCUMENT_TITLE) -> Document:
        return await DocumentManager.create(doc_id, title)

    @staticmethod
    async def get_document(doc_id: str) -> Document | None:
        return await DocumentManager.get_or_load(doc_id)

    @staticmethod
    async def apply_operation(doc_id: str, op: Operation) -> tuple[Document, int]:
        doc = await DocumentManager.get_or_load(doc_id)
        if doc is None:
            raise ValueError(f"Document '{doc_id}' does not exist. Please create it first.")
        return await DocumentManager.apply_and_persist(doc_id, op)

    @staticmethod
    async def update_title(doc_id: str, title: str) -> bool:
        return await DocumentManager.update_title(doc_id, title)