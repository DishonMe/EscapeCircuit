@echo off
echo Starting EscapeCircuit (Backend and Frontend)...
echo.

:: Kill any stale Python/uvicorn processes that may be locking the database
echo Cleaning up stale processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM uvicorn.exe >nul 2>&1
timeout /t 1 /nobreak >nul
:: Remove SQLite WAL/SHM lock files if present
del /q "%~dp0escape_circuit.db-wal" >nul 2>&1
del /q "%~dp0escape_circuit.db-shm" >nul 2>&1
echo Done.
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
echo Installing frontend dependencies...
cd apps\nextjs-app
call npm install
if errorlevel 1 (
    echo Frontend dependency installation failed.
    cd ..\..
    pause
    exit /b 1
)
cd ..\..

echo.
echo Starting servers...
echo Press Ctrl+C to stop both servers.

:: Use npx concurrently to run both commands in the same terminal
:: -k: kill others if one fails
:: --names: labels for output
:: -c: colors for output
call npx -y concurrently -k -n "API,WEB" -c "blue,magenta" ^
  "pip install -r requirements.txt && cd src && python -m uvicorn Backend.main:app --reload --host 127.0.0.1 --port 8081" ^
  "cd apps\nextjs-app && npm run dev"

pause
