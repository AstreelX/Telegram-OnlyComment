import logging
from html import escape

from aiogram import Bot, Router
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from bot import texts
from bot.config import Config
from bot.db.repo import PostThreadsRepo
from bot.filters import IN_GROUP, AllowedChat
from bot.middlewares.settings import ChatSettingsMiddleware
from bot.models import ChatSettings
from bot.services.chat_cache import ChatCache
from bot.services.moderation import MessageFacts, should_delete
from bot.services.permissions import is_chat_admin
from bot.services.warnings import Warner

logger = logging.getLogger(__name__)

router = Router(name="moderation")
router.message.filter(IN_GROUP, AllowedChat())
router.message.middleware(ChatSettingsMiddleware())

# Всё остальное — служебные сообщения (вход участников, закреп и т. п.), их не трогаем.
USER_CONTENT = frozenset({
    ContentType.TEXT, ContentType.ANIMATION, ContentType.AUDIO, ContentType.DOCUMENT,
    ContentType.LIVE_PHOTO, ContentType.PAID_MEDIA, ContentType.PHOTO, ContentType.STICKER,
    ContentType.STORY, ContentType.VIDEO, ContentType.VIDEO_NOTE, ContentType.VOICE,
    ContentType.CHECKLIST, ContentType.CONTACT, ContentType.DICE, ContentType.GAME,
    ContentType.POLL, ContentType.VENUE, ContentType.LOCATION, ContentType.RICH_MESSAGE,
})  # fmt: skip


@router.message()
async def moderate(
    message: Message,
    bot: Bot,
    config: Config,
    chat_settings: ChatSettings,
    chat_cache: ChatCache,
    posts: PostThreadsRepo,
    warner: Warner,
) -> None:
    if message.is_automatic_forward:
        await posts.add(message.chat.id, message.message_id)
        return
    if not chat_settings.enabled:
        return

    facts = await _collect_facts(message, bot, config, chat_settings, chat_cache, posts)
    if not should_delete(facts, chat_settings):
        return

    try:
        await message.delete()
    except TelegramAPIError as e:
        logger.warning("Не удалось удалить %s в %s: %s", message.message_id, message.chat.id, e)
        return

    author = _author_html(message)
    if chat_settings.warn_enabled:
        warning = texts.WARNING.format(author=author)
        await warner.warn(bot, message.chat.id, _author_id(message), warning, chat_settings.warn_ttl)
    if chat_settings.log_chat_id:
        await _report(bot, chat_settings.log_chat_id, message, author)


async def _collect_facts(
    message: Message,
    bot: Bot,
    config: Config,
    settings: ChatSettings,
    chat_cache: ChatCache,
    posts: PostThreadsRepo,
) -> MessageFacts:
    chat_id = message.chat.id
    sender_chat = message.sender_chat
    user_id = message.from_user.id if message.from_user else None

    from_admin = (
        (sender_chat is not None and sender_chat.id == chat_id)  # анонимный админ
        or user_id in config.owner_ids
        or (
            settings.exempt_admins
            and sender_chat is None
            and user_id is not None
            and await is_chat_admin(bot, chat_cache, user_id, chat_id)
        )
    )
    # Только связанный канал: от имени своего канала может писать любой участник
    from_channel = (
        settings.exempt_channel
        and sender_chat is not None
        and sender_chat.id == (await chat_cache.get(bot, chat_id)).linked_chat_id
    )
    reply = message.reply_to_message

    return MessageFacts(
        is_service=message.content_type not in USER_CONTENT,
        is_reply=reply is not None,
        # Пост канала и комментарии лежат в ветке, а отдельные сообщения админов,
        # связанного канала и служебные — нет. Ответы на них уводили бы разговор из комментариев.
        reply_to_top_level=reply is not None and not reply.is_automatic_forward and reply.message_thread_id is None,
        in_post_thread=await _in_post_thread(message, posts),
        from_admin=from_admin,
        from_channel=from_channel,
    )


async def _in_post_thread(message: Message, posts: PostThreadsRepo) -> bool:
    reply = message.reply_to_message
    if reply is not None and reply.is_automatic_forward:
        await posts.add(message.chat.id, reply.message_id)
        return True
    thread_id = message.message_thread_id or (reply.message_thread_id if reply else None)
    return thread_id is not None and await posts.contains(message.chat.id, thread_id)


def _author_html(message: Message) -> str:
    # При sender_chat в from_user лежит служебный бот Telegram, а не человек
    if message.sender_chat:
        return escape(message.sender_chat.title or str(message.sender_chat.id))
    if message.from_user:
        return message.from_user.mention_html()
    return "неизвестно"


def _author_id(message: Message) -> int:
    if message.sender_chat:
        return message.sender_chat.id
    return message.from_user.id if message.from_user else 0


async def _report(bot: Bot, log_chat_id: int, message: Message, author: str) -> None:
    content = (message.text or message.caption or "")[:500]
    text = texts.LOG_ENTRY.format(
        chat=escape(message.chat.title or str(message.chat.id)),
        author=author,
        content_type=message.content_type.value,
        text=f"<blockquote>{escape(content)}</blockquote>" if content else "",
    )
    try:
        await bot.send_message(log_chat_id, text)
    except TelegramAPIError as e:
        logger.warning("Не удалось записать в журнал %s: %s", log_chat_id, e)
