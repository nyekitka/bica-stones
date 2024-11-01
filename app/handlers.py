from aiogram import types, F, Router, Bot
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import CommandStart
import asyncio
import os
import logging

from . import keyboards, messages
from database import wrappers as wr

class StoneState(StatesGroup):
    choose_number_of_stones = State()
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
        call.answer(str(ex))
        return
    await call.answer('')
    is_admin = user.is_admin()
    await call.message.answer(messages.lobby_entered(lobby_id, False),
                              reply_markup=keyboards.inlobby_keyboard(is_admin))
    if not is_admin:
        lobby_users = await lobby.users()
        num_players = len([user for user in lobby_users if not user.is_admin()])
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
        await state.set_state(StoneState.choose_number_of_stones)
        await message.answer(messages.choose_num_stones())


@router.message(StoneState.choose_number_of_stones)
async def choose_num_of_stones(
    message: types.Message,
    state: FSMContext
) -> None:
    number = 0
    try:
        number = int(message.text)
    except ValueError:
        await message.answer(messages.incorrect_number())
        return
    if 1 <= number <= 200:
        await state.clear()
        lobby = await wr.Lobby.make_lobby(number)
        await message.answer(messages.lobby_created(lobby.lobby_id()), 
                             reply_markup=keyboards.start_keyboard(True))
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
        num_players = len([user for user in lobby_users if not user.is_admin()])
        for other_user in lobby_users:
            await message.bot.send_message(
                chat_id=other_user.id, 
                text=messages.left_lobby(num_players, True)
            )

@router.message((F.text == 'Начать игру'))
async def start_game(
    message: types.Message,
    state: FSMContext
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    if user.is_admin():
        lobby = await user.lobby()
        if lobby is None:
            await message.answer(messages.starting_not_being_in_lobby(),
                           reply_markup=keyboards.start_keyboard(True))
            return
        try:
            await lobby.start_game()
        except wr.ActionException as ex:
            await message.answer(str(ex))
            return
        await game_loop(message.bot, lobby)
        
async def round_loop(bot: Bot, lobby: wr.Lobby):
    users = await lobby.users()
    round = lobby.round()
    for user in users:
        if not user.is_admin():
            try:
                info = await lobby.field_for_user(user)
            except wr.ActionException as ex:
                logging.error(str(ex))
            is_picked = any(map(lambda x: x[0], info.values()))
            await bot.send_message(
                chat_id=user.id,
                text=messages.info_message(round, info),
                parse_mode='MarkdownV2',
                reply_markup=keyboards.ingame_keyboard(False, is_picked)
            )
        else:
            await bot.send_message(
                chat_id=user.id,
                text=messages.round_started(round),
                reply_markup=keyboards.ingame_keyboard(True)
            )
    await asyncio.sleep(30)

async def game_loop(bot: Bot, lobby: wr.Lobby):
    while lobby.stones_left() != 0:
        await round_loop(bot, lobby)
        await lobby.end_round()
        users = await lobby.users()
        round = lobby.round()
        for user in users:
            await bot.send_message(
                chat_id=user.id,
                text=messages.round_ended(round - 1),
                reply_markup=keyboards.remove_keyboard
            )
        await asyncio.sleep(10)
    users = await lobby.users()
    for user in users:
        if user.is_admin():
            logs_path = await lobby.get_logs()
            await bot.send_document(
                caption=messages.game_over(True),
                chat_id=user.id,
                document=FSInputFile(logs_path, f'Логи игры {lobby.lobby_id()}.csv'),
                reply_markup=keyboards.start_keyboard(True)
            )
            os.remove(logs_path)
        else:
            await bot.send_message(
                chat_id=user.id,
                text=messages.game_over(False),
                parse_mode='MarkdownV2',
                reply_markup=keyboards.start_keyboard(False)
            )
    await lobby.end_game()

@router.message((F.text == 'Выбрать камень'))
async def choose_stone(
    message: types.Message,
    state: FSMContext
) -> None:
    await message.answer(messages.choose_stone())
    await state.set_state(StoneState.choose_stone)

@router.message((F.text == 'Отойти от камня'))
async def leave_stone(
    message: types.Message,
    state: FSMContext
) -> None:
    user = await wr.User.add_or_get(message.from_user.id)
    try:
        await user.leave_stone()
    except wr.ActionException as ex:
        reply_markup = None
        if 'лобби' in str(ex):
            reply_markup = keyboards.inlobby_keyboard(False)
        else:
            reply_markup = keyboards.ingame_keyboard(False, False)
        await message.answer(
            text=str(ex),
            reply_markup=reply_markup
        )
        return
    await message.answer(
        text=messages.stone_left(),
        reply_markup=keyboards.ingame_keyboard(False, False)
    )

@router.message(StoneState.choose_stone)
async def choose_stone_to_leave(
    message: types.Message,
    state: FSMContext
) -> None:
    number_of_stone = None
    user = await wr.User.add_or_get(message.from_user.id)
    try:
        number_of_stone = int(message.text)
        await user.choose_stone(number_of_stone)
    except ValueError:
        await message.answer(messages.incorrect_number())
        return
    except wr.ActionException as ex:
        await message.answer(str(ex))
        return
    await message.answer(
        text=messages.stone_chosen(number_of_stone),
        reply_markup=keyboards.ingame_keyboard(False, True)
    )
    await state.clear()
