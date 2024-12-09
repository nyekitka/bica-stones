from aiogram import types, F, Router, Bot
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import CommandStart
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from random import randint

from app import keyboards, messages
from app.game import bot, dp
from database import wrappers as wr



async def enter_lobby(
    lobby_id: int,
    agent_id: int
) -> None:
    user = await wr.User.add_or_get(agent_id, 'agent')
    lobby = await wr.Lobby.get_lobby(lobby_id)
    try:
        await lobby.join_user(user)
    except AttributeError as ex:
        raise wr.ActionException(messages.no_such_lobby(lobby_id))
    lobby_users = await lobby.users()
    num_players = lobby.number_of_players()
    for other_user in lobby_users:
        if other_user.id != agent_id:
            await bot.send_message(
                chat_id=other_user.id, 
                text=messages.lobby_entered(num_players, True)
            )

async def leave_lobby(
    agent_id: int
) -> None:
    user = await wr.User.add_or_get(agent_id, 'agent')
    lobby = await user.lobby()
    try:
        await lobby.kick_user(user)
    except AttributeError as ex:
        raise wr.ActionException(messages.leaving_lobby_without_being_in()) from ex
    lobby_users = await lobby.users()
    num_players = lobby.number_of_players()
    for other_user in lobby_users:
        if other_user.id != agent_id:
            await bot.send_message(
                chat_id=other_user.id, 
                text=messages.left_lobby(num_players, True)
            )

async def pick_stone(
    agent_id: int,
    stone: int
) -> None:
    logging.debug(f"Player {agent_id} chose stone {stone}")
    user = await wr.User.add_or_get(agent_id, 'agent')
    lobby = await user.lobby()
    picked = dp.update.middleware._middlewares[0].picked()
    queues = dp.update.middleware._middlewares[0].queues()
    try:
        if stone == 0:
            await user.leave_stone()
        else:
            await user.choose_stone(stone)
        picked[lobby.lobby_id()] += 1
        logging.debug(f"Added to counter: {picked[lobby.lobby_id()]}")
    except wr.ActionException as ex:
        logging.debug(f'While user {agent_id} tried pick stone {stone}, error occured: {ex}')
        raise ex
    num_players = lobby.number_of_players()
    if picked[lobby.lobby_id()] == num_players:
        logging.debug('Everyone made a choice')
        queue = queues[lobby.lobby_id()]
        picked[lobby.lobby_id()] = 0
        await queue.put('chosen')

async def get_game_environment(
    agent_id : int
) -> dict[int, tuple[int, list[int]]]:
    user = await wr.User.add_or_get(agent_id, 'agent')
    lobby = await user.lobby()
    return await lobby.field_for_user(user)

async def wait_until_start_round(
    agent_id : int,
    timeout : int = 600
) -> bool:
    user = await wr.User.add_or_get(agent_id, 'agent')
    lobby = await user.lobby()
    for _ in range(timeout):
        if lobby.status() == 'started':
            return True
        else:
            asyncio.sleep(1)
    return False

async def wait_until_start_move(
    agent_id : int,
    timeout : int = 600
) -> bool:
    user = await wr.User.add_or_get(agent_id, 'agent')
    lobby : wr.Lobby = user.lobby()
    if lobby.status() == 'created' or lobby.status() == 'waiting':
        return await wait_until_start_round(agent_id, timeout)
    elif lobby.status() == 'finished':
        raise wr.ActionException(messages.game_is_already_finished())
    else:
        picked = dp.update.middleware._middlewares[0].picked()
        while timeout > 0 and picked != lobby.number_of_players():
            picked = dp.update.middleware._middlewares[0].picked()
            asyncio.sleep(1)
            timeout -= 1
        if timeout == 0:
            return False
        while timeout > 0 and picked < lobby.number_of_players():
            picked = dp.update.middleware._middlewares[0].picked()
            asyncio.sleep(1)
            timeout -= 1
        return timeout != 0
