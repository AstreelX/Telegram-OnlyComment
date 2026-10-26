"""Апдейты проходят через настоящий Dispatcher. Сеть подменена фейковой сессией."""

from collections.abc import AsyncGenerator, AsyncIterator
from itertools import count
from typing import Any

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import DeleteMessage, SendMessage, TelegramMethod
from aiogram.types import Chat, Message, Update

from bot.app import create_dispatcher
from bot.config import Config
from bot.db.database import Database
from bot.db.repo import ChatSettingsRepo, PostThreadsRepo
from bot.models import ReplyMode
from bot.services.chat_cache import ChatInfo
from bot.services.warnings import Warner

CHAT = -1001
CHANNEL = -1002
ADMIN = 10
USER = 20

_ids = count(1)


class FakeSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []

    async def make_request(self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None) -> Any:
        self.calls.append(method)
        if isinstance(method, SendMessage):
            return Message(message_id=next(_ids), date=0, chat=Chat(id=method.chat_id, type="group"), text=method.text)
        return True

    async def stream_content(self, *args: Any, **kwargs: Any) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError
        yield b""

    async def close(self) -> None:
        pass

    def of(self, kind: type) -> list[Any]:
        return [c for c in self.calls if isinstance(c, kind)]


class StubChatCache:
    async def get(self, bot: Bot, chat_id: int, max_age: float | None = None) -> ChatInfo:
        return ChatInfo("Обсуждения", CHANNEL, frozenset({ADMIN}), 0)


@pytest.fixture(scope="module")
def dispatcher() -> Dispatcher:
    # Роутеры модульные и подключаются к диспетчеру один раз, поэтому он общий для всех тестов
    config = Config(_env_file=None, bot_token="42:TEST", allowed_chat_ids=str(CHAT), owner_ids="1")
    return create_dispatcher(config, db=None)  # type: ignore[arg-type]


@pytest.fixture
async def env(dispatcher: Dispatcher) -> AsyncIterator[tuple[Dispatcher, Bot, FakeSession]]:
    db = await Database.connect(":memory:")
    dispatcher["repo"] = ChatSettingsRepo(db)
    dispatcher["posts"] = PostThreadsRepo(db)
    dispatcher["warner"] = Warner()
    dispatcher["chat_cache"] = StubChatCache()
    session = FakeSession()
    yield dispatcher, Bot("42:TEST", session=session), session
    await db.close()


def _msg(chat_id: int = CHAT, user_id: int = USER, text: str = "привет", **extra: Any) -> Update:
    message = {
        "message_id": next(_ids),
        "date": 0,
        "chat": {"id": chat_id, "type": "supergroup", "title": "Обсуждения"},
        "from": {"id": user_id, "is_bot": False, "first_name": "Тест"},
        "text": text,
        **extra,
    }
    if text.startswith("/"):
        message["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
    return Update(update_id=next(_ids), message=message)


def _reply_to(message_id: int, **extra: Any) -> dict[str, Any]:
    return {
        "message_id": message_id,
        "date": 0,
        "chat": {"id": CHAT, "type": "supergroup"},
        "text": "...",
        **extra,
    }


async def test_non_reply_deleted(env) -> None:
    dp, bot, session = env
    await dp.feed_update(bot, _msg())
    assert len(session.of(DeleteMessage)) == 1


async def test_reply_kept(env) -> None:
    dp, bot, session = env
    await dp.feed_update(bot, _msg(reply_to_message=_reply_to(5)))
    assert not session.of(DeleteMessage)


async def test_unknown_chat_ignored(env) -> None:
    dp, bot, session = env
    await dp.feed_update(bot, _msg(chat_id=-999))
    assert not session.calls


async def test_admin_kept(env) -> None:
    dp, bot, session = env
    await dp.feed_update(bot, _msg(user_id=ADMIN))
    assert not session.of(DeleteMessage)


async def test_linked_channel_kept_other_channel_deleted(env) -> None:
    dp, bot, session = env
    await dp.feed_update(bot, _msg(sender_chat={"id": CHANNEL, "type": "channel", "title": "Канал"}))
    assert not session.of(DeleteMessage)
    await dp.feed_update(bot, _msg(sender_chat={"id": -5555, "type": "channel", "title": "Чужой"}))
    assert len(session.of(DeleteMessage)) == 1


async def test_command_from_user_is_moderated(env) -> None:
    dp, bot, session = env
    await dp.feed_update(bot, _msg(text="/off"))
    assert len(session.of(DeleteMessage)) == 1
    assert (await dp["repo"].get(CHAT)).enabled


async def test_command_from_admin_changes_settings(env) -> None:
    dp, bot, session = env
    await dp.feed_update(bot, _msg(user_id=ADMIN, text="/off"))
    assert not (await dp["repo"].get(CHAT)).enabled
    assert session.of(SendMessage)

    await dp.feed_update(bot, _msg())
    assert not session.of(DeleteMessage)


async def test_thread_mode(env) -> None:
    dp, bot, session = env
    await dp["repo"].update(CHAT, reply_mode=ReplyMode.THREAD)

    post = _msg(sender_chat={"id": CHANNEL, "type": "channel", "title": "Канал"}, is_automatic_forward=True)
    await dp.feed_update(bot, post)
    post_id = post.message.message_id

    # ответ на комментарий внутри ветки поста
    await dp.feed_update(bot, _msg(message_thread_id=post_id, reply_to_message=_reply_to(post_id + 100)))
    assert not session.of(DeleteMessage)

    # ответ на сообщение вне веток постов
    await dp.feed_update(bot, _msg(message_thread_id=777, reply_to_message=_reply_to(777)))
    assert len(session.of(DeleteMessage)) == 1


async def test_warning_and_log(env) -> None:
    dp, bot, session = env
    await dp["repo"].update(CHAT, warn_enabled=True, warn_ttl=60, log_chat_id=1)
    await dp.feed_update(bot, _msg(text="спам"))
    sent = session.of(SendMessage)
    assert [m.chat_id for m in sent] == [CHAT, 1]
    assert "спам" in sent[1].text


def _press(user_id: int, action: str) -> Update:
    from bot.keyboards.settings import SettingsCb

    return Update(
        update_id=next(_ids),
        callback_query={
            "id": str(next(_ids)),
            "from": {"id": user_id, "is_bot": False, "first_name": "Тест"},
            "chat_instance": "x",
            "data": SettingsCb(action=action, chat_id=CHAT).pack(),
            "message": _reply_to(next(_ids), date=1),
        },
    )


async def test_settings_button_by_admin(env) -> None:
    dp, bot, session = env
    await dp.feed_update(bot, _press(ADMIN, "warn_enabled"))
    await dp.feed_update(bot, _press(ADMIN, "warn_ttl"))
    settings = await dp["repo"].get(CHAT)
    assert settings.warn_enabled and settings.warn_ttl == 30


async def test_settings_button_by_user_denied(env) -> None:
    from aiogram.methods import AnswerCallbackQuery

    dp, bot, session = env
    await dp.feed_update(bot, _press(USER, "enabled"))
    assert (await dp["repo"].get(CHAT)).enabled
    assert session.of(AnswerCallbackQuery)[0].show_alert
