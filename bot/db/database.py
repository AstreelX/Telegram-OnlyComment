from pathlib import Path

import aiosqlite

# Ключ — номер версии схемы (PRAGMA user_version). Новые изменения добавляются следующим номером.
MIGRATIONS = {
    1: """
        CREATE TABLE chat_settings (
            chat_id        INTEGER PRIMARY KEY,
            enabled        INTEGER NOT NULL,
            reply_mode     TEXT    NOT NULL,
            exempt_admins  INTEGER NOT NULL,
            exempt_channel INTEGER NOT NULL,
            warn_enabled   INTEGER NOT NULL,
            warn_ttl       INTEGER NOT NULL,
            log_chat_id    INTEGER
        );
        CREATE TABLE post_threads (
            chat_id    INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            PRIMARY KEY (chat_id, message_id)
        );
    """,
}


class Database:
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn

    @classmethod
    async def connect(cls, path: Path | str) -> "Database":
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        db = cls(conn)
        await db._migrate()
        return db

    async def _migrate(self) -> None:
        cursor = await self.conn.execute("PRAGMA user_version")
        (version,) = await cursor.fetchone()
        for target in sorted(MIGRATIONS):
            if target > version:
                await self.conn.executescript(MIGRATIONS[target])
                await self.conn.execute(f"PRAGMA user_version = {target}")
        await self.conn.commit()

    async def close(self) -> None:
        await self.conn.close()
