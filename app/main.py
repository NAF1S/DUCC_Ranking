from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import asyncio
from . import models, database, schemas
from .database import engine, SessionLocal
from .services import ChessService

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DUCC Player Ranking")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def update_player_ratings(player: models.Player, db: Session):
    """Update ratings for a player"""
    try:
        if player.chesscom_username:
            chesscom_rating = await ChessService.get_chesscom_rating(player.chesscom_username)
            if chesscom_rating:
                player.chesscom_rating = chesscom_rating

        if player.lichess_username:
            lichess_rating = await ChessService.get_lichess_rating(player.lichess_username)
            if lichess_rating:
                player.lichess_rating = lichess_rating

        db.commit()
        db.refresh(player)
    except Exception as e:
        print(f"Error updating ratings for player {player.id}: {e}")
        db.rollback()

@app.get("/")
async def root():
    return {"message": "Welcome to DUCC Player Ranking API"}

@app.post("/players/")
async def add_player(
    player: schemas.PlayerCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        if not player.chesscom_username and not player.lichess_username:
            raise HTTPException(status_code=400, detail="At least one username is required")

        # Check if player already exists
        existing_player = None
        if player.chesscom_username:
            existing_player = db.query(models.Player).filter(models.Player.chesscom_username == player.chesscom_username).first()
        if not existing_player and player.lichess_username:
            existing_player = db.query(models.Player).filter(models.Player.lichess_username == player.lichess_username).first()

        if existing_player:
            raise HTTPException(status_code=400, detail="Player already exists")

        # Create new player
        new_player = models.Player(
            chesscom_username=player.chesscom_username,
            lichess_username=player.lichess_username
        )
        db.add(new_player)
        db.commit()
        db.refresh(new_player)

        # Update ratings in background
        background_tasks.add_task(update_player_ratings, new_player, db)

        return new_player
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/players/", response_model=List[dict])
async def get_players(db: Session = Depends(get_db)):
    try:
        players = db.query(models.Player).all()
        return [
            {
                "id": player.id,
                "chesscom_username": player.chesscom_username,
                "lichess_username": player.lichess_username,
                "chesscom_rating": player.chesscom_rating,
                "lichess_rating": player.lichess_rating
            }
            for player in players
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/players/rankings/")
async def get_rankings(db: Session = Depends(get_db)):
    try:
        players = db.query(models.Player).all()
        # Sort players by their highest rating
        sorted_players = sorted(
            players,
            key=lambda x: max(
                x.chesscom_rating or 0,
                x.lichess_rating or 0
            ),
            reverse=True
        )
        return [
            {
                "rank": i + 1,
                "id": player.id,
                "chesscom_username": player.chesscom_username,
                "lichess_username": player.lichess_username,
                "chesscom_rating": player.chesscom_rating,
                "lichess_rating": player.lichess_rating,
                "highest_rating": max(
                    player.chesscom_rating or 0,
                    player.lichess_rating or 0
                )
            }
            for i, player in enumerate(sorted_players)
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/players/{player_id}/update/")
async def update_player_ratings_endpoint(
    player_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    try:
        player = db.query(models.Player).filter(models.Player.id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        background_tasks.add_task(update_player_ratings, player, db)
        return {"message": "Rating update started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 