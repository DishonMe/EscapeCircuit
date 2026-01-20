# EscapeCircuit - Next.js App

Main web client for EscapeCircuit using Next.js 14 App Router.

## Quickstart

Prerequisites: Node 20+, Yarn 1.22+.

```bash
cd apps/nextjs-app
cp .env.example .env   # adjust values if needed
yarn install
yarn dev               # http://localhost:3000
```

If you prefer npm: replace `yarn` with `npm run` where appropriate.

## Environment

Set these in `.env` (or `.env.local`):

- `NEXT_PUBLIC_API_URL` — API base (default `http://localhost:8080/api`)
- `NEXT_PUBLIC_URL` — app origin (default `http://localhost:3000`)

## Scripts

- `yarn dev` — start dev server
- `yarn build` / `yarn start` — production build and serve
- `yarn lint` — lint
- `yarn check-types` — TypeScript checks
- `yarn test` — unit tests (Vitest)
- `yarn test-e2e` — Playwright tests (requires backend running)
- `yarn storybook` / `yarn build-storybook` — UI docs
- `yarn generate` — scaffold components via Plop

## Notes

- Windows users can start backend + frontend together via the root `run_server.bat` (runs FastAPI on 127.0.0.1:8080 and this app on 3000).
- For standalone frontend development, point `NEXT_PUBLIC_API_URL` to your backend.

## Project Structure

```
apps/nextjs-app/
├── public/                 # static assets
├── src/
│   ├── app/                # Next.js app router routes/layouts
│   ├── components/         # reusable UI components
│   ├── features/           # feature modules
│   ├── hooks/              # custom hooks
│   ├── lib/                # utilities
│   ├── types/              # shared types
│   └── utils/              # helpers
├── playwright.config.ts    # e2e config
├── vitest.config.ts        # unit test config
└── package.json
```

## Tech Highlights

- Next.js 14 App Router, React 18
- TypeScript, Tailwind CSS
- Zustand for state, React Query for data
- Vitest + Testing Library, Playwright for e2e
- ESLint, Prettier, Storybook
