"""
Module providing class that can be used to interact with database.
"""
from typing import Optional
from aiogram import Dispatcher, Bot, BaseMiddleware
from aiogram import types
from aiogram.fsm.context import FSMContext

import json
import os

from database.query import init_pool, connection_pool
from app.handlers import router

async def main():
    await init_pool()
    async with connection_pool.connection():
        print("Got the connection")
        pass
    token = os.environ.get("BOT_TOKEN")
    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
