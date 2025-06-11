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
from . import sheet_sync

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
    if not player.chesscom_username and not player.lichess_username:
        raise HTTPException(status_code=400, detail="At least one username (Chess.com or Lichess) is required")

    db_player = models.Player(**player.dict())
    db.add(db_player)
    db.commit()
    db.refresh(db_player)

    # Update ratings in background
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
    """Get all players with their names and FIDE IDs"""
    players = db.query(models.Player).all()
    ratings_list = []

    for player in players:
        if player.fide_id:
            try:
                # Fetch FIDE rating for player
                fide_data = await ChessService.get_fide_rating(player.fide_id)
                fide_rating = fide_data.get('standard_rating') if fide_data else None
            except Exception as e:
                logger.error(f"Error fetching FIDE rating for player {player.name}: {str(e)}")
                fide_rating = None
        else:
            fide_rating = None

        ratings_list.append({
            "name": player.name or "-",
            "fide_id": str(player.fide_id) if player.fide_id else "-",
            "fide_rating": str(fide_rating) if fide_rating else "-"
        })

    return ratings_list

@app.post("/sync/sheet/")
async def sync_google_sheet(
    spreadsheet_id: str,
    range_name: str = "Sheet1!A:B",
    db: Session = Depends(get_db)
):
    """Sync player names and FIDE IDs from Google Sheet"""
    try:
        await sheet_sync.sync_sheet_data(db, spreadsheet_id, range_name)
        return {"message": "Successfully synced data from Google Sheet"}
    except Exception as e:
        logger.error(f"Error in sheet sync: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync data from Google Sheet: {str(e)}"
        )

async def insert_test_data(db: Session):
    """Insert test data if database is empty"""
    if db.query(models.Player).count() == 0:
        test_players = [
            {
                "name": "John Doe",
                "fide_id": 12345678,
                "chesscom_username": "JohnDoe123",
                "lichess_username": "JohnLichess",
                "chesscom_rating": 1850,
                "lichess_rating": 1920
            },
            {
                "name": "Alice Smith",
                "fide_id": 23456789,
                "chesscom_username": "AliceChess",
                "lichess_username": "AliceLichess",
                "chesscom_rating": 2100,
                "lichess_rating": 2150
            }
        ]
        
        for player_data in test_players:
            player = models.Player(**player_data)
            db.add(player)
        
        try:
            db.commit()
            logger.info("Test data inserted successfully")
        except Exception as e:
            db.rollback()
            logger.error(f"Error inserting test data: {str(e)}")

# Call insert_test_data on startup
@app.on_event("startup")
async def startup_event():
    db = SessionLocal()
    try:
        await insert_test_data(db)
    finally:
        db.close()
