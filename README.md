# DUCC Player Ranking

A web application to track and display chess player rankings from Chess.com and Lichess.org.

## Features

- Add players with their Chess.com and/or Lichess.org usernames
- View player rankings sorted by highest rating
- Real-time updates of the rankings table
- Clean and modern user interface

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the FastAPI server:
```bash
python run.py
```

3. Open the `index.html` file in your web browser or serve it using a local web server.

## Usage

1. Enter a Chess.com username and/or Lichess.org username in the input fields
2. Click "Add Player" to add the player to the database
3. View the rankings table which automatically updates with the latest data
4. Players are ranked based on their highest rating across both platforms

## API Endpoints

- `GET /` - Welcome message
- `POST /players/` - Add a new player
- `GET /players/` - Get all players
- `GET /players/rankings/` - Get ranked list of players

## Note

This is a basic implementation. To get actual ratings from Chess.com and Lichess.org, you would need to:
1. Register for API keys from both platforms
2. Implement the rating fetching logic in the backend
3. Set up a periodic job to update ratings 