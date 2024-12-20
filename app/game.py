"""
Module providing class that can be used to interact with database.
"""
from typing import Optional
from aiogram import Dispatcher, Bot

import os

from database.query import init_pool, connection_pool
from app.handlers import router
from app.middleware import SignalMiddleware
from database import wrappers as wr

token = os.environ.get("BOT_TOKEN")
bot = Bot(token=token)
dp = Dispatcher()

async def main():
    lobby_ids = await wr.Lobby.lobby_ids()
    dp.update.middleware(SignalMiddleware(lobby_ids))
    dp.include_router(router)
    await dp.start_polling(bot)
