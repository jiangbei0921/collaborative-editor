import aiosqlite

from app.config import DATABASE_PATH
from app.database.schema import SCHEMA_SQL

DB_PATH = DATABASE_PATH

_pool: aiosqlite.Connection | None = None


async def _migrate_add_title_column(conn: aiosqlite.Connection) -> None:
    cursor = await conn.execute("PRAGMA table_info(documents)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "title" not in columns:
        await conn.execute(
            "ALTER TABLE documents ADD COLUMN title TEXT NOT NULL DEFAULT '未命名文档'"
        )
        await conn.commit()


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.executescript(SCHEMA_SQL)
    await _migrate_add_title_column(conn)
    await conn.commit()
    await conn.close()


async def get_connection() -> aiosqlite.Connection:
    global _pool
    if _pool is None or not _pool._running:
        _pool = await aiosqlite.connect(DB_PATH)
        _pool.row_factory = aiosqlite.Row
    return _pool


async def close_db() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None