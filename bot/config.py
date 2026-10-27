from pathlib import Path
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr
    owner_ids: Annotated[frozenset[int], NoDecode] = frozenset()
    allowed_chat_ids: Annotated[frozenset[int], NoDecode] = frozenset()

    db_path: Path = Path("data/bot.db")
    log_level: str = "INFO"
    # Прокси для запросов к Telegram: http://..., socks5://user:pass@host:port
    proxy: SecretStr = SecretStr("")

    mode: Literal["polling", "webhook"] = "polling"
    drop_pending_updates: bool = False

    webhook_base_url: str = ""
    webhook_path: str = "/tg/webhook"
    webhook_secret: SecretStr = SecretStr("")
    webapp_host: str = "0.0.0.0"
    webapp_port: int = 8080

    @field_validator("owner_ids", "allowed_chat_ids", mode="before")
    @classmethod
    def _split_ids(cls, value: object) -> object:
        # В .env списки пишутся как "1, 2, 3", а не JSON
        if isinstance(value, str):
            return frozenset(int(part) for part in value.split(",") if part.strip())
        return value

    @model_validator(mode="after")
    def _check_webhook(self) -> "Config":
        if self.mode == "webhook":
            if not self.webhook_base_url.startswith("https://"):
                raise ValueError("MODE=webhook требует WEBHOOK_BASE_URL вида https://...")
            if not self.webhook_path.startswith("/"):
                raise ValueError("WEBHOOK_PATH должен начинаться с /")
        return self

    @property
    def webhook_url(self) -> str:
        return self.webhook_base_url.rstrip("/") + self.webhook_path
