import pytest
import pytest_mock
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from utils import TEST_USER, TEST_USER_CHAT, TEST_MESSAGE
from app.handlers import start

class TestMessageHandlers:
    @pytest_asyncio
    @pytest.mark.parametrize(
        ["is_admin", "lobby", "res"],
        [
            [True, None, "Добро пожаловать, Никита!"],
            [False, None, "Добро пожаловать, Никита!"],
            [True, 1, "Вы находитесь в игре, поэтому команда /start сейчас бесполезна."],
            [False, 1, "Вы находитесь в игре, поэтому команда /start сейчас бесполезна."]
        ]
    )
    async def test_start(is_admin: bool, lobby, res, storage, bot):
        mocker.patch("User.lobby", lobby)
        mocker.patch("User.is_admin", is_admin)
        state = FSMContext(
            storage=storage,
            key=StorageKey(
                bot_id=bot.id,
                chat_id=TEST_USER_CHAT.id,
                user_id=TEST_USER.id
            )
        )
        message = TEST_MESSAGE
        db_connection = AsyncMock()
        await start(message, state, db_connection)
        message.answer.assert_called_with(res)