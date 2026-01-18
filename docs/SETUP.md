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
```

### 2. Environment Configuration

Create a `.env.local` file in `apps/react-vite/`:

```env
# API Configuration
VITE_API_URL=http://localhost:3000/api

# Feature Flags
VITE_ENABLE_ADMIN_PANEL=false
VITE_ENABLE_COMMUNITY_FEATURES=true
```

## Development

### Start Development Server

```bash
cd apps/react-vite
yarn dev
```

The application will be available at `http://localhost:5173`

### Build for Production

```bash
yarn build
```

### Preview Production Build

```bash
yarn preview
```

## Testing

### Unit Tests

```bash
yarn test
```

### E2E Tests

```bash
# Start the mock server in one terminal
yarn run-mock-server

# In another terminal, run tests
yarn test-e2e
```

## Code Quality

### Linting

```bash
yarn lint
```

### Type Checking

```bash
yarn check-types
```

### Generate New Components

```bash
yarn generate
```

This uses Plop to scaffold new components with tests.

## Storybook (UI Component Documentation)

```bash
# Start Storybook
yarn storybook

# Build Storybook for deployment
yarn build-storybook
```

Storybook will be available at `http://localhost:6006`

## Troubleshooting

### Port Already in Use
If port 5173 is already in use, Vite will automatically use the next available port.

### Module Not Found Errors
Clear node_modules and reinstall:
```bash
rm -rf node_modules
yarn install
```

### Build Fails with TypeScript Errors
Run type checking separately:
```bash
yarn check-types
```

### E2E Tests Failing
Ensure the mock server is running and the app is not already running on port 5173.

## Project Structure Quick Reference

```
apps/react-vite/
├── src/
│   ├── app/              # App entry point and routing
│   ├── components/       # Reusable UI components
│   ├── features/         # Feature modules
│   ├── hooks/            # Custom hooks
│   ├── lib/              # Utilities and helpers
│   ├── types/            # TypeScript types
│   └── main.tsx          # React app entry
├── public/               # Static files
├── playwright.config.ts  # E2E test configuration
├── vitest.config.ts      # Unit test configuration
└── tsconfig.json         # TypeScript configuration
```

## Next Steps

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the project structure
2. Check out the [React Vite documentation](https://vitejs.dev/)
3. Review the example components in `src/components`
4. Start building features following the established patterns
