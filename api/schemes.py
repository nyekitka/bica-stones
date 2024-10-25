from pydantic import BaseModel
from typing import Optional

class Player(BaseModel):
    name: str
    surname: str
    
class SMove(BaseModel):
    player_id: int
    stone_id: Optional[int]
    