# EscapeCircuit 🔌⚡

"Wire your way out."

EscapeCircuit is a web app for creating and solving logic-circuit puzzles.

## Quickstart

### Windows: One Command to Run Everything

Use [run_server.bat](run_server.bat) from the repo root to start both the FastAPI backend and Next.js frontend together:

```
.\run_server.bat
```

**What it does:**
- Initializes the local SQLite database: `python src/init_db.py`
- Seeds puzzle riddles: `python src/insert_riddles.py`
- Seeds an admin user (username: `admin`, password: `password123`): `python src/seed_admin.py`
- Starts the FastAPI server on http://127.0.0.1:8080
- Starts the Next.js dev server on http://localhost:3000

**Requirements:**
- Python 3.10+ with `pip` available
- Node 20+ with `npm` and `npx`
- Internet access on first run (installs dependencies)

**Stop:** Press Ctrl+C to stop both processes.

### Manual Setup (without .bat)

Prerequisites: Node 20+, Yarn 1.22+.

**Backend:**
```bash
pip install -r requirements.txt
python src/init_db.py
python src/insert_riddles.py
python src/seed_admin.py
python -m uvicorn src.Backend.main:app --reload --host 127.0.0.1 --port 8080
```

**Frontend (in another terminal):**
```bash
cd apps/nextjs-app
cp .env.example .env   # adjust values if needed
yarn install
yarn dev
```

Then open http://localhost:3000 in your browser.

## Common Tasks

```bash
yarn build          # production build
yarn start          # run the built app
yarn test           # unit tests (Vitest)
```

## Project Layout

- apps/nextjs-app/ — main Next.js 14 App Router client (TypeScript, Tailwind, Zustand, React Query)

### Repository Tree

```
EscapeCircuit/
├── apps/nextjs-app/                    # Next.js 14 frontend
│   └── src/
│       ├── app/                        # App Router & pages
│       │   └── puzzles/[id]/          # Puzzle workspace
│       ├── components/
│       │   └── workstation-grid.tsx   # Circuit design canvas (core UI)
│       ├── features/                   # Redux-like modules
│       ├── hooks/                      # Custom React hooks
│       ├── types/api.ts                # API type definitions
│       └── utils/                      # Helpers & utilities
│
├── src/                                # FastAPI backend (Python)
│   ├── Backend/
│   │   ├── main.py                    # FastAPI app entry
│   │   ├── APILayer/
│   │   │   ├── AdminController.py     # Auth & admin endpoints
│   │   │   ├── CircuitController.py   # Circuit/puzzle endpoints
│   │   │   ├── PuzzleController.py    # Puzzle logic endpoints
│   │   │   └── auth_utils.py          # JWT & security
│   │   ├── DomainLayer/               # Business logic & models
│   │   ├── ServiceLayer/              # Data processing services
│   │   └── PersistantLayer/           # Database queries (SQLite)
│   │
│   ├── init_db.py                     # Database initialization
│   ├── insert_riddles.py              # Seed riddle data
│   └── seed_admin.py                  # Create admin user
│
├── riddles/                            # Puzzle definitions & tests
│   ├── riddle_01_binary_adder          # Sample
│       ├── riddle_01_binary_adder_config.json
│       ├── riddle_01_binary_adder_instructions.tex
│       ├── riddle_01_binary_adder_sample_solution.json
│   ├── riddle_02_half_adder            # etc..
│
├── docs/                               # Documentation
│   ├── FEATURES.md                    # Feature overview
│   └── SETUP.md                       # Setup guide
│
├── run_server.bat                      # Windows startup script
└── README.md
```

## Environment

Copy `.env.example` to `.env` in `apps/nextjs-app` and adjust:

- `NEXT_PUBLIC_API_URL` — API base (default `http://localhost:8080/api`)
- `NEXT_PUBLIC_URL` — app origin (default `http://localhost:3000`)

## Seeded Puzzles

- Binary Adder Quiz: Full-adder logic with restricted gates.
- Half Adder Quiz: Two-bit sum/carry combinational challenge.
- Sequential Binary Adder Quiz: Bit-stream addition across cycles.
- Palindrome Detector: Detect palindromic 4-bit patterns.
- 2-Bit Comparator: Compute GT/EQ/LT for two 2-bit values.
- Full Adder Circuit1: Alternate full-adder implementation challenge.
- Twice 2 Bits in 3 Bits: Decode write-once 3-bit memory snapshots.

## Documentation

- Frontend app details live in [apps/nextjs-app/README.md](apps/nextjs-app/README.md)
- Additional high-level notes are in [docs/FEATURES.md](docs/FEATURES.md)

## Team

**Academic Advisor:** Niv Gilboa.

**Clients:** Gera Weiss and Oded Margalit.

**Team:** Dor Steinlauf, Noam Yosef, Mendy Dishon, Yuval Zarmi.

## License

[MIT](/LICENSE)
