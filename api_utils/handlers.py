import asyncio
import logging

from app import messages
from app.game import bot, dp
from database import wrappers as wr
from data.exception import (
    _ACTION_OUT_OF_LOBBY, 
    _NO_SUCH_LOBBY, 
    _GAME_IS_NOT_RUNNING
)



async def enter_lobby(
    lobby_id: int,
    agent_id: int
) -> None:
    user = await wr.User.add_or_get(agent_id, 'agent')
    lobby = await wr.Lobby.get_lobby(lobby_id)
    try:
        await lobby.join_user(user)
    except AttributeError:
        raise wr.ActionException(_NO_SUCH_LOBBY)
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
    logging.debug(f'user is {user}')
    lobby = await user.lobby()
    logging.debug(f'lobby is {lobby}')
    try:
        await lobby.kick_user(user)
    except AttributeError:
        raise wr.ActionException(_ACTION_OUT_OF_LOBBY)
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
) -> bool:
    logging.debug(f"Player {agent_id} chose stone {stone}")
    user = await wr.User.add_or_get(agent_id, 'agent')
    lobby = await user.lobby()
    if lobby is None:
        raise wr.ActionException(_ACTION_OUT_OF_LOBBY)
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
        await asyncio.sleep(5)
        return lobby.status() != 'waiting'
    else:
        while picked[lobby.lobby_id()] != num_players and picked[lobby.lobby_id()] != 0:
            await asyncio.sleep(1)
            picked = dp.update.middleware._middlewares[0].picked()
        await asyncio.sleep(5)
        return lobby.status() != 'waiting'

async def get_game_environment(
    agent_id : int
) -> dict[int, tuple[int, list[int]]]:
    user = await wr.User.add_or_get(agent_id, 'agent')
    lobby = await user.lobby()
    if lobby is None:
        raise wr.ActionException(_ACTION_OUT_OF_LOBBY)
    elif lobby.status() != 'started':
        raise wr.ActionException(_GAME_IS_NOT_RUNNING)
    return await lobby.field_for_user(user)

async def wait_until_start_round(
    agent_id : int,
    timeout : int = 600
) -> bool:
    user = await wr.User.add_or_get(agent_id, 'agent')
    logging.debug(f'user: {user}')
    lobby = await user.lobby()
    logging.debug(f'lobby: {lobby}')
    if lobby is None:
        raise wr.ActionException(_ACTION_OUT_OF_LOBBY)
    for _ in range(timeout):
        logging.debug(f'tick: {_}')
        if lobby.status() == 'started':
            logging.debug('round started')
            return True
        else:
            logging.debug('sleeping 1 sec')
            await asyncio.sleep(1)
    return False
