#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Safe deployment script for EscapeCircuit backend
#
# SQLite WAL-mode requires special care during deployment.  A forceful kill
# while a -wal file has uncommitted pages can leave the database in a state
# that needs recovery, or in the worst case, causes corruption if the -wal
# or -shm files are deleted or copied mid-transaction.
#
# This script:
#   1. Gracefully stops the running uvicorn process (SIGTERM → WAL checkpoint)
#   2. Backs up the DB *after* the WAL is fully checkpointed
#   3. Pulls code + installs deps
#   4. Restarts the service
#
# ROLLBACK INSTRUCTIONS
# ---------------------
# If the deployment fails and the new code cannot start:
#
#   1. Stop the broken service:
#        pkill -f "uvicorn Backend.main:app" 2>/dev/null; sleep 2
#
#   2. List available backups:
#        ls -lt backups/
#
#   3. Restore the most recent backup:
#        cp backups/escape_circuit_<TIMESTAMP>.db escape_circuit.db
#
#   4. Revert the code:
#        git checkout <previous-commit-hash>
#        pip3 install -r requirements.txt
#
#   5. Restart:
#        bash run_server.sh
# =============================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
DB_FILE="$PROJECT_ROOT/escape_circuit.db"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
UVICORN_PATTERN="uvicorn Backend.main:app"

# Colours for terminal output (no-op if not a tty)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Colour

info()  { echo -e "${GREEN}[deploy]${NC} $*"; }
warn()  { echo -e "${YELLOW}[deploy]${NC} $*"; }
error() { echo -e "${RED}[deploy]${NC} $*" >&2; }

# ─── 1. Pre-flight ──────────────────────────────────────────────────────────

info "Deployment started at $(date)"
info "Project root: $PROJECT_ROOT"
echo

# ─── 2. Graceful shutdown ───────────────────────────────────────────────────
#
# WHY GRACEFUL MATTERS FOR SQLite WAL:
#
#   When uvicorn receives SIGTERM it finishes in-flight requests, then Python's
#   atexit / garbage collection closes the SQLite connection.  On close, SQLite
#   automatically runs a WAL checkpoint — replaying all committed pages from
#   the -wal file back into the main .db file.  After a clean shutdown:
#
#     - escape_circuit.db    contains ALL committed data
#     - escape_circuit.db-wal  is zero-length or absent
#     - escape_circuit.db-shm  is zero-length or absent
#
#   This means the .db file alone is a complete, self-contained backup.
#   A forceful kill (SIGKILL / kill -9) skips this checkpoint, leaving
#   committed data stranded in the -wal file.  Copying .db without its
#   -wal in that state yields a backup with MISSING transactions.
# ────────────────────────────────────────────────────────────────────────────

info "Stopping backend service (graceful SIGTERM)..."

UVICORN_PID=$(pgrep -f "$UVICORN_PATTERN" 2>/dev/null || true)

if [ -n "$UVICORN_PID" ]; then
    # Send SIGTERM — uvicorn will finish in-flight requests and checkpoint WAL
    kill "$UVICORN_PID" 2>/dev/null || true
    info "Sent SIGTERM to uvicorn (PID $UVICORN_PID). Waiting for shutdown..."

    # Wait up to 15 seconds for graceful exit
    WAITED=0
    while kill -0 "$UVICORN_PID" 2>/dev/null; do
        sleep 1
        WAITED=$((WAITED + 1))
        if [ "$WAITED" -ge 15 ]; then
            warn "uvicorn did not exit within 15s — sending SIGKILL"
            kill -9 "$UVICORN_PID" 2>/dev/null || true
            sleep 1
            break
        fi
    done

    info "Backend stopped."
else
    warn "No running uvicorn process found — skipping shutdown."
fi
echo

# ─── 3. Automated backup ────────────────────────────────────────────────────
#
# Only safe to copy AFTER the process has exited (WAL fully checkpointed).
# We verify the -wal file is empty or absent before copying.
# ────────────────────────────────────────────────────────────────────────────

if [ -f "$DB_FILE" ]; then
    # Verify WAL is checkpointed (empty or absent)
    WAL_FILE="${DB_FILE}-wal"
    if [ -f "$WAL_FILE" ]; then
        WAL_SIZE=$(stat -f%z "$WAL_FILE" 2>/dev/null || stat -c%s "$WAL_FILE" 2>/dev/null || echo "unknown")
        if [ "$WAL_SIZE" != "0" ] && [ "$WAL_SIZE" != "unknown" ]; then
            warn "WAL file is non-empty (${WAL_SIZE} bytes)."
            warn "Running manual checkpoint before backup..."
            # Force a checkpoint using the sqlite3 CLI
            if command -v sqlite3 &>/dev/null; then
                sqlite3 "$DB_FILE" "PRAGMA wal_checkpoint(TRUNCATE);"
                info "Manual WAL checkpoint completed."
            else
                warn "sqlite3 CLI not found — backing up .db + .wal + .shm together."
            fi
        fi
    fi

    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/escape_circuit_${TIMESTAMP}.db"
    cp "$DB_FILE" "$BACKUP_FILE"

    # If -wal/-shm still exist and are non-empty, copy them too for safety
    for ext in "-wal" "-shm"; do
        SIDECAR="${DB_FILE}${ext}"
        if [ -f "$SIDECAR" ] && [ -s "$SIDECAR" ]; then
            cp "$SIDECAR" "${BACKUP_FILE}${ext}"
        fi
    done

    BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    info "Database backed up: $BACKUP_FILE ($BACKUP_SIZE)"

    # Prune backups older than 30 days
    find "$BACKUP_DIR" -name "escape_circuit_*.db*" -mtime +30 -delete 2>/dev/null || true
else
    warn "No database file found at $DB_FILE — skipping backup."
fi
echo

# ─── 4. Update code & dependencies ──────────────────────────────────────────

info "Pulling latest code from main..."
cd "$PROJECT_ROOT"
git pull origin main
echo

info "Installing Python dependencies..."
pip3 install -r requirements.txt --quiet
echo

info "Running database migrations (init + seed)..."
python3 src/init_db.py
python3 src/seed_admin.py
echo

# ─── 5. Restart & verify ────────────────────────────────────────────────────

info "Starting backend service..."

# Load environment (GOOGLE_CLIENT_ID) from the frontend .env
ENV_FILE="$PROJECT_ROOT/apps/nextjs-app/.env"
if [ -f "$ENV_FILE" ]; then
    # Extract NEXT_PUBLIC_GOOGLE_CLIENT_ID and export as GOOGLE_CLIENT_ID
    GCID=$(grep -E '^NEXT_PUBLIC_GOOGLE_CLIENT_ID=' "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [ -n "$GCID" ]; then
        export GOOGLE_CLIENT_ID="$GCID"
        info "Loaded GOOGLE_CLIENT_ID from $ENV_FILE"
    else
        warn "NEXT_PUBLIC_GOOGLE_CLIENT_ID not found in $ENV_FILE"
    fi
fi

# Start uvicorn in the background (production: consider gunicorn w/ uvicorn workers)
cd "$PROJECT_ROOT/src"
nohup python3 -m uvicorn Backend.main:app \
    --host 127.0.0.1 \
    --port 8080 \
    > "$PROJECT_ROOT/logs/uvicorn.log" 2>&1 &

NEW_PID=$!
cd "$PROJECT_ROOT"

# Give it a moment to boot
sleep 3

# Health check
if kill -0 "$NEW_PID" 2>/dev/null; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/ 2>/dev/null || echo "000")
    if [ "$HTTP_STATUS" = "200" ]; then
        info "Health check passed (HTTP $HTTP_STATUS)"
        info "Backend running on PID $NEW_PID — http://127.0.0.1:8080"
    else
        warn "Process is running (PID $NEW_PID) but health check returned HTTP $HTTP_STATUS"
        warn "Check logs: tail -f $PROJECT_ROOT/logs/uvicorn.log"
    fi
else
    error "Backend failed to start! Check logs: $PROJECT_ROOT/logs/uvicorn.log"
    error "To rollback, see instructions at the top of this script."
    exit 1
fi
echo

info "Deployment completed successfully at $(date)"
info "Backup: $BACKUP_FILE"
info "Logs:   $PROJECT_ROOT/logs/uvicorn.log"
