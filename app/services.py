import os
import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

class ChessService:
    @staticmethod
    async def get_chesscom_rating(username: str) -> float:
        """Fetch Chess.com rating for a player"""
        try:
            url = f"https://api.chess.com/pub/player/{username}/stats"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Get the highest rating from all time controls
                        ratings = [
                            data.get('chess_daily', {}).get('last', {}).get('rating', 0),
                            data.get('chess_rapid', {}).get('last', {}).get('rating', 0),
                            data.get('chess_blitz', {}).get('last', {}).get('rating', 0),
                            data.get('chess_bullet', {}).get('last', {}).get('rating', 0)
                        ]
                        return max(ratings) if max(ratings) > 0 else None
                    elif response.status == 404:
                        print(f"Player {username} not found on Chess.com")
                        return None
                    else:
                        print(f"Error fetching Chess.com rating: HTTP {response.status}")
                        return None
        except Exception as e:
            print(f"Error fetching Chess.com rating: {e}")
            return None

    @staticmethod
    async def get_lichess_rating(username: str) -> float:
        """Fetch Lichess rating for a player"""
        try:
            url = f"https://lichess.org/api/user/{username}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Get the highest rating from all time controls
                        ratings = [
                            data.get('perfs', {}).get('bullet', {}).get('rating', 0),
                            data.get('perfs', {}).get('blitz', {}).get('rating', 0),
                            data.get('perfs', {}).get('rapid', {}).get('rating', 0),
                            data.get('perfs', {}).get('classical', {}).get('rating', 0)
                        ]
                        return max(ratings) if max(ratings) > 0 else None
                    elif response.status == 404:
                        print(f"Player {username} not found on Lichess")
                        return None
                    else:
                        print(f"Error fetching Lichess rating: HTTP {response.status}")
                        return None
        except Exception as e:
            print(f"Error fetching Lichess rating: {e}")
            return None 
        
    @staticmethod
    async def get_fide_rating(fide_id: int, timeout: int = 10) -> dict:
        """
        Scrape FIDE ratings for Standard, Rapid, and Blitz for a given player ID
        
        Args:
            fide_id: FIDE ID number
            timeout: Request timeout in seconds
        
        Returns:
            dict: Player information including all three ratings, or None if failed
        """
        url = f"https://ratings.fide.com/profile/{fide_id}"
        
        # Headers to mimic a real browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        try:
            print(f"Fetching data from: {url}")
            
            # Use aiohttp for async consistency with other methods
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        print(f"HTTP Error: {response.status}")
                        return None
                    
                    html_content = await response.text()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Initialize player data dictionary
            player_data = {
                'fide_id': fide_id,
                'name': None,
                'country': None,
                'standard_rating': None,
                'rapid_rating': None,
                'blitz_rating': None
            }
            
            # Extract player name (usually in h1 tag)
            name_element = soup.find('h1')
            if name_element:
                player_data['name'] = name_element.text.strip()
            
            # Find the directory section
            directory_section = soup.find('section', class_='directory')
            if not directory_section:
                print("Could not find directory section")
                return None
            
            # Find profile-section within directory
            profile_section = directory_section.find('div', class_='profile-section')
            if not profile_section:
                print("Could not find profile-section")
                return None
            
            # Find profile-games within profile-section
            profile_games = profile_section.find('div', class_='profile-games')
            if not profile_games:
                print("Could not find profile-games")
                return None
            
            # Find all game type divs (should be 3: standard, rapid, blitz)
            game_divs = profile_games.find_all('div', recursive=False)
            
            print(f"Found {len(game_divs)} game type sections")
            
            # Process each game type div
            for i, game_div in enumerate(game_divs):
                # Get the first <p> tag which should contain the rating
                first_p = game_div.find('p')
                if first_p:
                    rating_text = first_p.text.strip()
                    print(f"Game type {i + 1} rating text: '{rating_text}'")
                    
                    # Extract numeric rating from the text
                    rating_match = re.search(r'\b(\d{3,4})\b', rating_text)
                    if rating_match:
                        rating = int(rating_match.group(1))
                        
                        # Determine which type based on position or content
                        if i == 0:  # First div is typically Standard
                            player_data['standard_rating'] = rating
                        elif i == 1:  # Second div is typically Rapid
                            player_data['rapid_rating'] = rating
                        elif i == 2:  # Third div is typically Blitz
                            player_data['blitz_rating'] = rating
                        
                        print(f"Extracted rating: {rating}")
                    else:
                        print(f"No numeric rating found in: {rating_text}")
                else:
                    print(f"No <p> tag found in game div {i + 1}")
            
            # Try to extract country information
            try:
                country_element = soup.find('img', {'alt': re.compile(r'.*flag.*', re.I)})
                if country_element and country_element.get('title'):
                    player_data['country'] = country_element['title']
            except:
                pass
            
            return player_data
            
        except asyncio.TimeoutError:
            print(f"Request timeout for FIDE ID: {fide_id}")
            return None
        except Exception as e:
            print(f"Error fetching FIDE rating: {e}")
            return None

    @staticmethod
    async def get_fide_highest_rating(fide_id: int) -> int:
        """
        Get the highest rating from FIDE (Standard, Rapid, or Blitz)
        
        Args:
            fide_id: FIDE ID number
            
        Returns:
            int: Highest rating, or None if failed
        """
        player_data = await ChessService.get_fide_rating(fide_id)
        if not player_data:
            return None
        
        ratings = [
            player_data.get('standard_rating', 0) or 0,
            player_data.get('rapid_rating', 0) or 0,
            player_data.get('blitz_rating', 0) or 0
        ]
        
        max_rating = max(ratings)
        return max_rating if max_rating > 0 else None

    @staticmethod
    async def get_all_ratings(chess_com_username: str = None, 
                            lichess_username: str = None, 
                            fide_id: int = None) -> dict:
        """
        Get ratings from all platforms for a player
        
        Args:
            chess_com_username: Chess.com username
            lichess_username: Lichess username  
            fide_id: FIDE ID number
            
        Returns:
            dict: All available ratings and player info
        """
        results = {
            'chess_com': None,
            'lichess': None,
            'fide': None,
            'highest_overall': 0
        }
        
        # Create tasks for concurrent execution
        tasks = []
        
        if chess_com_username:
            tasks.append(('chess_com', ChessService.get_chesscom_rating(chess_com_username)))
        
        if lichess_username:
            tasks.append(('lichess', ChessService.get_lichess_rating(lichess_username)))
        
        if fide_id:
            tasks.append(('fide', ChessService.get_fide_rating(fide_id)))
        
        # Execute all requests concurrently
        if tasks:
            completed_tasks = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            for i, (platform, _) in enumerate(tasks):
                result = completed_tasks[i]
                if not isinstance(result, Exception) and result is not None:
                    results[platform] = result
                    
                    # Update highest overall rating
                    if platform == 'fide':
                        fide_highest = await ChessService.get_fide_highest_rating(fide_id)
                        if fide_highest and fide_highest > results['highest_overall']:
                            results['highest_overall'] = fide_highest
                    else:
                        if result > results['highest_overall']:
                            results['highest_overall'] = result
        
        return results

# Example usage and testing
async def test_chess_service():
    """Test function to demonstrate usage"""
    
    # Test individual services
    print("Testing Chess.com...")
    chess_com_rating = await ChessService.get_chesscom_rating("hikaru")
    print(f"Chess.com rating: {chess_com_rating}")
    
    print("\nTesting Lichess...")
    lichess_rating = await ChessService.get_lichess_rating("DrNykterstein")
    print(f"Lichess rating: {lichess_rating}")
    
    print("\nTesting FIDE...")
    fide_data = await ChessService.get_fide_rating(10297677)
    print(f"FIDE data: {fide_data}")
    
    # Test getting highest FIDE rating
    fide_highest = await ChessService.get_fide_highest_rating(10297677)
    print(f"FIDE highest rating: {fide_highest}")
    
    # Test getting all ratings for a player
    print("\nTesting all ratings...")
    all_ratings = await ChessService.get_all_ratings(
        chess_com_username="hikaru",
        lichess_username="DrNykterstein", 
        fide_id=10297677
    )
    print(f"All ratings: {all_ratings}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_chess_service())