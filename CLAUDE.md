# EscapeCircuit — Agent Instructions

Logic-circuit puzzle web app. Monorepo: Next.js frontend + FastAPI backend.

## Stack
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind, Zustand, React Query, Radix UI, next-themes. Runtime: Node 20+, Yarn 1.22+.
- **Backend:** FastAPI + Uvicorn, Pydantic, SQLite (WAL mode), JWT auth, Google OAuth. Runtime: Python 3.10+.
- **Tests:** Vitest (frontend unit), Playwright (e2e), Pytest (backend). Storybook for component dev.

## Layout
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

## Conventions
- **Before commit/push:** run `yarn check-types`, `yarn lint`, `yarn test`, `yarn build` in `apps/nextjs-app/`, and `pytest` at root. If touching env loading or shell scripts, reason through `deploy.sh` and `run_server.sh` — they use `set -euo pipefail`, so an unbound var will break deploy.
- **SQLite is WAL mode.** Never delete `*.db-wal` / `*.db-shm`. Don't `kill -9` uvicorn — use SIGTERM so WAL checkpoints cleanly. See the header comment in [deploy.sh](deploy.sh) for rollback and WAL rationale.
- **Secrets:** only in `apps/nextjs-app/.env` (gitignored). `NEXT_PUBLIC_GOOGLE_CLIENT_ID` lives there; `init_env.py` propagates it to the backend. Don't commit `.env`.
- **Dev admin:** `admin` / `password123`. Dev-only.
- **Branch naming:** `<issue-number>-<kebab-slug>` (e.g. `231-puzzle-solution-mid-solving-saving`).
- **Backend layering:** controllers call services, services call domain + persistent. Don't shortcut APILayer → PersistantLayer.

## Don't
- Don't commit `escape_circuit.db*`, `node_modules/`, or `.env`.
- Don't add a new start script at repo root — extend `init_env.py`, `run_server.sh`, or `run_server.bat`.
- Don't introduce a second state or data-fetching library — use Zustand + React Query.
- Don't restructure `src/Backend/` layers without saying so explicitly.

## References
- Setup: [HOWTORUN.md](HOWTORUN.md), [docs/SETUP.md](docs/SETUP.md)
- Features: [docs/FEATURES.md](docs/FEATURES.md)
- Backend class diagram: [backend_class_diagram.mmd](backend_class_diagram.mmd)
