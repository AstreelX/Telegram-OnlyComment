from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllChatAdministrators, BotCommandScopeAllPrivateChats

from bot.config import Config
from bot.db.database import Database
from bot.db.repo import ChatSettingsRepo, PostThreadsRepo
from bot.handlers import routers
from bot.services.chat_cache import ChatCache
from bot.services.warnings import Warner

PRIVATE_COMMANDS = [
    BotCommand(command="settings", description="Настройки чатов"),
    BotCommand(command="whereami", description="Мой user ID"),
    BotCommand(command="status", description="Состояние бота (владельцам)"),
    BotCommand(command="help", description="Что умеет бот"),
]
ADMIN_COMMANDS = [
    BotCommand(command="settings", description="Меню настроек"),
    BotCommand(command="on", description="Включить модерацию"),
    BotCommand(command="off", description="Выключить модерацию"),
    BotCommand(command="mode", description="any или thread"),
    BotCommand(command="warn", description="on, off или секунды"),
    BotCommand(command="logchat", description="ID чата журнала или off"),
    BotCommand(command="whereami", description="ID этого чата"),
]


def create_bot(config: Config) -> Bot:
    return Bot(
        config.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )


def create_dispatcher(config: Config, db: Database) -> Dispatcher:
    # Эти объекты aiogram передаёт в хендлеры и фильтры по имени аргумента
    dp = Dispatcher(
        config=config,
        repo=ChatSettingsRepo(db),
        posts=PostThreadsRepo(db),
        chat_cache=ChatCache(),
        warner=Warner(),
    )
    dp.include_routers(*routers)
    dp.startup.register(_set_commands)
    return dp


async def _set_commands(bot: Bot) -> None:
    await bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeAllChatAdministrators())
