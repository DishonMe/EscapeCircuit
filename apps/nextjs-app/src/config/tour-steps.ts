import { Step } from 'react-joyride';

// `react-joyride`'s Step type doesn't include `title`, but the underlying
// tooltip API forwards it through. Cast to a permissive type so our custom
// TourTooltip can render `step.title` for richer headers.
type TourStep = Step & { title?: string };

/**
 * Browse Puzzles Tour - /app/puzzles
 */
export const browsePuzzlesTourSteps: TourStep[] = [
  {
    title: 'Filter the gallery',
    target: '.puzzle-filters-button',
    content:
      'Hunt for the right puzzle by difficulty, fun, clarity, or solve status. Try opening it now and slide a filter to see how the list reshuffles.',
    placement: 'bottom',
  },
  {
    title: 'Peek at the brief',
    target: '.puzzle-instructions-button',
    content:
      'Open the instructions before diving in — they spell out the goal, constraints, and any creator notes.',
    placement: 'bottom',
  },
  {
    title: 'Close the brief',
    target: '.dialog-close-button',
    content:
      'Close the dialog whenever you are ready. The puzzle list is right behind it.',
    placement: 'bottom',
  },
  {
    title: 'Sort to taste',
    target: '.puzzle-sort-dropdown',
    content:
      'Sort by creation date, difficulty, fun, or clarity. A great way to surface puzzles that match your current mood.',
    placement: 'bottom',
  },
  {
    title: 'Jump into the Workstation',
    target: '.puzzle-card-action',
    content:
      'Click Solve Puzzle to enter the Workstation — that is where you wire your gates, run tests, and earn XP.',
    placement: 'left',
  },
  {
    title: 'Bookmark for later',
    target: '.puzzle-save-button',
    content:
      'Spotted something tempting but short on time? Save it — bookmarks are a click away from your dashboard.',
    placement: 'left',
  },
  {
    title: 'Rate what you solve',
    target: '.puzzle-rating-section',
    content:
      'After you spend real time on a puzzle, rate it. Creators get feedback, and other players find the gems.',
    placement: 'top',
  },
];

/**
 * Puzzle Workstation Tour - /app/puzzles/[id]
 */
export const workstationTourSteps: TourStep[] = [
  {
    title: 'Your component palette',
    target: '.workstation-component-menu',
    content:
      'Every gate you can use lives here. Drag one onto the grid to start building — Arsenal pieces show up too when the puzzle allows them.',
    placement: 'right',
  },
  {
    title: 'The work surface',
    target: '.workstation-grid',
    content:
      'Drop components onto the grid and wire their ports. The colored squares on the edges are your inputs and outputs.',
    placement: 'top',
  },
  {
    title: 'Run the tests',
    target: '.workstation-check-button',
    content:
      'When your circuit looks right, hit Test Solution. Pass every test and you bank XP, a medal, and a leaderboard spot.',
    placement: 'top',
  },
  {
    title: 'Inspect your circuit',
    target: '.workstation-debugger-button',
    content:
      'Stuck? Open the Debugger and step through your signals one tick at a time to find the logic gap.',
    placement: 'left',
  },
  {
    title: 'Re-read the puzzle',
    target: '.workstation-instructions-button',
    content:
      'Need a quick refresher on the goal? Pop the instructions back open without losing your wires.',
    placement: 'left',
  },
  {
    title: 'Close the instructions',
    target: '.dialog-close-button',
    content:
      'Close the dialog to return to your workstation when you are ready.',
    placement: 'left',
  },
  {
    title: 'Experiment safely',
    target: '.workstation-sandbox-toggle',
    content:
      'The Sandbox is your scratch pad — try alternate wirings here without touching your real solution.',
    placement: 'top',
  },
];

/**
 * Create Puzzle Tour - /app/create-puzzle
 */
export const createPuzzleTourSteps: TourStep[] = [
  {
    title: 'Start with the basics',
    target: '.create-puzzle-basic-tab',
    content:
      'Name your puzzle, write a hook, and pick a difficulty. Set a gate budget or cycle limit here if you want a tight challenge.',
    placement: 'bottom',
  },
  {
    title: 'Build the reference solution',
    target: '.create-puzzle-solution-tab',
    content:
      'Wire the correct circuit yourself. You can also lock in a starter board that solvers must build around.',
    placement: 'bottom',
  },
  {
    title: 'Define what "correct" means',
    target: '.create-puzzle-test-cases-tab',
    content:
      'List the input/expected-output cases your puzzle grades against — or wire up Python tests for stream-based puzzles.',
    placement: 'bottom',
  },
  {
    title: 'Brief your solvers',
    target: '.create-puzzle-instructions-tab',
    content:
      'Write the puzzle story in Markdown. LaTeX math is supported, so go ahead with the equations.',
    placement: 'bottom',
  },
  {
    title: 'Add custom pieces',
    target: '.create-puzzle-custom-pieces-tab',
    content:
      'Optionally bake in puzzle-specific sub-circuits — handy when you want to scope the gate set or hint at structure.',
    placement: 'bottom',
  },
  {
    title: 'Ship it',
    target: '.create-puzzle-publish-button',
    content:
      'Publish when ready or keep it as a draft and iterate. You can come back to tune anything later.',
    placement: 'top',
  },
];

/**
 * My Puzzles Tour - /app/my-puzzles
 */
export const myPuzzlesTourSteps: TourStep[] = [
  {
    title: 'Switch between drafts and published',
    target: '.tour-my-puzzles-tabs',
    content:
      'Toggle between puzzles you have published and drafts you are still polishing.',
    placement: 'bottom',
  },
  {
    title: 'Start a new puzzle',
    target: '.tour-my-puzzles-create',
    content:
      'Spin up a brand-new puzzle from scratch — the create-puzzle tour will walk you through it the first time.',
    placement: 'bottom',
  },
  {
    title: 'Manage each puzzle',
    target: '.tour-my-puzzles-actions',
    content:
      'Edit details, publish or unpublish, or delete a puzzle from here. Changes apply immediately.',
    placement: 'top',
    scrollIntoView: true,
    scrollTarget: '.tour-my-puzzles-actions',
  } as TourStep,
];

/**
 * Arsenal Tour - /app/arsenal
 */
export const arsenalTourSteps: TourStep[] = [
  {
    title: 'Your custom pieces live here',
    target: '.tour-arsenal-list',
    content:
      'Every piece you have built is stored in your Arsenal. Use them in any puzzle that allows arsenal pieces.',
    placement: 'bottom',
  },
  {
    title: 'Peek inside a piece',
    target: '.tour-arsenal-preview',
    content:
      'Preview the internal wiring of a piece without leaving this page — handy for remembering what each one does.',
    placement: 'top',
  },
  {
    title: 'Keep things tidy',
    target: '.tour-arsenal-actions',
    content:
      'Rename, restyle, or delete pieces. A clean arsenal is a fast arsenal.',
    placement: 'top',
  },
];

/**
 * Arsenal Creator Tour - /app/arsenal/creator
 */
export const arsenalCreatorTourSteps: TourStep[] = [
  {
    title: 'Declare your ports',
    target: '.tour-creator-io-config',
    content:
      'Pick how many inputs and outputs this piece exposes. Those numbers decide what other puzzles can wire into.',
    placement: 'bottom',
  },
  {
    title: 'Drag in gates',
    target: '.tour-creator-palette',
    content:
      'Drag basic gates onto the grid — or reuse pieces from your existing Arsenal to compose more complex logic quickly.',
    placement: 'right',
  },
  {
    title: 'Wire the circuit',
    target: '.tour-creator-grid',
    content:
      'Connect each declared input and output. If you skip a port, the Save dialog will warn you before it persists.',
    placement: 'top',
  },
  {
    title: 'Watch the cost meter',
    target: '.tour-creator-cost',
    content:
      'Basic gates cost 1 each, reused Arsenal pieces inherit their own cost. Keep this in mind for budget-tight puzzles.',
    placement: 'bottom',
  },
  {
    title: 'Save your piece',
    target: '.tour-creator-save',
    content:
      'Click Save Piece to open the naming dialog. Give it a name, description, and optional visual style — then it joins your Arsenal.',
    placement: 'top',
  },
];

/**
 * Profile Tour - /app/profile
 */
export const profileTourSteps: TourStep[] = [
  {
    title: 'Track your climb',
    target: '.tour-profile-stats',
    content:
      'Your overall level, XP, and progression live here. Watch the numbers grow as you solve.',
    placement: 'bottom',
  },
  {
    title: 'Show off your medals',
    target: '.tour-profile-medals',
    content:
      'Every gold, silver, and bronze you earn is collected here. Tap one to revisit the puzzle behind it.',
    placement: 'bottom',
  },
];
