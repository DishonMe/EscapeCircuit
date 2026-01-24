@echo off
echo Starting EscapeCircuit (Backend and Frontend)...
echo.
echo Initializing database...
python src\init_db.py
if errorlevel 1 (
    echo Database initialization failed.
    pause
    exit /b 1
)

echo.
echo Loading riddles...
python src\insert_riddles.py
if errorlevel 1 (
    echo Riddle loading failed.
    pause
    exit /b 1
)

echo.
echo Seeding admin user...
python src\seed_admin.py
if errorlevel 1 (
    echo Admin user seeding failed.
    pause
    exit /b 1
)

echo.
echo Starting servers...
echo Press Ctrl+C to stop both servers.

:: Use npx concurrently to run both commands in the same terminal
:: -k: kill others if one fails
:: --names: labels for output
:: -c: colors for output
call npx -y concurrently -k -n "API,WEB" -c "blue,magenta" ^
  "pip install -r requirements.txt && cd src && python -m uvicorn Backend.main:app --reload --host 127.0.0.1 --port 8080" ^
  "cd apps\nextjs-app && npm run dev"

pause
