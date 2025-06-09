from pydantic import BaseModel
from typing import Optional

class PlayerCreate(BaseModel):
    chesscom_username: Optional[str] = None
    lichess_username: Optional[str] = None

class Player(BaseModel):
    id: int
    chesscom_username: Optional[str] = None
    lichess_username: Optional[str] = None
    chesscom_rating: Optional[float] = None
    lichess_rating: Optional[float] = None

    class Config:
        orm_mode = True 