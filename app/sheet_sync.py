import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from typing import List, Dict
import pickle
from sqlalchemy.orm import Session
from fastapi import HTTPException
from . import models
from .logger import setup_logger

logger = setup_logger('sheet_sync')

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_google_sheet_credentials():
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), 'token.pickle')
    
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            logger.info("Loaded existing credentials")
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            os.remove(token_path)
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Refreshed expired credentials")
            except Exception as e:
                logger.error(f"Error refreshing credentials: {str(e)}")
                creds = None
        
        if not creds:
            creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"Credentials file not found at {creds_path}")
            
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            logger.info("Generated new credentials")
            
            # Save the new credentials
            try:
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info(f"Saved new credentials to {token_path}")
            except Exception as e:
                logger.error(f"Error saving credentials: {str(e)}")

    return creds

def get_sheet_data(spreadsheet_id: str, range_name: str) -> List[Dict]:
    """
    Fetch data from Google Sheet
    Returns list of dictionaries with 'name' and 'fide_id' keys
    """
    try:
        creds = get_google_sheet_credentials()
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])

        if not values:
            logger.warning('No data found in sheet')
            return []

        # Convert values to list of dictionaries
        players_data = []
        for row in values[1:]:  # Skip header row
            try:
                # Expecting [Name, FIDE ID] format
                name = row[0].strip() if row[0] else None
                fide_id = int(row[1].strip()) if len(row) > 1 and row[1].strip() else None
                
                if name:  # Only add if name exists
                    players_data.append({
                        'name': name,
                        'fide_id': fide_id
                    })
            except (ValueError, IndexError) as e:
                logger.error(f"Error processing row {row}: {str(e)}")
                continue

        return players_data

    except Exception as e:
        logger.error(f"Error fetching sheet data: {str(e)}")
        raise

async def sync_sheet_data(db: Session, spreadsheet_id: str, range_name: str):
    """Sync data from Google Sheet to database"""
    try:
        logger.info(f"Starting sync from sheet {spreadsheet_id}")
        data = get_sheet_data(spreadsheet_id, range_name)
        
        if not data:
            logger.warning("No data found in sheet")
            raise ValueError("No data found in Google Sheet")

        # Start a transaction
        logger.info("Beginning database transaction")
        transaction = db.begin_nested()
        try:
            # Clear existing players
            deleted_count = db.query(models.Player).delete()
            logger.info(f"Deleted {deleted_count} existing players")
            
            # Track successful and failed entries
            success_count = 0
            error_count = 0
            
            for row in data:
                try:
                    if not row['name']:
                        logger.warning("Skipping row with empty name")
                        error_count += 1
                        continue

                    new_player = models.Player(
                        name=row['name'],
                        fide_id=row['fide_id']
                    )
                    db.add(new_player)
                    success_count += 1
                    logger.info(f"Added player: {row['name']} with FIDE ID: {row['fide_id']}")
                except Exception as row_error:
                    error_count += 1
                    logger.error(f"Error processing row {row}: {str(row_error)}")
                    continue

            # Commit the transaction if everything was successful
            transaction.commit()
            db.commit()
            
            logger.info(f"Sync completed. Added {success_count} players. {error_count} errors.")
            return {
                "success": True,
                "message": f"Successfully synced {success_count} players from sheet",
                "details": {
                    "success_count": success_count,
                    "error_count": error_count,
                    "total_rows": len(data)
                }
            }
        except Exception as trans_error:
            transaction.rollback()
            logger.error(f"Transaction error: {str(trans_error)}")
            raise
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error syncing sheet data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync data from Google Sheet: {str(e)}"
        )
