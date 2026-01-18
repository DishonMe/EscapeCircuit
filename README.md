# EscapeCircuit 🔌⚡

"Wire your way out."

EscapeCircuit is a web app for creating and solving logic-circuit puzzles.

## Quickstart

Prerequisites: Node 20+, Yarn 1.22+.

```bash
cd apps/nextjs-app
cp .env.example .env   # adjust values if needed
yarn install
# start the web app on http://localhost:3000
yarn dev
```

### Windows: one command for API + Web

Use [run_server.bat](run_server.bat) from the repo root to start both backend (FastAPI/uvicorn) and the Next.js dev server together.

What it does:
- Runs `python src/init_db.py` and `python src/insert_riddles.py` to prep the local DB and seed riddles.
- Starts the FastAPI server on http://127.0.0.1:8080.
- Starts the Next.js app on http://localhost:3000 via `npm run dev` in [apps/nextjs-app](apps/nextjs-app).

Requirements:
- Python 3.10+ with `pip` available.
- Node 20+ with `npm` and `npx`.
- Internet access on first run (installs `requirements.txt` and `concurrently`).

Run it:

```
.\u200brun_server.bat
```

Stop with Ctrl+C (stops both processes). If you prefer yarn for the frontend, start the API separately and run `yarn dev` inside apps/nextjs-app.

## Common Tasks

```bash
yarn build          # production build
yarn start          # run the built app
yarn lint           # lint code
yarn check-types    # TypeScript checks
yarn test           # unit tests (Vitest)
yarn test-e2e       # Playwright e2e (requires backend)
yarn storybook      # UI docs at http://localhost:6006
yarn build-storybook
yarn generate       # scaffold components with Plop
```

## Project Layout

- apps/nextjs-app/ — main Next.js 14 App Router client (TypeScript, Tailwind, Zustand, React Query)

### Repository Tree

```
EscapeCircuit/
├── apps/
│   ├── nextjs-app/           # active frontend (Next.js 14)
│   │   ├── public/
│   │   ├── src/
│   │   ├── playwright.config.ts
│   │   ├── vitest.config.ts
│   │   └── package.json
│   └── react-vite/           # legacy stub (not in use)
├── docs/                     # high-level docs (features, setup)
├── riddles/                  # puzzle/riddle assets and tests
├── src/                      # backend utilities and scripts
├── package.json              # root scripts (delegates to apps/nextjs-app)
└── README.md
```

## Environment

Copy `.env.example` to `.env` in `apps/nextjs-app` and adjust:

- `NEXT_PUBLIC_API_URL` — API base (default `http://localhost:8080/api`)
- `NEXT_PUBLIC_URL` — app origin (default `http://localhost:3000`)

## Documentation

- Frontend app details live in [apps/nextjs-app/README.md](apps/nextjs-app/README.md)
- Additional high-level notes are in [docs/FEATURES.md](docs/FEATURES.md)

## Team

**Academic Advisor:** Niv Gilboa.

**Clients:** Gera Weiss and Oded Margalit.

**Team:** Dor Steinlauf, Noam Yosef, Mendy Dishon, Yuval Zarmi.

## License

[MIT](/LICENSE)
