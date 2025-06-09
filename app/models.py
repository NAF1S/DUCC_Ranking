from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .database import Base

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    chesscom_username = Column(String, unique=True, nullable=True)
    lichess_username = Column(String, unique=True, nullable=True)
    chesscom_rating = Column(Float, nullable=True)
    lichess_rating = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 