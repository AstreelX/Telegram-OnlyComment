import asyncio
import logging
import secrets

from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.config import Config

logger = logging.getLogger(__name__)


async def run_webhook(bot: Bot, dp: Dispatcher, config: Config) -> None:
    # Telegram присылает секрет в заголовке X-Telegram-Bot-Api-Secret-Token,
    # запросы без него SimpleRequestHandler отклоняет с 401
    secret = config.webhook_secret.get_secret_value() or secrets.token_urlsafe(32)

    async def on_startup(bot: Bot) -> None:
        await bot.set_webhook(
            config.webhook_url,
            secret_token=secret,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=config.drop_pending_updates,
        )
        logger.info("Webhook установлен: %s", config.webhook_url)

    async def health(_: web.Request) -> web.Response:
        return web.Response(text="OK")

    dp.startup.register(on_startup)

    app = web.Application()
    app.router.add_get("/health", health)
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=secret).register(app, path=config.webhook_path)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, config.webapp_host, config.webapp_port).start()
    logger.info("Слушаю %s:%s%s", config.webapp_host, config.webapp_port, config.webhook_path)
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
