from aiogram.filters import Filter
from aiogram.types import Message

from bot.config import Config


class IsOwner(Filter):
    async def __call__(self, message: Message, config: Config) -> bool:
        return message.from_user is not None and message.from_user.id in config.owner_ids
