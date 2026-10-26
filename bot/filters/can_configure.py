from aiogram import Bot
from aiogram.filters import Filter
from aiogram.types import Message

from bot.config import Config
from bot.services.chat_cache import ChatCache
from bot.services.permissions import can_configure


class CanConfigure(Filter):
    """Сообщение в группе от того, кто может её настраивать.

    Если фильтр не прошёл, команда уходит дальше по роутерам и модерируется как обычное сообщение.
    """

    async def __call__(self, message: Message, bot: Bot, config: Config, chat_cache: ChatCache) -> bool:
        if message.sender_chat and message.sender_chat.id == message.chat.id:
            # анонимный админ пишет от имени группы
            return message.chat.id in config.allowed_chat_ids
        if message.from_user is None:
            return False
        return await can_configure(bot, config, chat_cache, message.from_user.id, message.chat.id)
