from aiogram import types, F, Router, Bot
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command, CommandStart
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

import asyncio
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from random import randint

from . import (
    keyboards, messages,
    utils, loops
)
from database import wrappers as wr

class StoneState(StatesGroup):
    choose_number_of_stones = State()
    choose_round_time = State()
    choose_stone = State()

router = Router()

@router.message(CommandStart())
async def start(
    message: types.Message
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    lobby = await user.lobby()
    if lobby is None:
        await message.answer(messages.welcome(message.from_user.first_name),
                             reply_markup=keyboards.start_keyboard(user.is_admin()))
    else:
        if lobby.status() == 'waiting':
            await message.answer(messages.useless_start(),
                                reply_markup=keyboards.start_keyboard(user.is_admin()))
        else:
            await message.answer(messages.useless_start())

@router.message((F.text == 'Войти в лобби'))
async def enter_lobby(
    message: types.Message
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    lobby = await user.lobby()
    if lobby is None:
        lobbys = await wr.Lobby.lobby_ids(user.is_admin())
        if len(lobbys) == 0:
            await message.answer(messages.no_lobbies(user.is_admin()))
        else:
            await message.answer(messages.choose_lobby(),
                                reply_markup=keyboards.lobbies_keyboard(lobbys))

@router.callback_query(F.data.startswith('enter'))
async def enter_chosen_lobby(
    call: types.CallbackQuery
) -> None:
    lobby_id = int(call.data.split()[1])
    user = await wr.User.add_or_get(call.from_user.id)
    lobby = await wr.Lobby.get_lobby(lobby_id)
    try:
        await lobby.join_user(user)
    except wr.ActionException as ex:
        await call.answer(str(ex))
        return
    await call.answer('')
    is_admin = user.is_admin()
    if lobby.status() == 'created':
        await call.message.answer(
            text=messages.lobby_entered(lobby_id, False),
            reply_markup=keyboards.inlobby_keyboard(is_admin)
        )
        await call.message.delete()
    else:
        await call.message.answer(
            text=messages.lobby_entered(lobby_id, False),
            reply_markup=keyboards.ingame_keyboard(is_admin)
        )
        await call.message.delete()
    if not is_admin:
        num_players = lobby.number_of_players()
        text = messages.lobby_entered(num_players, True)
        await utils.send_message_to_all_users(
            bot=call.bot,
            lobby=lobby,
            message=text,
            roles=['player', 'admin']
        )
        
@router.message((F.text == 'Создать лобби'))
async def create_lobby(
    message: types.Message,
    state: FSMContext
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    if user.is_admin():
        await state.set_state(StoneState.choose_round_time)
        await message.answer(messages.choose_round_time())

@router.message(StoneState.choose_round_time)
async def choose_round_time(
    message: types.Message,
    state: FSMContext
) -> None:
    number = 0
    try:
        number = int(message.text)
    except ValueError:
        await message.answer(messages.incorrect_number())
        return
    if 1 <= number <= 60:
        await state.set_state(StoneState.choose_number_of_stones)
        await state.set_data({'minutes' : number})
        await message.answer(messages.choose_num_stones())
    else:
        await message.answer(messages.incorrect_round_length(number))

@router.message(StoneState.choose_number_of_stones)
async def choose_num_of_stones(
    message: types.Message,
    state: FSMContext
) -> Optional[int]:
    data = await state.get_data()
    minutes = data['minutes']
    number = 0
    try:
        number = int(message.text)
    except ValueError:
        await message.answer(messages.incorrect_number())
        return
    if 1 <= number <= 200:
        await state.clear()
        lobby = await wr.Lobby.make_lobby(number, minutes*60000)
        await message.answer(messages.lobby_created(lobby.lobby_id()), 
                             reply_markup=keyboards.start_keyboard(True))
        return lobby.lobby_id()
    else:
        await message.answer(messages.incorrect_num_stones(number))

@router.message((F.text == "Выйти из лобби"))
async def leave_lobby(
    message: types.Message
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    lobby = await user.lobby()
    try:
        await lobby.kick_user(user)
    except AttributeError:
        await message.answer(messages.leaving_lobby_without_being_in(),
                       reply_markup=keyboards.start_keyboard(user.is_admin()))
        return
    except wr.ActionException as ex:
        await message.answer(str(ex))
        return
    is_admin = user.is_admin()
    await message.answer(messages.left_lobby(lobby.lobby_id(), False),
                   reply_markup=keyboards.start_keyboard(is_admin))
    if not is_admin:
        num_players = lobby.number_of_players()
        text = messages.left_lobby(num_players, True)
        await utils.send_message_to_all_users(
            bot=message.bot,
            lobby=lobby,
            message=text,
            roles=['player', 'admin']
        )

@router.message((F.text == 'Начать игру'))
async def start_game(
    message: types.Message,
    queues: Dict[int, asyncio.Queue]
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    if user.is_admin():
        lobby = await user.lobby()
        if lobby is None:
            await message.answer(messages.starting_not_being_in_lobby(),
                           reply_markup=keyboards.start_keyboard(True))
            return
        logging.debug(f'num of players - {lobby.number_of_players()}')
        if lobby.number_of_players() < 2:
            await message.answer(messages.not_enough_players_for_start(),
                                 reply_markup=keyboards.inlobby_keyboard(True))
            return
        try:
            await lobby.start_game()
            await loops.round_loop(
                bot=message.bot,
                lobby=lobby,
                queue=queues[lobby.lobby_id()]
            )
        except wr.ActionException as ex:
            await message.answer(str(ex))
            return
        
@router.message((F.text == 'Запустить новый раунд'))
async def start_new_round(
    message: types.Message,
    queues: Dict[int, asyncio.Queue]
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    if user.is_admin():
        lobby = await user.lobby()
        if lobby is None:
            await message.answer(messages.starting_not_being_in_lobby(),
                           reply_markup=keyboards.start_keyboard(True))
            return
        try:
            await loops.round_loop(message.bot, lobby, queues[lobby.lobby_id()])
        except wr.ActionException as ex:
            await message.answer(str(ex))
            return

@router.message((F.text == 'Закончить игру'))
async def end_game(
    message: types.Message
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    if user.is_admin():
        lobby = await user.lobby()
        users = await lobby.users()
        logs_path = await lobby.get_logs()
        await utils.send_document_to_all_users(
            bot=message.bot,
            caption=messages.game_over(True),
            lobby=lobby,
            document=FSInputFile(logs_path, f'Логи игры {lobby.lobby_id()}.csv'),
            reply_markup=keyboards.start_keyboard(True),
            parse_mode='MarkdownV2',
            roles=['admin']
        )
        os.remove(logs_path)
        await utils.send_message_to_all_users(
            bot=message.bot,
            lobby=lobby,
            message=messages.game_over(False),
            parse_mode='MarkdownV2',
            reply_markup=keyboards.start_keyboard(False)
        )
        try:
            await lobby.end_game()
        except wr.ActionException as ex:
            await message.answer(str(ex))

@router.callback_query((F.data.startswith('pick')))
async def pick_stone(
    call: types.CallbackQuery,
    queues: dict[int, asyncio.Queue],
    picked: dict[int, int]
) -> None:
    _, stone, round = call.data.split(' ')
    if stone == 'empty':
        await call.answer(messages.no_stone_to_pick())
    else:
        stone = int(stone)
        round = int(round)
        logging.debug(f"Player {call.from_user.id} chose stone {stone}")
        user = await wr.User.add_or_get(call.from_user.id)
        lobby = await user.lobby()
        if lobby.round() != round or lobby.status() != 'started':
            await call.answer(messages.inactive_keyboard())
            await call.message.delete()
            return
        try:
            if stone == 0:
                await user.leave_stone()
            else:
                await user.choose_stone(stone)
            picked[lobby.lobby_id()] += 1
            logging.debug(f"Added to counter: {picked[lobby.lobby_id()]}")
        except wr.ActionException as ex:
            logging.debug(f'While user {call.from_user.id} tried pick stone {stone}, error occured: {ex}')
            await call.answer(str(ex))
            return
        num_players = lobby.number_of_players()
        if picked[lobby.lobby_id()] == num_players:
            logging.debug('Everyone made a choice')
            queue = queues[lobby.lobby_id()]
            picked[lobby.lobby_id()] = 0
            await queue.put('chosen')
        await call.answer(messages.choice_is_made())
        await call.message.delete()

@router.message(Command("request"))
async def request_admin(
    message: types.Message
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    if user.is_admin():
        await message.answer(
            text=messages.invalid_request()
        )
    else:
        supreme_id = wr.User.SUPREME_ADMIN_ID
        await message.bot.send_message(
            chat_id=supreme_id,
            text=messages.request_for_admin(message.from_user),
            parse_mode='MarkdownV2',
            reply_markup=keyboards.request_keyboard(message.from_user.id)
        )
        await message.answer(
            text=messages.wait_for_acception()
        )

@router.callback_query((F.data.startswith('accept')))
async def accept_request(
    call : types.CallbackQuery
) -> None:
    _, id = call.data.split()
    id = int(id)
    user = await wr.User.add_or_get(id, 'player')
    lobby = await user.lobby()
    if lobby is not None and lobby.status() == 'started':
        await call.answer(
            text=messages.wait_til_player_leave(),
            show_alert=True
        )
        return
    elif lobby is not None:
        await lobby.kick_user(user)
        num_of_players = lobby.number_of_players()
        await utils.send_message_to_all_users(
            bot=call.bot,
            lobby=lobby,
            message=messages.left_lobby(num_of_players, True),
            roles=['player', 'admin']
        )
        await call.bot.send_message(
            chat_id=id,
            text=messages.left_lobby(num_of_players, False)
        )
    await call.answer()
    await call.message.delete()
    await wr.User.set_status(user, 'admin')
    await call.bot.send_message(
        text=messages.request_accepted(),
        chat_id=id,
        reply_markup=keyboards.start_keyboard(True)
    )

@router.callback_query((F.data.startswith('deny')))
async def deny_request(
    call: types.CallbackQuery
) -> None:
    await call.answer()
    await call.message.delete()
    _, id = call.data.split()
    id = int(id)
    await call.bot.send_message(
        chat_id=id,
        text=messages.request_denied()
    )