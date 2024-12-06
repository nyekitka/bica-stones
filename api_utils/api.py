from fastapi import FastAPI
import asyncio
import logging
from data.exception import *
from data.exception import _UNKNOWN_ERROR
from database.query import init_pool
from dotenv import load_dotenv
from api_utils.handlers import *
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
        return await Lobby().lobby_ids()
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
        await enter_lobby(lobby_id, agent_id)
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
        await leave_lobby(agent_id)
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


@app.post("/game/pick_stone/")
async def pick_stone(
        agent_id: int,
        stone: int
):
    try:
        await pick_stone(agent_id, stone)
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