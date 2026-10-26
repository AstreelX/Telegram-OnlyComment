from dataclasses import fields, replace

import aiosqlite

from bot.db.database import Database
from bot.models import ChatSettings, ReplyMode

_COLUMNS = [f.name for f in fields(ChatSettings)]
_UPSERT = (
    f"INSERT INTO chat_settings ({', '.join(_COLUMNS)}) VALUES ({', '.join('?' * len(_COLUMNS))}) "
    f"ON CONFLICT(chat_id) DO UPDATE SET {', '.join(f'{c} = excluded.{c}' for c in _COLUMNS[1:])}"
)


def _from_row(row: aiosqlite.Row) -> ChatSettings:
    return ChatSettings(
        chat_id=row["chat_id"],
        enabled=bool(row["enabled"]),
        reply_mode=ReplyMode(row["reply_mode"]),
        exempt_admins=bool(row["exempt_admins"]),
        exempt_channel=bool(row["exempt_channel"]),
        warn_enabled=bool(row["warn_enabled"]),
        warn_ttl=row["warn_ttl"],
        log_chat_id=row["log_chat_id"],
    )


class ChatSettingsRepo:
    """Настройки чатов. Читаются из БД один раз, дальше берутся из памяти."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._cache: dict[int, ChatSettings] = {}

    async def get(self, chat_id: int) -> ChatSettings:
        if chat_id in self._cache:
            return self._cache[chat_id]
        cursor = await self._db.conn.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
        row = await cursor.fetchone()
        settings = _from_row(row) if row else ChatSettings(chat_id=chat_id)
        self._cache[chat_id] = settings
        return settings

    async def update(self, chat_id: int, **changes: object) -> ChatSettings:
        settings = replace(await self.get(chat_id), **changes)
        await self._db.conn.execute(_UPSERT, [getattr(settings, c) for c in _COLUMNS])
        await self._db.conn.commit()
        self._cache[chat_id] = settings
        return settings


class PostThreadsRepo:
    """ID постов канала, пересланных в группу. Нужны для режима «только ветки постов»."""

    def __init__(self, db: Database) -> None:
        self._db = db

    async def add(self, chat_id: int, message_id: int) -> None:
        await self._db.conn.execute(
            "INSERT OR IGNORE INTO post_threads (chat_id, message_id) VALUES (?, ?)", (chat_id, message_id)
        )
        await self._db.conn.commit()

    async def contains(self, chat_id: int, message_id: int) -> bool:
        cursor = await self._db.conn.execute(
            "SELECT 1 FROM post_threads WHERE chat_id = ? AND message_id = ?", (chat_id, message_id)
        )
        return await cursor.fetchone() is not None
