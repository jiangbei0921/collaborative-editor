import logging

from fastapi import WebSocket

from app.document.service import DocumentService
from app.operation.manager import OperationManager
from app.types.models import Document, DocumentMessage, Operation, WebSocketMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    _connections: dict[str, dict[str, WebSocket]] = {}

    @classmethod
    def _get_doc_connections(cls, doc_id: str) -> dict[str, WebSocket]:
        if doc_id not in cls._connections:
            cls._connections[doc_id] = {}
        return cls._connections[doc_id]

    @classmethod
    async def join(cls, client_id: str, doc_id: str, ws: WebSocket) -> Document:
        doc_conns = cls._get_doc_connections(doc_id)
        doc_conns[client_id] = ws

        doc = await DocumentService.get_document(doc_id)
        if doc is None:
            await ws.send_json({"type": "error", "reason": f"Document '{doc_id}' not found"})
            await ws.close()
            raise ValueError(f"Document '{doc_id}' not found")
        msg = DocumentMessage(document=doc)
        await ws.send_json(msg.model_dump())
        return doc

    @classmethod
    async def leave(cls, client_id: str, doc_id: str) -> None:
        doc_conns = cls._get_doc_connections(doc_id)
        doc_conns.pop(client_id, None)
        if not doc_conns:
            cls._connections.pop(doc_id, None)

    @classmethod
    async def broadcast(cls, doc_id: str, sender_id: str, message: WebSocketMessage) -> None:
        doc_conns = cls._get_doc_connections(doc_id)
        data = message.model_dump()
        for client_id, ws in doc_conns.items():
            if client_id != sender_id:
                await ws.send_json(data)

    @classmethod
    async def broadcast_raw(cls, doc_id: str, sender_id: str, data: dict) -> None:
        doc_conns = cls._get_doc_connections(doc_id)
        for client_id, ws in doc_conns.items():
            if client_id != sender_id:
                await ws.send_json(data)

    @classmethod
    async def broadcast_cursor(cls, doc_id: str, sender_id: str, data: dict) -> None:
        doc_conns = cls._get_doc_connections(doc_id)
        for client_id, ws in doc_conns.items():
            if client_id != sender_id:
                try:
                    await ws.send_json(data)
                except Exception:
                    logger.warning("broadcast_cursor failed for %s in doc %s", client_id, doc_id, exc_info=True)

    @classmethod
    def get_online_users(cls, doc_id: str) -> list[str]:
        doc_conns = cls._connections.get(doc_id, {})
        return list(doc_conns.keys())

    @classmethod
    async def broadcast_presence(cls, doc_id: str) -> None:
        users = cls.get_online_users(doc_id)
        doc_conns = cls._get_doc_connections(doc_id)
        data = {
            "type": "presence",
            "document_id": doc_id,
            "users": users,
        }
        for ws in doc_conns.values():
            await ws.send_json(data)

    @classmethod
    async def broadcast_title_update(cls, doc_id: str, title: str) -> None:
        doc_conns = cls._get_doc_connections(doc_id)
        data = {
            "type": "document_title_updated",
            "document_id": doc_id,
            "title": title,
        }
        for ws in doc_conns.values():
            try:
                await ws.send_json(data)
            except Exception:
                pass

    @classmethod
    async def handle_operation(
        cls, client_id: str, doc_id: str, op: Operation
    ) -> WebSocketMessage:
        result = await OperationManager.process(client_id, doc_id, op)
        return result