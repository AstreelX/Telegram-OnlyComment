"""Решение «удалять или нет». Не зависит от aiogram, чтобы его было легко тестировать."""

from dataclasses import dataclass

from bot.models import ChatSettings, ReplyMode


@dataclass(frozen=True, slots=True)
class MessageFacts:
    is_service: bool = False  # вход/выход участников, закреп и прочие служебные
    is_automatic_forward: bool = False  # пост канала, автоматически пересланный в группу
    is_reply: bool = False
    reply_to_top_level: bool = False  # ответ на сообщение вне веток: не пост и не комментарий
    in_post_thread: bool = False  # сообщение внутри ветки комментариев к посту
    from_admin: bool = False  # админ чата, анонимный админ или владелец бота
    from_channel: bool = False  # от имени связанного канала


def should_delete(facts: MessageFacts, settings: ChatSettings) -> bool:
    if not settings.enabled or facts.is_service or facts.is_automatic_forward:
        return False
    if settings.exempt_admins and facts.from_admin:
        return False
    if settings.exempt_channel and facts.from_channel:
        return False
    if settings.reply_mode is ReplyMode.THREAD:
        return not facts.in_post_thread
    return not facts.is_reply or facts.reply_to_top_level
