from html import escape

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot import texts
from bot.config import Config
from bot.filters import IN_GROUP, IN_PRIVATE, CanConfigure, IsOwner
from bot.services.chat_cache import ChatCache

router = Router(name="common")


@router.message(CommandStart(), IN_PRIVATE)
@router.message(Command("help"), IN_PRIVATE)
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP)


@router.message(Command("whereami"), IN_PRIVATE)
async def cmd_whereami_private(message: Message) -> None:
    await message.answer(texts.YOUR_ID.format(user_id=message.from_user.id))


@router.message(Command("whereami"), IN_GROUP, CanConfigure())
async def cmd_whereami_group(message: Message) -> None:
    await message.reply(texts.CHAT_ID.format(chat_id=message.chat.id))


@router.message(Command("status"), IN_PRIVATE, IsOwner())
async def cmd_status(message: Message, bot: Bot, config: Config, chat_cache: ChatCache) -> None:
    lines = [texts.STATUS_HEADER.format(mode=config.mode, count=len(config.allowed_chat_ids)), ""]
    if not config.allowed_chat_ids:
        lines.append(texts.STATUS_NO_CHATS)
    for chat_id in sorted(config.allowed_chat_ids):
        try:
            member = await bot.get_chat_member(chat_id, bot.id)
        except TelegramAPIError:
            lines.append(texts.STATUS_CHAT_ERROR.format(chat_id=chat_id))
            continue
        title = escape((await chat_cache.get(bot, chat_id)).title)
        line = texts.STATUS_CHAT_OK if getattr(member, "can_delete_messages", False) else texts.STATUS_CHAT_NO_RIGHTS
        lines.append(line.format(title=title, chat_id=chat_id))
    await message.answer("\n".join(lines))
