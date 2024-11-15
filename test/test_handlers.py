import pytest
import pytest_mock
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

# from utils import TEST_USER, TEST_USER_CHAT, TEST_MESSAGE
# import app.handlers as h
import app.messages as msg
import app.keyboards as kboards

class TestMessageHandlers:    
    def test_correct_json_names(self):
        assert ('{' not in msg.info_message())
        assert ('{' not in msg.no_lobbies(True))
        assert ('{' not in msg.no_lobbies(False))
        assert ('{' not in msg.lobby_is_running())
        assert ('{' not in msg.useless_start())
        assert ('{' not in msg.welcome("Nikita"))
        assert ('{' not in msg.choose_lobby())
        assert ('{' not in msg.choose_round_time())
        assert ('{' not in msg.choose_num_stones())
        assert ('{' not in msg.incorrect_number())
        assert ('{' not in msg.incorrect_num_stones(1))
        assert ('{' not in msg.incorrect_round_length(1))
        assert ('{' not in msg.lobby_created(1))
        assert ('{' not in msg.lobby_entered(1, False))
        assert ('{' not in msg.lobby_entered(1, True))
        assert ('{' not in msg.leaving_lobby_without_being_in())
        assert ('{' not in msg.left_lobby(1, True))
        assert ('{' not in msg.left_lobby(1, False))
        assert ('{' not in msg.starting_not_being_in_lobby())
        assert ('{' not in msg.round_started(1, 1, True))
        assert ('{' not in msg.round_started(1, 1, False))
        assert ('{' not in msg.round_ended(1, 1, False))
        assert ('{' not in msg.round_ended(1, 0, False))
        assert ('{' not in msg.round_ended(1, 1, True))
        assert ('{' not in msg.round_ended(1, 0, True))
        assert ('{' not in msg.choose_stone())
        assert ('{' not in msg.stone_left())
        assert ('{' not in msg.stone_chosen(1))
        assert ('{' not in msg.game_over(True))
        assert ('{' not in msg.game_over(False))
        assert ('{' not in msg.no_stone_to_pick())
        assert ('{' not in msg.choice_is_made())
    
    @pytest.mark.parametrize(
            "number, message",
            [[1, "Ещё один игрок присоединился. В лобби 1 игрок."],
            [2, "Ещё один игрок присоединился. В лобби 2 игрока."],
            [3, "Ещё один игрок присоединился. В лобби 3 игрока."],
            [4, "Ещё один игрок присоединился. В лобби 4 игрока."],
            [5, "Ещё один игрок присоединился. В лобби 5 игроков."],
            [6, "Ещё один игрок присоединился. В лобби 6 игроков."],
            [7, "Ещё один игрок присоединился. В лобби 7 игроков."],
            [8, "Ещё один игрок присоединился. В лобби 8 игроков."],
            [9, "Ещё один игрок присоединился. В лобби 9 игроков."],
            [10, "Ещё один игрок присоединился. В лобби 10 игроков."],
            [21, "Ещё один игрок присоединился. В лобби 21 игрок."]]
    )
    def test_agreement(self, number, message):
        assert (msg.lobby_entered(number, True) == message)
    
    @pytest.mark.parametrize(
            "func, args",
            [[msg.round_started, (1, 1, False)],
             [msg.round_started, (1, 1, True)],
             [msg.game_over, (True,)],
             [msg.game_over, (False,)]]
    )
    def test_markdown_escaping(self, func, args):
        escaping_symbols='[]()~`>#+-=!.'
        res : str = func(*args)
        for symbol in escaping_symbols:
            assert (res.count(symbol) == res.count('\\' + symbol))