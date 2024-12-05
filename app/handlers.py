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

from . import keyboards, messages
from database import wrappers as wr

class StoneState(StatesGroup):
    choose_number_of_stones = State()
    choose_round_time = State()
    choose_stone = State()

router = Router()

@router.message(CommandStart())
async def start(
    message: types.Message,
    state: FSMContext
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
    call: types.CallbackQuery,
    state: FSMContext
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
        lobby_users = await lobby.users()
        num_players = lobby.number_of_players()
        for other_user in lobby_users:
            await call.bot.send_message(
                chat_id=other_user.id, 
                text=messages.lobby_entered(num_players, True)
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
    message: types.Message,
    state: FSMContext
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
        lobby_users = await lobby.users()
        num_players = lobby.number_of_players()
        for other_user in lobby_users:
            await message.bot.send_message(
                chat_id=other_user.id, 
                text=messages.left_lobby(num_players, True)
            )

@router.message((F.text == 'Начать игру'))
async def start_game(
    message: types.Message,
    state: FSMContext,
    queues: Dict[int, asyncio.Queue]
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    if user.is_admin():
        lobby = await user.lobby()
        if lobby is None:
            await message.answer(messages.starting_not_being_in_lobby(),
                           reply_markup=keyboards.start_keyboard(True))
            return
        if lobby.number_of_players() < 2:
            await message.answer(messages.not_enough_players_for_start(),
                                 reply_markup=keyboards.inlobby_keyboard(True))
            return
        try:
            await lobby.start_game()
            await round_loop(message.bot, lobby, queues[lobby.lobby_id()])
        except wr.ActionException as ex:
            await message.answer(str(ex))
            return
        
@router.message((F.text == 'Запустить новый раунд'))
async def start_new_round(
    message: types.Message,
    state: FSMContext,
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
            await round_loop(message.bot, lobby, queues[lobby.lobby_id()])
        except wr.ActionException as ex:
            await message.answer(str(ex))
            return

@router.message((F.text == 'Закончить игру'))
async def end_game(
    message: types.Message,
    state: FSMContext
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    if user.is_admin():
        lobby = await user.lobby()
        users = await lobby.users()
        bot = message.bot
        for user in users:
            if user.is_admin():
                logs_path = await lobby.get_logs()
                await bot.send_document(
                    caption=messages.game_over(True),
                    chat_id=user.id,
                    document=FSInputFile(logs_path, f'Логи игры {lobby.lobby_id()}.csv'),
                    reply_markup=keyboards.start_keyboard(True),
                    parse_mode='MarkdownV2'
                )
                os.remove(logs_path)
            else:
                await bot.send_message(
                    chat_id=user.id,
                    text=messages.game_over(False),
                    parse_mode='MarkdownV2',
                    reply_markup=keyboards.start_keyboard(False)
                )
        try:
            await lobby.end_game()
        except wr.ActionException as ex:
            await message.answer(str(ex))

async def move_loop(
        bot: Bot, 
        lobby: wr.Lobby,
        queue: asyncio.Queue
) -> bool:
    users = await lobby.users()
    for user in users:
        if not user.is_admin():
            try:
                info = await lobby.field_for_user(user)
            except wr.ActionException as ex:
                logging.error(str(ex))
            await bot.send_message(
                chat_id=user.id,
                text=messages.info_message(),
                reply_markup=keyboards.field_keyboard(info, lobby.default_stones_cnt, lobby.round())
            )
    sig = await queue.get()
    await lobby.end_move()
    return sig == 'end'
    
async def round_loop(
        bot: Bot,
        lobby: wr.Lobby,
        queue: asyncio.Queue
) -> None:
    await lobby.start_round()
    users = await lobby.users()
    minutes = int(lobby.round_duration_ms/60000)
    round = lobby.round()
    for user in users:
        await bot.send_message(
            chat_id = user.id,
            text = messages.round_started(round, minutes, user.is_admin()),
            parse_mode='MarkdownV2',
            reply_markup=keyboards.ingame_keyboard(user.is_admin())
        )
    scheduler = AsyncIOScheduler()
    scheduler.start()
    end_time = datetime.now() + timedelta(minutes=minutes)
    scheduler.add_job(
        func=round_ended,
        trigger=DateTrigger(end_time),
        args=[queue]
    )
    is_finished = False
    is_first_move = True
    while lobby.stones_left() > 0 and not is_finished:
        if is_first_move:
            is_first_move = False
        else:
            await asyncio.sleep(5)
        is_finished = await move_loop(bot, lobby, queue)
    stones_left = lobby.stones_left()
    for user in users:
        await bot.send_message(
            chat_id=user.id,
            text=messages.round_ended(lobby.round(), stones_left, user.is_admin()),
            reply_markup=keyboards.between_rounds_keyboard(user.is_admin())
        )
    await lobby.end_round()

async def round_ended(
    queue: asyncio.Queue
) -> None:
    await queue.put("end")

@router.callback_query((F.data.startswith('pick')))
async def pick_stone(
    call: types.CallbackQuery,
    state: FSMContext,
    queues: list[asyncio.Queue]
) -> None:
    _, stone, round = call.data.split(' ')
    if stone == 'empty':
        await call.answer(messages.no_stone_to_pick())
    else:
        stone = int(stone)
        round = int(round)
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
        except wr.ActionException as ex:
            await call.answer(str(ex))
            return
        lobby = await user.lobby()
        num_finishied = await lobby.num_players_with_chosen_stone()
        num_players = lobby.number_of_players()
        logging.debug(f'{num_finishied}/{num_players} picked a stone')
        if num_finishied == num_players:
            queue = queues[lobby.lobby_id()]
            await queue.put('chosen')
            logging.debug('signal is sent')
        await call.answer(messages.choice_is_made())
        await call.message.delete()