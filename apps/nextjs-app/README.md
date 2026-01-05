# EscapeCircuit - Next.js App

The main application for EscapeCircuit, built with Next.js App Router.

## Get Started

Prerequisites:

- Node 20+
- Yarn 1.22+

To set up the app:

```bash
cd apps/nextjs-app
cp .env.example .env
yarn install
```

#### `yarn run-mock-server`

Start the mock API server on [http://localhost:8080/api](http://localhost:8080/api).

#### `yarn dev`

Start the development server on [http://localhost:3000](http://localhost:3000).

## Features

- Modern Next.js 14 with App Router
- TypeScript for type safety
- Tailwind CSS for styling
- Zustand for state management
- React Query for API calls
- Comprehensive testing with Vitest
- ESLint and Prettier for code quality

## Project Structure

```
src/
  app/          # Next.js app router pages
  components/   # Reusable UI components
  features/     # Feature-specific modules
  hooks/        # Custom React hooks
  lib/          # Utility libraries
  types/        # TypeScript type definitions
  utils/        # Helper functions
```
