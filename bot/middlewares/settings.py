from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.db.repo import ChatSettingsRepo


class ChatSettingsMiddleware(BaseMiddleware):
    """Кладёт настройки чата в аргумент хендлера `chat_settings`."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        repo: ChatSettingsRepo = data["repo"]
        data["chat_settings"] = await repo.get(event.chat.id)
        return await handler(event, data)
