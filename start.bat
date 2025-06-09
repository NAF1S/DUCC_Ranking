@echo off
echo Starting DUCC Player Ranking application...
echo.
echo 1. Installing dependencies...
pip install -r requirements.txt

echo.
echo 2. Starting FastAPI server...
start cmd /k python run.py

echo.
echo 3. Opening the application in browser...
timeout /t 3 /nobreak > NUL
start "" index.html

echo.
echo Application startup complete!
echo.
echo You can now access the application in your browser.
echo If the page doesn't open automatically, open 'index.html' manually.
echo The API server is running at http://localhost:8000 