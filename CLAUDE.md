# EscapeCircuit — Agent Instructions

## Project Overview
Logic-circuit puzzle web app — students wire logic gates to solve riddles (binary adder, palindrome detector, counters, etc.). Academic project: advisor Niv Gilboa; clients Gera Weiss + Oded Margalit. Monorepo: Next.js frontend + FastAPI backend.

## Tech Stack & Versions
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind, Zustand, React Query, Radix UI, next-themes. Runtime: Node 20+, Yarn 1.22+.
- **Backend:** FastAPI + Uvicorn, Pydantic, SQLite (WAL mode), JWT auth, Google OAuth. Runtime: Python 3.10+.
- **Tests:** Vitest (frontend unit), Playwright (e2e), Pytest (backend). Storybook for component dev.

## Architecture & Folder Map
- `apps/nextjs-app/` — frontend. See [apps/nextjs-app/README.md](apps/nextjs-app/README.md).
- `src/Backend/` — layered FastAPI app: `APILayer/` (controllers) · `ServiceLayer/` · `DomainLayer/` (models) · `PersistantLayer/` (SQLite queries). Entry: `main.py`.
- `riddles/` — puzzle definitions (`*_config.json`, `*_instructions.tex`, `*_sample_solution.json`).
- `src/tests/` — backend tests.
- `escape_circuit.db` — dev SQLite at repo root, WAL mode.
- Seed scripts: `src/init_db.py`, `src/insert_riddles.py`, `src/seed_admin.py`.

## Commands
- **Dev (both servers):** `python init_env.py` from repo root (API :8080 + Next :3000).
- **Backend only:** `python -m uvicorn Backend.main:app --reload --host 127.0.0.1 --port 8080` from `src/`.
- **Frontend only:** `yarn dev` in `apps/nextjs-app/`.
- **Tests:** `pytest` at root; `yarn test` in `apps/nextjs-app/`.
- **Typecheck / lint / build:** `yarn check-types` / `yarn lint` / `yarn build` in `apps/nextjs-app/`.
- **DB reset:** `python src/reinit_db.py` (or the three seed scripts in order).

## Coding Conventions
- **Backend layering:** controllers call services; services call domain + persistent. Don't shortcut APILayer → PersistantLayer.
- **State/data:** use Zustand + React Query. Don't introduce a second library for either.
- **Frontend components:** kebab-case filenames (e.g. `workstation-grid.tsx`), PascalCase exports.

## Critical Rules
- **ALWAYS before commit/push:** run `yarn check-types`, `yarn lint`, `yarn test`, `yarn build` in `apps/nextjs-app/` and `pytest` at root. If touching env loading or shell scripts, reason through `deploy.sh` and `run_server.sh` — both use `set -euo pipefail`, so an unbound var breaks deploy.
- **NEVER delete `*.db-wal` / `*.db-shm`** — SQLite is WAL mode. Don't `kill -9` uvicorn; use SIGTERM so WAL checkpoints cleanly. See [deploy.sh](deploy.sh) header for rollback + WAL rationale.
- **NEVER commit `.env`, `escape_circuit.db*`, or `node_modules/`.** Secrets live only in `apps/nextjs-app/.env`; `init_env.py` propagates `NEXT_PUBLIC_GOOGLE_CLIENT_ID` to the backend.
- **NEVER add a new start script at repo root** — extend `init_env.py`, `run_server.sh`, or `run_server.bat`.
- **NEVER restructure `src/Backend/` layers** without calling it out explicitly.
- **Dev admin creds:** `admin` / `password123` — dev-only; never ship.

## Naming & Git
- **Branches:** `<issue-number>-<kebab-slug>` (e.g. `231-puzzle-solution-mid-solving-saving`).
- **PRs:** merged via GitHub PRs (see recent `Merge pull request #...` commits); reference the issue number.

## References
- Setup: [HOWTORUN.md](HOWTORUN.md), [docs/SETUP.md](docs/SETUP.md)
- Features: [docs/FEATURES.md](docs/FEATURES.md)
- Backend class diagram: [backend_class_diagram.mmd](backend_class_diagram.mmd)
