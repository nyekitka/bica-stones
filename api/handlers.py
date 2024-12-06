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
    user = await wr.User.add_or_get(agent_id)
    lobby = await wr.Lobby.get_lobby(lobby_id)
    try:
        await lobby.join_user(user)
    except AttributeError as ex:
        raise wr.ActionException(messages.no_such_lobby(lobby_id)) from ex
    lobby_users = await lobby.users()
    num_players = lobby.number_of_players()
    for other_user in lobby_users:
        await bot.send_message(
            chat_id=other_user.id, 
            text=messages.lobby_entered(num_players, True)
        )

async def leave_lobby(
    agent_id: int
) -> None:
    user = await wr.User.add_or_get(agent_id)
    lobby = await user.lobby()
    try:
        await lobby.kick_user(user)
    except AttributeError as ex:
        raise wr.ActionException(messages.leaving_lobby_without_being_in()) from ex
    lobby_users = await lobby.users()
    num_players = lobby.number_of_players()
    for other_user in lobby_users:
        await bot.send_message(
            chat_id=other_user.id, 
            text=messages.left_lobby(num_players, True)
        )

async def pick_stone(
    agent_id: int,
    stone: int
) -> None:
    logging.debug(f"Player {agent_id} chose stone {stone}")
    user = await wr.User.add_or_get(agent_id)
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