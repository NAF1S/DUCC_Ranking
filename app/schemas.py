from pydantic import BaseModel, field_validator, Field
from typing import Optional
from datetime import datetime
import re

class PlayerBase(BaseModel):
    name: str
    fide_id: Optional[int] = None
    chesscom_username: Optional[str] = None
    lichess_username: Optional[str] = None

class PlayerCreate(PlayerBase):
    @field_validator('chesscom_username')
    @classmethod
    def validate_chesscom_username(cls, v):
        if v is not None:
            if not v:  # Empty string
                return None
            v = v.strip()
            if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
                raise ValueError('Chess.com username can only contain alphanumeric characters, dots, dashes, and underscores')
            if len(v) < 3 or len(v) > 50:
                raise ValueError('Chess.com username must be between 3 and 50 characters')
        return v

    @field_validator('lichess_username')
    @classmethod
    def validate_lichess_username(cls, v):
        if v is not None:
            if not v:  # Empty string
                return None
            v = v.strip()
            if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
                raise ValueError('Lichess username can only contain alphanumeric characters, dots, dashes, and underscores')
            if len(v) < 2 or len(v) > 50:
                raise ValueError('Lichess username must be between 2 and 50 characters')
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v:
            raise ValueError('Player name is required')
        return v.strip()

    @field_validator('fide_id')
    @classmethod
    def validate_fide_id(cls, v):
        if v is not None:
            if v < 100000 or v > 99999999:
                raise ValueError('Invalid FIDE ID format (must be between 100000 and 99999999)')
        return v

class Player(PlayerBase):
    id: int
    fide_rating: Optional[float] = None
    chesscom_rating: Optional[float] = None
    lichess_rating: Optional[float] = None
    highest_rating: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PlayerRanking(Player):
    rank: int = Field(..., description="Player's rank based on highest rating")

class PlayerUpdate(BaseModel):
    name: str
    fide_id: Optional[int] = None
    chesscom_username: Optional[str] = None
    lichess_username: Optional[str] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is None or not v.strip():
            raise ValueError('Player name is required')
        return v.strip()

    @field_validator('chesscom_username')
    @classmethod
    def validate_chesscom_username(cls, v):
        if v is None or not v.strip():
            return None
            
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Chess.com username can only contain alphanumeric characters, dots, dashes, and underscores')
        if len(v) < 3 or len(v) > 50:
            raise ValueError('Chess.com username must be between 3 and 50 characters')
        return v

    @field_validator('lichess_username')
    @classmethod
    def validate_lichess_username(cls, v):
        if v is None or not v.strip():
            return None
            
        v = v.strip()
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Lichess username can only contain alphanumeric characters, dots, dashes, and underscores')
        if len(v) < 2 or len(v) > 50:
            raise ValueError('Lichess username must be between 2 and 50 characters')
        return v

    @field_validator('fide_id')
    @classmethod
    def validate_fide_id(cls, v):
        if v is None:
            return None
        try:
            v = int(v)
            if v < 100000 or v > 99999999:
                raise ValueError('Invalid FIDE ID format (must be between 100000 and 99999999)')
            return v
        except (ValueError, TypeError):
            return None