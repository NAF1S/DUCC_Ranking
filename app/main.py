from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
import os
from . import models, database, schemas
from .database import engine, SessionLocal
from .services import ChessService
from .logger import setup_logger

# Set up logger
logger = setup_logger('main')

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

# Mount static files
project_dir = os.path.dirname(os.path.dirname(__file__))
static_dir = os.path.join(project_dir, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Index file not found")

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

        # Update highest rating
        ratings = [r for r in [player.chesscom_rating, player.lichess_rating] if r is not None]
        if ratings:
            player.highest_rating = max(ratings)

        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating ratings for player {player.id}: {str(e)}")
        return False

@app.post("/players/", response_model=schemas.Player)
async def create_player(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    """Create a new player"""
    # At least one identifier (FIDE ID, Chess.com username, or Lichess username) is required
    if not player.fide_id and not player.chesscom_username and not player.lichess_username:
        raise HTTPException(
            status_code=400, 
            detail="At least one identifier (FIDE ID, Chess.com username, or Lichess username) is required"
        )

    db_player = models.Player(**player.dict())
    db.add(db_player)
    
    try:
        db.commit()
        db.refresh(db_player)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating player: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    # Update ratings in background
    if db_player.chesscom_username or db_player.lichess_username:
        await update_player_ratings(db_player, db)
    
    return db_player

@app.get("/players/", response_model=List[schemas.Player])
def get_players(db: Session = Depends(get_db)):
    """Get all players"""
    return db.query(models.Player).all()

@app.get("/players/rankings/", response_model=List[schemas.PlayerRanking])
def get_rankings(db: Session = Depends(get_db)):
    """Get player rankings"""
    players = db.query(models.Player).order_by(models.Player.highest_rating.desc()).all()
    rankings = []
    for i, player in enumerate(players, 1):
        player_dict = schemas.PlayerRanking.from_orm(player).dict()
        player_dict['rank'] = i
        rankings.append(schemas.PlayerRanking(**player_dict))
    return rankings

@app.post("/players/{player_id}/update/")
async def update_player(player_id: int, db: Session = Depends(get_db)):
    """Update a player's ratings"""
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    success = await update_player_ratings(player, db)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update player ratings")
    return {"message": "Ratings updated successfully"}

@app.get("/players/ratings/")
async def get_player_ratings(db: Session = Depends(get_db)):
    """Get all players with their names, FIDE IDs, and ratings from all platforms"""
    players = db.query(models.Player).all()
    ratings_list = []

    for player in players:
        # Initialize rating data
        rating_data = {
            "name": player.name or "-",
            "fide_id": str(player.fide_id) if player.fide_id else "-",
            "fide_rating": "-",
            "chesscom_rating": "-",
            "lichess_rating": "-"
        }

        # If player has FIDE ID, fetch their rating
        if player.fide_id:
            try:
                logger.info(f"Fetching FIDE rating for player {player.name} with ID {player.fide_id}")
                fide_data = await ChessService.get_fide_rating(player.fide_id)
                if fide_data and fide_data.get('rapid_rating'):
                    rating_data["fide_rating"] = str(fide_data['rapid_rating'])
                    logger.info(f"Found FIDE rapid rating {fide_data['rapid_rating']} for player {player.name}")
            except Exception as e:
                logger.error(f"Error fetching FIDE rating for player {player.name}: {str(e)}")

        # Get Chess.com rating
        if player.chesscom_username:
            try:
                logger.info(f"Fetching Chess.com rating for player {player.name}")
                chesscom_data = await ChessService.get_chesscom_rating(player.chesscom_username)
                if chesscom_data:
                    rating_data["chesscom_rating"] = str(chesscom_data)
            except Exception as e:
                logger.error(f"Error fetching Chess.com rating for player {player.name}: {str(e)}")

        # Get Lichess rating
        if player.lichess_username:
            try:
                logger.info(f"Fetching Lichess rating for player {player.name}")
                lichess_data = await ChessService.get_lichess_rating(player.lichess_username)
                if lichess_data:
                    rating_data["lichess_rating"] = str(lichess_data)
            except Exception as e:
                logger.error(f"Error fetching Lichess rating for player {player.name}: {str(e)}")
                
        ratings_list.append(rating_data)

    # Sort the ratings list by FIDE rating (highest to lowest)
    def get_fide_rating(player):
        try:
            return float(player['fide_rating']) if player['fide_rating'] != '-' else -1
        except (ValueError, TypeError):
            return -1

    ratings_list.sort(key=get_fide_rating, reverse=True)
    return ratings_list



@app.delete("/players/delete/{player_name}")
async def delete_player(player_name: str, db: Session = Depends(get_db)):
    """Delete a player by name"""
    try:
        # Find and delete the player
        player = db.query(models.Player).filter(models.Player.name == player_name).first()
        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_name} not found")
        
        db.delete(player)
        db.commit()
        
        return {"message": f"Player {player_name} deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting player {player_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

