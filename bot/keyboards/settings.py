from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import texts
from bot.models import ChatSettings


class SettingsCb(CallbackData, prefix="cfg"):
    # open, list, close, log_here, log_off, warn_ttl, reply_mode
    # или имя булевой настройки, которую нужно переключить
    action: str
    chat_id: int = 0


def settings_keyboard(s: ChatSettings, in_private: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    def add(text: str, action: str) -> None:
        b.button(text=text, callback_data=SettingsCb(action=action, chat_id=s.chat_id))

    add(texts.BTN_ENABLED.format(flag=texts.flag(s.enabled)), "enabled")
    add(texts.BTN_MODE.format(mode=texts.MODE_NAMES[s.reply_mode]), "reply_mode")
    add(texts.BTN_EXEMPT_ADMINS.format(flag=texts.flag(s.exempt_admins)), "exempt_admins")
    add(texts.BTN_EXEMPT_CHANNEL.format(flag=texts.flag(s.exempt_channel)), "exempt_channel")
    add(texts.BTN_WARN.format(flag=texts.flag(s.warn_enabled)), "warn_enabled")
    if s.warn_enabled:
        add(texts.BTN_WARN_TTL.format(ttl=s.warn_ttl), "warn_ttl")
    if s.log_chat_id:
        add(texts.BTN_LOG_OFF, "log_off")
    elif in_private:
        add(texts.BTN_LOG_HERE, "log_here")
    if in_private:
        add(texts.BTN_BACK, "list")
    add(texts.BTN_CLOSE, "close")

    b.adjust(1)
    return b.as_markup()


def chats_keyboard(chats: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for chat_id, title in chats:
        b.button(text=title, callback_data=SettingsCb(action="open", chat_id=chat_id))
    b.button(text=texts.BTN_CLOSE, callback_data=SettingsCb(action="close"))
    b.adjust(1)
    return b.as_markup()
