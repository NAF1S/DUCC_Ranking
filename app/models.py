from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .database import Base

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)  # Allow manual ID assignment
    name = Column(String, nullable=False)  # Required field
    fide_id = Column(Integer, unique=True, nullable=True)
    chesscom_username = Column(String, unique=True, nullable=True)
    lichess_username = Column(String, unique=True, nullable=True)
    fide_rating = Column(Float, nullable=True, default=None)
    chesscom_rating = Column(Float, nullable=True, default=None)
    lichess_rating = Column(Float, nullable=True, default=None)
    highest_rating = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
