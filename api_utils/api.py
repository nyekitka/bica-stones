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
    """
    Возвращает список доступных для входа лобби.
    """
    logging.info('get request')
    try:
        result =  await Lobby.lobby_ids()
        return {
            "status": "success",
            "code": 200,
            "result": result
        }
    except ActionException as ex:
        return {
            "status": "error",
            "code": 400,
            "message": str(ex)
        }
    except Exception as ex:
        return {
            "status": "error",
            "code": 500,
            "message": _UNKNOWN_ERROR
        }


@app.post("/enter_lobby/")
async def enter_lobby(
    lobby_id: int,
    agent_id: int
):
    """
    Посылает запрос на вход данного агента в лобби.

    Параметры:
    - lobby_id – ID лобби, в которое нужно войти;
    - agent_id – ID агента, который пытается войти в лобби.
    """
    logging.info('get request')
    try:
        await hnd.enter_lobby(lobby_id, agent_id)
        return {
            "status": "success",
            "code": 200,
            "message": "Agent entered lobby"
        }
    except ActionException as ex:
        return {
            "status": "error",
            "code": 400,
            "message": str(ex)
        }
    except Exception as ex:
        return {
            "status": "error",
            "code": 500,
            "message": _UNKNOWN_ERROR
        }


@app.post("/game/leave_lobby/")
async def leave_lobby(
    agent_id: int
):
    """
    Выводит из лобби агента.

    Параметры:
    - agent_id – ID агента, которому нужно выйти.
    """
    try:
        await hnd.leave_lobby(agent_id)
    except ActionException as ex:
        return {
            "status": "error",
            "code": 400,
            "message": str(ex)
        }
    except Exception as ex:
        return {
            "status": "error",
            "code": 500,
            "message": _UNKNOWN_ERROR
        }
    return {
        "status": "success",
        "code": 200,
        "message": "Agent left lobby"
    }

@app.get("/game/get_game_info/")
async def get_game_info(agent_id: int):
    """
    Возвращает информацию об окружающей среде для агента. Ответ представляет из себя словарь,
    ключи в котором – номера камней (0 означает, что соответствующие игроки не стоят ни у какого камня).
    Под каждым ключем стоит пара значений, первое из которых – индикатор того, стоит ли данный агент у этого камня,
    а второе – список других агентов, которые стоят у этого камня.

    Пример ответа на запрос приведён ниже:
    ```
    {
        "0" : [False, ["E"]],
        "1" : [False, ["A"]],
        "2" : [True, []],
        "3" : [False, []],
        "4" : [False, ["B", "C", "D"]]
    }
    ```
    Данный ответ означает, что данный агент один стоит у камня 2, агенты B, C и D
    стоят у камня 4, агент A стоит у камня 1, а агент E не стоит ни у одного камня.

    Параметры:
    - agent_id – ID агента, для которого нужно получить информацию о поле.
    """
    try:
        return {
            "status": "success",
            "code": 200,
            "message": await hnd.get_game_environment(agent_id)
        }
    except ActionException as ex:
        return {
            "status": "error",
            "code": 400,
            "message": str(ex)
        }
    except Exception as ex:
        return {
            "status": "error",
            "code": 500,
            "message": str(ex)
        }

@app.post("/game/pick_stone/")
async def pick_stone(
    agent_id: int,
    stone: int
):
    """
    Запрос о выборе данным агентом данного камня. Если выбор произошёл успешно, то ответ на этот
    запрос вернётся только когда будет доступный следующий ход или раунд закончится. 
    При этом в ответе на запрос будет указано начался ли следующий ход или раунд закончился.

    Параметры:
    - agent_id – ID агента, который должен выбрать камень;
    - stone – номер камня, который агент должен выбрать (если агент хочет отойти от камней, то 0);
    """
    res = None
    try:
        res = await hnd.pick_stone(agent_id, stone)
    except ActionException as ex:
        return {
            "status": "error",
            "code": 400,
            "message": str(ex)
        }
    except Exception as ex:
        return {
            "status": "error",
            "code": 500,
            "message": _UNKNOWN_ERROR
        }
    new_move = "Начался новый ход." if res else "Раунд закончен."
    return {
        "status": "success",
        "code": 200,
        "message": "Агент выбрал камень. " + new_move
    }
    
    
@app.get("/game/wait_round_start/")
async def wait_round_start(agent_id: int, timeout: int = 600):
    """
    Возвращает ответ только когда раунд в игре начался, либо если превышено время ожидания.
    
    Параметры:
    - agent_id - ID агента;
    - timeout - время ожидания в секундах. По умолчанию 600 сек.
    """
    try:
        res = await hnd.wait_until_start_round(agent_id, timeout)
        return {
            "status": "success",
            "code": 200,
            "message": "Раунд начался" if res else "Превышено время ожидания"
        }
    except ActionException as ex:
       return {
           "status": "error",
           "code": 400,
           "message": str(ex)
       }
    except Exception as ex:
        return {
            "status": "error",
            "code": 500,
            "message": _UNKNOWN_ERROR
        }