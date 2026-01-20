@echo off
echo Starting EscapeCircuit (Backend and Frontend)...
@REM echo.
@REM echo Initializing database...
@REM python src\init_db.py
@REM if errorlevel 1 (
@REM     echo Database initialization failed.
@REM     pause
@REM     exit /b 1
@REM )

@REM echo.
@REM echo Loading riddles...
@REM python src\insert_riddles.py
@REM if errorlevel 1 (
@REM     echo Riddle loading failed.
@REM     pause
@REM     exit /b 1
@REM )

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
