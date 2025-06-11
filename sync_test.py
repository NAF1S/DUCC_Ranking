import asyncio
import aiohttp
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sync():
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            logger.info("Attempting to sync with Google Sheet...")
            async with session.post(
                'http://localhost:8000/sync/sheet/',
                params={
                    'spreadsheet_id': '1FmzuR1jxHTfn8BCWsSztPtW8yfQJheij4NlU-lPPrKI',
                    'range_name': 'Sheet1!A:B'
                }
            ) as response:
                print(f"Status: {response.status}")
                print(f"Response: {await response.text()}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_sync())
