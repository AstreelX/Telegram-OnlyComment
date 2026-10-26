import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import JOIN_TRANSITION, ChatMemberUpdatedFilter
from aiogram.types import ChatMemberUpdated, Message

from bot import texts
from bot.config import Config
from bot.filters import IN_GROUP, AllowedChat

logger = logging.getLogger(__name__)

router = Router(name="membership")


async def _notify_owners(bot: Bot, config: Config, text: str) -> None:
    for owner_id in config.owner_ids:
        try:
            await bot.send_message(owner_id, text)
        except TelegramAPIError as e:
            # Владелец ещё не писал боту /start
            logger.warning("Не удалось написать владельцу %s: %s", owner_id, e)


@router.my_chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION), IN_GROUP)
async def on_bot_added(event: ChatMemberUpdated, bot: Bot, config: Config) -> None:
    if event.chat.id in config.allowed_chat_ids:
        return
    logger.info("Добавлен в чужой чат %s, выхожу", event.chat.id)
    title = escape(event.chat.title or str(event.chat.id))
    await _notify_owners(bot, config, texts.LEFT_UNKNOWN_CHAT.format(title=title, chat_id=event.chat.id))
    try:
        await bot.leave_chat(event.chat.id)
    except TelegramAPIError as e:
        logger.warning("Не удалось выйти из %s: %s", event.chat.id, e)


@router.message(F.migrate_to_chat_id, IN_GROUP, AllowedChat())
async def on_migrated(message: Message, bot: Bot, config: Config) -> None:
    title = escape(message.chat.title or str(message.chat.id))
    text = texts.CHAT_MIGRATED.format(title=title, old_id=message.chat.id, new_id=message.migrate_to_chat_id)
    await _notify_owners(bot, config, text)
