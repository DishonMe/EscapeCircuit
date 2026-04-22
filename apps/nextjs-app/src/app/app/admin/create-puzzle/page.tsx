/**
 * Create Puzzle Form Component with Tabs
 * Supports creating puzzles with form input or file upload
 */
'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import { useQueryClient, useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { CircleAlert, CircleCheck, CircuitBoard } from 'lucide-react';
import Cookies from 'js-cookie';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';
import { PageHero } from '@/components/ui/page-hero/page-hero';
import { StyledSelect } from '@/components/ui/styled-select/styled-select';

const DIFFICULTY_OPTIONS = [
  { value: 'EASY' as const, label: 'Easy' },
  { value: 'MEDIUM' as const, label: 'Medium' },
  { value: 'HARD' as const, label: 'Hard' },
];

const TEST_CASE_KIND_OPTIONS = [
  { value: 'blackbox' as const, label: 'Blackbox (Combinatorial)' },
  { value: 'stream' as const, label: 'Stream (Sequential)' },
];

const BIT_OPTIONS = [
  { value: 0, label: '0' },
  { value: 1, label: '1' },
];
import MarkdownIt from 'markdown-it';
// @ts-ignore - markdown-it-katex doesn't have types
import markdownItKatex from 'markdown-it-katex';
import 'katex/dist/katex.min.css';
import {
  WorkstationGrid,
  type ComponentDef,
  type PlacedGridComponent,
  type SelectedComponentState,
} from '@/app/app/puzzles/[id]/_components/workstation-grid';
import type { Wire } from '@/types/api';

type TabName =
  | 'basic'
  | 'test-cases'
  | 'python-tests'
  | 'instructions'
  | 'solution';

interface BasicInfo {
  name: string;
  description: string;
  budget: number;
  creator_budget: number | null;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  timeLimit: number | null;
  minCycles: number | null;
  maxCycles: number | null;
  minGateCount: number | null;
  totalGateCount: number | null;
  gateQuotas: Record<string, number>;
  minGateQuotas: Record<string, number>;
  gateSet: string[];
  inputs: string[];
  outputs: string[];
  allowArsenal: boolean;
  boardRows: number | null;
  boardCols: number | null;
}

interface TestCase {
  id?: string;
  kind?: 'blackbox' | 'stream'; // Default: 'blackbox'
  inputs?: Record<string, number>;
  expectedOutputs?: Record<string, number>;
  inputStream?: Array<Record<string, number>>;
  expectedOutputStream?: Record<string, number[]>;
}

// Helper functions for parsing binary string format
const parseBinaryString = (str: string): number[] => {
  const trimmed = str.trim();
  if (!trimmed) return [];
  if (trimmed.includes(',')) {
    return trimmed
      .split(',')
      .map((b) => {
        const val = parseInt(b.trim(), 10);
        return val === 0 || val === 1 ? val : NaN;
      })
      .filter((v) => !isNaN(v));
  } else {
    return trimmed
      .split('')
      .map((b) => {
        const val = parseInt(b, 10);
        return val === 0 || val === 1 ? val : NaN;
      })
      .filter((v) => !isNaN(v));
  }
};

const arrayToBinaryString = (arr: number[]): string => {
  return arr.join(',');
};

const formatInputStreamForDisplay = (
  inputStream?: Array<Record<string, number>>,
): string => {
  if (!inputStream || inputStream.length === 0) {
    return '[]';
  }

  const inputNameMap: Record<string, true> = {};
  inputStream.forEach((cycleInputs) => {
    Object.keys(cycleInputs || {}).forEach((inputName) => {
      inputNameMap[inputName] = true;
    });
  });

  const inputNames = Object.keys(inputNameMap);
  if (inputNames.length === 0) {
    return `${inputStream.length} cycles`;
  }

  return inputNames
    .map((inputName) => {
      const values = inputStream.map(
        (cycleInputs) => cycleInputs[inputName] ?? 0,
      );
      return `${inputName}: [${values.join(',')}]`;
    })
    .join('; ');
};

const canonicalizeValue = (value: unknown): unknown => {
  if (Array.isArray(value)) {
    return value.map((item) => canonicalizeValue(item));
  }

  if (value && typeof value === 'object') {
    const objectValue = value as Record<string, unknown>;
    return Object.keys(objectValue)
      .sort()
      .reduce<Record<string, unknown>>((acc, key) => {
        acc[key] = canonicalizeValue(objectValue[key]);
        return acc;
      }, {});
  }

  return value;
};

const getTestCaseComparisonSignature = (testCase: TestCase): string => {
  const kind: 'blackbox' | 'stream' =
    testCase.kind === 'stream' ? 'stream' : 'blackbox';

  const comparableCase =
    kind === 'stream'
      ? {
          kind,
          inputStream: testCase.inputStream || [],
          expectedOutputStream: testCase.expectedOutputStream || {},
        }
      : {
          kind,
          inputs: testCase.inputs || {},
          expectedOutputs: testCase.expectedOutputs || {},
        };

  return JSON.stringify(canonicalizeValue(comparableCase));
};

interface CreatePuzzleData {
  basic: BasicInfo;
  testCases: TestCase[];
  pythonTests: File | null;
  instructions: string;
  solutionJSON: string;
}

const availableGates = [
  'AND',
  'OR',
  'NOT',
  'XOR',
  'NAND',
  'NOR',
  'XNOR',
  'DFF',
];

const CUSTOM_MIN_MAX_TARGETS = [
  {
    name: '__CUSTOM_TOTAL__',
    label: 'All custom pieces (total usage)',
    maxCanBeZero: true,
  },
] as const;

const ARSENAL_MAX_ONLY_TARGETS = [
  {
    name: '__ARSENAL_TOTAL__',
    label: 'All non-shared arsenal pieces (total usage)',
    maxCanBeZero: false,
  },
  {
    name: '__ARSENAL_EACH__',
    label: 'Each non-shared arsenal piece (per piece)',
    maxCanBeZero: false,
  },
] as const;

const ADMIN_ZERO_ALLOWED_GATE_KEYS = new Set(['__CUSTOM_TOTAL__']);
const ADMIN_ARSENAL_MAX_ONLY_KEYS = new Set([
  '__ARSENAL_TOTAL__',
  '__ARSENAL_EACH__',
]);

// Convert LaTeX to Markdown for preview rendering
const latexToMarkdown = (latex: string): string => {
  let markdown = latex;

  // Convert tabular to markdown tables
  const tabularyRegex =
    /\\begin\{(?:tabular|array)\}\{[^}]*\}(.*?)\\end\{(?:tabular|array)\}/gs;
  markdown = markdown.replace(tabularyRegex, (match, content) => {
    const rows = content
      .split('\\\\')
      .map((row: string) => row.replace(/\\hline/g, '').trim())
      .filter((row: string) => row.length > 0);

    if (rows.length === 0) return '';

    const mdRows = rows.map((row: string) => {
      const cells = row.split('&').map((cell: string) => cell.trim());
      return '| ' + cells.join(' | ') + ' |';
    });

    if (mdRows.length > 0) {
      const firstRowCells = rows[0].split('&').length;
      const separator = '|' + Array(firstRowCells).fill('---|').join('');
      mdRows.splice(1, 0, separator);
    }

    return '\n' + mdRows.join('\n') + '\n';
  });

  // Convert sections to markdown headers
  markdown = markdown.replace(/\\section\*\s*\{([^}]+)\}/g, '# $1');
  markdown = markdown.replace(/\\subsection\*\s*\{([^}]+)\}/g, '## $1');
  markdown = markdown.replace(/\\subsubsection\*\s*\{([^}]+)\}/g, '### $1');

  // Convert text formatting
  markdown = markdown.replace(/\\textbf\s*\{([^}]+)\}/g, '**$1**');
  markdown = markdown.replace(/\\textit\s*\{([^}]+)\}/g, '*$1*');
  markdown = markdown.replace(/\\texttt\s*\{([^}]+)\}/g, '`$1`');

  // Handle lists
  markdown = markdown.replace(/\\begin\{itemize\}/g, '');
  markdown = markdown.replace(/\\end\{itemize\}/g, '');
  markdown = markdown.replace(/\\item\s+/g, '- ');
  markdown = markdown.replace(/\\begin\{enumerate\}/g, '');
  markdown = markdown.replace(/\\end\{enumerate\}/g, '');

  // Handle centers
  markdown = markdown.replace(/\\begin\{center\}(.*?)\\end\{center\}/gs, '$1');

  // Line breaks
  markdown = markdown.replace(/\\\\/g, '\n');

  return markdown;
};

// Instructions preview component
const InstructionsPreview = ({ latex }: { latex: string }) => {
  const [renderedHtml, setRenderedHtml] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const renderPreview = async () => {
      if (!latex) {
        if (isMounted) {
          setRenderedHtml(null);
        }
        return;
      }

      const markdown = latexToMarkdown(latex);
      const md = new MarkdownIt({ html: true }).use(markdownItKatex);
      const html = md.render(markdown);
      const { default: DOMPurify } = await import('dompurify');

      if (isMounted) {
        setRenderedHtml(
          DOMPurify.sanitize(html, {
            ALLOWED_TAGS: [
              'p',
              'strong',
              'em',
              'u',
              'code',
              'pre',
              'blockquote',
              'h1',
              'h2',
              'h3',
              'h4',
              'h5',
              'h6',
              'ul',
              'ol',
              'li',
              'table',
              'thead',
              'tbody',
              'tr',
              'th',
              'td',
              'a',
              'span',
              'div',
              'i',
              'br',
              'sup',
              'sub',
              'annotation',
              'semantics',
              'mrow',
              'mi',
              'mn',
              'mo',
              'mtext',
              'mfrac',
              'msup',
              'msub',
              'mroot',
              'msqrt',
            ],
            ALLOWED_ATTR: ['class', 'style', 'href', 'data-*'],
          }),
        );
      }
    };

    renderPreview().catch(() => {
      if (isMounted) {
        setRenderedHtml(null);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [latex]);

  return (
    <div className="w-full rounded-xl border border-border bg-secondary/50 p-4 min-h-96 overflow-y-auto text-[13px]">
      <style>{`
        .prose .katex {
          vertical-align: baseline !important;
          margin: 0 !important;
          padding: 0 !important;
          line-height: 1 !important;
          font-size: inherit;
          display: inline;
          white-space: nowrap;
          position: relative;
          top: -0.35em;
        }
        .prose table {
          border-collapse: collapse;
          width: 100%;
          margin: 1em 0;
        }
        .prose table td,
        .prose table th {
          border: 1px solid currentColor;
          padding: 0.5em;
          text-align: center;
          vertical-align: middle;
          line-height: 1.4;
        }
        .prose table th {
          font-weight: bold;
          background-color: rgba(0, 0, 0, 0.05);
        }
      `}</style>
      {renderedHtml ? (
        <div
          className="prose prose-sm max-w-none dark:prose-invert text-foreground [&_*]:text-foreground"
          dangerouslySetInnerHTML={{ __html: renderedHtml }}
        />
      ) : (
        <p className="text-foreground/75">No instructions yet</p>
      )}
    </div>
  );
};

export default function CreatePuzzleForm() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabName>('basic');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirm, setShowConfirm] = useState<'submit' | 'cancel' | null>(
    null,
  );

  // Workstation state for solution design
  const [placed, setPlaced] = useState<PlacedGridComponent[]>([]);
  const [wires, setWires] = useState<Wire[]>([]);
  const [selectedComponent, setSelectedComponent] =
    useState<SelectedComponentState>({ mode: 'none' });
  const [draggedPaletteComponentId, setDraggedPaletteComponentId] = useState<
    string | null
  >(null);

  const [data, setData] = useState<CreatePuzzleData>({
    basic: {
      name: '',
      description: '',
      budget: 0,
      creator_budget: null,
      difficulty: 'EASY',
      timeLimit: null,
      minCycles: null,
      maxCycles: null,
      minGateCount: null,
      totalGateCount: null,
      gateQuotas: {},
      minGateQuotas: {},
      gateSet: [],
      inputs: [],
      outputs: [],
      allowArsenal: true,
      boardRows: null,
      boardCols: null,
    },
    testCases: [],
    pythonTests: null,
    instructions: '',
    solutionJSON: '',
  });

  const [testCaseForm, setTestCaseForm] = useState<TestCase>({
    kind: 'blackbox',
    inputs: {},
    expectedOutputs: {},
    inputStream: [],
    expectedOutputStream: {},
  });

  // State for stream test case string representation
  const [streamInputStrings, setStreamInputStrings] = useState<
    Record<string, string>
  >({});
  const [streamOutputStrings, setStreamOutputStrings] = useState<
    Record<string, string>
  >({});

  const handleBasicChange = (field: keyof BasicInfo, value: any) => {
    setData((prev) => ({
      ...prev,
      basic: { ...prev.basic, [field]: value },
    }));
  };

  const handleAddTestCase = () => {
    const initializedForm = { ...testCaseForm };

    if (
      (initializedForm.kind === 'blackbox' || !initializedForm.kind) &&
      (data.basic.inputs.length === 0 || data.basic.outputs.length === 0)
    ) {
      alert(
        'Please add at least one input and one output before creating a blackbox test case.',
      );
      return;
    }

    // Only initialize inputs/outputs if this is a blackbox test case
    if (initializedForm.kind === 'blackbox' || !initializedForm.kind) {
      if (!initializedForm.inputs) initializedForm.inputs = {};
      if (!initializedForm.expectedOutputs)
        initializedForm.expectedOutputs = {};

      data.basic.inputs.forEach((inputName) => {
        if (!(inputName in initializedForm.inputs!)) {
          initializedForm.inputs![inputName] = 0;
        }
      });

      data.basic.outputs.forEach((outputName) => {
        if (!(outputName in initializedForm.expectedOutputs!)) {
          initializedForm.expectedOutputs![outputName] = 0;
        }
      });
    } else if (initializedForm.kind === 'stream') {
      // For stream, convert string format to JSON format
      const inputArrays: Record<string, number[]> = {};
      const outputArrays: Record<string, number[]> = {};

      // Parse input streams
      data.basic.inputs.forEach((inputName) => {
        const streamStr = streamInputStrings[inputName] || '';
        inputArrays[inputName] = parseBinaryString(streamStr);
      });

      // Parse output streams
      data.basic.outputs.forEach((outputName) => {
        const streamStr = streamOutputStrings[outputName] || '';
        outputArrays[outputName] = parseBinaryString(streamStr);
      });

      // Validate: at least one input stream must have values
      const hasAnyInput = Object.values(inputArrays).some(
        (arr) => arr.length > 0,
      );
      if (!hasAnyInput) {
        alert(
          'At least one input stream must have values\nExample: "01010" or "0,1,0,1,0"',
        );
        return;
      }

      // Validate: at least one output stream must have values
      const hasAnyOutput = Object.values(outputArrays).some(
        (arr) => arr.length > 0,
      );
      if (!hasAnyOutput) {
        alert(
          'At least one output stream must have values\nExample: "10101" or "1,0,1,0,1"',
        );
        return;
      }

      // Determine the number of cycles
      const numCycles = Math.max(
        ...Object.values(inputArrays).map((arr) => arr.length),
        ...Object.values(outputArrays).map((arr) => arr.length),
      );

      // Check min_cycles constraint
      if (data.basic.minCycles !== null && numCycles < data.basic.minCycles) {
        alert(
          `Test case has ${numCycles} cycles but minimum required is ${data.basic.minCycles}`,
        );
        return;
      }

      // Check max_cycles constraint
      if (data.basic.maxCycles !== null && numCycles > data.basic.maxCycles) {
        alert(
          `Test case has ${numCycles} cycles but maximum allowed is ${data.basic.maxCycles}`,
        );
        return;
      }

      // Verify all input streams have the same length
      for (const [inputName, values] of Object.entries(inputArrays)) {
        if (values.length > 0 && values.length !== numCycles) {
          alert(
            `Input "${inputName}" length ${values.length} doesn't match other streams (${numCycles} cycles)`,
          );
          return;
        }
      }

      // Verify all output streams have the same length
      for (const [outputName, values] of Object.entries(outputArrays)) {
        if (values.length > 0 && values.length !== numCycles) {
          alert(
            `Output "${outputName}" length ${values.length} doesn't match other streams (${numCycles} cycles)`,
          );
          return;
        }
      }

      // Fill empty inputs with zeros for the required cycles
      data.basic.inputs.forEach((inputName) => {
        while (inputArrays[inputName].length < numCycles) {
          inputArrays[inputName].push(0);
        }
      });

      // Fill empty outputs with zeros for the required cycles
      data.basic.outputs.forEach((outputName) => {
        while (outputArrays[outputName].length < numCycles) {
          outputArrays[outputName].push(0);
        }
      });

      // Convert to backend format: inputStream is array of dicts, expectedOutputStream is dict of arrays
      const inputStream: Array<Record<string, number>> = [];
      for (let i = 0; i < numCycles; i++) {
        const cycleInputs: Record<string, number> = {};
        data.basic.inputs.forEach((inputName) => {
          cycleInputs[inputName] = inputArrays[inputName][i];
        });
        inputStream.push(cycleInputs);
      }

      initializedForm.inputStream = inputStream;
      initializedForm.expectedOutputStream = outputArrays;
    }

    const newTestCaseSignature =
      getTestCaseComparisonSignature(initializedForm);
    const hasDuplicateTestCase = data.testCases.some(
      (existingTestCase) =>
        getTestCaseComparisonSignature(existingTestCase) ===
        newTestCaseSignature,
    );

    if (hasDuplicateTestCase) {
      alert('An identical test case already exists.');
      return;
    }

    setData((prev) => ({
      ...prev,
      testCases: [
        ...prev.testCases,
        {
          id: `tc-${Date.now()}`,
          ...initializedForm,
        },
      ],
    }));

    // Reset form
    setTestCaseForm({
      kind: initializedForm.kind || 'blackbox',
      inputs: {},
      expectedOutputs: {},
      inputStream: [],
      expectedOutputStream: {},
    });
    setStreamInputStrings({});
    setStreamOutputStrings({});
  };

  const handleRemoveTestCase = (id: string | undefined) => {
    if (!id) return;
    setData((prev) => ({
      ...prev,
      testCases: prev.testCases.filter((tc) => tc.id !== id),
    }));
  };

  // Build component catalog for workstation
  const uiCatalog = useMemo(() => {
    const catalog: Record<string, ComponentDef> = {};
    const gateConfigs: Record<
      string,
      { size: { w: number; h: number }; ports: any[] }
    > = {
      AND: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      OR: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      XOR: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      NOT: {
        size: { w: 3, h: 1 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      NAND: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      NOR: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      XNOR: {
        size: { w: 3, h: 2 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'IN1', kind: 'input', offset: { row: 1, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
      DFF: {
        size: { w: 3, h: 1 },
        ports: [
          { id: 'IN0', kind: 'input', offset: { row: 0, col: 0 } },
          { id: 'OUT0', kind: 'output', offset: { row: 0, col: 2 } },
        ],
      },
    };

    for (const gateName of data.basic.gateSet) {
      const config = gateConfigs[gateName] || gateConfigs.AND;
      catalog[gateName] = {
        id: gateName,
        label: gateName,
        cost: 1,
        size: config.size,
        ports: config.ports,
      };
    }
    return catalog;
  }, [data.basic.gateSet]);

  // Export solution from workstation
  const exportSolution = useCallback(async () => {
    // Build eval_map by simulating circuit on test cases
    const evalMap: Record<string, Record<string, number>> = {};
    let simulationErrors: string[] = [];

    // Check if circuit exists
    if (placed.length === 0 && wires.length === 0) {
      alert('No circuit designed. Add gates and wires before exporting.');
      return;
    }

    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8081/api';
    const baseUrl = apiUrl.replace(/\/api\/?$/, '');

    // Simulate circuit for each test case
    for (const tc of data.testCases) {
      if (tc.kind === 'stream') {
        // === STREAM TEST CASE: Simulate entire sequence, then extract eval_map entries ===
        if (!tc.inputStream || !tc.expectedOutputStream) {
          simulationErrors.push(
            `Stream test case is missing inputStream or expectedOutputStream`,
          );
          continue;
        }

        try {
          // Simulate the entire sequence at once to preserve state
          const response = await fetch(
            `${baseUrl}/debugger/simulate-sequence`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                input_stream: tc.inputStream,
                placed: placed,
                wires: wires,
              }),
            },
          );

          if (!response.ok) {
            const err = await response.json();
            console.error('[EXPORT-STREAM] API Error:', err);
            throw new Error(err.detail || 'Sequence simulation failed');
          }

          const result = await response.json();
          const cycleOutputs = result.cycle_outputs || {};

          // Extract outputs for each cycle and build eval_map
          for (let cycleIdx = 0; cycleIdx < tc.inputStream.length; cycleIdx++) {
            const cycleInput = (tc.inputStream[cycleIdx] || {}) as Record<
              string,
              number
            >;
            const expectedOutputStream = tc.expectedOutputStream || {};

            // Get expected outputs for this cycle
            const cycleExpectedOutputs = Object.fromEntries(
              Object.entries(expectedOutputStream).map(
                ([outName, outValues]: [string, any]) => [
                  outName,
                  Array.isArray(outValues) ? outValues[cycleIdx] : outValues,
                ],
              ),
            );

            // Get actual outputs for this cycle from the sequence simulation
            const cycleKey = `cycle_${cycleIdx}`;
            const cycleActualOutputs = cycleOutputs[cycleKey] || {};

            // Reorder cycle actual outputs to match expected outputs key order
            const reorderedCycleOutputs: Record<string, number> = {};
            const expectedOutputKeys = Object.keys(cycleExpectedOutputs);
            for (const key of expectedOutputKeys) {
              reorderedCycleOutputs[key] = cycleActualOutputs[key];
            }

            // Create eval_map key for this input - MUST be sorted for backend lookup
            const sortedInputKeys: string[] = Object.keys(cycleInput).sort();
            const evalKey = JSON.stringify(
              Object.fromEntries(
                sortedInputKeys.map((k: string) => [k, cycleInput[k]]),
              ),
              undefined,
              '',
            );

            // For sequential circuits, the same input can appear in different cycles
            // with different outputs due to state. We'll use the first occurrence.
            if (!(evalKey in evalMap)) {
              evalMap[evalKey] = reorderedCycleOutputs;
            } else {
            }

            // Check if this cycle matches expected output
            const cycleMatches =
              JSON.stringify(reorderedCycleOutputs) ===
              JSON.stringify(cycleExpectedOutputs);
            if (!cycleMatches) {
              simulationErrors.push(
                `Stream test cycle ${cycleIdx} ${JSON.stringify(cycleInput)}: ` +
                  `Expected ${JSON.stringify(cycleExpectedOutputs)} but got ${JSON.stringify(reorderedCycleOutputs)}`,
              );
            }
          }
        } catch (e) {
          console.error('[EXPORT-STREAM] Error:', e);
          simulationErrors.push(
            `Stream test case simulation error: ${String(e)}`,
          );
        }
      } else if (
        tc.kind === 'blackbox' ||
        (tc.inputs !== undefined && tc.expectedOutputs !== undefined)
      ) {
        // === BLACKBOX TEST CASE ===
        const testInputs = tc.inputs || {};
        const expectedOutputs = tc.expectedOutputs || {};

        const sortedInputKeys: string[] = Object.keys(testInputs).sort();
        const key = JSON.stringify(
          Object.fromEntries(
            sortedInputKeys.map((k: string) => [k, testInputs[k]]),
          ),
          undefined,
          '',
        );

        try {
          // Call backend API to actually simulate the circuit
          const response = await fetch(`${baseUrl}/debugger/simulate-circuit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              inputs: tc.inputs,
              placed: placed,
              wires: wires,
            }),
          });

          if (!response.ok) {
            const err = await response.json();
            console.error('[EXPORT-BLACKBOX] API Error:', err);
            throw new Error(err.detail || 'Simulation failed');
          }

          const result = await response.json();
          const simulatedOutputs = result.outputs || {};

          // Reorder simulated outputs to match expected outputs key order
          const reorderedOutputs: Record<string, number> = {};
          const expectedKeys = Object.keys(expectedOutputs);
          for (const key of expectedKeys) {
            reorderedOutputs[key] = simulatedOutputs[key];
          }

          // Store the ACTUAL circuit output, not the expected output
          evalMap[key] = reorderedOutputs;

          // Check if it matches expected
          const matches =
            JSON.stringify(reorderedOutputs) ===
            JSON.stringify(expectedOutputs);
          if (!matches) {
            simulationErrors.push(
              `Test ${Object.keys(testInputs)
                .map((k: string) => `${k}=${testInputs[k]}`)
                .join(',')}: ` +
                `Expected ${JSON.stringify(expectedOutputs)} but got ${JSON.stringify(reorderedOutputs)}`,
            );
          }
        } catch (e) {
          console.error('[EXPORT-BLACKBOX] Error:', e);
          simulationErrors.push(`Simulation error: ${String(e)}`);
        }
      }
    }

    if (simulationErrors.length > 0) {
      console.warn(
        '[EXPORT] Simulation warnings ignored for export:',
        simulationErrors,
      );
    }

    // All tests passed - create solution
    const solution = {
      eval_map: evalMap,
      circuit: {
        placed: placed.map((p) => ({
          id: p.id,
          componentId: p.componentId,
          origin: p.origin,
          rotation: p.rotation,
        })),
        wires: wires.map((w) => ({
          id: w.id,
          from: w.from,
          to: w.to,
        })),
      },
    };

    setData((prev) => ({
      ...prev,
      solutionJSON: JSON.stringify(solution, null, 2),
    }));

    alert('Circuit validated. All test cases passed. Solution exported.');
  }, [placed, wires, data.testCases]);

  const handleAddInputField = () => {
    // Find the first input that hasn't been added to the form yet
    const missingInput = data.basic.inputs.find(
      (inputName) => !(inputName in (testCaseForm.inputs || {})),
    );
    const inputName =
      missingInput || `input_${Object.keys(testCaseForm.inputs || {}).length}`;
    setTestCaseForm((prev) => ({
      ...prev,
      inputs: { ...(prev.inputs || {}), [inputName]: 0 },
    }));
  };

  const handleAddOutputField = () => {
    // Find the first output that hasn't been added to the form yet
    const missingOutput = data.basic.outputs.find(
      (outputName) => !(outputName in (testCaseForm.expectedOutputs || {})),
    );
    const outputName =
      missingOutput ||
      `output_${Object.keys(testCaseForm.expectedOutputs || {}).length}`;
    setTestCaseForm((prev) => ({
      ...prev,
      expectedOutputs: { ...(prev.expectedOutputs || {}), [outputName]: 0 },
    }));
  };

  const handleSubmit = async () => {
    if (!data.basic.name.trim()) {
      alert('Puzzle name is required');
      return;
    }
    if (data.basic.gateSet.length === 0) {
      alert('Select at least one gate type');
      return;
    }
    if (data.basic.inputs.length === 0 || data.basic.outputs.length === 0) {
      alert('Define at least one input and one output');
      return;
    }
    if (data.testCases.length === 0) {
      alert('Add at least one test case');
      return;
    }
    if (!data.instructions.trim()) {
      alert('Add instructions for the puzzle');
      return;
    }
    if (!data.solutionJSON.trim()) {
      alert('Provide a sample solution');
      return;
    }

    if (
      data.basic.minGateCount !== null &&
      data.basic.totalGateCount !== null &&
      data.basic.minGateCount > data.basic.totalGateCount
    ) {
      alert('Minimum Gate Count cannot exceed Gate Limit');
      return;
    }

    const sanitizedMinGateQuotas = Object.fromEntries(
      Object.entries(data.basic.minGateQuotas).filter(
        ([gateName]) => !ADMIN_ARSENAL_MAX_ONLY_KEYS.has(gateName),
      ),
    ) as Record<string, number>;

    for (const [gateName, minValue] of Object.entries(sanitizedMinGateQuotas)) {
      const numericMin = Number(minValue);
      if (!Number.isInteger(numericMin) || numericMin < 0) {
        alert(
          `Invalid minimum limit for ${gateName}. Use a non-negative integer.`,
        );
        return;
      }
    }

    for (const [gateName, maxValue] of Object.entries(data.basic.gateQuotas)) {
      const numericMax = Number(maxValue);
      if (!Number.isInteger(numericMax) || numericMax < 0) {
        alert(
          `Invalid maximum limit for ${gateName}. Use a non-negative integer.`,
        );
        return;
      }
      if (numericMax === 0 && !ADMIN_ZERO_ALLOWED_GATE_KEYS.has(gateName)) {
        alert(`Maximum limit for ${gateName} must be greater than 0.`);
        return;
      }
    }

    const quotaNames = new Set([
      ...Object.keys(sanitizedMinGateQuotas),
      ...Object.keys(data.basic.gateQuotas),
    ]);
    for (const gateName of quotaNames) {
      const minValue = sanitizedMinGateQuotas[gateName];
      const maxValue = data.basic.gateQuotas[gateName];
      if (
        minValue !== undefined &&
        maxValue !== undefined &&
        minValue > maxValue
      ) {
        alert(`Minimum limit for ${gateName} cannot exceed maximum limit.`);
        return;
      }
    }

    setIsSubmitting(true);
    try {
      const authToken = Cookies.get(AUTH_TOKEN_COOKIE_NAME);

      // Convert test cases from camelCase to snake_case for backend
      const convertedTestCases = data.testCases.map(({ id, ...tc }) => {
        const converted: any = {
          kind: tc.kind,
        };

        if (tc.kind === 'stream') {
          // Stream test case: inputStream -> input_stream, expectedOutputStream -> expected_output_stream
          converted.input_stream = tc.inputStream || [];
          converted.expected_output_stream = tc.expectedOutputStream || {};
        } else {
          // Blackbox test case: inputs and expectedOutputs
          converted.inputs = tc.inputs || {};
          converted.expected_outputs = tc.expectedOutputs || {};
        }

        return converted;
      });

      // ADD: Convert gate quotas to gate_limit test cases
      const gateQuotasEntries = Object.entries(data.basic.gateQuotas);
      const minGateQuotasEntries = Object.entries(sanitizedMinGateQuotas);

      // Create test cases for maximum gate limits
      if (gateQuotasEntries.length > 0) {
        gateQuotasEntries.forEach(([gateName, gateLimit]) => {
          convertedTestCases.push({
            kind: 'gate_limit',
            gate_name: gateName,
            gate_limit: gateLimit,
          });
        });
      }

      // Create test cases for minimum gate limits
      if (minGateQuotasEntries.length > 0) {
        minGateQuotasEntries.forEach(([gateName, minGateLimit]) => {
          convertedTestCases.push({
            kind: 'gate_limit',
            gate_name: gateName,
            min_gate_limit: minGateLimit,
          });
        });
      }

      // ADD: Add total gate count limit test case if specified
      if (
        (data.basic.minGateCount ?? 0) > 0 ||
        (data.basic.totalGateCount ?? 0) > 0
      ) {
        convertedTestCases.push({
          kind: 'gate_count_limit',
          min_gate_count:
            (data.basic.minGateCount ?? 0) > 0
              ? data.basic.minGateCount
              : undefined,
          max_gate_count:
            (data.basic.totalGateCount ?? 0) > 0
              ? data.basic.totalGateCount
              : undefined,
        });
      }

      const configData = {
        puzzle: {
          name: data.basic.name,
          description: data.basic.description,
          budget: data.basic.budget,
          creator_budget: data.basic.creator_budget,
          time_limit_seconds: data.basic.timeLimit,
          difficulty: data.basic.difficulty,
          default_gate_set: data.basic.gateSet,
          inputs: data.basic.inputs,
          outputs: data.basic.outputs,
          min_cycles: data.basic.minCycles,
          max_cycles: data.basic.maxCycles,
          min_gate_count: data.basic.minGateCount,
          total_gate_count: data.basic.totalGateCount,
          allow_arsenal: data.basic.allowArsenal,
          board: {
            rows: data.basic.boardRows,
            cols: data.basic.boardCols,
          },
        },
        test_cases: convertedTestCases,
      };

      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8081/api';
      const baseUrl = apiUrl.replace(/\/api\/?$/, '');

      const formData = new FormData();
      formData.append(
        'config_file',
        new Blob([JSON.stringify(configData, null, 2)], {
          type: 'application/json',
        }),
        'puzzle_config.json',
      );
      formData.append(
        'instructions_file',
        new Blob([data.instructions], { type: 'text/plain' }),
        'puzzle_instructions.tex',
      );
      formData.append(
        'sample_solution_file',
        new Blob([data.solutionJSON], { type: 'application/json' }),
        'puzzle_solution.json',
      );

      // Add Python tests file if provided
      if (data.pythonTests) {
        formData.append(
          'python_tests_file',
          data.pythonTests,
          data.pythonTests.name,
        );
      }

      formData.append('difficulty', data.basic.difficulty);

      const res = await fetch(`${baseUrl}/admin/create-puzzle-form`, {
        method: 'POST',
        headers: {
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        const detail = err.detail;
        const errorMessage =
          typeof detail === 'string'
            ? detail
            : JSON.stringify(detail) || 'Upload failed';
        throw new Error(errorMessage);
      }

      setShowConfirm(null);
      alert('Puzzle created successfully!');
      await queryClient.invalidateQueries({ queryKey: ['puzzles'] });
      router.push('/app/my-puzzles');
    } catch (err: any) {
      alert('Error: ' + (err.message || 'Failed to create puzzle'));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setShowConfirm(null);
    router.push('/app/admin/upload-puzzle');
  };

  return (
    <div className="p-8 max-w-6xl mx-auto text-foreground">
      <PageHero
        badge="Admin tools"
        icon={CircuitBoard}
        title="Create New Puzzle"
        description="Design a new circuit challenge end-to-end — basic info, test cases, instructions, and a sample solution."
      />

      {/* Tabs */}
      <div className="flex border-b mb-6">
        {(
          [
            'basic',
            'test-cases',
            'python-tests',
            'instructions',
            'solution',
          ] as TabName[]
        ).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-6 py-2 text-[13px] font-semibold transition-colors ${
              activeTab === tab
                ? 'border-b-2 border-foreground text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab === 'basic'
              ? 'Basic Info'
              : tab === 'test-cases'
                ? 'Test Cases'
                : tab === 'python-tests'
                  ? 'Python Tests'
                  : tab === 'instructions'
                    ? 'Instructions'
                    : 'Solution'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="mb-8">
        {activeTab === 'basic' && (
          <div className="space-y-6">
            <div>
              <label className="block text-[13px] font-medium text-foreground mb-2">
                Puzzle Name *
              </label>
              <input
                type="text"
                value={data.basic.name}
                onChange={(e) => handleBasicChange('name', e.target.value)}
                className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="e.g., Binary Adder"
              />
            </div>

            <div>
              <label className="block text-[13px] font-medium text-foreground mb-2">
                Description *
              </label>
              <textarea
                value={data.basic.description}
                onChange={(e) =>
                  handleBasicChange('description', e.target.value)
                }
                className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                rows={3}
                placeholder="Brief description of the puzzle"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Budget *
                </label>
                <input
                  type="number"
                  value={data.basic.budget}
                  onChange={(e) =>
                    handleBasicChange('budget', parseInt(e.target.value))
                  }
                  className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder="e.g., 20"
                />
              </div>

              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Difficulty *
                </label>
                <StyledSelect
                  aria-label="Difficulty"
                  value={data.basic.difficulty}
                  onValueChange={(v) => handleBasicChange('difficulty', v)}
                  options={DIFFICULTY_OPTIONS}
                />
              </div>
            </div>

            <div>
              <label className="block text-[13px] font-medium text-foreground mb-2">
                Time Limit (seconds, optional)
              </label>
              <input
                type="number"
                value={data.basic.timeLimit ?? ''}
                onChange={(e) =>
                  handleBasicChange(
                    'timeLimit',
                    e.target.value ? parseInt(e.target.value) : null,
                  )
                }
                className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="Leave empty for no limit"
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Min Cycles (optional)
                </label>
                <input
                  type="number"
                  value={data.basic.minCycles ?? ''}
                  onChange={(e) =>
                    handleBasicChange(
                      'minCycles',
                      e.target.value ? parseInt(e.target.value) : null,
                    )
                  }
                  className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder="For sequential circuits"
                />
              </div>
              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Max Cycles (optional)
                </label>
                <input
                  type="number"
                  value={data.basic.maxCycles ?? ''}
                  onChange={(e) =>
                    handleBasicChange(
                      'maxCycles',
                      e.target.value ? parseInt(e.target.value) : null,
                    )
                  }
                  className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder="For sequential circuits"
                />
              </div>
              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Minimum Gate Count (optional)
                </label>
                <input
                  type="number"
                  min="1"
                  value={data.basic.minGateCount ?? ''}
                  onChange={(e) => {
                    const val = e.target.value
                      ? parseInt(e.target.value)
                      : null;
                    // Only accept values > 0, treat 0 or negative as null
                    handleBasicChange(
                      'minGateCount',
                      val && val > 0 ? val : null,
                    );
                  }}
                  className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder="Min gates required"
                />
              </div>
              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Gate Limit (optional)
                </label>
                <input
                  type="number"
                  min="1"
                  value={data.basic.totalGateCount ?? ''}
                  onChange={(e) => {
                    const val = e.target.value
                      ? parseInt(e.target.value)
                      : null;
                    // Only accept values > 0, treat 0 or negative as null
                    handleBasicChange(
                      'totalGateCount',
                      val && val > 0 ? val : null,
                    );
                  }}
                  className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder="Max gates allowed"
                />
              </div>
            </div>

            <div>
              <label className="block text-[13px] font-medium text-foreground mb-2">
                Gate Set *
              </label>
              <div className="flex flex-wrap gap-2">
                {availableGates.map((gate) => (
                  <button
                    key={gate}
                    onClick={() => {
                      const gateSet = data.basic.gateSet.includes(gate)
                        ? data.basic.gateSet.filter((g) => g !== gate)
                        : [...data.basic.gateSet, gate];
                      handleBasicChange('gateSet', gateSet);
                    }}
                    className={`px-4 py-2 rounded-lg border text-[13px] font-medium transition-colors ${
                      data.basic.gateSet.includes(gate)
                        ? 'bg-foreground text-background border-foreground'
                        : 'bg-card border-border text-foreground hover:bg-secondary'
                    }`}
                  >
                    {gate}
                  </button>
                ))}
              </div>
            </div>

            {data.basic.gateSet.length > 0 && (
              <div className="space-y-4">
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Per-Gate Limits (optional)
                </label>
                <p className="text-[11px] text-muted-foreground mb-2">
                  Ordered by category. Basic and custom limits support min/max.
                  Non-shared arsenal limits are max-only.
                </p>

                <div>
                  <label className="block text-[12px] font-semibold text-foreground mb-2">
                    1) Specific Gates (min/max)
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {data.basic.gateSet.map((gate) => (
                      <div
                        key={gate}
                        className="border p-2 rounded-lg bg-secondary/50"
                      >
                        <label className="text-[11px] font-semibold text-foreground">
                          {gate}
                        </label>
                        <div className="text-[10px] text-muted-foreground mb-1">
                          Category: Basic gate
                        </div>
                        <div className="space-y-1">
                          <input
                            type="number"
                            min="1"
                            value={data.basic.gateQuotas[gate] ?? ''}
                            onChange={(e) => {
                              const newQuotas = { ...data.basic.gateQuotas };
                              if (e.target.value) {
                                newQuotas[gate] = parseInt(e.target.value, 10);
                              } else {
                                delete newQuotas[gate];
                              }
                              handleBasicChange('gateQuotas', newQuotas);
                            }}
                            className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                            placeholder="Max count"
                          />
                          <input
                            type="number"
                            min="0"
                            value={data.basic.minGateQuotas[gate] ?? ''}
                            onChange={(e) => {
                              const newMinQuotas = {
                                ...data.basic.minGateQuotas,
                              };
                              if (e.target.value) {
                                newMinQuotas[gate] = parseInt(
                                  e.target.value,
                                  10,
                                );
                              } else {
                                delete newMinQuotas[gate];
                              }
                              handleBasicChange('minGateQuotas', newMinQuotas);
                            }}
                            className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                            placeholder="Min count"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-[12px] font-semibold text-foreground mb-2">
                    2) Custom (min/max)
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {CUSTOM_MIN_MAX_TARGETS.map((target) => (
                      <div
                        key={target.name}
                        className="border p-2 rounded-lg bg-secondary/50"
                      >
                        <label className="text-[11px] font-semibold text-foreground">
                          {target.name}
                        </label>
                        <div className="text-[10px] text-muted-foreground mb-1">
                          Category: {target.label}
                        </div>
                        <div className="space-y-1">
                          <input
                            type="number"
                            min={target.maxCanBeZero ? '0' : '1'}
                            value={data.basic.gateQuotas[target.name] ?? ''}
                            onChange={(e) => {
                              const newQuotas = { ...data.basic.gateQuotas };
                              if (e.target.value) {
                                newQuotas[target.name] = parseInt(
                                  e.target.value,
                                  10,
                                );
                              } else {
                                delete newQuotas[target.name];
                              }
                              handleBasicChange('gateQuotas', newQuotas);
                            }}
                            className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                            placeholder={
                              target.maxCanBeZero
                                ? 'Max count (0 allowed)'
                                : 'Max count'
                            }
                          />
                          <input
                            type="number"
                            min="0"
                            value={data.basic.minGateQuotas[target.name] ?? ''}
                            onChange={(e) => {
                              const newMinQuotas = {
                                ...data.basic.minGateQuotas,
                              };
                              if (e.target.value) {
                                newMinQuotas[target.name] = parseInt(
                                  e.target.value,
                                  10,
                                );
                              } else {
                                delete newMinQuotas[target.name];
                              }
                              handleBasicChange('minGateQuotas', newMinQuotas);
                            }}
                            className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                            placeholder="Min count"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-[12px] font-semibold text-foreground mb-2">
                    3) Non-Shared Arsenal (max only)
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {ARSENAL_MAX_ONLY_TARGETS.map((target) => (
                      <div
                        key={target.name}
                        className="border p-2 rounded-lg bg-secondary/50"
                      >
                        <label className="text-[11px] font-semibold text-foreground">
                          {target.name}
                        </label>
                        <div className="text-[10px] text-muted-foreground mb-1">
                          Category: {target.label}
                        </div>
                        <input
                          type="number"
                          min="1"
                          value={data.basic.gateQuotas[target.name] ?? ''}
                          onChange={(e) => {
                            const newQuotas = { ...data.basic.gateQuotas };
                            if (e.target.value) {
                              newQuotas[target.name] = parseInt(
                                e.target.value,
                                10,
                              );
                            } else {
                              delete newQuotas[target.name];
                            }
                            handleBasicChange('gateQuotas', newQuotas);
                          }}
                          className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                          placeholder="Max count"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Inputs *
                </label>
                <div className="space-y-2">
                  {data.basic.inputs.map((input, idx) => (
                    <div key={idx} className="flex gap-2">
                      <input
                        type="text"
                        value={input}
                        onChange={(e) => {
                          const newInputs = [...data.basic.inputs];
                          newInputs[idx] = e.target.value;
                          handleBasicChange('inputs', newInputs);
                        }}
                        className="flex-1 rounded-lg border border-border bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                        placeholder={`Input ${idx + 1}`}
                      />
                      <button
                        onClick={() => {
                          handleBasicChange(
                            'inputs',
                            data.basic.inputs.filter((_, i) => i !== idx),
                          );
                        }}
                        className="px-3 py-2 rounded-lg bg-red-50/50 text-red-700 text-[13px] hover:bg-red-100 transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() =>
                      handleBasicChange('inputs', [
                        ...data.basic.inputs,
                        `input_${data.basic.inputs.length}`,
                      ])
                    }
                    className="w-full rounded-lg bg-emerald-50/50 px-4 py-2 text-[13px] text-emerald-700 hover:bg-emerald-100 transition-colors"
                  >
                    + Add Input
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Outputs *
                </label>
                <div className="space-y-2">
                  {data.basic.outputs.map((output, idx) => (
                    <div key={idx} className="flex gap-2">
                      <input
                        type="text"
                        value={output}
                        onChange={(e) => {
                          const newOutputs = [...data.basic.outputs];
                          newOutputs[idx] = e.target.value;
                          handleBasicChange('outputs', newOutputs);
                        }}
                        className="flex-1 rounded-lg border border-border bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                        placeholder={`Output ${idx + 1}`}
                      />
                      <button
                        onClick={() => {
                          handleBasicChange(
                            'outputs',
                            data.basic.outputs.filter((_, i) => i !== idx),
                          );
                        }}
                        className="px-3 py-2 rounded-lg bg-red-50/50 text-red-700 text-[13px] hover:bg-red-100 transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() =>
                      handleBasicChange('outputs', [
                        ...data.basic.outputs,
                        `output_${data.basic.outputs.length}`,
                      ])
                    }
                    className="w-full rounded-lg bg-emerald-50/50 px-4 py-2 text-[13px] text-emerald-700 hover:bg-emerald-100 transition-colors"
                  >
                    + Add Output
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'test-cases' && (
          <div className="space-y-6">
            <div className="rounded-xl border border-border bg-secondary/50 p-4">
              <h3 className="font-semibold mb-4">Add Test Case</h3>

              {(data.basic.inputs.length === 0 ||
                data.basic.outputs.length === 0) && (
                <div className="mb-4 rounded-lg border border-amber-300/50 bg-amber-50/40 p-3">
                  <p className="text-[13px] text-amber-800 mb-2">
                    Add at least one input and one output to define test data.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() =>
                        handleBasicChange('inputs', [
                          ...data.basic.inputs,
                          `input_${data.basic.inputs.length}`,
                        ])
                      }
                      className="rounded-lg bg-emerald-50/70 px-3 py-1.5 text-[12px] text-emerald-700 hover:bg-emerald-100 transition-colors"
                    >
                      + Add Input
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        handleBasicChange('outputs', [
                          ...data.basic.outputs,
                          `output_${data.basic.outputs.length}`,
                        ])
                      }
                      className="rounded-lg bg-emerald-50/70 px-3 py-1.5 text-[12px] text-emerald-700 hover:bg-emerald-100 transition-colors"
                    >
                      + Add Output
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveTab('basic')}
                      className="rounded-lg border border-border bg-card px-3 py-1.5 text-[12px] text-foreground hover:bg-secondary transition-colors"
                    >
                      Open Basic Info
                    </button>
                  </div>
                </div>
              )}

              <div className="mb-4">
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Test Case Type
                </label>
                <StyledSelect
                  aria-label="Test case type"
                  value={testCaseForm.kind || 'blackbox'}
                  onValueChange={(v) =>
                    setTestCaseForm((prev) => ({
                      ...prev,
                      kind: v,
                      inputs: {},
                      expectedOutputs: {},
                      inputStream: [],
                      expectedOutputStream: {},
                    }))
                  }
                  options={TEST_CASE_KIND_OPTIONS}
                />
                <p className="text-[11px] text-foreground/75 mt-1">
                  {testCaseForm.kind === 'stream'
                    ? 'Sequential test with input/output values at each time step'
                    : 'Single combinatorial test case with fixed inputs and outputs'}
                </p>
              </div>

              {(testCaseForm.kind === 'blackbox' || !testCaseForm.kind) && (
                <>
                  {data.basic.inputs.length > 0 && (
                    <div>
                      <label className="block text-[13px] font-medium text-foreground mb-2">
                        Inputs
                      </label>
                      <div className="space-y-2 mb-4">
                        {data.basic.inputs.map((inputName) => (
                          <div
                            key={inputName}
                            className="flex items-center gap-2"
                          >
                            <label className="w-32">{inputName}:</label>
                            <StyledSelect
                              aria-label={`Input value for ${inputName}`}
                              className="w-24"
                              value={testCaseForm.inputs?.[inputName] ?? 0}
                              onValueChange={(v) =>
                                setTestCaseForm((prev) => ({
                                  ...prev,
                                  inputs: {
                                    ...prev.inputs,
                                    [inputName]: v,
                                  },
                                }))
                              }
                              options={BIT_OPTIONS}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {data.basic.outputs.length > 0 && (
                    <div>
                      <label className="block text-[13px] font-medium text-foreground mb-2">
                        Expected Outputs
                      </label>
                      <div className="space-y-2 mb-4">
                        {data.basic.outputs.map((outputName) => (
                          <div
                            key={outputName}
                            className="flex items-center gap-2"
                          >
                            <label className="w-32">{outputName}:</label>
                            <StyledSelect
                              aria-label={`Expected output for ${outputName}`}
                              className="w-24"
                              value={
                                testCaseForm.expectedOutputs?.[outputName] ?? 0
                              }
                              onValueChange={(v) =>
                                setTestCaseForm((prev) => ({
                                  ...prev,
                                  expectedOutputs: {
                                    ...prev.expectedOutputs,
                                    [outputName]: v,
                                  },
                                }))
                              }
                              options={BIT_OPTIONS}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {testCaseForm.kind === 'stream' && (
                <>
                  <div className="p-3 bg-amber-50/50 border border-border rounded-lg text-[13px] text-amber-700 mb-4">
                    <p className="font-semibold">
                      Stream Test Case (Sequential)
                    </p>
                    <p className="mt-1">
                      Define input and output sequences for testing sequential
                      circuits. Each step represents one clock cycle.
                    </p>
                  </div>

                  <div className="mb-6">
                    <h4 className="font-semibold mb-3">Input Streams</h4>
                    <p className="text-[11px] text-foreground/75 mb-3">
                      Enter binary sequences: "01010" or "0,1,0,1,0" format
                    </p>
                    <div className="space-y-3">
                      {data.basic.inputs.map((inputName) => (
                        <div key={inputName}>
                          <label className="block text-[13px] font-medium text-foreground mb-1">
                            {inputName}
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. 01010 or 0,1,0,1,0"
                            value={streamInputStrings[inputName] || ''}
                            onChange={(e) => {
                              const value = e.target.value;
                              // Only allow 0, 1, and commas
                              if (/^[01,]*$/.test(value)) {
                                setStreamInputStrings((prev) => ({
                                  ...prev,
                                  [inputName]: value,
                                }));
                              }
                            }}
                            className="w-full rounded-lg border border-border bg-transparent p-2 font-mono text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mb-6">
                    <h4 className="font-semibold mb-3">
                      Expected Output Streams
                    </h4>
                    <p className="text-[11px] text-foreground/75 mb-3">
                      Enter binary sequences: "01010" or "0,1,0,1,0" format
                    </p>
                    <div className="space-y-3">
                      {data.basic.outputs.map((outputName) => (
                        <div key={outputName}>
                          <label className="block text-[13px] font-medium text-foreground mb-1">
                            {outputName}
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. 01010 or 0,1,0,1,0"
                            value={streamOutputStrings[outputName] || ''}
                            onChange={(e) => {
                              const value = e.target.value;
                              // Only allow 0, 1, and commas
                              if (/^[01,]*$/.test(value)) {
                                setStreamOutputStrings((prev) => ({
                                  ...prev,
                                  [outputName]: value,
                                }));
                              }
                            }}
                            className="w-full rounded-lg border border-border bg-transparent p-2 font-mono text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              <button
                onClick={handleAddTestCase}
                className="w-full rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background hover:bg-foreground/90 transition-colors"
              >
                Add Test Case
              </button>
            </div>

            {data.testCases.length > 0 && (
              <div>
                <h3 className="font-semibold mb-4">
                  Test Cases ({data.testCases.length})
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-[13px]">
                    <thead>
                      <tr className="bg-secondary">
                        <th className="border p-2 text-left">Type</th>
                        <th className="border p-2 text-left">Inputs</th>
                        <th className="border p-2 text-left">Outputs</th>
                        <th className="border p-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.testCases.map((tc) => (
                        <tr key={tc.id} className="hover:bg-secondary/50">
                          <td className="border p-2 font-mono text-[11px]">
                            {tc.kind === 'stream' ? 'Stream' : 'Blackbox'}
                          </td>
                          <td className="border p-2 font-mono text-[11px]">
                            {tc.kind === 'stream'
                              ? formatInputStreamForDisplay(tc.inputStream)
                              : JSON.stringify(tc.inputs)}
                          </td>
                          <td className="border p-2 font-mono text-[11px]">
                            {tc.kind === 'stream'
                              ? Object.entries(tc.expectedOutputStream || {})
                                  .map(
                                    ([k, v]) =>
                                      `${k}: [${(v as number[]).join(',')}]`,
                                  )
                                  .join('; ')
                              : JSON.stringify(tc.expectedOutputs)}
                          </td>
                          <td className="border p-2 text-center">
                            <button
                              onClick={() => handleRemoveTestCase(tc.id)}
                              className="px-3 py-1 rounded-lg bg-red-50/50 text-red-700 text-[13px] hover:bg-red-100 transition-colors"
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'python-tests' && (
          <div className="space-y-6">
            <div className="rounded-xl border border-border bg-secondary/50 p-4">
              <h3 className="font-semibold mb-2">Python Tests (Optional)</h3>
              <p className="text-[13px] text-muted-foreground mb-4">
                Upload a Python file with custom test cases for puzzle
                validation. Tests will run when users submit solutions.
              </p>

              <div className="space-y-3 mb-4">
                <h4 className="text-[13px] font-semibold">How Tests Work:</h4>
                <ul className="text-[13px] text-muted-foreground space-y-2 list-disc list-inside">
                  <li>
                    <strong>REQUIRED:</strong> Define{' '}
                    <code className="bg-black/20 px-1 rounded">
                      def run_tests(solution):
                    </code>{' '}
                    function
                  </li>
                  <li>
                    <strong>Purpose:</strong> Call your individual test
                    functions from{' '}
                    <code className="bg-black/20 px-1 rounded">
                      run_tests()
                    </code>
                  </li>
                  <li>
                    <strong>No return statements:</strong> Tests don't return
                    values
                  </li>
                  <li>
                    <strong>Raise on failure:</strong> Use{' '}
                    <code className="bg-black/20 px-1 rounded">
                      raise Exception("error message")
                    </code>{' '}
                    to fail
                  </li>
                  <li>
                    <strong>Silent pass:</strong> If no error is raised, the
                    test passes
                  </li>
                  <li>
                    <strong>Available context:</strong>{' '}
                    <code className="bg-black/20 px-1 rounded">solution</code>{' '}
                    dict contains the circuit structure
                  </li>
                </ul>
              </div>

              <div className="space-y-2">
                <label className="block text-[13px] font-medium text-foreground">
                  Python Tests File (optional)
                </label>
                <input
                  type="file"
                  accept=".py"
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    setData((prev) => ({ ...prev, pythonTests: file }));
                  }}
                  className="w-full"
                />
                {data.pythonTests && (
                  <p className="inline-flex items-center gap-1.5 text-[12px] text-green-600">
                    <CircleCheck className="size-3.5" aria-hidden />
                    {data.pythonTests.name} selected
                  </p>
                )}
              </div>

              <details className="mt-4 p-3 bg-black/20 rounded-lg">
                <summary className="cursor-pointer font-semibold text-[13px]">
                  Example Test File
                </summary>
                <pre className="mt-3 p-3 bg-black/30 rounded text-[11px] overflow-x-auto">
                  {`# Example: validate_solution.py
# Define individual test functions that validate the solution
# The 'solution' dict contains: placedComponents, wires, totalCost, etc.

def test_has_enough_components():
    """Check that solution has minimum components"""
    components = solution.get('placedComponents', [])
    if len(components) < 2:
        raise Exception("Solution must have at least 2 components")

def test_uses_xor_gate():
    """Check specific gate usage"""
    components = solution.get('placedComponents', [])
    has_xor = any(c.get('componentId') == 'XOR' for c in components)
    if not has_xor:
        raise Exception("Solution must use at least one XOR gate")

def test_circuit_structure():
    """Validate circuit connectivity"""
    wires = solution.get('wires', [])
    if len(wires) < 1:
        raise Exception("Solution must have at least one wire connection")

# REQUIRED: Define run_tests() function that calls all test functions
def run_tests(solution):
    """Main test runner - this function is called automatically"""
    test_has_enough_components()
    test_uses_xor_gate()
    test_circuit_structure()`}
                </pre>
              </details>
            </div>
          </div>
        )}

        {activeTab === 'instructions' && (
          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-4">
              <label className="block font-semibold">
                Instructions (LaTeX) *
              </label>
              <textarea
                value={data.instructions}
                onChange={(e) =>
                  setData((prev) => ({ ...prev, instructions: e.target.value }))
                }
                className="w-full rounded-lg border border-border bg-transparent p-4 font-mono text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                rows={15}
                placeholder="\\section*{Puzzle Instructions}\n\nExplain the puzzle to users in LaTeX format with math expressions like $C_{out}$ for subscripts..."
              />
              <div className="text-[13px] text-foreground/80">
                Use LaTeX syntax: {'\\section*'}, {'\\subsection*'},{' '}
                {'\\textbf{}'}, {'\\textit{}'}, $...$ for math,{' '}
                {'\\begin{itemize}'} for lists, {'\\begin{tabular}'} for tables
              </div>
            </div>
            <div className="space-y-4">
              <label className="block font-semibold">Live Preview</label>
              <InstructionsPreview latex={data.instructions} />
            </div>
          </div>
        )}

        {activeTab === 'solution' && (
          <div className="space-y-4">
            <div className="bg-secondary/50 border border-border p-4 rounded-lg">
              <h3 className="mb-2 inline-flex items-center gap-2 font-semibold text-foreground">
                <CircuitBoard
                  className="size-4 text-muted-foreground"
                  aria-hidden
                />
                Design Your Solution Circuit
              </h3>
              <div className="text-[13px] text-foreground mb-3 space-y-2">
                <p>
                  <strong>IMPORTANT:</strong> Your circuit must correctly
                  implement the logic for ALL test cases:
                </p>
                <ul className="list-disc list-inside ml-2">
                  {data.testCases.length > 0 ? (
                    data.testCases.map((tc, i) => {
                      if (tc.kind === 'blackbox') {
                        return (
                          <li key={i}>
                            Test {i}: Input {JSON.stringify(tc.inputs)} → Output{' '}
                            {JSON.stringify(tc.expectedOutputs)}
                          </li>
                        );
                      }
                      return null;
                    })
                  ) : (
                    <li>No test cases defined yet</li>
                  )}
                </ul>
                <p className="mt-2 inline-flex items-start gap-2 font-semibold text-orange-700">
                  <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                  <span>
                    Your circuit&apos;s actual output must match the expected
                    outputs above. Test in the Debugger to verify.
                  </span>
                </p>
              </div>
              <button
                onClick={exportSolution}
                className="rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background hover:bg-foreground/90 transition-colors"
              >
                Export Solution (generates eval_map from circuit)
              </button>
            </div>

            {/* Workstation Grid (with menu on left) */}
            <div className="grid grid-cols-[240px_1fr] gap-4 rounded-xl border border-border bg-card shadow-card h-[700px]">
              {/* Gate Palette Sidebar */}
              <div className="border-r p-3 overflow-y-auto bg-secondary/50">
                <div className="text-[13px] font-semibold text-foreground mb-3">
                  Available Gates
                </div>
                {data.basic.gateSet.length === 0 ? (
                  <p className="text-[11px] text-foreground/75">
                    Select gates in "Basic Info" tab
                  </p>
                ) : (
                  <div className="space-y-2">
                    {data.basic.gateSet.map((gateName) => (
                      <div
                        key={gateName}
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.effectAllowed = 'copy';
                          e.dataTransfer.setData(
                            'application/x-escapecircuit-component',
                            gateName,
                          );
                          e.dataTransfer.setData('text/plain', gateName);
                          setDraggedPaletteComponentId(gateName);
                        }}
                        onDragEnd={() => setDraggedPaletteComponentId(null)}
                        className="p-2 border border-border bg-card rounded-lg cursor-move hover:bg-secondary/50 font-medium text-[13px] text-foreground transition"
                      >
                        {gateName}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Workstation Grid */}
              <WorkstationGrid
                puzzleId="create-draft"
                inputs={data.basic.inputs}
                outputs={data.basic.outputs}
                catalog={uiCatalog}
                placed={placed}
                wires={wires}
                selectedComponent={selectedComponent}
                onSelectedComponentChange={setSelectedComponent}
                onPlacedChange={setPlaced}
                onWiresChange={setWires}
                draggedPaletteComponentId={draggedPaletteComponentId}
              />
            </div>

            {/* Export Status */}
            {data.solutionJSON.trim() && (
              <div className="p-3 bg-emerald-50/50 border border-border rounded-lg">
                <p className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-emerald-700">
                  <CircleCheck className="size-4" aria-hidden />
                  Solution exported and ready
                </p>
              </div>
            )}

            {/* Fallback: Manual JSON Input */}
            <details className="rounded-xl border border-border bg-secondary/50 p-4">
              <summary className="cursor-pointer font-semibold text-foreground">
                OR: Paste Pre-Built Solution JSON
              </summary>
              <div className="mt-4 space-y-3">
                <p className="text-[13px] text-foreground">
                  If you have a solution from another source, paste its JSON
                  here:
                </p>
                <textarea
                  value={data.solutionJSON}
                  onChange={(e) =>
                    setData((prev) => ({
                      ...prev,
                      solutionJSON: e.target.value,
                    }))
                  }
                  className="w-full rounded-lg border border-border bg-transparent p-3 font-mono text-[11px] h-32 focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder={`{\n  "placed": [\n    {"id": "g1", "componentId": "XOR", "origin": {"row": 0, "col": 0}, "rotation": 0}\n  ],\n  "wires": [],\n  "inputs": ["A", "B"],\n  "outputs": ["S"],\n  "used_gates": ["XOR"]\n}`}
                />
              </div>
            </details>
          </div>
        )}
      </div>

      {/* Submit/Cancel Buttons */}
      <div className="flex gap-4 justify-end border-t pt-6">
        <button
          onClick={() => setShowConfirm('cancel')}
          className="rounded-lg border border-border bg-card px-6 py-2 text-[13px] font-medium text-foreground hover:bg-secondary transition-colors"
          disabled={isSubmitting}
        >
          Cancel
        </button>
        <button
          onClick={() => setShowConfirm('submit')}
          className="rounded-lg bg-foreground px-6 py-2 text-[13px] font-medium text-background hover:bg-foreground/90 transition-colors disabled:opacity-50"
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Creating...' : 'Create Puzzle'}
        </button>
      </div>

      {/* Confirmation Dialogs */}
      {showConfirm === 'submit' && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card p-6 rounded-xl shadow-card max-w-sm">
            <h2 className="text-xl font-semibold mb-4">Confirm Creation</h2>
            <p className="mb-6">
              Are you sure you want to create this puzzle? Make sure all
              information is correct.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setShowConfirm(null)}
                className="flex-1 rounded-lg border border-border bg-card px-4 py-2 text-[13px] font-medium text-foreground hover:bg-secondary transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                className="flex-1 rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background hover:bg-foreground/90 transition-colors"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {showConfirm === 'cancel' && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card p-6 rounded-xl shadow-card max-w-sm">
            <h2 className="text-xl font-semibold mb-4">Discard Changes?</h2>
            <p className="mb-6">
              You will lose all unsaved changes if you go back.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setShowConfirm(null)}
                className="flex-1 rounded-lg border border-border bg-card px-4 py-2 text-[13px] font-medium text-foreground hover:bg-secondary transition-colors"
              >
                Keep Editing
              </button>
              <button
                onClick={handleCancel}
                className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-[13px] font-medium text-white hover:bg-red-700 transition-colors"
              >
                Discard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
