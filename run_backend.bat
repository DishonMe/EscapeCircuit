@echo off
echo Installing dependencies...
pip install -r requirements.txt
echo Starting EscapeCircuit Backend...
cd src
python -m uvicorn Backend.main:app --reload --host 127.0.0.1 --port 8080
pause
