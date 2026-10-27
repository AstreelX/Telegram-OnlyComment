import logging
from dataclasses import dataclass
from time import monotonic

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ChatInfo:
    title: str
    linked_chat_id: int | None
    admin_ids: frozenset[int]
    fetched_at: float


class ChatCache:
    """Название, связанный канал и админы чата. Обновляются не чаще раза в `ttl` секунд."""

    def __init__(self, ttl: float = 300) -> None:
        self._ttl = ttl
        self._items: dict[int, ChatInfo] = {}

    async def get(self, bot: Bot, chat_id: int, max_age: float | None = None) -> ChatInfo:
        info = self._items.get(chat_id)
        limit = self._ttl if max_age is None else max_age
        if info and monotonic() - info.fetched_at < limit:
            return info

        try:
            chat = await bot.get_chat(chat_id)
            admins = await bot.get_chat_administrators(chat_id)
        except TelegramAPIError as e:
            logger.warning("Не удалось получить данные чата %s: %s", chat_id, e)
            if info is None:
                info = ChatInfo(str(chat_id), None, frozenset(), monotonic())
                self._items[chat_id] = info
            return info

        info = ChatInfo(
            title=chat.title or str(chat_id),
            linked_chat_id=chat.linked_chat_id,
            admin_ids=frozenset(member.user.id for member in admins),
            fetched_at=monotonic(),
        )
        self._items[chat_id] = info
        return info

    def forget(self, chat_id: int) -> None:
        """Следующий `get` перечитает данные чата, например после смены админов."""
        self._items.pop(chat_id, None)
