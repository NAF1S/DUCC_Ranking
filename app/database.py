from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

# Check if running on Vercel
IS_VERCEL = os.environ.get('VERCEL', False)

if IS_VERCEL:
    # Use in-memory SQLite for Vercel
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
else:
    # Use file-based SQLite for local development
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chess_players.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()