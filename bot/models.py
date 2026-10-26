from dataclasses import dataclass
from enum import StrEnum


class ReplyMode(StrEnum):
    ANY = "any"  # ответ на любое сообщение
    THREAD = "thread"  # только внутри ветки комментариев к посту


WARN_TTL_CHOICES = (5, 10, 30, 60)


@dataclass(frozen=True, slots=True)
class ChatSettings:
    chat_id: int
    enabled: bool = True
    reply_mode: ReplyMode = ReplyMode.ANY
    exempt_admins: bool = True
    exempt_channel: bool = True
    warn_enabled: bool = False
    warn_ttl: int = 10
    log_chat_id: int | None = None
