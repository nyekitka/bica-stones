from fastapi import FastAPI
import asyncio
import logging
from api_tools.handlers import GeneralApiHendler, GameApiHendler
from api_tools.schemes import *
from data.exception import *
from data.exception import _UNKNOWN_ERROR
from database.query import init_pool
from dotenv import load_dotenv

app = FastAPI()
processor = GeneralApiHendler()
game = GameApiHendler()


@app.on_event("startup")
async def startup():
    init_exceptions()
    load_dotenv()
    await init_pool()

###### АПИ ОБЩЕГО НАЗНАЧЕНИЯ ######
@app.get('/lobby/lobby_ids/')
async def get_lobby_ids():
    lobby_ids = await processor.get_lobby_ids()
    return {"ID lists of available lobbies" : lobby_ids}


@app.post('/lobby/make_lobby/')
async def make_lobby(n_stones: SLobbyMaker):
    lobby_id = await processor.make_lobby(n_stones.n_stones)
    return {"message": "The lobby has been created. Lobby ID: " + str(lobby_id)}


@app.post("/lobby/{lobby_id}/add_player/")
async def add_player(lobby_id: int):
    try:
        user_id = await processor.add_user(lobby_id)
    except ActionException as e:
        return {"message": str(e)}
    return {"message": "the player has been added. Player ID: " + str(user_id)}


@app.get("/lobby/{lobby_id}/get_players/")
async def get_players(lobby_id: int):
    try:
        players = await processor.get_players(lobby_id)
    except ActionException as e:
        return {"message": str(e)}
    return {"players": players}


@app.post("/lobby/{lobby_id}/kick_player/")
async def del_player(lobby_id: int, user_id: SUserID):
    try:
        await processor.del_player(lobby_id, user_id.user_id)
    except ActionException as e:
        return {"message": str(e)}
    return {"message": "the player has been kicked"}


@app.post("/lobby/{lobby_id}/start_game/")
async def start_game(lobby_id: int):
    try:
        await processor.start_game(lobby_id)
    except ActionException as e:
        return {"message": str(e)}
    return {"message": "the game has been started"}


@app.post("/lobby/{lobby_id}/end_game/")
async def end_game(lobby_id: int):
    try:
        await processor.end_game(lobby_id)
    except ActionException as e:
        return {"message": str(e)}
    return {"message": "the game has been ended"}

@app.get("/lobby/{lobby_id}/round/")
async def get_round(lobby_id: int):
    try:
        round = await processor.get_round(lobby_id)
    except ActionException as e:
        return {"message": str(e)}
    except Exception as e:
        return {"message": e}
    return {"current round": round}


@app.get("/lobby/{lobby_id}/env_info/")
async def get_env_info(lobby_id: int, user: SUserID):
    try:
        env_info = await processor.get_env_info(lobby_id, user.user_id)
    except ActionException as e:
        return {"message": str(e)}
    except Exception as e:
        return {"message": _UNKNOWN_ERROR}
    return {"env_info": env_info}


@app.get("/lobby/{lobby_id}/cnt_stones/")
def count_stones(lobby_id: int):
    try:
        n_stones = processor.count_stones(lobby_id)
    except ActionException as e:
        return {"message": str(e)}
    return {"number of stones": n_stones}


@app.post("/lobby/{lobby_id}/end_round/")
async def end_round(lobby_id: int):
    try:
        await processor.end_round(lobby_id)
    except ActionException as e:
        return {"message": str(e)}
    return {"message": "the round has been ended"}


@app.post("/user/leave_stone/")
async def leave_stone(user: SUserID):
    try:
        await processor.leave_stone(user.user_id)
    except ActionException as e:
        return {"message": str(e)}
    except Exception as e:
        return {"message": _UNKNOWN_ERROR}
    return {"message": "The player moved away from the stone"}


@app.post("/user/make_move/")
async def make_move(move: SMoveMaker):
    try:
        await processor.make_move(move)
    except ActionException as e:
        return {"message": str(e)}
    except Exception as e:
        return {"message": _UNKNOWN_ERROR}
    return {"message": "the move has been made"}
    
##### ПОЛЬЗОВАТЕЛЬСКОЕ АПИ ######

@app.post("/game/add_player/")
async def game_add_player(user: SUserID):
    try:
        await game.add_player(user)
    except ActionException as e:
        return {"message": str(e)}
    #except Exception as e:
    #    return {"message": _UNKNOWN_ERROR}
    return {"message": "Player has been added to the lobby"}


@app.post("/game/start_game/")
async def game_start_game(user: SUserID):
    try:
        await game.start_game(user)
    except ActionException as e:
        return {"message": str(e)}
    except Exception as e:
        return {"message": _UNKNOWN_ERROR}
    return {"message": "The game has been started"}

@app.get("/game/get_env_info/")
async def game_get_env_info(user: SUserID):
    try:
        env_info = await game.get_env_info(user)
    except ActionException as e:
        return {"message": str(e)}
    except Exception as e:
        return {"message": _UNKNOWN_ERROR}
    return env_info


@app.post("/game/make_move/")
async def game_make_move(move: SMoveMaker):
    try:
        msg = await game.make_move(move)
    except ActionException as e:
        return {"message": str(e)}
    except Exception as e:
        return {"message": _UNKNOWN_ERROR}
    return msg

@app.get("/game/current_state/")
async def game_current_state(user: SUserID):
    try:
        state = game.get_current_state(user)
    except ActionException as e:
        return {"message": str(e)}
    except Exception as e:
        return {"message": _UNKNOWN_ERROR}
    return state


@app.post("/game/end_game/")
async def game_end_game(user: SUserID):
    try:
        await game.end_game(user.user_id)
    except ActionException as e:
        return {"message": str(e)}
    except Exception as e:
        return {"message": _UNKNOWN_ERROR}
    return {"message": "The game has been ended"}


@app.post("/game/clean_history/")
def clean_history(user: SUserID):
    game.reset()
    return {"message": "The history has been cleaned"}


@app.post("/game/set_config/")
def set_config(config: SGameConfig):
    if game._cur_lobby is not None:
        return {"message": "Can't set config while. The game is in progress."}
    game.set_config(config)
    return {"message": "The config has been set"}
