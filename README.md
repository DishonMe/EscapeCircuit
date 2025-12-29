# EscapeCircuit 🔌⚡

**"Wire your way out."**

An interactive puzzle game for creating and solving logic circuits. Design custom puzzles, manage components within budget constraints, and challenge others to solve your creations.

## Project Overview

EscapeCircuit is a web-based application where users can:

- **Solve Logic Puzzles**: Place circuit components and connect them with wires to achieve target outputs
- **Create Puzzles**: Design custom logic circuit puzzles with configurable difficulty and budgets
- **Manage Profiles**: Track puzzle-solving achievements and view creation statistics
- **Browse Puzzles**: Discover and play puzzles created by the community
- **Moderate Content**: Admin tools for managing puzzles and user submissions

## Tech Stack

- **Frontend**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI
- **State Management**: React Context/Hooks
- **Testing**: Vitest + Playwright
- **Code Quality**: ESLint, TypeScript

## Getting Started

### Prerequisites
- Node.js and Yarn

### Installation

```bash
# Install dependencies for the React Vite app
yarn prepare

# Navigate to the app directory
cd apps/react-vite

# Start development server
yarn dev
```

### Available Scripts

```bash
# Development
yarn dev              # Start dev server

# Building
yarn build           # Build for production
yarn preview         # Preview production build

# Testing & Quality
yarn test            # Run unit tests
yarn test-e2e        # Run end-to-end tests
yarn lint            # Run ESLint
yarn check-types     # Type check with TypeScript

# Code Generation
yarn generate        # Generate new components/files with Plop

# Documentation
yarn storybook       # Start Storybook development
yarn build-storybook # Build Storybook
```

## Project Structure

```
apps/react-vite/
├── src/
│   ├── components/       # Reusable UI components
│   ├── features/         # Feature-specific modules
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # Utility functions and helpers
│   ├── types/            # TypeScript type definitions
│   ├── utils/            # Utility functions
│   ├── app/              # Main app layout
│   ├── config/           # Configuration files
│   └── main.tsx          # Entry point
├── public/               # Static assets
└── package.json
```

## Features

### Circuit Board
- Drag-and-drop component placement
- Visual wire routing and connections
- Real-time cost calculation
- Budget tracking against limits

### Puzzle Management
- Puzzle creation wizard
- Difficulty configuration
- Budget constraints
- Input/output specification

### User Features
- Profile pages with statistics
- Puzzle history and achievements
- Community puzzle browsing
- Search and filtering

### Admin Tools
- Content moderation
- Puzzle review system
- User management

## Documentation

For detailed information about project structure, standards, and architectural decisions, see the [docs folder](docs/).

## Team

- **Academic Advisor**: Niv Gilboa
- **Clients**: Gera Weiss and Oded Margalit
- **Development Team**: Dor Steinlauf, Noam Yosef, Mendy Dishon, Yuval Zarmi

## License

[MIT](/LICENSE)
