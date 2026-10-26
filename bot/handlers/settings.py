from html import escape

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot import texts
from bot.config import Config
from bot.db.repo import ChatSettingsRepo
from bot.filters import IN_GROUP, IN_PRIVATE, CanConfigure
from bot.keyboards.settings import SettingsCb, chats_keyboard, settings_keyboard
from bot.models import WARN_TTL_CHOICES, ChatSettings, ReplyMode
from bot.services.chat_cache import ChatCache
from bot.services.permissions import can_configure

router = Router(name="settings")

_TOGGLES = {"enabled", "exempt_admins", "exempt_channel", "warn_enabled"}


async def _menu(
    bot: Bot, repo: ChatSettingsRepo, chat_cache: ChatCache, chat_id: int, in_private: bool
) -> tuple[str, InlineKeyboardMarkup]:
    settings = await repo.get(chat_id)
    info = await chat_cache.get(bot, chat_id)
    return texts.settings_text(settings, info.title), settings_keyboard(settings, in_private)


async def _available_chats(bot: Bot, config: Config, chat_cache: ChatCache, user_id: int) -> list[tuple[int, str]]:
    chats = []
    for chat_id in sorted(config.allowed_chat_ids):
        if await can_configure(bot, config, chat_cache, user_id, chat_id):
            chats.append((chat_id, (await chat_cache.get(bot, chat_id)).title))
    return chats


async def _edit(message: Message, text: str, markup: InlineKeyboardMarkup) -> None:
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


# --- меню ---


@router.message(Command("settings"), IN_GROUP, CanConfigure())
async def settings_in_group(message: Message, bot: Bot, repo: ChatSettingsRepo, chat_cache: ChatCache) -> None:
    text, markup = await _menu(bot, repo, chat_cache, message.chat.id, in_private=False)
    await message.answer(text, reply_markup=markup)


@router.message(Command("settings"), IN_PRIVATE)
async def settings_in_private(
    message: Message, bot: Bot, config: Config, repo: ChatSettingsRepo, chat_cache: ChatCache
) -> None:
    chats = await _available_chats(bot, config, chat_cache, message.from_user.id)
    if not chats:
        await message.answer(texts.NO_CHATS)
    elif len(chats) == 1:
        text, markup = await _menu(bot, repo, chat_cache, chats[0][0], in_private=True)
        await message.answer(text, reply_markup=markup)
    else:
        await message.answer(texts.CHOOSE_CHAT, reply_markup=chats_keyboard(chats))


@router.callback_query(SettingsCb.filter())
async def on_settings_button(
    query: CallbackQuery,
    callback_data: SettingsCb,
    bot: Bot,
    config: Config,
    repo: ChatSettingsRepo,
    chat_cache: ChatCache,
) -> None:
    message = query.message
    if not isinstance(message, Message):
        await query.answer(texts.MESSAGE_GONE, show_alert=True)
        return
    in_private = message.chat.type == "private"
    user_id = query.from_user.id
    action = callback_data.action
    chat_id = callback_data.chat_id

    if action == "list" and in_private:
        chats = await _available_chats(bot, config, chat_cache, user_id)
        await _edit(message, texts.CHOOSE_CHAT if chats else texts.NO_CHATS, chats_keyboard(chats))
        await query.answer()
        return

    # Права проверяются на каждое нажатие: кнопку в группе может нажать кто угодно
    if not (action == "close" and in_private) and not await can_configure(bot, config, chat_cache, user_id, chat_id):
        await query.answer(texts.NO_RIGHTS, show_alert=True)
        return

    if action == "close":
        try:
            await message.delete()
        except TelegramBadRequest:
            await message.edit_reply_markup(reply_markup=None)
        await query.answer()
        return

    settings = await repo.get(chat_id)
    changes = _changes_for(action, settings, in_private, user_id)
    if changes is None and action != "open":
        await query.answer()
        return
    if changes:
        await repo.update(chat_id, **changes)

    text, markup = await _menu(bot, repo, chat_cache, chat_id, in_private)
    await _edit(message, text, markup)
    await query.answer()


def _changes_for(action: str, s: ChatSettings, in_private: bool, user_id: int) -> dict[str, object] | None:
    if action in _TOGGLES:
        return {action: not getattr(s, action)}
    if action == "reply_mode":
        return {"reply_mode": ReplyMode.THREAD if s.reply_mode is ReplyMode.ANY else ReplyMode.ANY}
    if action == "warn_ttl":
        later = [t for t in WARN_TTL_CHOICES if t > s.warn_ttl]
        return {"warn_ttl": later[0] if later else WARN_TTL_CHOICES[0]}
    if action == "log_here" and in_private:
        return {"log_chat_id": user_id}
    if action == "log_off":
        return {"log_chat_id": None}
    return None


# --- команды в группе ---


@router.message(Command("on", "off"), IN_GROUP, CanConfigure())
async def cmd_on_off(message: Message, command: CommandObject, repo: ChatSettingsRepo) -> None:
    enabled = command.command == "on"
    await repo.update(message.chat.id, enabled=enabled)
    await message.reply(texts.ENABLED if enabled else texts.DISABLED)


@router.message(Command("mode"), IN_GROUP, CanConfigure())
async def cmd_mode(message: Message, command: CommandObject, repo: ChatSettingsRepo) -> None:
    try:
        mode = ReplyMode((command.args or "").strip().lower())
    except ValueError:
        await message.reply(texts.MODE_USAGE)
        return
    await repo.update(message.chat.id, reply_mode=mode)
    await message.reply(texts.MODE_SET.format(mode=texts.MODE_NAMES[mode]))


@router.message(Command("warn"), IN_GROUP, CanConfigure())
async def cmd_warn(message: Message, command: CommandObject, repo: ChatSettingsRepo) -> None:
    arg = (command.args or "").strip().lower()
    if arg == "off":
        await repo.update(message.chat.id, warn_enabled=False)
        await message.reply(texts.WARN_OFF)
        return
    if arg == "on":
        settings = await repo.update(message.chat.id, warn_enabled=True)
    elif arg.isdigit() and 1 <= int(arg) <= 300:
        settings = await repo.update(message.chat.id, warn_enabled=True, warn_ttl=int(arg))
    else:
        await message.reply(texts.WARN_USAGE)
        return
    await message.reply(texts.WARN_ON.format(ttl=settings.warn_ttl))


@router.message(Command("logchat"), IN_GROUP, CanConfigure())
async def cmd_logchat(message: Message, command: CommandObject, bot: Bot, repo: ChatSettingsRepo) -> None:
    arg = (command.args or "").strip().lower()
    if arg == "off":
        await repo.update(message.chat.id, log_chat_id=None)
        await message.reply(texts.LOG_OFF)
        return
    try:
        log_chat_id = int(arg)
    except ValueError:
        await message.reply(texts.LOG_USAGE)
        return
    try:
        title = escape(message.chat.title or str(message.chat.id))
        await bot.send_message(log_chat_id, texts.LOG_TEST.format(title=title))
    except TelegramAPIError:
        await message.reply(texts.LOG_UNREACHABLE.format(chat_id=log_chat_id))
        return
    await repo.update(message.chat.id, log_chat_id=log_chat_id)
    await message.reply(texts.LOG_SET.format(chat_id=log_chat_id))
