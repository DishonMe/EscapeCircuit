#!/bin/bash

echo "Starting EscapeCircuit (Backend and Frontend)..."
echo ""

# 1. Initialize Database
echo "Initializing database..."
# Changed slash to / and added python3 safety
python3 src/init_db.py
if [ $? -ne 0 ]; then
    echo "Database initialization failed."
    exit 1
fi

# 2. Load Riddles
echo ""
echo "Loading riddles..."
python3 src/insert_riddles.py
if [ $? -ne 0 ]; then
    echo "Riddle loading failed."
    exit 1
fi

# 3. Seed Admin User
echo ""
echo "Seeding admin user..."
python3 src/seed_admin.py
if [ $? -ne 0 ]; then
    echo "Admin user seeding failed."
    exit 1
fi

echo ""
echo "Starting servers..."
echo "Press Ctrl+C to stop both servers."

# 3. Start Servers
# Changed line continuation to \
# Changed paths to / (apps/nextjs-app)
npx -y concurrently -k -n "API,WEB" -c "blue,magenta" \
  "pip install -r requirements.txt && cd src && python3 -m uvicorn Backend.main:app --reload --host 127.0.0.1 --port 8080" \
  "cd apps/nextjs-app && npm run dev"