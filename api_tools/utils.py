import asyncio
from collections import defaultdict
from data.exception import ActionException, _MOVE_ALREADY_MADE, \
    _NO_STONE


class VariableWaiter:
    def __init__(self):
        self.var = None
        self.cond = asyncio.Condition()
        
    async def wait_for_value(self, value):
        async with self.cond:
            while self.var != value:
                print("Waiting for value {}".format(value))
                await self.cond.wait()
            
    async def set_value(self, value):
        async with self.cond:
            print("Setting value {}".format(value))
            self.var = value
            self.cond.notify_all()
            
            
class SetStones:
    def __init__(self, n_stones: int = 5):
        self.n_stones = n_stones
        self.stone_to_players = {stone_id: set() for stone_id in range(1, n_stones + 1)}
        self.player_id_to_stone = defaultdict(int)
        self.moves = defaultdict(int) # player_id to stone_id
        
    def make_move(self, user_id: int, stone_id: int):
        if user_id in self.moves:
            raise ActionException(_MOVE_ALREADY_MADE)
        if stone_id not in self.stone_to_players:
            raise ActionException(_NO_STONE)
        self.moves[user_id] = stone_id
        
    def handle(self):
        for player_id, stone_id in self.moves.items():
            if self.player_id_to_stone[player_id] != 0:
                cur_stone_id = self.player_id_to_stone[player_id]
                self.stone_to_players[cur_stone_id].remove(player_id)
            self.player_id_to_stone[player_id] = stone_id
            self.stone_to_players[stone_id].add(player_id)
            
        del_stones = set()
        for stone_id, players in self.stone_to_players.items():
            if len(players) == 2:
                del_stones.add(stone_id)
                for player_id in players:
                    self.player_id_to_stone[player_id] = 0
        for stone_id in del_stones:
            self.stone_to_players.pop(stone_id)
            print(f"Stone {stone_id} was deleted")
        self.moves = defaultdict(int)
        
    def get_cnt_stones(self):
        return len(self.stone_to_players.keys())
    
    def __str__(self):
        return "STONE_TO_PLAYERS: {} ".format(str(self.stone_to_players)) + \
               "PLAYER_TO_STONE: {}".format(str(self.player_id_to_stone))