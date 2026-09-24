import json
import time
from typing import Optional

import aiosqlite

from app.database.database import get_connection
from app.types.models import Block, Document, Operation, normalize_title, DEFAULT_DOCUMENT_TITLE


class DocumentRepository:
    @staticmethod
    async def create(doc_id: str, title: str = DEFAULT_DOCUMENT_TITLE) -> Document:
        now = int(time.time() * 1000)
        normalized = normalize_title(title)
        conn = await get_connection()
        await conn.execute(
            "INSERT INTO documents (id, title, version, created_at, updated_at) VALUES (?, ?, 0, ?, ?)",
            (doc_id, normalized, now, now),
        )
        await conn.commit()
        return Document(id=doc_id, title=normalized, version=0, blocks=[], updated_at=now)

    @staticmethod
    async def get_by_id(doc_id: str) -> Optional[Document]:
        conn = await get_connection()
        async with conn.execute(
            "SELECT title, version, updated_at FROM documents WHERE id = ?", (doc_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return Document(
            id=doc_id,
            title=row["title"],
            version=row["version"],
            blocks=[],
            updated_at=row["updated_at"],
        )

    @staticmethod
    async def update_version(doc_id: str, version: int) -> None:
        now = int(time.time() * 1000)
        conn = await get_connection()
        await conn.execute(
            "UPDATE documents SET version = ?, updated_at = ? WHERE id = ?",
            (version, now, doc_id),
        )
        await conn.commit()

    @staticmethod
    async def update_title(doc_id: str, title: str) -> bool:
        normalized = normalize_title(title)
        now = int(time.time() * 1000)
        conn = await get_connection()
        cursor = await conn.execute(
            "UPDATE documents SET title = ?, updated_at = ? WHERE id = ?",
            (normalized, now, doc_id),
        )
        await conn.commit()
        return cursor.rowcount > 0


class BlockRepository:
    @staticmethod
    async def create(block: Block, document_id: str, sort_order: int) -> None:
        conn = await get_connection()
        await conn.execute(
            "INSERT INTO blocks (id, document_id, type, content, sort_order) VALUES (?, ?, ?, ?, ?)",
            (block.id, document_id, block.type, block.content, sort_order),
        )
        await conn.commit()

    @staticmethod
    async def get_by_document(doc_id: str) -> list[Block]:
        conn = await get_connection()
        async with conn.execute(
            "SELECT id, type, content FROM blocks WHERE document_id = ? ORDER BY sort_order",
            (doc_id,),
        ) as cursor:
            rows = await cursor.fetchall()
        return [Block(id=r["id"], type=r["type"], content=r["content"]) for r in rows]

    @staticmethod
    async def update(block_id: str, content: str) -> None:
        conn = await get_connection()
        await conn.execute(
            "UPDATE blocks SET content = ? WHERE id = ?",
            (content, block_id),
        )
        await conn.commit()

    @staticmethod
    async def delete(block_id: str) -> None:
        conn = await get_connection()
        await conn.execute("DELETE FROM blocks WHERE id = ?", (block_id,))
        await conn.commit()

    @staticmethod
    async def delete_by_document(doc_id: str) -> None:
        conn = await get_connection()
        await conn.execute("DELETE FROM blocks WHERE document_id = ?", (doc_id,))
        await conn.commit()

    @staticmethod
    async def get_next_sort_order(doc_id: str) -> int:
        conn = await get_connection()
        async with conn.execute(
            "SELECT MAX(sort_order) FROM blocks WHERE document_id = ?", (doc_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return (row[0] or 0) + 1


class OperationRepository:
    @staticmethod
    async def create(op: Operation) -> None:
        now = int(time.time() * 1000)
        conn = await get_connection()
        await conn.execute(
            "INSERT INTO operations (id, document_id, client_id, block_id, type, version, payload, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                op.id,
                op.document_id,
                op.client_id,
                op.block_id,
                op.type,
                op.version,
                json.dumps({
                    "position": op.position,
                    "content": op.content,
                    "length": op.length,
                }),
                now,
            ),
        )
        await conn.commit()

    @staticmethod
    async def exists(op_id: str) -> bool:
        conn = await get_connection()
        async with conn.execute(
            "SELECT 1 FROM operations WHERE id = ?", (op_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return row is not None