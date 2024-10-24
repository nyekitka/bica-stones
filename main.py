import asyncio
import logging
import os

from dotenv import load_dotenv

from app.game import main
from data.exception import init_exceptions

if __name__ == '__main__':
    init_exceptions()
    load_dotenv()
    logging.basicConfig(level=os.getenv('LOG_LEVEL'))
    asyncio.get_event_loop().run_until_complete(main())
