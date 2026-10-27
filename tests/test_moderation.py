import pytest

from bot.models import ChatSettings, ReplyMode
from bot.services.moderation import MessageFacts, should_delete

ANY = ChatSettings(chat_id=1)
THREAD = ChatSettings(chat_id=1, reply_mode=ReplyMode.THREAD)


@pytest.mark.parametrize(
    ("facts", "settings", "expected"),
    [
        (MessageFacts(), ANY, True),
        (MessageFacts(is_reply=True), ANY, False),
        # ответ на отдельное сообщение админа — не комментарий
        (MessageFacts(is_reply=True, reply_to_top_level=True), ANY, True),
        (MessageFacts(is_reply=True, reply_to_top_level=True, from_admin=True), ANY, False),
        (MessageFacts(is_automatic_forward=True), ANY, False),
        (MessageFacts(is_service=True), ANY, False),
        (MessageFacts(), ChatSettings(chat_id=1, enabled=False), False),
        # исключения
        (MessageFacts(from_admin=True), ANY, False),
        (MessageFacts(from_admin=True), ChatSettings(chat_id=1, exempt_admins=False), True),
        (MessageFacts(from_channel=True), ANY, False),
        (MessageFacts(from_channel=True), ChatSettings(chat_id=1, exempt_channel=False), True),
        # режим thread: ответ вне ветки поста не спасает
        (MessageFacts(is_reply=True), THREAD, True),
        (MessageFacts(is_reply=True, in_post_thread=True), THREAD, False),
        (MessageFacts(in_post_thread=True), THREAD, False),
        (MessageFacts(), THREAD, True),
        (MessageFacts(is_automatic_forward=True), THREAD, False),
    ],
)
def test_should_delete(facts: MessageFacts, settings: ChatSettings, expected: bool) -> None:
    assert should_delete(facts, settings) is expected
