from aiogram import Bot

from bot.config import Config
from bot.services.chat_cache import ChatCache

# Если пользователя нет в кешированном списке админов, список перечитывается,
# но не чаще этого интервала: только что назначенный админ не ждёт полный TTL.
_ADMIN_RECHECK_AGE = 30


async def is_chat_admin(bot: Bot, chat_cache: ChatCache, user_id: int, chat_id: int) -> bool:
    if user_id in (await chat_cache.get(bot, chat_id)).admin_ids:
        return True
    return user_id in (await chat_cache.get(bot, chat_id, max_age=_ADMIN_RECHECK_AGE)).admin_ids


async def can_configure(bot: Bot, config: Config, chat_cache: ChatCache, user_id: int, chat_id: int) -> bool:
    """Владелец бота может настраивать любой разрешённый чат, админ — только свой."""
    if chat_id not in config.allowed_chat_ids:
        return False
    if user_id in config.owner_ids:
        return True
    return await is_chat_admin(bot, chat_cache, user_id, chat_id)
