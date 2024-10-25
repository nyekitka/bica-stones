from fastapi import FastAPI
import asyncio
from game_process import GameProcess
from schemes import Player, SMove

app = FastAPI()
lock = asyncio.Lock()
players = dict()

processor = GameProcess()

@app.post('/add_player/')
async def add_player(player: Player):
    async with lock:
        return processor.add_player(player)

@app.post('/start_game/{player_id}')
async def start_game(player_id: int):
    async with lock:
        
        if not processor.game_can_be_started():
            return {"message": "There are not enough registered players"}
        
        processor.add_player_to_curr_game(player_id)
    await processor.wait_for_starting_game()
    return {"message": "Game started"}

@app.get('/game/env_info/{player_id}')
async def get_env_info(player_id: int):
    async with lock:
        return processor.get_env_info(int(player_id))

@app.get('/game/current_state/')
async def get_current_state():
    async with lock:
        return processor.get_current_state()
    
@app.post("/game/move/{player_id}")
async def make_move(player_id: int, move: SMove):
    async with lock:
        return processor.make_move(player_id, move)
