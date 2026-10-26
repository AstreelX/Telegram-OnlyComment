from aiogram import F
from aiogram.enums import ChatType

from bot.filters.allowed_chat import AllowedChat
from bot.filters.can_configure import CanConfigure
from bot.filters.owner import IsOwner

IN_GROUP = F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})
IN_PRIVATE = F.chat.type == ChatType.PRIVATE

__all__ = ["IN_GROUP", "IN_PRIVATE", "AllowedChat", "CanConfigure", "IsOwner"]
