"""
Main file that is used to run the bot
"""

import asyncio
import os
import logging
import json

from dotenv import dotenv_values
from aiogram import Dispatcher, Bot

from app.handlers import router

env = dotenv_values()
bot = Bot(token=env['BOT_TOKEN'])
dp = Dispatcher()


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Pressed Ctrl+C. Interrupting...')
