from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
import os
from datetime import datetime
from . import models, database, schemas
from .database import engine, SessionLocal
from .services import ChessService
from .logger import setup_logger

# Set up logger
logger = setup_logger('main')

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DUCC Player Ranking")

# Enable CORS for Vercel deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your Vercel frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if not os.getenv("VERCEL"):
    # Only mount static files in local development
    project_dir = os.path.dirname(os.path.dirname(__file__))
    static_dir = os.path.join(project_dir, "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_root():
    if os.getenv("VERCEL"):
        # When deployed on Vercel, serve the HTML content directly
        html_content = """
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chess Ratings Dashboard</title>
        <!-- Include your styles here -->
    </head>
    <body>
        <!-- Your HTML content will be injected here -->
    </body>
</html>
"""
        return HTMLResponse(content=html_content, status_code=200)
    else:
        # In local development, serve from static file
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
        ratings_updated = False
        
        if player.chesscom_username:
            try:
                chesscom_rating = await ChessService.get_chesscom_rating(player.chesscom_username)
                if chesscom_rating:
                    player.chesscom_rating = chesscom_rating
                    ratings_updated = True
            except Exception as e:
                logger.error(f"Error fetching Chess.com rating for {player.chesscom_username}: {str(e)}")

        if player.lichess_username:
            try:
                lichess_rating = await ChessService.get_lichess_rating(player.lichess_username)
                if lichess_rating:
                    player.lichess_rating = lichess_rating
                    ratings_updated = True
            except Exception as e:
                logger.error(f"Error fetching Lichess rating for {player.lichess_username}: {str(e)}")

        # Update highest rating
        ratings = [r for r in [player.fide_rating, player.chesscom_rating, player.lichess_rating] if r is not None]
        if ratings:
            player.highest_rating = max(ratings)
            ratings_updated = True

        if ratings_updated:
            db.commit()
        
        return True
    except Exception as e:
        logger.error(f"Error updating ratings for player {player.id}: {str(e)}")
        return False

# Replace the update_fide_rating function in main.py with this improved version

async def update_fide_rating(player: models.Player, db: Session):
    """Update FIDE rating for a player with better error handling and logging"""
    if not player.fide_id:
        logger.info(f"No FIDE ID for player {player.name}, skipping FIDE rating update")
        return False

    try:
        logger.info(f"Fetching FIDE rating for player {player.name} with FIDE ID {player.fide_id}")
        fide_data = await ChessService.get_fide_rating(player.fide_id)
        
        if not fide_data:
            logger.warning(f"No FIDE data returned for player {player.name} with FIDE ID {player.fide_id}")
            return False
        
        # Log the complete FIDE data for debugging
        logger.info(f"Complete FIDE data for {player.name}: {fide_data}")
        
        rapid_rating = fide_data.get('rapid_rating')
        if rapid_rating is None or rapid_rating == 0:
            logger.warning(f"No valid rapid rating found in FIDE data for player {player.name}. Raw value: {rapid_rating}")
            return False
            
        logger.info(f"Got FIDE rapid rating for player {player.name}: {rapid_rating}")
        
        # Store the old rating for comparison
        old_rating = player.fide_rating
        
        # Update the rating
        player.fide_rating = rapid_rating
        
        # Update highest rating considering the new FIDE rating
        ratings = [r for r in [player.fide_rating, player.chesscom_rating, player.lichess_rating] 
                  if r is not None and r > 0]
        if ratings:
            player.highest_rating = max(ratings)
            
        try:
            # Flush to ensure the changes are pending
            db.flush()
            
            # Verify the change was applied
            if player.fide_rating != rapid_rating:
                logger.error(f"Rating not properly set for {player.name}. Expected: {rapid_rating}, Got: {player.fide_rating}")
                return False
            
            # Commit the transaction
            db.commit()
            
            logger.info(f"Successfully updated FIDE rating for player {player.name} from {old_rating} to {rapid_rating}")
            return True
            
        except Exception as e:
            logger.error(f"Database error while updating FIDE rating for player {player.name}: {str(e)}")
            db.rollback()
            return False
            
    except Exception as e:
        logger.error(f"Error fetching FIDE rating for player {player.name}: {str(e)}")
        db.rollback()
        return False

@app.post("/players/", response_model=schemas.Player)
async def create_player(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    """Create a new player with dynamic ID based on ranking"""
    try:
        # Validate input
        if not player.fide_id and not player.chesscom_username and not player.lichess_username:
            raise HTTPException(
                status_code=400, 
                detail="At least one identifier (FIDE ID, Chess.com username, or Lichess username) is required"
            )

        # Check for duplicate usernames/IDs
        if player.fide_id and db.query(models.Player).filter(models.Player.fide_id == player.fide_id).first():
            raise HTTPException(status_code=400, detail="FIDE ID already exists")
        if player.chesscom_username and db.query(models.Player).filter(models.Player.chesscom_username == player.chesscom_username).first():
            raise HTTPException(status_code=400, detail="Chess.com username already exists")
        if player.lichess_username and db.query(models.Player).filter(models.Player.lichess_username == player.lichess_username).first():
            raise HTTPException(status_code=400, detail="Lichess username already exists")
        if db.query(models.Player).filter(models.Player.name == player.name).first():
            raise HTTPException(status_code=400, detail="Player name already exists")

        # Create new player
        db_player = models.Player(**player.dict())
        
        # Add to database temporarily to get ratings
        db.add(db_player)
        db.flush()  # This assigns a temporary ID        # Get initial ratings
        ratings_updated = False
        
        # First, get FIDE rating since it's usually more important
        if db_player.fide_id:
            if await update_fide_rating(db_player, db):
                ratings_updated = True
        
        # Then get other platform ratings
        if db_player.chesscom_username or db_player.lichess_username:
            if await update_player_ratings(db_player, db):
                ratings_updated = True

        # Now determine the correct ID based on rating
        players = get_players_by_rating(db)
        
        # Find where the new player should be inserted
        new_rank = 1
        for p in players:
            if p.id != db_player.id:  # Skip the new player
                if p.highest_rating is not None and (db_player.highest_rating is None or p.highest_rating > db_player.highest_rating):
                    new_rank += 1

        # Shift existing IDs if needed
        if new_rank <= len(players):
            db.execute(
                "UPDATE players SET id = id + 1 WHERE id >= :new_rank AND id != :temp_id",
                {"new_rank": new_rank, "temp_id": db_player.id}
            )

        # Assign the final ID
        db_player.id = new_rank
        
        # Commit all changes
        db.commit()
        db.refresh(db_player)
        
        return db_player
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating player: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/players/", response_model=List[schemas.Player])
def get_players(db: Session = Depends(get_db)):
    """Get all players"""
    return db.query(models.Player).all()

@app.get("/players/rankings/", response_model=List[schemas.PlayerRanking])
def get_rankings(db: Session = Depends(get_db)):
    """Get player rankings"""
    players = get_players_by_rating(db)
    rankings = []
    for player in players:
        player_dict = schemas.PlayerRanking.from_orm(player).dict()
        player_dict['rank'] = player.id  # Use the ID as rank since they're now synchronized
        rankings.append(schemas.PlayerRanking(**player_dict))
    return rankings

@app.post("/players/{player_id}/update/")
async def update_player(player_id: int, db: Session = Depends(get_db)):
    """Update a player's ratings"""
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")    # Update both FIDE and platform ratings
    fide_success = await update_fide_rating(player, db)
    platform_success = await update_player_ratings(player, db)
    
    if not fide_success and not platform_success:
        raise HTTPException(status_code=500, detail="Failed to update any ratings")
        
    return {"message": "Ratings updated successfully"}

@app.get("/players/ratings/")
async def get_player_ratings(refresh: bool = False, db: Session = Depends(get_db)):
    """Get all players with their names, FIDE IDs, and ratings from all platforms"""
    players = db.query(models.Player).all()
    ratings_list = []

    for player in players:        # Initialize rating data with stored database values        # Initialize rating data with stored database values
        rating_data = {
            "id": player.id,
            "name": player.name or "-",
            "fide_id": str(player.fide_id) if player.fide_id else "-",
            "fide_rating": str(player.fide_rating) if player.fide_rating not in [None, 0] else "-",
            "chesscom_rating": str(player.chesscom_rating) if player.chesscom_rating not in [None, 0] else "-",
            "lichess_rating": str(player.lichess_rating) if player.lichess_rating not in [None, 0] else "-"
        }
        
        # Log the rating data for debugging
        logger.info(f"Player {player.name} ratings: FIDE={player.fide_rating}, Chess.com={player.chesscom_rating}, Lichess={player.lichess_rating}")

        # Only fetch fresh ratings if refresh is requested
        if refresh:
            try:                # Update FIDE rating                # Handle FIDE rating update
                if player.fide_id:
                    logger.info(f"Refreshing FIDE rating for player {player.name}")
                    fide_success = await update_fide_rating(player, db)
                    if fide_success:
                        logger.info(f"Successfully updated FIDE rating in database: {player.fide_rating}")
                        rating_data["fide_rating"] = str(player.fide_rating) if player.fide_rating not in [None, 0] else "-"
                    else:
                        logger.warning(f"Failed to update FIDE rating for player {player.name}")
                        # Keep existing rating in rating_data

                if player.chesscom_username:
                    logger.info(f"Refreshing Chess.com rating for player {player.name}")
                    chesscom_data = await ChessService.get_chesscom_rating(player.chesscom_username)
                    if chesscom_data:
                        rating_data["chesscom_rating"] = str(chesscom_data)
                        player.chesscom_rating = chesscom_data

                if player.lichess_username:
                    logger.info(f"Refreshing Lichess rating for player {player.name}")
                    lichess_data = await ChessService.get_lichess_rating(player.lichess_username)
                    if lichess_data:
                        rating_data["lichess_rating"] = str(lichess_data)
                        player.lichess_rating = lichess_data

                # Update highest rating
                ratings = [r for r in [player.fide_rating, player.chesscom_rating, player.lichess_rating] if r is not None]
                if ratings:
                    player.highest_rating = max(ratings)
                
                db.commit()

            except Exception as e:
                logger.error(f"Error refreshing ratings for player {player.name}: {str(e)}")
                # Continue with stored ratings on error
                pass
                
        ratings_list.append(rating_data)    # Sort players by highest rating and update IDs
    players_sorted = get_players_by_rating(db)
    
    # Create a mapping of player IDs to their new rank
    rank_mapping = {p.id: i + 1 for i, p in enumerate(players_sorted)}
    
    # Update the ratings list with correct ranks
    for rating_data in ratings_list:
        player_id = rating_data["id"]
        rating_data["id"] = rank_mapping.get(player_id, player_id)  # Fallback to original ID if not found
    
    # Sort the list by ID (which now represents rank)
    ratings_list.sort(key=lambda x: x["id"])
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

@app.put("/players/{player_id}", response_model=schemas.Player)
async def update_player(player_id: int, player: schemas.PlayerUpdate, db: Session = Depends(database.get_db)):
    """Update a player's information"""
    try:
        # Log incoming data for debugging
        logger.info(f"Updating player {player_id} with data: {player.dict()}")
        db_player = db.query(models.Player).filter(models.Player.id == player_id).first()
        if not db_player:
            raise HTTPException(status_code=404, detail="Player not found")

        # Check for duplicate player name
        existing_player = db.query(models.Player).filter(
            models.Player.name == player.name,
            models.Player.id != player_id
        ).first()
        if existing_player:
            raise HTTPException(status_code=400, detail="Player name already exists")

        # Update player information
        db_player.name = player.name
        db_player.fide_id = player.fide_id
        db_player.chesscom_username = player.chesscom_username
        db_player.lichess_username = player.lichess_username
        db_player.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(db_player)
        return db_player
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating player {player_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def get_players_by_rating(db: Session):
    """Get players sorted by highest rating and assign new ranking-based IDs"""
    # Get all players ordered by highest rating
    players = db.query(models.Player).order_by(
        models.Player.highest_rating.desc().nulls_last(),
        models.Player.id.asc()  # Secondary sort by ID for stable ordering
    ).all()
    return players

def reassign_ids(db: Session):
    """Reassign IDs to all players based on their ranking"""
    players = get_players_by_rating(db)
    
    # Temporarily disable foreign key constraints if any
    db.execute("PRAGMA foreign_keys = OFF;")
    
    try:
        # Create a temporary table
        db.execute("CREATE TEMPORARY TABLE temp_players AS SELECT * FROM players;")
        db.execute("DELETE FROM players;")
        
        # Reinsert players with new IDs based on ranking
        for rank, player in enumerate(players, 1):
            player.id = rank
            db.add(player)
        
        db.commit()
        db.execute("DROP TABLE temp_players;")
    except Exception as e:
        db.rollback()
        db.execute("INSERT INTO players SELECT * FROM temp_players;")
        db.execute("DROP TABLE temp_players;")
        raise e
    finally:
        db.execute("PRAGMA foreign_keys = ON;")

def get_next_rank(db: Session, new_highest_rating: float = None) -> int:
    """Get the next rank (ID) for a new player based on their highest rating"""
    query = db.query(models.Player).order_by(
        models.Player.highest_rating.desc().nulls_last()
    )

    if new_highest_rating is None:
        # If no rating, add at the end
        return query.count() + 1

    # Count how many players have a higher rating
    higher_rated_count = query.filter(
        models.Player.highest_rating >= new_highest_rating
    ).count()

    return higher_rated_count + 1

