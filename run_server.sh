#!/bin/bash

echo "Starting EscapeCircuit (Backend and Frontend)..."
echo ""

# Kill any stale Python/uvicorn processes that may be locking the database
echo "Cleaning up stale processes..."
pkill -f python || true
pkill -f uvicorn || true
sleep 2
# Note: Do NOT delete WAL/SHM files — SQLite recovers them automatically
# and deleting them can lose committed data
echo "Done."
echo ""

# 1. Initialize Database
echo "Initializing database..."
python3 src/init_db.py
if [ $? -ne 0 ]; then
    echo "Database initialization failed."
    read -p "Press Enter to exit..." </dev/null
    exit 1
fi

# 2. Load Riddles
echo ""
echo "Loading riddles..."
python3 src/insert_riddles.py
if [ $? -ne 0 ]; then
    echo "Riddle loading failed."
    read -p "Press Enter to exit..." </dev/null
    exit 1
fi

# 3. Seed Admin User
echo ""
echo "Seeding admin user..."
python3 src/seed_admin.py
if [ $? -ne 0 ]; then
    echo "Admin user seeding failed."
    read -p "Press Enter to exit..." </dev/null
    exit 1
fi

echo ""
echo "Installing frontend dependencies..."
cd apps/nextjs-app
npm install
if [ $? -ne 0 ]; then
    echo "Frontend dependency installation failed."
    cd ../..
    read -p "Press Enter to exit..." </dev/null
    exit 1
fi
cd ../..

echo ""
echo "Starting servers..."
echo "Press Ctrl+C to stop both servers."
echo ""

# Start servers using Python environment setup
python3 init_env.py