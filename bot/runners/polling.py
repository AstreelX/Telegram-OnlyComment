from aiogram import Bot, Dispatcher

from bot.config import Config


async def run_polling(bot: Bot, dp: Dispatcher, config: Config) -> None:
    # Пока у бота стоит webhook, Telegram не отдаёт обновления через getUpdates
    await bot.delete_webhook(drop_pending_updates=config.drop_pending_updates)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
