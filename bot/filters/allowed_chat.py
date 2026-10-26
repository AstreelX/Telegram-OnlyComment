from aiogram.filters import Filter
from aiogram.types import Message

from bot.config import Config


class AllowedChat(Filter):
    async def __call__(self, message: Message, config: Config) -> bool:
        return message.chat.id in config.allowed_chat_ids
