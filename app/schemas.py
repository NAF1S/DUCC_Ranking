from pydantic import BaseModel, field_validator, Field
from typing import Optional
import re

class PlayerBase(BaseModel):
    name: Optional[str] = None
    fide_id: Optional[int] = None
    chesscom_username: Optional[str] = None
    lichess_username: Optional[str] = None

class PlayerCreate(PlayerBase):
    @field_validator('chesscom_username')
    @classmethod
    def validate_chesscom_username(cls, v):
        if v is not None:
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
            v = v.strip()
            if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
                raise ValueError('Lichess username can only contain alphanumeric characters, dots, dashes, and underscores')
            if len(v) < 2 or len(v) > 50:
                raise ValueError('Lichess username must be between 2 and 50 characters')
        return v    @field_validator('fide_id')
    @classmethod
    def validate_fide_id(cls, v):
        if v is not None:
            if v < 100000 or v > 99999999:
                raise ValueError('Invalid FIDE ID format')
        return v

    @field_validator('*', mode='before')
    @classmethod
    def validate_at_least_one(cls, v, info):
        if info.field_name == 'lichess_username' and not info.data.get('chesscom_username'):
            if not v:
                raise ValueError('At least one username (Chess.com or Lichess) is required')
        return v

class Player(PlayerBase):
    id: int
    chesscom_rating: Optional[float] = None
    lichess_rating: Optional[float] = None
    highest_rating: Optional[float] = None

    model_config = {
        'from_attributes': True
    }

class PlayerRanking(Player):
    rank: int

class PlayerRating(BaseModel):
    username: str
    name: Optional[str] = None
    fide_id: Optional[int] = None
    lichess_rapid_rating: Optional[float] = None
    fide_rating: Optional[float] = None

    model_config = {
        'from_attributes': True
    }

class SyncStats(BaseModel):
    total_players: int
    players_with_ratings: int
    platform_stats: dict
    last_sync: Optional[str]
    sync_interval_minutes: int

class SyncStatus(BaseModel):
    is_running: bool
    is_syncing: bool
    last_sync: Optional[str]
    sync_interval_minutes: int