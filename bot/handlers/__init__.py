from aiogram import Router

from bot.handlers import common, membership, moderation, settings

# Порядок важен: модерация последней получает всё, что не забрали команды.
routers: list[Router] = [membership.router, common.router, settings.router, moderation.router]
