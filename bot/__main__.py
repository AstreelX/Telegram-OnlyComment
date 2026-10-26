import asyncio
import contextlib
import logging
import sys

from pydantic import ValidationError

from bot.app import create_bot, create_dispatcher
from bot.config import Config
from bot.db.database import Database
from bot.runners.polling import run_polling
from bot.runners.webhook import run_webhook

logger = logging.getLogger("bot")


async def main(config: Config) -> None:
    if not config.allowed_chat_ids:
        logger.warning("ALLOWED_CHAT_IDS пуст: бот нигде не будет модерировать")
    if not config.owner_ids:
        logger.warning("OWNER_IDS пуст: настраивать чаты смогут только их админы")

    db = await Database.connect(config.db_path)
    bot = create_bot(config)
    dp = create_dispatcher(config, db)
    logger.info("Запуск в режиме %s", config.mode)
    try:
        if config.mode == "webhook":
            await run_webhook(bot, dp, config)
        else:
            await run_polling(bot, dp, config)
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    try:
        config = Config()
    except ValidationError as e:
        sys.exit(f"Ошибка в .env:\n{e}")

    logging.basicConfig(level=config.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main(config))
