import pytest
import pytest_asyncio
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from mocked_bot import MockedBot

@pytest.fixture(scope="session")
def bot():
    return MockedBot()

@pytest_asyncio.fixture(scope="session")
async def dispatcher():
    dp = Dispatcher()
    await dp.emit_startup()
    try:
        yield dp
    finally:
        await dp.emit_shutdown()

@pytest_asyncio.fixture(scope="session")
async def memory_storage():
    storage = MemoryStorage()
    try:
        yield storage
    finally:
        await storage.close()