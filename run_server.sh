#!/usr/bin/env bash
set -e

echo "Starting EscapeCircuit (Backend and Frontend)..."
echo

# Kill any stale Python/uvicorn processes that may be locking the database
echo "Cleaning up stale processes..."
pkill -f "uvicorn Backend.main:app" 2>/dev/null || true
if command -v lsof >/dev/null 2>&1; then
  LISTEN_PIDS=$(lsof -t -iTCP:8080 -sTCP:LISTEN 2>/dev/null | tr '\n' ' ')
  if [ -n "${LISTEN_PIDS// }" ]; then
    kill ${LISTEN_PIDS} 2>/dev/null || true
    sleep 1
    kill -9 ${LISTEN_PIDS} 2>/dev/null || true
  fi
fi
# Note: Do NOT delete WAL/SHM files — SQLite recovers them automatically
# and deleting them can lose committed data
sleep 2
echo "Done."
echo

echo "Initializing database..."
if ! python3 src/init_db.py; then
  echo "Database initialization failed."
  exit 1
fi
echo

echo "Loading riddles..."
if ! python3 src/insert_riddles.py; then
  echo "Riddle loading failed."
  exit 1
fi
echo

echo "Seeding admin user..."
if ! python3 src/seed_admin.py; then
  echo "Admin user seeding failed."
  exit 1
fi
echo

echo "Installing frontend dependencies..."
cd apps/nextjs-app
if ! npm install; then
  echo "Frontend dependency installation failed."
  cd ../..
  exit 1
fi
cd ../..
echo

echo "Starting servers..."
echo "Press Ctrl+C to stop both servers."
echo

# Use Python helper to load .env file and start servers with environment variables
python3 init_env.py
