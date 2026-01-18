# EscapeCircuit Setup Guide

## Prerequisites

- **Node.js** 16+ 
- **Yarn** 1.22+
- **Git**

## Installation

### 1. Install Dependencies

```bash
# From the root directory
yarn prepare

# Or manually navigate to the app
cd apps/react-vite
yarn install
# EscapeCircuit Setup Guide

Current frontend: Next.js app in `apps/nextjs-app`.

## Prerequisites

- Node.js 20+
- Yarn 1.22+
- Python 3.10+ (for backend if running locally)

## Install & Run (Frontend)

```bash
cd apps/nextjs-app
cp .env.example .env   # adjust API URL if needed
yarn install
yarn dev               # http://localhost:3000
```

Key env vars:

- `NEXT_PUBLIC_API_URL` (default `http://localhost:8080/api`)
- `NEXT_PUBLIC_URL` (default `http://localhost:3000`)

## Backend + Frontend together (Windows)

From repo root:

```bash
.\run_server.bat
```

This seeds the DB, starts FastAPI on 127.0.0.1:8080, and runs the Next.js dev server on 3000.

## Tests & Quality (Frontend)

- `yarn test` — unit (Vitest)
- `yarn test-e2e` — Playwright (requires backend running)
- `yarn lint` — lint
- `yarn check-types` — TypeScript checks
- `yarn storybook` — UI docs at http://localhost:6006
- `yarn generate` — scaffold components (Plop)

## Structure (Frontend)

```
apps/nextjs-app/
├── public/
├── src/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   └── utils/
├── playwright.config.ts
├── vitest.config.ts
└── package.json
```
```bash
