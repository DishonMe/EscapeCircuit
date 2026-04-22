#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "EscapeCircuit Hard DB Reset"
echo
echo "WARNING: This will permanently delete all local database data:"
echo "  - users"
echo "  - puzzles"
echo "  - solve attempts/progress"
echo "  - ratings/discussions/notifications"
echo

read -r -p "Type RESET to continue (anything else cancels): " CONFIRM
if [[ "$CONFIRM" != "RESET" ]]; then
  echo
  echo "Cancelled."
  exit 0
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "ERROR: python3 or python is required."
  exit 1
fi

echo
echo "[1/6] Stopping running Python/uvicorn processes..."
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "python.*Backend.main:app" 2>/dev/null || true
pkill -f "python3.*Backend.main:app" 2>/dev/null || true
sleep 2

echo "[2/6] Backing up current DB (if present)..."
if [[ -f "escape_circuit.db" ]]; then
  cp -f "escape_circuit.db" "escape_circuit.db.bak"
  echo "Backup created: escape_circuit.db.bak"
else
  echo "No existing DB file found, skipping backup."
fi

echo "[3/6] Deleting DB files..."
rm -f "escape_circuit.db" "escape_circuit.db-wal" "escape_circuit.db-shm"

echo "[4/6] Initializing schema..."
if ! "$PYTHON_BIN" "src/init_db.py"; then
  echo "ERROR: init_db failed."
  exit 1
fi

echo "[5/6] Importing riddles..."
if ! "$PYTHON_BIN" "src/insert_riddles.py"; then
  echo "ERROR: insert_riddles failed."
  exit 1
fi

echo "[6/6] Seeding admin user..."
if ! "$PYTHON_BIN" "src/seed_admin.py"; then
  echo "ERROR: seed_admin failed."
  exit 1
fi

echo
echo "Hard reset complete."
echo "Admin credentials: username=admin password=password123"
echo
echo "Next step: run ./run_server.sh to start backend + frontend."
