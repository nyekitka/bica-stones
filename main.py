import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from database.query import init_pool, connection_pool
from database.wrappers import User
from app.game import main
from data.exception import init_exceptions
import uvicorn
from api_utils.api import app


async def start_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=5000)
    server = uvicorn.Server(config)
    await server.serve()


async def entrypoint():
    await init_pool()
    async with connection_pool.connection():
        logging.info("Got the connection to DB")
        pass
    supreme_admin_id = os.getenv('SUPREME_ADMIN_ID')
    if supreme_admin_id:
        try:
            user = await User.add_or_get(int(supreme_admin_id), 'admin')
            if user.status() != 'admin':
                await user.set_status('admin')
            User.SUPREME_ADMIN_ID = supreme_admin_id
        except ValueError:
            logging.error('tg_id of supreme_admin has incorrect format')
    await asyncio.gather(main(), start_server())


if __name__ == '__main__':
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    init_exceptions()
    load_dotenv()
    logging.basicConfig(level='DEBUG')

    try:
        asyncio.run(entrypoint())
    except KeyboardInterrupt:
        print('Pressed Ctrl+C. Interrupting...')
