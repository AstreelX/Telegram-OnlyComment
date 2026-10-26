import asyncio
import logging
from time import monotonic

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)


class Warner:
    """Предупреждения об удалении: не чаще раза в `cooldown` секунд на автора, с автоудалением."""

    def __init__(self, cooldown: float = 30) -> None:
        self._cooldown = cooldown
        self._last: dict[tuple[int, int], float] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    async def warn(self, bot: Bot, chat_id: int, author_id: int, text: str, ttl: int) -> None:
        now = monotonic()
        key = (chat_id, author_id)
        if now - self._last.get(key, float("-inf")) < self._cooldown:
            return
        self._last[key] = now
        if len(self._last) > 10_000:
            self._last = {k: t for k, t in self._last.items() if now - t < self._cooldown}

        try:
            sent = await bot.send_message(chat_id, text)
        except TelegramAPIError as e:
            logger.warning("Не удалось отправить предупреждение в %s: %s", chat_id, e)
            return

        task = asyncio.create_task(self._delete_later(bot, chat_id, sent.message_id, ttl))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @staticmethod
    async def _delete_later(bot: Bot, chat_id: int, message_id: int, ttl: int) -> None:
        await asyncio.sleep(ttl)
        try:
            await bot.delete_message(chat_id, message_id)
        except TelegramAPIError as e:
            logger.debug("Предупреждение %s в %s не удалено: %s", message_id, chat_id, e)
