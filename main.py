import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from app.game import main
from data.exception import init_exceptions

if __name__ == '__main__':
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    init_exceptions()
    load_dotenv()
    logging.basicConfig(level='DEBUG')
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Pressed Ctrl+C. Interrupting...')
