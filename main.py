import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from app.game import main
from data.exception import init_exceptions
import uvicorn
from api_utils.api import app


async def start_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=5000)
    server = uvicorn.Server(config)
    logging.info('CHECK')
    await server.serve()


async def main2():
    await asyncio.gather(main(), start_server())


if __name__ == '__main__':
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    init_exceptions()
    load_dotenv()
    logging.basicConfig(level='DEBUG')
    logging.info('checked')

    try:
        asyncio.run(main2())
    except KeyboardInterrupt:
        print('Pressed Ctrl+C. Interrupting...')
