from pydantic import BaseModel
from typing import Optional


class SLobbyMaker(BaseModel):
    n_stones: int
    
    
class SUserID(BaseModel):
    user_id: int
   

class SMoveMaker(BaseModel):
    user_id: int
    stone_id: int 

class SGameConfig(BaseModel):
    n_stones: int
    n_players: int 