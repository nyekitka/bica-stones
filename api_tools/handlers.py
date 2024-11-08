import asyncio
from database.wrappers import Lobby, User
from data.exception import ActionException, _NO_LOBBY, _ALREADY_IN_LOBBY, _NO_USER, _GAME_IS_RUNNING, \
    _NOT_ENOUGH_PLAYERS, _GAME_IS_NOT_RUNNING, _NO_STONE
from api_tools.schemes import *
from collections import defaultdict
from api_tools.utils import SetStones

lock = asyncio.Lock()

GAME_STATES = {
    1: "waiting for each player to receive information about the environment",
    2: "waiting for each player to make a move",
    3: "the game is over"
}

class GeneralApiHendler:
    
    def __init__(self):
        self._lobby = defaultdict(int)
        self._users = defaultdict(int)
        self._cur_lobby_id = 1
        self._cur_user_id = 1
        
    async def get_lobby_ids(self):
        lobby_ids = sorted(self._lobby.keys())
        return lobby_ids
    
    async def make_lobby(self, n_stones):
        async with lock:
            self._lobby[self._cur_lobby_id] = await Lobby.make_lobby(n_stones)
            self._cur_lobby_id += 1
            return self._cur_lobby_id - 1
        
    async def add_user(self, lobby_id):
        if lobby_id not in self._lobby:
            raise ActionException(_NO_LOBBY)
        async with lock:
            user = await User.add_or_get(self._cur_user_id)
            self._users[self._cur_user_id] = user
            self._cur_user_id += 1
            await self._lobby[lobby_id].join_user(user)
            return self._cur_user_id - 1
        
    async def get_players(self, lobby_id):
        if lobby_id not in self._lobby:
            raise ActionException(_NO_LOBBY)
        players = await self._lobby[lobby_id].users()
        return "\n".join([str(player) for player in players])
    
    async def del_player(self, lobby_id, user_id):
        if lobby_id not in self._lobby:
            raise ActionException(_NO_LOBBY)
        if user_id not in self._users:
            raise ActionException(_NO_USER)
        await self._lobby[lobby_id].kick_user(self._users[user_id])
        
    async def start_game(self, lobby_id):
        if lobby_id not in self._lobby:
            raise ActionException(_NO_LOBBY)
        await self._lobby[lobby_id].start_game()
        
    async def end_game(self, lobby_id):
        if lobby_id not in self._lobby:
            raise ActionException(_NO_LOBBY)
        await self._lobby[lobby_id].end_game()
        
    async def get_round(self, lobby_id):
        if lobby_id not in self._lobby:
            raise ActionException(_NO_LOBBY)
        return self._lobby[lobby_id].round()
    
    async def get_env_info(self, lobby_id, user_id):
        if lobby_id not in self._lobby:
            raise ActionException(_NO_LOBBY)
        if user_id not in self._users:
            raise ActionException(_NO_USER)
        return await self._lobby[lobby_id].field_for_user(self._users[user_id])
    
    def count_stones(self, lobby_id):
        if lobby_id not in self._lobby:
            raise ActionException(_NO_LOBBY)
        return self._lobby[lobby_id].stones_left()
    
    async def end_round(self, lobby_id):
        if lobby_id not in self._lobby:
            raise ActionException(_NO_LOBBY)
        await self._lobby[lobby_id].end_round()
        
    async def leave_stone(self, user_id: int):
        if user_id not in self._users:
            raise ActionException(_NO_USER)
        await self._users[user_id].leave_stone()
        
    async def make_move(self, move: SMoveMaker):
        if move.user_id not in self._users:
            raise ActionException(_NO_USER)
        await self._users[move.user_id].choose_stone(move.stone_id)
    

class GameApiHendler:
    
    def __init__(self, n_stones: int = 5, n_players: int = 2):
        
        self._n_stones = 2
        self._n_players = 2
        self._n_max_rounds = 5
        
        self._player_id_to_user = dict()
        self._player_id_to_lobby_id = dict()
        self._lobby_id_to_lobby = dict()
        self._cur_lobby = None
        self._cur_lobby_id = 0
        self._lobby_id_to_state =  dict()
        self._lobby_id_to_stones = dict()
        self._informed_players = defaultdict(set)
        self._acted_players = defaultdict(set)
        
    async def add_player(self, user_id: SUserID):
        if user_id.user_id in self._player_id_to_user:
            raise ActionException(_ALREADY_IN_LOBBY)
        async with lock:
            player = await User.add_or_get(user_id.user_id)
            self._player_id_to_user[user_id.user_id] = player
            if self._cur_lobby is not None:
                await self._cur_lobby.join_user(player)
            else:
                self._cur_lobby = await Lobby.make_lobby(self._n_stones)
                await self._cur_lobby.join_user(player)
            self._lobby_id_to_lobby[self._cur_lobby_id] = self._cur_lobby
            self._player_id_to_lobby_id[user_id.user_id] = self._cur_lobby_id
            if len(await self._cur_lobby.users()) == self._n_players:
                self._cur_lobby = None
                self._cur_lobby_id += 1
                
    async def start_game(self, user: SUserID):
        if user.user_id not in self._player_id_to_user:
            raise ActionException(_NO_USER)
        if self._player_id_to_lobby_id[user.user_id] == self._cur_lobby_id:
            raise ActionException(_NOT_ENOUGH_PLAYERS)
        lobby_id = self._player_id_to_lobby_id[user.user_id]
        if self._lobby_id_to_lobby[lobby_id].status() != "waiting":
            raise ActionException(_GAME_IS_RUNNING)
        async with lock:
            await self._lobby_id_to_lobby[lobby_id].start_game()
            self._lobby_id_to_state[lobby_id] = 2
            self._lobby_id_to_stones[lobby_id] = SetStones(self._n_stones)
            
    async def get_env_info(self, user: SUserID):
        if user.user_id not in self._player_id_to_user:
            raise ActionException(_NO_USER)
        lobby_id = self._player_id_to_lobby_id[user.user_id]
        if lobby_id not in self._lobby_id_to_state:
            raise ActionException(_GAME_IS_NOT_RUNNING)
        if self._lobby_id_to_state[lobby_id] != 1:
            return {
                "message" : "Cannot get env info. Current state is {}".format(
                    GAME_STATES[self._lobby_id_to_state[lobby_id]])
            }
        _ = await self._lobby_id_to_lobby[lobby_id].field_for_user(
            self._player_id_to_user[user.user_id])
        env_info = str(self._lobby_id_to_stones[lobby_id])
        self._informed_players[lobby_id].add(user.user_id)
        if len(self._informed_players[lobby_id]) == self._n_players:
            self._informed_players[lobby_id] = set()
            self._lobby_id_to_state[lobby_id] = 2
        return {"env_info": env_info}
    
    async def make_move(self, move: SMoveMaker):
        user_id, stone_id = move.user_id, move.stone_id
        if user_id not in self._player_id_to_user:
            raise ActionException(_NO_USER)
        if stone_id not in set(list(range(1, self._n_stones+1))):
            raise ActionException(_NO_STONE)
        lobby_id = self._player_id_to_lobby_id[user_id]
        if lobby_id not in self._lobby_id_to_state:
            raise ActionException(_GAME_IS_NOT_RUNNING)
        if self._lobby_id_to_state[lobby_id] != 2:
            return {
                "message" : "Cannot make move. Current state is {}".format(
                    GAME_STATES[self._lobby_id_to_state[lobby_id]])
            }
        try:
            await self._player_id_to_user[user_id].leave_stone()
            await self._player_id_to_user[user_id].choose_stone(stone_id)
        except ActionException as e:
            pass    
        self._lobby_id_to_stones[lobby_id].make_move(user_id, stone_id)
        self._acted_players[lobby_id].add(user_id)
        if len(self._acted_players[lobby_id]) == self._n_players:
            self._acted_players[lobby_id] = set()
            self._lobby_id_to_state[lobby_id] = 1
            self._lobby_id_to_stones[lobby_id].handle()
            if self._lobby_id_to_stones[lobby_id].get_cnt_stones() == 0:
                async with lock:
                    await self._lobby_id_to_lobby[lobby_id].end_round()
                    self._lobby_id_to_state[lobby_id] = 2
                    self._lobby_id_to_stones[lobby_id] = SetStones(self._n_stones)
                    self._informed_players[lobby_id] = set()
                    self._acted_players[lobby_id] = set()
                    return {"message": "The round has ended. New round starts."}
                
        return {"message": "The move has been made"}
    
    def get_current_state(self, user: SUserID):
        if user.user_id not in self._player_id_to_user:
            raise ActionException(_NO_USER)
        lobby_id = self._player_id_to_lobby_id[user.user_id]
        if lobby_id not in self._lobby_id_to_state:
            raise ActionException(_GAME_IS_NOT_RUNNING)
        return {
            "state": GAME_STATES[self._lobby_id_to_state[lobby_id]]}
        
    async def end_game(self, user_id: int):
        if user_id not in self._player_id_to_user:
            raise ActionException(_NO_USER)
        lobby_id = self._player_id_to_lobby_id[user_id]
        del_players = []
        for cur_player_id, cur_lobby_id in self._player_id_to_lobby_id.items():
            if lobby_id == cur_lobby_id:
                del_players.append(cur_player_id)
        for player_id in del_players:
            self._player_id_to_lobby_id.pop(player_id)
            self._player_id_to_user.pop(player_id)
        await self._lobby_id_to_lobby[lobby_id].end_game()
        self._lobby_id_to_lobby.pop(lobby_id)
        self._lobby_id_to_state.pop(lobby_id)
        self._lobby_id_to_stones.pop(lobby_id)
        
    def reset(self):
        # вспомогательный метод
        self.__init__()
        
    def set_config(self, config: SGameConfig):
        self._n_stones = config.n_stones
        self._n_players = config.n_players
        
        
    
        
        
    
        

    
