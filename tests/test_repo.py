from collections.abc import AsyncIterator

import pytest

from bot.db.database import Database
from bot.db.repo import ChatSettingsRepo, PostThreadsRepo
from bot.models import ChatSettings, ReplyMode


@pytest.fixture
async def db(tmp_path) -> AsyncIterator[Database]:
    database = await Database.connect(tmp_path / "bot.db")
    yield database
    await database.close()


async def test_defaults_for_unknown_chat(db: Database) -> None:
    assert await ChatSettingsRepo(db).get(-100) == ChatSettings(chat_id=-100)


async def test_update_survives_restart(db: Database, tmp_path) -> None:
    await ChatSettingsRepo(db).update(-100, reply_mode=ReplyMode.THREAD, warn_enabled=True, log_chat_id=42)
    await db.close()

    reopened = await Database.connect(tmp_path / "bot.db")
    settings = await ChatSettingsRepo(reopened).get(-100)
    await reopened.close()

    assert settings.reply_mode is ReplyMode.THREAD
    assert settings.warn_enabled is True
    assert settings.log_chat_id == 42


async def test_post_threads(db: Database) -> None:
    posts = PostThreadsRepo(db)
    await posts.add(-100, 7)
    await posts.add(-100, 7)
    assert await posts.contains(-100, 7)
    assert not await posts.contains(-100, 8)
    assert not await posts.contains(-200, 7)
