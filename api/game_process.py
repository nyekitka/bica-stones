import asyncio
from utils import VariableWaiter
from schemes import Player, SMove

lock = asyncio.Lock()

states_of_game_process = {
    1: "waiting fot starting game",
    2: "Waiting for each player to receive information about the environment",
    3: "Waiting for each player's make move",
    4: "The previous game is over. Waiting for the start of a new game"
}

class GameProcess:
    
    def __init__(self, n_players=2, n_stones=2):
 
        self.waiter_for_starting_game = VariableWaiter()
        self.players_in_game = [] # id игроков, которые учавствуют в игре
        self.all_players = dict() # зарегистрированные игроки, id to player
        self.n_players = n_players
        self.n_stones = n_stones
        self.stone_to_players = dict()
        self.player_to_stone = dict()
        self.game_is_started = False
        self.current_state = 1
        self.players_recevied_env_info = set()
        self.current_moves = dict() # player_id to Stone
        
    def get_number_of_players(self):

        return len(self.all_players)
    
    def add_player(self, player: Player):
        
        if self.current_state != 1:
            return {"message": 
                f"You can't add player. Current state: {states_of_game_process[self.current_state]}"}

        if player in self.all_players.values():
            return {"message": "Player already exists."}
        player_id = self.get_number_of_players() + 1
        self.all_players[player_id] = player
        return {"message": "Player added."}
    
    def add_player_to_curr_game(self, player_id):
        
        if self.current_state != 1:
            return {"message": 
                f"You can't add player to the existing game. Current state: {states_of_game_process[self.current_state]}"}
        
        if not (player_id in self.all_players):
            return {"message": "Player not found."}
        if player_id in self.players_in_game:
            return {"message": "Player already in game."}
        self.players_in_game.append(player_id)
        return {"message": "Player added to game."}
 
    def game_can_be_started(self):
        return self.get_number_of_players() >= self.n_players
    
    def init_initial_state(self):

        self.stone_to_players = {(i+1): [] for i in range(self.n_stones)}
        self.player_to_stone = {player_id: None for player_id in self.players_in_game}
    
    async def wait_for_starting_game(self):

        async with lock:
            cnt_players = len(self.players_in_game)
            task = asyncio.create_task(self.waiter_for_starting_game.set_value(cnt_players))
            await task
        
        await self.waiter_for_starting_game.wait_for_value(self.n_players)
       
        self.init_initial_state() 
        self.game_is_started = True
        self.current_state = 2 
        
    def get_env_info(self, player_id):
        
        if self.current_state != 2:
            return {"message": 
                f"You can't get information about the environment. Current state: {states_of_game_process[self.current_state]}"}
        
        if player_id not in self.players_in_game:
            return {"message": "Player not in game"}
        
        self.players_recevied_env_info.add(player_id)
        
        if len(self.players_recevied_env_info) == len(self.players_in_game):
            self.current_state = 3
            self.players_recevied_env_info = set()
        
        return {
            "stone_to_players": self.stone_to_players,
            "player_to_stone": self.player_to_stone
            }
        
    def get_current_state(self):
        return {
            "message": states_of_game_process[self.current_state]
        }
    
    def handler(self):
        print()
        for player_id, stone_id in self.current_moves.items():
            
            if self.player_to_stone[player_id] is not None:
                self.stone_to_players[self.player_to_stone[player_id]].remove(player_id)
            
            self.player_to_stone[player_id] = stone_id
            if stone_id is not None:
                self.stone_to_players[stone_id].append(player_id)
         
        del_stones = set()   
        for stone_id, players_stone in self.stone_to_players.items():
            if len(players_stone) == 2:
        
                for player_id in players_stone:
                    self.player_to_stone[player_id] = None   
                del_stones.add(stone_id)
                
        for stone_id in del_stones:
            print(f"Stone {stone_id} was deleted.")
            self.stone_to_players.pop(stone_id)
        
            
    def make_move(self, player_id, move: SMove):
        
        if self.current_state != 3:
            return {"message": 
                f"You can't make a move. Current state: {states_of_game_process[self.current_state]}"}
        
        if player_id not in self.players_in_game:
            return {"message": "Player not in game"}
        
        if player_id in self.current_moves:
            return {"message": "Player already made a move"}
        
        if move.stone_id not in self.stone_to_players and move.stone_id != 0:
            return {"message": "Stone not found"}
        
        if move.stone_id != 0:
            self.current_moves[player_id] = move.stone_id
        else:
            self.current_moves[player_id] = None
        
        if len(self.current_moves) == len(self.players_in_game):
            self.handler()
            self.current_state = 2
            self.current_moves = dict()
            
            if len(self.stone_to_players) == 0:
                print("Game over")
                self.__init__()
        
        return {"message": "Move made"}
        
        
        