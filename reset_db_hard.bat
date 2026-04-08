@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo EscapeCircuit Hard DB Reset
echo.
echo WARNING: This will permanently delete all local database data:
echo   - users
echo   - puzzles
echo   - solve attempts/progress
echo   - ratings/discussions/notifications
echo.
set /p CONFIRM=Type RESET to continue (anything else cancels): 
if /I not "%CONFIRM%"=="RESET" (
    echo.
    echo Cancelled.
    exit /b 0
)

echo.
echo [1/6] Stopping running Python/uvicorn processes...
taskkill /F /IM uvicorn.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/6] Backing up current DB (if present)...
if exist "escape_circuit.db" (
    copy /Y "escape_circuit.db" "escape_circuit.db.bak" >nul
    echo Backup created: escape_circuit.db.bak
) else (
    echo No existing DB file found, skipping backup.
)

echo [3/6] Deleting DB files...
del /F /Q "escape_circuit.db" >nul 2>&1
del /F /Q "escape_circuit.db-wal" >nul 2>&1
del /F /Q "escape_circuit.db-shm" >nul 2>&1

echo [4/6] Initializing schema...
python "src\init_db.py"
if errorlevel 1 (
    echo ERROR: init_db failed.
    exit /b 1
)

echo [5/6] Importing riddles...
python "src\insert_riddles.py"
if errorlevel 1 (
    echo ERROR: insert_riddles failed.
    exit /b 1
)

echo [6/6] Seeding admin user...
python "src\seed_admin.py"
if errorlevel 1 (
    echo ERROR: seed_admin failed.
    exit /b 1
)

echo.
echo Hard reset complete.
echo Admin credentials: username=admin password=password123
echo.
echo Next step: run run_server.bat to start backend + frontend.

exit /b 0