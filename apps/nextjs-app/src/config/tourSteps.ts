import { Step } from 'react-joyride';

/**
 * Browse Puzzles Tour - /app/puzzles
 */
export const browsePuzzlesTourSteps: Step[] = [
  {
    target: '.puzzle-filters-button',
    content:
      'Use the Filters button to search for puzzles by name, difficulty, fun rating, clearness rating, and solve status. You can also sort results to find puzzles that match your skill level.',
    placement: 'bottom',
  },
  {
    target: '.puzzle-instructions-button',
    content:
      'Open the instructions to understand the puzzle goal, constraints, and any hints before you start solving.',
    placement: 'bottom',
  },
  {
    target: '.dialog-close-button',
    content:
      'Use the Close button to exit the instructions and return to the puzzle list.',
    placement: 'left',
  },
  {
    target: '.puzzle-sort-dropdown',
    content:
      'Sort puzzles by creation date, difficulty level, fun rating, or clarity. Find the perfect puzzle to work on next!',
    placement: 'bottom',
  },
  {
    target: '.puzzle-card-action',
    content:
      'Click the "Solve Puzzle" button to enter the Workstation. Here you\'ll design your circuit logic, place gates, and test your solution against the challenge.',
    placement: 'left',
  },
  {
    target: '.puzzle-save-button',
    content:
      'Bookmark puzzles you want to tackle later by clicking the Save button. Your saved puzzles are easy to find on your dashboard.',
    placement: 'left',
  },
  {
    target: '.puzzle-rating-section',
    content:
      'After solving or spending time on a puzzle, you can rate it for fun and clarity. This helps other players find great puzzles and helps creators improve!',
    placement: 'top',
  },
];

/**
 * Puzzle Workstation Tour - /app/puzzles/[id]
 */
export const workstationTourSteps: Step[] = [
  {
    target: '.workstation-component-menu',
    content:
      'Your circuit component palette is here. Drag logic gates (AND, OR, NOT, XOR, etc.) onto the workspace to build your solution. You can also use saved Arsenal pieces if the puzzle allows them.',
    placement: 'right',
  },
  {
    target: '.workstation-grid',
    content:
      'This is your workspace. Place components from the palette onto the grid, and then wire them together by connecting their input and output ports. The colored squares represent your inputs and outputs.',
    placement: 'top',
  },
  {
    target: '.workstation-check-button',
    content:
      'Once your circuit is complete, click "Test Solution" to run simulations against the puzzle\'s test cases. If you pass all tests, you\'ll earn XP and a medal based on your performance!',
    placement: 'top',
  },
  {
    target: '.workstation-debugger-button',
    content:
      'Stuck? Use the Debugger to trace signal flow through your circuit step-by-step. This helps you find logic errors and understand how your gates interact.',
    placement: 'left',
  },
  {
    target: '.workstation-instructions-button',
    content:
      'Refer back to the puzzle instructions to understand the problem statement, constraints, and hints from the puzzle creator.',
    placement: 'left',
  },
  {
    target: '.dialog-close-button',
    content:
      'Use the Close button to exit the instructions and return to the workstation.',
    placement: 'left',
  },
  {
    target: '.workstation-sandbox-toggle',
    content:
      'This is the Sandbox: a safe area where you can experiment freely without changing your current puzzle solution state.',
    placement: 'top',
  },
];

/**
 * Create Puzzle Tour - /app/create-puzzle
 */
export const createPuzzleTourSteps: Step[] = [
  {
    target: '.create-puzzle-basic-tab',
    content:
      'Start here! Name your puzzle, write a description, and set its difficulty level (Easy, Medium, or Hard). You can also set performance constraints like gate budget and cycle limits.',
    placement: 'bottom',
  },
  {
    target: '.create-puzzle-solution-tab',
    content:
      'Build the correct solution circuit here. Design the gates and wires that solve your puzzle. You can also define an "Initial Board" with locked components that solvers must build around.',
    placement: 'bottom',
  },
  {
    target: '.create-puzzle-test-cases-tab',
    content:
      'Define the test cases that validate solver solutions. Specify input values and expected outputs. Solvers must pass all tests to win. Use Python tests for more complex stream-based evaluation.',
    placement: 'bottom',
  },
  {
    target: '.create-puzzle-instructions-tab',
    content:
      'Write clear puzzle instructions in Markdown. Include the problem description, any hints, and context. Support for LaTeX math formulas is included!',
    placement: 'bottom',
  },
  {
    target: '.create-puzzle-custom-pieces-tab',
    content:
      'Optionally create custom sub-circuit pieces for this specific puzzle. These can be used by solvers or as reference implementations.',
    placement: 'bottom',
  },
  {
    target: '.create-puzzle-publish-button',
    content:
      'When ready, publish your puzzle to make it available to the community. Or keep it as a draft to test and refine it further.',
    placement: 'top',
  },
];

/**
 * My Puzzles Tour - /app/my-puzzles
 */
export const myPuzzlesTourSteps: Step[] = [
  {
    target: '.tour-my-puzzles-tabs',
    content:
      'Switch between your published puzzles and unpublished drafts.',
    placement: 'bottom',
  },
  {
    target: '.tour-my-puzzles-create',
    content:
      'Click here to create a brand new puzzle.',
    placement: 'bottom',
  },
  {
    target: '.tour-my-puzzles-actions',
    content:
      'Manage your puzzles here: edit details, publish/unpublish, or delete them.',
    placement: 'top',
  },
];

/**
 * Arsenal Tour - /app/arsenal
 */
export const arsenalTourSteps: Step[] = [
  {
    target: '.tour-arsenal-list',
    content:
      'This is your collection of custom-built circuit pieces.',
    placement: 'bottom',
  },
  {
    target: '.tour-arsenal-preview',
    content:
      'Preview the internal logic of your saved pieces.',
    placement: 'top',
  },
  {
    target: '.tour-arsenal-actions',
    content:
      'Keep your arsenal organized by renaming or deleting unused pieces.',
    placement: 'top',
  },
];

/**
 * Profile Tour - /app/profile
 */
export const profileTourSteps: Step[] = [
  {
    target: '.tour-profile-stats',
    content:
      'Track your overall progression, Level, and total XP here.',
    placement: 'bottom',
  },
  {
    target: '.tour-profile-medals',
    content:
      'See your puzzle-solving achievements and the medals you\'ve earned.',
    placement: 'bottom',
  },
];
