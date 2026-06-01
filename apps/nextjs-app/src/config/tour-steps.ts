import { Step } from 'react-joyride';

type TourStep = Step & { 
  title?: string;
  scrollIntoView?: boolean;
  scrollTarget?: string;
  before?: () => Promise<void> | void;
};

const switchToTab = (tabClass: string) => {
  return () =>
    new Promise<void>((resolve) => {
      const tab = document.querySelector(tabClass) as HTMLElement | null;
      if (tab) {
        tab.click();
        setTimeout(resolve, 150);
      } else {
        resolve();
      }
    });
};

/**
 * Browse Puzzles Tour - /app/puzzles
 */
export const browsePuzzlesTourSteps: TourStep[] = [
  {
    title: 'At a Glance',
    target: '.puzzle-info-section',
    content:
      'Check out the puzzle difficulty, title, and description to find the perfect challenge.',
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
    title: 'Jump into the Workstation',
    target: '.puzzle-card-action',
    content:
      'Click Solve Puzzle to enter the Workstation — that is where you wire your gates, run tests, and earn XP.',
    placement: 'left',
  },
  {
    title: 'Filter the gallery',
    target: '.puzzle-filters-button',
    content:
      'Hunt for the right puzzle by difficulty, fun, clarity, or solve status. Try opening it now and slide a filter to see how the list reshuffles.',
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
  {
    title: 'View Leaderboard',
    target: '.puzzle-leaderboard-button',
    content:
      'See how your solution stacks up against other players. Compete for the fastest time or the most efficient circuit.',
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
    title: 'Basic Information',
    target: '.create-puzzle-basic-tab',
    content:
      'Start by naming your puzzle, adding a description, and setting the difficulty level.',
    placement: 'bottom',
    before: switchToTab('.create-puzzle-basic-tab'),
  },
  {
    title: 'Budget and Constraints',
    target: '#cp-field-budget',
    content:
      'Set a maximum gate budget to challenge your solvers. You can also define cycle constraints and per-component limits.',
    placement: 'bottom',
    before: switchToTab('.create-puzzle-basic-tab'),
  },
  {
    title: 'Define what "correct" means',
    target: '.create-puzzle-test-cases-tab',
    content:
      'This is where you list the test cases your puzzle grades against to check the logic.',
    placement: 'bottom',
    before: switchToTab('.create-puzzle-test-cases-tab'),
  },
  {
    title: 'Test Case Types',
    target: '#cp-field-11',
    content:
      'Choose Blackbox for standard inputs/expected-outputs, or Stream for sequential multi-tick arrays.',
    placement: 'bottom',
    before: switchToTab('.create-puzzle-test-cases-tab'),
  },
  {
    title: 'Python Tests (Advanced)',
    target: '.create-puzzle-python-tests-tab',
    content:
      'For complex stream-based puzzles, you can wire up custom Python verification scripts instead of manual test cases.',
    placement: 'bottom',
    before: switchToTab('.create-puzzle-python-tests-tab'),
  },
  {
    title: 'Add custom pieces',
    target: '.create-puzzle-custom-pieces-tab',
    content:
      'Optionally bake in puzzle-specific sub-circuits — handy when you want to scope the gate set or hint at structure.',
    placement: 'bottom',
    before: switchToTab('.create-puzzle-custom-pieces-tab'),
  },
  {
    title: 'Brief your solvers',
    target: '.create-puzzle-instructions-tab',
    content:
      'Write the puzzle story in Markdown. LaTeX math is supported, so go ahead with the equations.',
    placement: 'bottom',
    before: switchToTab('.create-puzzle-instructions-tab'),
  },
  {
    title: 'Initial Board setup',
    target: '.create-puzzle-initial-board-tab',
    content:
      'Place locked components and wires on the board to force solvers to build around your starter layout.',
    placement: 'bottom',
    before: switchToTab('.create-puzzle-initial-board-tab'),
  },
  {
    title: 'Build the reference solution',
    target: '.create-puzzle-solution-tab',
    content:
      'Wire the correct circuit yourself to prove it is solvable. This also determines the "Creator Budget" score to beat.',
    placement: 'bottom',
    before: switchToTab('.create-puzzle-solution-tab'),
  },
  {
    title: 'Ship it',
    target: '.create-puzzle-publish-button',
    content:
      'Publish when ready or keep it as a draft and iterate. You can come back to tune anything later.',
    placement: 'top',
    before: switchToTab('.create-puzzle-basic-tab'),
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

/**
 * Debugger Tour - /app/puzzles/[id]
 */
export const debuggerTourSteps: TourStep[] = [
  {
    title: 'Inline Debugger Mode',
    target: '.debugger-step-controls',
    content:
      'Welcome to the Debugger! This tool helps you inspect exactly how signals flow through your circuit to easily find bugs and trace logic.',
    placement: 'bottom',
  },
  {
    title: 'Combinatorial vs Sequential',
    target: '.debugger-next-step-button',
    content:
      'For regular Combinatorial circuits, the debugger simply calculates the single steady state. For Sequential circuits (with D-Flip-Flops), the circuit evolves over time, and you can use the Next and Previous buttons to move through time tick by tick.',
    placement: 'bottom',
  },
  {
    title: 'Input Sequences',
    target: '.debugger-sequence-inputs',
    content:
      'When debugging sequential puzzles, you can define exactly what signals enter the circuit over time. Edit the sequence strings (like "10110") next to each input pin, then click "Refresh Debug" to simulate that timeline.',
    placement: 'top',
  },
  {
    title: 'Live Port Inspection',
    target: '.workstation-grid',
    content:
      'As you step through time, notice the small numbers floating near every input and output port on your gates. They update in real-time to show you the exact bit value (0 or 1) flowing through that wire at that moment.',
    placement: 'center',
  },
  {
    title: 'Full Debugger Report',
    target: '.debugger-full-report-button',
    content:
      "If stepping manually isn't enough, click here to open a comprehensive truth-table. For regular circuits, it shows all possible input combinations. For sequential circuits, it shows the state of every gate across every tick in your sequence.",
    placement: 'bottom',
  },
  {
    title: 'Exit Debugger',
    target: '.debugger-exit-button',
    content:
      'When you are done analyzing and ready to make changes, click Exit Debugger to return to the normal workstation building mode.',
    placement: 'bottom',
  },
];
