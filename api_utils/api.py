from fastapi import FastAPI
import asyncio
import logging
from data.exception import *
from data.exception import _UNKNOWN_ERROR
from database.query import init_pool
from dotenv import load_dotenv
import api_utils.handlers as hnd
from database.wrappers import Lobby

app = FastAPI()


@app.on_event("startup")
async def startup():
    init_exceptions()
    load_dotenv()
    await init_pool()


@app.get("/get_lobby_ids/")
async def get_lobby_ids():
    logging.info('get request')
    try:
        return await Lobby.lobby_ids()
    except Exception as ex:
        return {"message":
                    _UNKNOWN_ERROR
                }


@app.post("/enter_lobby/")
async def enter_lobby(
        lobby_id: int,
        agent_id: int
):
    logging.info('get request')
    try:
        await hnd.enter_lobby(lobby_id, agent_id)
    except ActionException as ex:
        return {
            "message": str(ex)
        }
    except Exception as ex:
        return {
            "message": _UNKNOWN_ERROR
        }
    return {
        "message": "Agent entered lobby"
    }


@app.post("/game/leave_lobby/")
async def leave_lobby(
        agent_id: int
):
    try:
        await hnd.leave_lobby(agent_id)
    except ActionException as ex:
        return {
            "message": str(ex)
        }
    except Exception as ex:
        return {
            "message": _UNKNOWN_ERROR
        }
    return {
        "message": "Agent left lobby"
    }

@app.get("/game/get_game_info/")
async def get_game_info(agent_id: int):
    try:
        return {
            "message": await hnd.get_game_environment(agent_id)
        }
    except ActionException as ex:
        return {
            "message": str(ex)
        }
    except Exception as ex:
        return {
            "message": str(ex)
        }

@app.post("/game/pick_stone/")
async def pick_stone(
        agent_id: int,
        stone: int
):
    try:
        await hnd.pick_stone(agent_id, stone)
    except ActionException as ex:
        return {
            "message": str(ex)
        }
    except Exception as ex:
        return {
            "message": _UNKNOWN_ERROR
        }
    return {
        "message": "Agent picked a stone"
    }