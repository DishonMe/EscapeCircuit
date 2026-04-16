/**
 * Create Puzzle Form Component with Tabs
 * Supports creating puzzles with form input or file upload
 */
"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Info } from "lucide-react";
import Cookies from "js-cookie";
import { AUTH_TOKEN_COOKIE_NAME } from "@/utils/auth-constants";
import { api } from "@/lib/api-client";
import { useMyArsenal } from "@/features/arsenal/api";
import MarkdownIt from "markdown-it";
// @ts-ignore - markdown-it-katex doesn't have types
import markdownItKatex from "markdown-it-katex";
import DOMPurify from "isomorphic-dompurify";
import "katex/dist/katex.min.css";
import { InfoPopup } from "@/components/ui/info-popup";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  WorkstationGrid,
  type ComponentDef,
  type PlacedGridComponent,
  type SelectedComponentState,
} from "@/app/app/puzzles/[id]/_components/workstation-grid";
import type { Wire } from "@/types/api";
import { cn } from "@/utils/cn";
import { PageTourLauncher } from "@/components/ui/page-tour-launcher";
import { createPuzzleTourSteps } from "@/config/tourSteps";

type TabName = "basic" | "test-cases" | "python-tests" | "instructions" | "initial-board" | "solution" | "custom-pieces";

interface BasicInfo {
  name: string;
  description: string;
  budget: number;
  creator_budget: number | null;
  difficulty: "EASY" | "MEDIUM" | "HARD";
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
  boardRows: number;
  boardCols: number;
  allowArsenal: boolean;
  allowedArsenalComponentIds: string[];
  arsenalComponentDisplayModes: Record<string, 'circuit' | 'description'>;
}

interface TestCase {
  id?: string;
  kind?: 'blackbox' | 'stream'; // Default: 'blackbox'
  inputs?: Record<string, number>;
  expectedOutputs?: Record<string, number>;
  inputStream?: Array<Record<string, number>>;
  expectedOutputStream?: Record<string, number[]>;
}

type GateLimitTarget = {
  name: string;
  category:
    | 'basic'
    | 'custom'
    | 'shared-arsenal'
    | 'custom-total'
    | 'private-arsenal-total'
    | 'private-arsenal-each';
  cost?: number;
  pins?: number;
  description: string;
  maxCanBeZero: boolean;
};

const buildDefaultTruthTable = (
  numInputs: number,
  numOutputs: number
): Record<string, number | Record<string, number>> => {
  const numCombinations = Math.pow(2, numInputs);
  const newTruthTable: Record<string, number | Record<string, number>> = {};

  for (let i = 0; i < numCombinations; i++) {
    const inputKey = i
      .toString(2)
      .padStart(numInputs, '0');

    if (numOutputs === 1) {
      newTruthTable[inputKey] = 0;
    } else {
      const outputObj: Record<string, number> = {};
      for (let j = 0; j < numOutputs; j++) {
        outputObj[`out${j}`] = 0;
      }
      newTruthTable[inputKey] = outputObj;
    }
  }

  return newTruthTable;
};

// Helper functions for parsing binary string format
const parseBinaryString = (str: string): number[] => {
  const trimmed = str.trim();
  if (!trimmed) return [];
  if (trimmed.includes(',')) {
    return trimmed.split(',').map(b => {
      const val = parseInt(b.trim(), 10);
      return (val === 0 || val === 1) ? val : NaN;
    }).filter(v => !isNaN(v));
  } else {
    return trimmed.split('').map(b => {
      const val = parseInt(b, 10);
      return (val === 0 || val === 1) ? val : NaN;
    }).filter(v => !isNaN(v));
  }
};

const arrayToBinaryString = (arr: number[]): string => {
  return arr.join(',');
};

interface CreatePuzzleData {
  basic: BasicInfo;
  testCases: TestCase[];
  pythonTests: File | null;
  instructions: string;
  solutionJSON: string;
}

const availableGates = [
  "AND",
  "OR",
  "NOT",
  "XOR",
  "NAND",
  "NOR",
  "XNOR",
  "DFF",
];

// Gate properties: cost and pin count
const GATE_PROPERTIES: Record<string, { cost: number; pins: number }> = {
  AND: { cost: 1, pins: 3 },
  OR: { cost: 1, pins: 3 },
  NOT: { cost: 1, pins: 2 },
  XOR: { cost: 1, pins: 3 },
  NAND: { cost: 1, pins: 3 },
  NOR: { cost: 1, pins: 3 },
  XNOR: { cost: 1, pins: 3 },
  DFF: { cost: 1, pins: 2 },
};

const ARSENAL_ZERO_FORBIDDEN_KEYS = new Set([
  '__ARSENAL_TOTAL__',
  '__ARSENAL_EACH__',
  '__ARSENAL_SHARED_TOTAL__',
  '__ARSENAL_SHARED_EACH__',
]);

const ARSENAL_MAX_ONLY_KEYS = new Set([
  '__ARSENAL_TOTAL__',
  '__ARSENAL_EACH__',
]);

// Truth tables for each gate
const TRUTH_TABLES: Record<
  string,
  { inputs: string[]; outputs: string[]; rows: string[][] }
> = {
  AND: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '0'],
      ['0', '1', '0'],
      ['1', '0', '0'],
      ['1', '1', '1'],
    ],
  },
  OR: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '0'],
      ['0', '1', '1'],
      ['1', '0', '1'],
      ['1', '1', '1'],
    ],
  },
  NOT: {
    inputs: ['IN'],
    outputs: ['OUT'],
    rows: [
      ['0', '1'],
      ['1', '0'],
    ],
  },
  XOR: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '0'],
      ['0', '1', '1'],
      ['1', '0', '1'],
      ['1', '1', '0'],
    ],
  },
  NAND: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '1'],
      ['0', '1', '1'],
      ['1', '0', '1'],
      ['1', '1', '0'],
    ],
  },
  NOR: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '1'],
      ['0', '1', '0'],
      ['1', '0', '0'],
      ['1', '1', '0'],
    ],
  },
  XNOR: {
    inputs: ['A', 'B'],
    outputs: ['OUT'],
    rows: [
      ['0', '0', '1'],
      ['0', '1', '0'],
      ['1', '0', '0'],
      ['1', '1', '1'],
    ],
  },
  DFF: {
    inputs: ['IN'],
    outputs: ['OUT'],
    rows: [
      ['0', '0'],
      ['1', '1'],
    ],
  },
};

const MAX_PUZZLE_NAME_LENGTH = 100;
const MAX_PUZZLE_DESCRIPTION_LENGTH = 2000;
const MAX_PUZZLE_INSTRUCTIONS_BYTES = 5 * 1024;
const DEFAULT_BOARD_ROWS = 15;
const DEFAULT_BOARD_COLS = 30;

const utf8ByteLength = (value: string) => new TextEncoder().encode(value).length;

// Convert LaTeX to Markdown for preview rendering
const latexToMarkdown = (latex: string): string => {
  let markdown = latex;
  
  // Convert tabular to markdown tables
  const tabularyRegex = /\\begin\{(?:tabular|array)\}\{[^}]*\}(.*?)\\end\{(?:tabular|array)\}/gs;
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
  const renderedHtml = useMemo(() => {
    if (!latex) return null;
    
    const markdown = latexToMarkdown(latex);
    const md = new MarkdownIt({ html: true }).use(markdownItKatex);
    const html = md.render(markdown);
    
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'p', 'strong', 'em', 'u', 'code', 'pre', 'blockquote',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'a', 'span', 'div', 'i', 'br', 'sup', 'sub',
        'annotation', 'semantics', 'mrow', 'mi', 'mn', 'mo', 'mtext',
        'mfrac', 'msup', 'msub', 'mroot', 'msqrt'
      ],
      ALLOWED_ATTR: ['class', 'style', 'href', 'data-*']
    });
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
        <p className="text-muted-foreground">No instructions yet</p>
      )}
    </div>
  );
};

export default function CreatePuzzleForm() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { data: myArsenalData } = useMyArsenal();
  const [activeTab, setActiveTab] = useState<TabName>("basic");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showConfirm, setShowConfirm] = useState<"submit" | "cancel" | null>(
    null
  );

  // Workstation state for solution design
  const [placed, setPlaced] = useState<PlacedGridComponent[]>([]);
  const [wires, setWires] = useState<Wire[]>([]);
  const [selectedComponent, setSelectedComponent] = useState<SelectedComponentState>({ mode: 'none' });
  const [draggedPaletteComponentId, setDraggedPaletteComponentId] = useState<string | null>(null);

  // Workstation state for initial board design (locked components)
  const [initialBoardPlaced, setInitialBoardPlaced] = useState<PlacedGridComponent[]>([]);
  const [initialBoardWires, setInitialBoardWires] = useState<Wire[]>([]);
  const [initialBoardSelectedComponent, setInitialBoardSelectedComponent] = useState<SelectedComponentState>({ mode: 'none' });
  const [initialBoardDraggedPaletteComponentId, setInitialBoardDraggedPaletteComponentId] = useState<string | null>(null);

  const [data, setData] = useState<CreatePuzzleData>({
    basic: {
      name: "",
      description: "",
      budget: 0,
      creator_budget: null,
      difficulty: "EASY",
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
      boardRows: DEFAULT_BOARD_ROWS,
      boardCols: DEFAULT_BOARD_COLS,
      allowArsenal: true,
      allowedArsenalComponentIds: [],
      arsenalComponentDisplayModes: {},
    },
    testCases: [],
    pythonTests: null,
    instructions: "",
    solutionJSON: "",
  });

  const [testCaseForm, setTestCaseForm] = useState<TestCase>({
    kind: 'blackbox',
    inputs: {},
    expectedOutputs: {},
    inputStream: [],
    expectedOutputStream: {},
  });

  // State for stream test case string representation
  const [streamInputStrings, setStreamInputStrings] = useState<Record<string, string>>({});
  const [streamOutputStrings, setStreamOutputStrings] = useState<Record<string, string>>({});

  // State for truth table dialog
  const [viewingTruthTableFor, setViewingTruthTableFor] = useState<string | null>(null);
  const [viewingCustomPieceTruthTable, setViewingCustomPieceTruthTable] = useState<number | null>(null);

  // State for solution structure guide modal
  const [guideModal, setGuideModal] = useState<'basic' | 'solution' | 'python-tests' | null>(null);

  // State for custom pieces form
  const [customPieceForm, setCustomPieceForm] = useState({
    name: "",
    description: "",
    cost: 0,
    numInputs: 1,
    numOutputs: 1,
    truthTable: buildDefaultTruthTable(1, 1),
    hideInternalStructure: true,
  });
  const [customPieces, setCustomPieces] = useState<any[]>([]);
  const [prevNumInputs, setPrevNumInputs] = useState(1);
  const [prevNumOutputs, setPrevNumOutputs] = useState(1);

  // Compute filtered arsenal pieces that are selected for this puzzle
  const selectedArsenalPieces = useMemo(() => {
    if (!myArsenalData || !data.basic.allowedArsenalComponentIds) {
      return [];
    }
    
    const filtered = myArsenalData.filter(piece => {
      const pieceIdStr = String(piece.id);
      const isIncluded = data.basic.allowedArsenalComponentIds.includes(pieceIdStr);
      return isIncluded;
    });
    
    const result = filtered.map(piece => {
      const pieceMeta = piece as any;
      // Parse structure to extract num_inputs and num_outputs
      let num_inputs = 1;
      let num_outputs = 1;
      
      try {
        const structure = JSON.parse(piece.structure_json || '{}');
        // Count the inputs and outputs from the structure
        if (structure.inputs) {
          num_inputs = Array.isArray(structure.inputs) ? structure.inputs.length : 1;
        }
        if (structure.outputs) {
          num_outputs = Array.isArray(structure.outputs) ? structure.outputs.length : 1;
        }
      } catch (e) {
        // If parsing fails, use defaults
        console.warn('Failed to parse arsenal piece structure:', piece.id, e);
      }
      
      return {
        id: piece.id,
        name: piece.name,
        cost: piece.cost,
        // Prefer persisted metadata from backend; fallback to derived values.
        num_inputs: Number(pieceMeta.num_inputs ?? num_inputs),
        num_outputs: Number(pieceMeta.num_outputs ?? num_outputs),
        truth_table: piece.truth_table ? JSON.parse(piece.truth_table) : {},
        structure_json: pieceMeta.structure_json,
        isArsenal: true,
        basic_gates: piece.basic_gates,
      };
    });
    
    return result;
  }, [myArsenalData, data.basic.allowedArsenalComponentIds]);

  // Combine custom and arsenal pieces for simulation
  const allPiecesForSimulation = useMemo(() => {
    const allPieces = [...customPieces, ...selectedArsenalPieces];
    return allPieces.map(piece => ({
      name: piece.name,
      cost: piece.cost,
      num_inputs: piece.num_inputs,
      num_outputs: piece.num_outputs,
      truth_table: piece.truth_table,
      structure_json: piece.structure_json,
      hideInternalStructure: piece.hideInternalStructure || false,
    }));
  }, [customPieces, selectedArsenalPieces]);

  const gateLimitTargets = useMemo<GateLimitTarget[]>(() => {
    const targets: GateLimitTarget[] = [];

    for (const gateName of data.basic.gateSet) {
      targets.push({
        name: gateName,
        category: 'basic',
        cost: GATE_PROPERTIES[gateName]?.cost ?? 1,
        pins: GATE_PROPERTIES[gateName]?.pins ?? 3,
        description: 'Basic gate',
        maxCanBeZero: false,
      });
    }

    for (const piece of customPieces) {
      targets.push({
        name: piece.name,
        category: 'custom',
        cost: piece.cost,
        pins: piece.num_inputs + piece.num_outputs,
        description: 'Custom piece',
        maxCanBeZero: true,
      });
    }

    targets.push({
      name: '__CUSTOM_TOTAL__',
      category: 'custom-total',
      description: 'All custom pieces (total usage)',
      maxCanBeZero: true,
    });

    for (const piece of selectedArsenalPieces) {
      targets.push({
        name: piece.name,
        category: 'shared-arsenal',
        cost: piece.cost,
        pins: piece.num_inputs + piece.num_outputs,
        description: 'Shared arsenal piece',
        maxCanBeZero: false,
      });
    }

    if (data.basic.allowArsenal) {
      targets.push({
        name: '__ARSENAL_TOTAL__',
        category: 'private-arsenal-total',
        description: 'All non-shared arsenal pieces (total usage)',
        maxCanBeZero: false,
      });

      targets.push({
        name: '__ARSENAL_EACH__',
        category: 'private-arsenal-each',
        description: 'Each non-shared arsenal piece (per piece)',
        maxCanBeZero: false,
      });
    }

    return targets;
  }, [
    data.basic.allowArsenal,
    data.basic.gateSet,
    customPieces,
    selectedArsenalPieces,
  ]);

  const basicGateLimitTargets = useMemo(
    () => gateLimitTargets.filter((target) => target.category === 'basic'),
    [gateLimitTargets]
  );

  const customLimitTargets = useMemo(
    () => gateLimitTargets.filter((target) => target.category === 'custom' || target.category === 'custom-total'),
    [gateLimitTargets]
  );

  const sharedArsenalLimitTargets = useMemo(
    () => gateLimitTargets.filter((target) => target.category === 'shared-arsenal'),
    [gateLimitTargets]
  );

  const privateArsenalLimitTargets = useMemo(
    () => gateLimitTargets.filter(
      (target) =>
        target.category === 'private-arsenal-total' ||
        target.category === 'private-arsenal-each'
    ),
    [gateLimitTargets]
  );

  // Initialize truth table when numInputs or numOutputs changes
  useEffect(() => {
    if (customPieceForm.numInputs !== prevNumInputs || customPieceForm.numOutputs !== prevNumOutputs) {
      const newTruthTable = buildDefaultTruthTable(
        customPieceForm.numInputs,
        customPieceForm.numOutputs
      );
      
      setCustomPieceForm((prev) => ({
        ...prev,
        truthTable: newTruthTable,
      }));
      setPrevNumInputs(customPieceForm.numInputs);
      setPrevNumOutputs(customPieceForm.numOutputs);
    }
  }, [customPieceForm.numInputs, customPieceForm.numOutputs, prevNumInputs, prevNumOutputs]);

  // Wrapper callbacks to auto-lock components/wires on initial board
  const handleInitialBoardPlacedChange = (newPlaced: PlacedGridComponent[]) => {
    // Ensure all items are locked
    const lockedPlaced = newPlaced.map(c => ({ ...c, isLocked: true }));
    setInitialBoardPlaced(lockedPlaced);
  };

  const handleInitialBoardWiresChange = (newWires: Wire[]) => {
    // Ensure all wires are locked
    const lockedWires = newWires.map(w => ({ ...w, isLocked: true }));
    setInitialBoardWires(lockedWires);
  };

  const handleBasicChange = (
    field: keyof BasicInfo,
    value: any
  ) => {
    setData((prev) => ({
      ...prev,
      basic: { ...prev.basic, [field]: value },
    }));
  };

  const handleArsenalSelection = (componentId: string, isSelected: boolean) => {
    setData((prev) => {
      // Ensure we have a valid array to work with
      const currentIds = Array.isArray(prev.basic.allowedArsenalComponentIds) 
        ? prev.basic.allowedArsenalComponentIds 
        : [];
      
      // Build new array: add if selected, remove if not
      let updated: string[];
      if (isSelected) {
        // Only add if not already present (prevent duplicates)
        if (!currentIds.includes(componentId)) {
          updated = [...currentIds, componentId];
        } else {
          updated = currentIds;
        }
      } else {
        // Remove the component ID
        updated = currentIds.filter((id) => id !== componentId);
      }
      
      // Update display modes for the component
      const modes = { ...prev.basic.arsenalComponentDisplayModes };
      if (!isSelected && modes[componentId]) {
        // Clear display mode when deselecting
        delete modes[componentId];
      } else if (isSelected && !modes[componentId]) {
        // Set default mode when selecting
        modes[componentId] = 'circuit';
      }
      
      return {
        ...prev,
        basic: { 
          ...prev.basic, 
          allowedArsenalComponentIds: updated,
          arsenalComponentDisplayModes: modes,
        },
      };
    });
  };

  const handleArsenalDisplayModeChange = (componentId: string, mode: 'circuit' | 'description') => {
    setData((prev) => ({
      ...prev,
      basic: {
        ...prev.basic,
        arsenalComponentDisplayModes: {
          ...prev.basic.arsenalComponentDisplayModes,
          [componentId]: mode,
        },
      },
    }));
  };

  const handleAddTestCase = () => {
    const initializedForm = { ...testCaseForm };

    if (
      (initializedForm.kind === 'blackbox' || !initializedForm.kind) &&
      (data.basic.inputs.length === 0 || data.basic.outputs.length === 0)
    ) {
      alert('Please add at least one input and one output before creating a blackbox test case.');
      return;
    }
    
    // Only initialize inputs/outputs if this is a blackbox test case
    if (initializedForm.kind === 'blackbox' || !initializedForm.kind) {
      if (!initializedForm.inputs) initializedForm.inputs = {};
      if (!initializedForm.expectedOutputs) initializedForm.expectedOutputs = {};
      
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
      const hasAnyInput = Object.values(inputArrays).some(arr => arr.length > 0);
      if (!hasAnyInput) {
        alert('At least one input stream must have values\nExample: "01010" or "0,1,0,1,0"');
        return;
      }
      
      // Validate: at least one output stream must have values
      const hasAnyOutput = Object.values(outputArrays).some(arr => arr.length > 0);
      if (!hasAnyOutput) {
        alert('At least one output stream must have values\nExample: "10101" or "1,0,1,0,1"');
        return;
      }
      
      // Determine the number of cycles
      const numCycles = Math.max(
        ...Object.values(inputArrays).map(arr => arr.length),
        ...Object.values(outputArrays).map(arr => arr.length)
      );
      
      // Check min_cycles constraint
      if (data.basic.minCycles !== null && numCycles < data.basic.minCycles) {
        alert(`Test case has ${numCycles} cycles but minimum required is ${data.basic.minCycles}`);
        return;
      }
      
      // Check max_cycles constraint
      if (data.basic.maxCycles !== null && numCycles > data.basic.maxCycles) {
        alert(`Test case has ${numCycles} cycles but maximum allowed is ${data.basic.maxCycles}`);
        return;
      }
      
      // Verify all input streams have the same length
      for (const [inputName, values] of Object.entries(inputArrays)) {
        if (values.length > 0 && values.length !== numCycles) {
          alert(`Input "${inputName}" length ${values.length} doesn't match other streams (${numCycles} cycles)`);
          return;
        }
      }
      
      // Verify all output streams have the same length
      for (const [outputName, values] of Object.entries(outputArrays)) {
        if (values.length > 0 && values.length !== numCycles) {
          alert(`Output "${outputName}" length ${values.length} doesn't match other streams (${numCycles} cycles)`);
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
      kind: 'blackbox',
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
    const gateConfigs: Record<string, { size: { w: number; h: number }; ports: any[] }> = {
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

    // Add basic gates
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

    // Add custom pieces to catalog
    for (const piece of customPieces) {
      // Generate ports based on num_inputs and num_outputs
      const ports: any[] = [];
      
      // Add input ports on the left
      for (let i = 0; i < piece.num_inputs; i++) {
        ports.push({
          id: `IN${i}`,
          kind: 'input',
          offset: { row: i, col: 0 },
        });
      }
      
      // Add output ports on the right (width is 3 for consistency with gates)
      const maxPorts = Math.max(piece.num_inputs, piece.num_outputs);
      for (let i = 0; i < piece.num_outputs; i++) {
        ports.push({
          id: `OUT${i}`,
          kind: 'output',
          offset: { row: i, col: 2 },
        });
      }
      
      catalog[piece.name] = {
        id: piece.name,
        label: piece.name,
        cost: piece.cost,
        size: { w: 3, h: Math.max(piece.num_inputs, piece.num_outputs) },
        ports: ports,
      };
    }

    // Add selected arsenal pieces to catalog
    for (const piece of selectedArsenalPieces) {
      // Generate ports based on num_inputs and num_outputs
      const ports: any[] = [];
      
      // Add input ports on the left
      for (let i = 0; i < piece.num_inputs; i++) {
        ports.push({
          id: `IN${i}`,
          kind: 'input',
          offset: { row: i, col: 0 },
        });
      }
      
      // Add output ports on the right (width is 3 for consistency with gates)
      for (let i = 0; i < piece.num_outputs; i++) {
        ports.push({
          id: `OUT${i}`,
          kind: 'output',
          offset: { row: i, col: 2 },
        });
      }
      
      catalog[piece.name] = {
        id: piece.name,
        label: piece.name,
        cost: piece.cost,
        size: { w: 3, h: Math.max(piece.num_inputs, piece.num_outputs) },
        ports: ports,
      };
    }

    return catalog;
  }, [data.basic.gateSet, customPieces, selectedArsenalPieces]);

  // Handler: When switching FROM initial-board TO solution tab, auto-populate solution with all initial board components
  const handleTabChange = (tab: TabName) => {
    if (tab === 'solution' && activeTab === 'initial-board') {
      // Auto-populate solution tab with all initial board components (they're all locked by default)
      const allPlaced = initialBoardPlaced;
      const allWires = initialBoardWires;
      
      // Merge items into solution (avoid duplicates by ID)
      setPlaced((prev) => {
        const idMap = new Map(prev.map((c) => [c.id, c]));
        allPlaced.forEach((c) => idMap.set(c.id, c));
        return Array.from(idMap.values());
      });
      
      setWires((prev) => {
        const idMap = new Map(prev.map((w) => [w.id, w]));
        allWires.forEach((w) => idMap.set(w.id, w));
        return Array.from(idMap.values());
      });
    }
    setActiveTab(tab);
  };

  // Export solution from workstation
  const exportSolution = useCallback(async () => {
    // Build eval_map by simulating circuit on test cases
    const evalMap: Record<string, Record<string, number>> = {};
    let simulationErrors: string[] = [];
    
    // Check if circuit exists
    if (placed.length === 0 && wires.length === 0) {
      alert('❌ No circuit designed! Please add gates and wires before exporting.');
      return;
    }
    
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8081/api";
    const baseUrl = apiUrl.replace(/\/api\/?$/, "");
    
    // Simulate circuit for each test case
    for (const tc of data.testCases) {
      if (tc.kind === 'stream') {
        // === STREAM TEST CASE: Simulate entire sequence, then extract eval_map entries ===
        if (!tc.inputStream || !tc.expectedOutputStream) {
          simulationErrors.push(`Stream test case is missing inputStream or expectedOutputStream`);
          continue;
        }
        
        try {
          // Simulate the entire sequence at once to preserve state
          const response = await fetch(`${baseUrl}/debugger/simulate-sequence`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              input_stream: tc.inputStream,
              placed: placed,
              wires: wires,
              custom_pieces: allPiecesForSimulation,
            }),
          });
          
          if (!response.ok) {
            const err = await response.json();
            console.error('[EXPORT-STREAM] API Error:', err);
            throw new Error(err.detail || 'Sequence simulation failed');
          }
          
          const result = await response.json();
          const cycleOutputs = result.cycle_outputs || {};
          
          // Extract outputs for each cycle and build eval_map
          for (let cycleIdx = 0; cycleIdx < tc.inputStream.length; cycleIdx++) {
            const cycleInput = (tc.inputStream[cycleIdx] || {}) as Record<string, number>;
            const expectedOutputStream = tc.expectedOutputStream || {};
            
            // Get expected outputs for this cycle
            const cycleExpectedOutputs = Object.fromEntries(
              Object.entries(expectedOutputStream).map(([outName, outValues]: [string, any]) => [
                outName,
                Array.isArray(outValues) ? outValues[cycleIdx] : outValues,
              ])
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
            const evalKey = JSON.stringify(Object.fromEntries(sortedInputKeys.map((k: string) => [k, cycleInput[k]])), undefined, '');
            
            // For sequential circuits, the same input can appear in different cycles
            // with different outputs due to state. We'll use the first occurrence.
            if (!(evalKey in evalMap)) {
              evalMap[evalKey] = reorderedCycleOutputs;
            }
            
            // Check if this cycle matches expected output
            const cycleMatches = JSON.stringify(reorderedCycleOutputs) === JSON.stringify(cycleExpectedOutputs);
            if (!cycleMatches) {
              simulationErrors.push(
                `Stream test cycle ${cycleIdx} ${JSON.stringify(cycleInput)}: ` +
                `Expected ${JSON.stringify(cycleExpectedOutputs)} but got ${JSON.stringify(reorderedCycleOutputs)}`
              );
            }
          }
        } catch (e) {
          console.error('[EXPORT-STREAM] Error:', e);
          simulationErrors.push(`Stream test case simulation error: ${String(e)}`);
        }
      } else if (tc.kind === 'blackbox' || (tc.inputs !== undefined && tc.expectedOutputs !== undefined)) {
        // === BLACKBOX TEST CASE ===
        const testInputs = tc.inputs || {};
        const expectedOutputs = tc.expectedOutputs || {};

        const sortedInputKeys: string[] = Object.keys(testInputs).sort();
        const key = JSON.stringify(Object.fromEntries(sortedInputKeys.map((k: string) => [k, testInputs[k]])), undefined, '');
        
        try {
          // Call backend API to actually simulate the circuit
          const response = await fetch(`${baseUrl}/debugger/simulate-circuit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              inputs: tc.inputs,
              placed: placed,
              wires: wires,
              custom_pieces: allPiecesForSimulation,
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
          const matches = JSON.stringify(reorderedOutputs) === JSON.stringify(expectedOutputs);

          if (!matches) {
            simulationErrors.push(
              `Test ${Object.keys(testInputs).map((k: string) => `${k}=${testInputs[k]}`).join(',')}: ` +
              `Expected ${JSON.stringify(expectedOutputs)} but got ${JSON.stringify(reorderedOutputs)}`
            );
          }
        } catch (e) {
          console.error('[EXPORT-BLACKBOX] Error:', e);
          simulationErrors.push(`Simulation error: ${String(e)}`);
        }
      }
    }
    
    if (simulationErrors.length > 0) {
      console.warn('[EXPORT] Simulation warnings ignored for export:', simulationErrors);
    }
    
    // All tests passed - create solution
    const totalCost = placed.reduce((sum, p) => {
      const comp = uiCatalog[p.componentId];
      return sum + (comp?.cost ?? 1);
    }, 0);

    const solution = {
      totalCost,
      eval_map: evalMap,
      circuit: {
        placed: placed.map(p => ({
          id: p.id,
          componentId: p.componentId,
          origin: p.origin,
          rotation: p.rotation,
        })),
        wires: wires.map(w => ({
          id: w.id,
          from: w.from,
          to: w.to,
        })),
      },
    };
    
    setData((prev) => ({
      ...prev,
      solutionJSON: JSON.stringify(solution, null, 2),
      basic: prev.basic.creator_budget === null
        ? { ...prev.basic, creator_budget: totalCost }
        : prev.basic,
    }));
    
    alert('✓ Circuit validated! All test cases passed. Solution exported.');
  }, [placed, wires, data.testCases, allPiecesForSimulation, uiCatalog]);

  const handleAddInputField = () => {
    // Find the first input that hasn't been added to the form yet
    const missingInput = data.basic.inputs.find(
      (inputName) => !(inputName in (testCaseForm.inputs || {}))
    );
    const inputName = missingInput || `input_${Object.keys(testCaseForm.inputs || {}).length}`;
    setTestCaseForm((prev) => ({
      ...prev,
      inputs: { ...(prev.inputs || {}), [inputName]: 0 },
    }));
  };

  const handleAddOutputField = () => {
    // Find the first output that hasn't been added to the form yet
    const missingOutput = data.basic.outputs.find(
      (outputName) => !(outputName in (testCaseForm.expectedOutputs || {}))
    );
    const outputName = missingOutput || `output_${Object.keys(testCaseForm.expectedOutputs || {}).length}`;
    setTestCaseForm((prev) => ({
      ...prev,
      expectedOutputs: { ...(prev.expectedOutputs || {}), [outputName]: 0 },
    }));
  };

  const handleCreateCustomPiece = async () => {
    if (!customPieceForm.name.trim()) {
      alert("Piece name is required");
      return;
    }
    if (!customPieceForm.description.trim()) {
      alert("Description is required for custom pieces");
      return;
    }
    if (customPieceForm.numInputs < 1 || customPieceForm.numInputs > 5) {
      alert("Inputs must be between 1 and 5");
      return;
    }
    if (customPieceForm.numOutputs < 1 || customPieceForm.numOutputs > 3) {
      alert("Outputs must be between 1 and 3");
      return;
    }
    if (Object.keys(customPieceForm.truthTable).length === 0) {
      alert("Truth table is required - please define all input combinations");
      return;
    }

    // Check max custom pieces limit (3 per puzzle)
    if (customPieces.length >= 3) {
      alert("Maximum 3 custom pieces per puzzle reached");
      return;
    }

    // Add to local list (note: will be saved when puzzle is created)
    const newPiece = {
      name: customPieceForm.name,
      description: customPieceForm.description,
      cost: customPieceForm.cost,
      num_inputs: customPieceForm.numInputs,
      num_outputs: customPieceForm.numOutputs,
      truth_table: customPieceForm.truthTable,
      hideInternalStructure: customPieceForm.hideInternalStructure,
    };

    setCustomPieces([...customPieces, newPiece]);
    setCustomPieceForm({
      name: "",
      description: "",
      cost: 0,
      numInputs: 1,
      numOutputs: 1,
      truthTable: buildDefaultTruthTable(1, 1),
      hideInternalStructure: true,
    });
    alert("✓ Custom piece created! It will be saved with the puzzle.");
  };

  const handleSubmit = async () => {
    if (!data.basic.name.trim()) {
      alert("Puzzle name is required");
      return;
    }
    if (data.basic.name.trim().length > MAX_PUZZLE_NAME_LENGTH) {
      alert(`Puzzle name must be at most ${MAX_PUZZLE_NAME_LENGTH} characters`);
      return;
    }
    if (data.basic.description.length > MAX_PUZZLE_DESCRIPTION_LENGTH) {
      alert(`Description must be at most ${MAX_PUZZLE_DESCRIPTION_LENGTH} characters`);
      return;
    }
    if (
      data.basic.gateSet.length === 0 &&
      customPieces.length === 0 &&
      selectedArsenalPieces.length === 0
    ) {
      alert("Add at least one available component source: gate type, custom piece, or shared arsenal piece");
      return;
    }
    if (data.basic.inputs.length === 0 || data.basic.outputs.length === 0) {
      alert("Define at least one input and one output");
      return;
    }
    if (data.testCases.length === 0) {
      alert("Add at least one test case");
      return;
    }
    if (!data.instructions.trim()) {
      alert("Add instructions for the puzzle");
      return;
    }
    if (utf8ByteLength(data.instructions) > MAX_PUZZLE_INSTRUCTIONS_BYTES) {
      alert(`Instructions must be at most ${MAX_PUZZLE_INSTRUCTIONS_BYTES} bytes`);
      return;
    }
    if (!data.solutionJSON.trim()) {
      alert("Provide a sample solution");
      return;
    }
    if (
      data.basic.creator_budget !== null &&
      data.basic.budget > 0 &&
      data.basic.budget <= data.basic.creator_budget
    ) {
      alert("Budget must be greater than Creator Budget");
      return;
    }

    if (
      data.basic.minGateCount !== null &&
      data.basic.totalGateCount !== null &&
      data.basic.minGateCount > data.basic.totalGateCount
    ) {
      alert("Minimum Gate Count cannot exceed Gate Limit");
      return;
    }

    const basicGateNames = new Set(data.basic.gateSet);
    const sharedArsenalNames = new Set(selectedArsenalPieces.map((piece) => piece.name));
    const sanitizedMinGateQuotas = Object.fromEntries(
      Object.entries(data.basic.minGateQuotas).filter(
        ([gateName]) => !ARSENAL_MAX_ONLY_KEYS.has(gateName)
      )
    ) as Record<string, number>;

    for (const [gateName, rawMin] of Object.entries(sanitizedMinGateQuotas)) {
      const minValue = Number(rawMin);
      if (!Number.isInteger(minValue) || minValue < 0) {
        alert(`Invalid minimum limit for ${gateName}. Use a non-negative integer.`);
        return;
      }
    }

    for (const [gateName, rawMax] of Object.entries(data.basic.gateQuotas)) {
      const maxValue = Number(rawMax);
      if (!Number.isInteger(maxValue) || maxValue < 0) {
        alert(`Invalid maximum limit for ${gateName}. Use a non-negative integer.`);
        return;
      }

      if (
        maxValue === 0 &&
        (
          basicGateNames.has(gateName) ||
          sharedArsenalNames.has(gateName) ||
          ARSENAL_ZERO_FORBIDDEN_KEYS.has(gateName)
        )
      ) {
        alert(`Maximum limit for ${gateName} cannot be 0.`);
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
      if (minValue !== undefined && maxValue !== undefined && minValue > maxValue) {
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
      if ((data.basic.minGateCount ?? 0) > 0 || (data.basic.totalGateCount ?? 0) > 0) {
        convertedTestCases.push({
          kind: 'gate_count_limit',
          min_gate_count: (data.basic.minGateCount ?? 0) > 0 ? data.basic.minGateCount : undefined,
          max_gate_count: (data.basic.totalGateCount ?? 0) > 0 ? data.basic.totalGateCount : undefined,
        });
      }
      
      const configData: {
        puzzle: Record<string, unknown>;
        test_cases: unknown[];
        custom_pieces?: Array<{
          name: string;
          cost: number;
          num_inputs: number;
          num_outputs: number;
          truth_table: Record<string, number>;
        }>;
      } = {
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
          gate_quotas: Object.keys(data.basic.gateQuotas).length > 0 ? data.basic.gateQuotas : undefined,
          allow_arsenal: data.basic.allowArsenal,
          allowed_arsenal_component_ids: data.basic.allowedArsenalComponentIds.length > 0 ? data.basic.allowedArsenalComponentIds : undefined,
          arsenal_component_display_modes: Object.keys(data.basic.arsenalComponentDisplayModes).length > 0 ? data.basic.arsenalComponentDisplayModes : undefined,
          board: {
            rows: data.basic.boardRows,
            cols: data.basic.boardCols,
          },
          // Initial board: locked components pre-placed for solver
          initial_board: initialBoardPlaced.length > 0 || initialBoardWires.length > 0 
            ? {
                locked_placed: initialBoardPlaced
                  .filter((c) => c.isLocked)
                  .map((c) => ({
                    id: c.id,
                    componentId: c.componentId,
                    origin: c.origin,
                    rotation: c.rotation,
                    isLocked: true,
                  })),
                locked_wires: initialBoardWires
                  .filter((w) => w.isLocked)
                  .map((w) => ({
                    id: w.id,
                    from: w.from,
                    to: w.to,
                    isLocked: true,
                  })),
              }
            : undefined,
        },
        test_cases: convertedTestCases,
      };

      // Add custom pieces to config if any exist
      if (customPieces.length > 0) {
        configData.custom_pieces = customPieces.map((piece) => ({
          name: piece.name,
          cost: piece.cost,
          num_inputs: piece.num_inputs,
          num_outputs: piece.num_outputs,
          truth_table: piece.truth_table,
        }));
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8081/api";
      const baseUrl = apiUrl.replace(/\/api\/?$/, "");

      const formData = new FormData();
      formData.append(
        "config_file",
        new Blob([JSON.stringify(configData, null, 2)], {
          type: "application/json",
        }),
        "puzzle_config.json"
      );
      formData.append(
        "instructions_file",
        new Blob([data.instructions], { type: "text/plain" }),
        "puzzle_instructions.tex"
      );
      formData.append(
        "sample_solution_file",
        new Blob([data.solutionJSON], { type: "application/json" }),
        "puzzle_solution.json"
      );
      
      // Add Python tests file if provided
      if (data.pythonTests) {
        formData.append(
          "python_tests_file",
          data.pythonTests,
          data.pythonTests.name
        );
      }
      
      formData.append("difficulty", data.basic.difficulty);

      const res = await fetch(`${baseUrl}/puzzles/create-puzzle-form`, {
        method: "POST",
        headers: {
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        const detail = err.detail;
        const errorMessage =
          typeof detail === "string"
            ? detail
            : JSON.stringify(detail) || "Upload failed";
        throw new Error(errorMessage);
      }

      const createResponse = await res.json();
      const puzzleId = createResponse.puzzle_id;

      // Custom pieces are now saved via the config file during puzzle creation
      // No need to save them separately

      const navigate = async () => {
        setIsSubmitting(false);
        await queryClient.invalidateQueries({ queryKey: ["puzzles"] });
        router.push("/app/my-puzzles");
      };
      
      setShowConfirm(null);
      alert("Puzzle created successfully!");
      navigate();
    } catch (err: any) {
      alert("Error: " + (err.message || "Failed to create puzzle"));
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setShowConfirm(null);
    router.push("/app/my-puzzles");
  };

  return (
    <>
      <PageTourLauncher
        tourName="create-puzzle"
        pageTitle="Create Puzzle"
        pageDescription="Learn the tabs and controls for building, testing, documenting, and publishing your puzzle."
        steps={createPuzzleTourSteps}
        side="left"
      />
      <div className="p-8 max-w-6xl mx-auto">
        <h1 className="text-3xl font-semibold mb-6">Create New Puzzle 🧩</h1>

        {/* Tabs */}
        <div className="flex border-b mb-6">
          {(["basic", "test-cases", "python-tests", "custom-pieces", "instructions", "initial-board", "solution"] as TabName[]).map(
            (tab) => (
              <button
                key={tab}
                className={`px-6 py-2 text-[13px] font-semibold transition-colors ${
                  tab === "basic"
                    ? "create-puzzle-basic-tab"
                    : tab === "test-cases"
                      ? "create-puzzle-test-cases-tab"
                      : tab === "custom-pieces"
                        ? "create-puzzle-custom-pieces-tab"
                        : tab === "instructions"
                          ? "create-puzzle-instructions-tab"
                          : tab === "solution"
                            ? "create-puzzle-solution-tab"
                            : ""
                } ${
                  activeTab === tab
                    ? "border-b-2 border-foreground text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
                onClick={() => handleTabChange(tab)}
              >
                {tab === "basic"
                  ? "Basic Info"
                  : tab === "test-cases"
                    ? "Test Cases"
                    : tab === "python-tests"
                      ? "Python Tests"
                      : tab === "custom-pieces"
                        ? "Custom Pieces"
                        : tab === "instructions"
                          ? "Instructions"
                          : tab === "initial-board"
                            ? "Initial Board"
                            : "Solution"}
              </button>
            )
          )}
        </div>

      {/* Tab Content */}
      <div className="mb-8">
        {activeTab === "basic" && (
          <div className="space-y-6">
            <div>
              <label className="block text-[13px] font-medium text-foreground mb-2">Puzzle Name *</label>
              <input
                type="text"
                value={data.basic.name}
                onChange={(e) => handleBasicChange("name", e.target.value)}
                maxLength={MAX_PUZZLE_NAME_LENGTH}
                className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="e.g., Binary Adder"
              />
              <div className="mt-1 text-right text-[11px] text-muted-foreground">
                {data.basic.name.length}/{MAX_PUZZLE_NAME_LENGTH}
              </div>
            </div>

            <div>
              <label className="block text-[13px] font-medium text-foreground mb-2">Description *</label>
              <textarea
                value={data.basic.description}
                onChange={(e) =>
                  handleBasicChange("description", e.target.value)
                }
                maxLength={MAX_PUZZLE_DESCRIPTION_LENGTH}
                className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                rows={3}
                placeholder="Brief description of the puzzle"
              />
              <div className="mt-1 text-right text-[11px] text-muted-foreground">
                {data.basic.description.length}/{MAX_PUZZLE_DESCRIPTION_LENGTH}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-1 text-[13px] font-medium text-foreground mb-2">
                  Budget *
                  <InfoPopup>
                    <p className="font-medium text-foreground mb-1">Budget</p>
                    <p>The max total gate cost solvers can use. Solvers who exceed this cannot submit.</p>
                    <p className="mt-1"><span className="font-medium text-foreground">Creator Budget</span> is your solution&apos;s gate cost and is auto-filled when you export your solution. Solvers who match or beat it earn a better medal.</p>
                  </InfoPopup>
                </label>
                <input
                  type="number"
                  value={data.basic.budget}
                  onChange={(e) =>
                    handleBasicChange("budget", parseInt(e.target.value))
                  }
                  className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder="e.g., 20"
                />
              </div>

              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">Difficulty *</label>
                <select
                  value={data.basic.difficulty}
                  onChange={(e) =>
                    handleBasicChange(
                      "difficulty",
                      e.target.value as "EASY" | "MEDIUM" | "HARD"
                    )
                  }
                  className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="EASY">Easy</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HARD">Hard</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[13px] font-medium text-foreground mb-2">
                Time Limit (seconds, optional)
              </label>
              <input
                type="number"
                value={data.basic.timeLimit ?? ""}
                onChange={(e) =>
                  handleBasicChange("timeLimit", e.target.value ? parseInt(e.target.value) : null)
                }
                className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                placeholder="Leave empty for no limit"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-1 text-[13px] font-medium text-foreground mb-2">
                  Board Rows
                  <InfoPopup>
                    <p className="font-medium text-foreground mb-1">Board Size</p>
                    <p>The circuit grid dimensions for solvers. Default is 15 rows x 30 columns.</p>
                    <p className="mt-1">Larger boards give solvers more room. Smaller boards increase difficulty.</p>
                  </InfoPopup>
                </label>
                <input
                  type="number"
                  min="5"
                  max="60"
                  value={data.basic.boardRows}
                  onChange={(e) =>
                    handleBasicChange(
                      "boardRows",
                      Math.max(5, Math.min(60, parseInt(e.target.value || `${DEFAULT_BOARD_ROWS}`, 10)))
                    )
                  }
                  className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Board Columns
                </label>
                <input
                  type="number"
                  min="10"
                  max="80"
                  value={data.basic.boardCols}
                  onChange={(e) =>
                    handleBasicChange(
                      "boardCols",
                      Math.max(10, Math.min(80, parseInt(e.target.value || `${DEFAULT_BOARD_COLS}`, 10)))
                    )
                  }
                  className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Min Cycles (optional)
                </label>
                <input
                  type="number"
                  value={data.basic.minCycles ?? ""}
                  onChange={(e) =>
                    handleBasicChange("minCycles", e.target.value ? parseInt(e.target.value) : null)
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
                  value={data.basic.maxCycles ?? ""}
                  onChange={(e) =>
                    handleBasicChange("maxCycles", e.target.value ? parseInt(e.target.value) : null)
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
                  value={data.basic.minGateCount ?? ""}
                  onChange={(e) => {
                    const val = e.target.value ? parseInt(e.target.value) : null;
                    // Only accept values > 0, treat 0 or negative as null
                    handleBasicChange("minGateCount", val && val > 0 ? val : null);
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
                  value={data.basic.totalGateCount ?? ""}
                  onChange={(e) => {
                    const val = e.target.value ? parseInt(e.target.value) : null;
                    // Only accept values > 0, treat 0 or negative as null
                    handleBasicChange("totalGateCount", val && val > 0 ? val : null);
                  }}
                  className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder="Max gates allowed"
                />
              </div>
            </div>

            <div>
              <label className="block text-[13px] font-medium text-foreground mb-2">Gate Set *</label>
              <div className="flex flex-wrap gap-2">
                {availableGates.map((gate) => (
                  <button
                    key={gate}
                    onClick={() => {
                      const gateSet = data.basic.gateSet.includes(gate)
                        ? data.basic.gateSet.filter((g) => g !== gate)
                        : [...data.basic.gateSet, gate];
                      handleBasicChange("gateSet", gateSet);
                    }}
                    className={`px-4 py-2 rounded-lg border text-[13px] font-medium transition-colors ${
                      data.basic.gateSet.includes(gate)
                        ? "bg-foreground text-background border-foreground"
                        : "bg-card border-border text-foreground hover:bg-secondary"
                    }`}
                  >
                    {gate}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="flex items-center gap-2 text-[13px] font-medium text-foreground cursor-pointer">
                <input
                  type="checkbox"
                  checked={data.basic.allowArsenal}
                  onChange={(e) =>
                    handleBasicChange("allowArsenal", e.target.checked)
                  }
                  className="rounded border border-border"
                />
                Allow Arsenal Pieces
              </label>
              <p className="text-[11px] text-muted-foreground mt-1">
                If unchecked, solver personal arsenal is disabled. Creator-shared arsenal pieces selected below are still available.
              </p>
            </div>

            {myArsenalData && myArsenalData.length > 0 && (
              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Creator Shared Arsenal Components
                </label>
                <p className="text-[11px] text-muted-foreground mb-3">
                  Select your arsenal components that are explicitly shared with solvers for this puzzle. These shared components remain available even if solver personal arsenal is disabled.
                </p>
                <div className="space-y-2 max-h-48 overflow-y-auto border border-border rounded-lg p-3 bg-secondary/30">
                  {myArsenalData.map((piece) => {
                    const isIncluded = data.basic.allowedArsenalComponentIds.includes(String(piece.id));
                    const displayMode = data.basic.arsenalComponentDisplayModes[String(piece.id)] || 'circuit';
                    return (
                      <div key={piece.id} className="flex items-center gap-2 text-[13px] hover:bg-secondary/50 p-2 rounded">
                        <input
                          type="checkbox"
                          checked={isIncluded}
                          onChange={(e) =>
                            handleArsenalSelection(String(piece.id), e.target.checked)
                          }
                          className="rounded border border-border"
                        />
                        <span className="font-medium flex-1">{piece.name}</span>
                        {isIncluded && (
                          <div className="flex gap-1">
                            <button
                              type="button"
                              onClick={() => handleArsenalDisplayModeChange(String(piece.id), 'circuit')}
                              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                                displayMode === 'circuit'
                                  ? 'bg-primary text-primary-foreground'
                                  : 'bg-secondary text-secondary-foreground border border-border hover:bg-secondary/80'
                              }`}
                              title="Show full circuit diagram"
                            >
                              Circuit
                            </button>
                            <button
                              type="button"
                              onClick={() => handleArsenalDisplayModeChange(String(piece.id), 'description')}
                              className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                                displayMode === 'description'
                                  ? 'bg-primary text-primary-foreground'
                                  : 'bg-secondary text-secondary-foreground border border-border hover:bg-secondary/80'
                              }`}
                              title="Show only component description"
                            >
                              Description
                            </button>
                          </div>
                        )}
                        <span className="text-[11px] text-muted-foreground ml-auto">
                          cost {piece.cost}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {gateLimitTargets.length > 0 && (
              <div className="space-y-4">
                <label className="block text-[13px] font-medium text-foreground mb-2">
                  Per-Component Limits (optional)
                </label>
                <p className="text-[11px] text-muted-foreground mb-2">
                  Ordered by category. Basic and custom limits support min/max. Non-shared arsenal limits are max-only.
                </p>

                {basicGateLimitTargets.length > 0 && (
                  <div>
                    <label className="block text-[12px] font-semibold text-foreground mb-2">
                      1) Basic Gates (min/max)
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {basicGateLimitTargets.map((target) => (
                        <div key={`${target.category}-${target.name}`} className="border p-2 rounded-lg bg-secondary/50">
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <div className="flex-1">
                              <label className="text-[11px] font-semibold text-foreground">{target.name}</label>
                              {target.cost !== undefined && target.pins !== undefined && (
                                <div className="text-[10px] text-muted-foreground">
                                  cost {target.cost} · pins {target.pins}
                                </div>
                              )}
                              <div className="text-[10px] text-muted-foreground">Category: {target.description}</div>
                            </div>
                            <button
                              type="button"
                              onClick={() => setViewingTruthTableFor(target.name)}
                              className="p-1 text-foreground/40 hover:text-foreground/70 transition-opacity"
                              title="View Truth Table"
                            >
                              <Info size={14} />
                            </button>
                          </div>
                          <div className="space-y-1">
                            <input
                              type="number"
                              min="1"
                              value={data.basic.gateQuotas[target.name] ?? ""}
                              onChange={(e) => {
                                const newQuotas = { ...data.basic.gateQuotas };
                                if (e.target.value) {
                                  newQuotas[target.name] = parseInt(e.target.value, 10);
                                } else {
                                  delete newQuotas[target.name];
                                }
                                handleBasicChange("gateQuotas", newQuotas);
                              }}
                              className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                              placeholder="Max count"
                            />
                            <input
                              type="number"
                              min="0"
                              value={data.basic.minGateQuotas[target.name] ?? ""}
                              onChange={(e) => {
                                const newMinQuotas = { ...data.basic.minGateQuotas };
                                if (e.target.value) {
                                  newMinQuotas[target.name] = parseInt(e.target.value, 10);
                                } else {
                                  delete newMinQuotas[target.name];
                                }
                                handleBasicChange("minGateQuotas", newMinQuotas);
                              }}
                              className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                              placeholder="Min count"
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {customLimitTargets.length > 0 && (
                  <div>
                    <label className="block text-[12px] font-semibold text-foreground mb-2">
                      2) Custom Pieces (min/max)
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {customLimitTargets.map((target) => (
                        <div key={`${target.category}-${target.name}`} className="border p-2 rounded-lg bg-secondary/50">
                          <label className="text-[11px] font-semibold text-foreground">{target.name}</label>
                          {target.cost !== undefined && target.pins !== undefined && (
                            <div className="text-[10px] text-muted-foreground">
                              cost {target.cost} · pins {target.pins}
                            </div>
                          )}
                          <div className="text-[10px] text-muted-foreground mb-1">Category: {target.description}</div>
                          <div className="space-y-1">
                            <input
                              type="number"
                              min={target.maxCanBeZero ? '0' : '1'}
                              value={data.basic.gateQuotas[target.name] ?? ""}
                              onChange={(e) => {
                                const newQuotas = { ...data.basic.gateQuotas };
                                if (e.target.value) {
                                  newQuotas[target.name] = parseInt(e.target.value, 10);
                                } else {
                                  delete newQuotas[target.name];
                                }
                                handleBasicChange("gateQuotas", newQuotas);
                              }}
                              className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                              placeholder={target.maxCanBeZero ? 'Max count (0 allowed)' : 'Max count'}
                            />
                            <input
                              type="number"
                              min="0"
                              value={data.basic.minGateQuotas[target.name] ?? ""}
                              onChange={(e) => {
                                const newMinQuotas = { ...data.basic.minGateQuotas };
                                if (e.target.value) {
                                  newMinQuotas[target.name] = parseInt(e.target.value, 10);
                                } else {
                                  delete newMinQuotas[target.name];
                                }
                                handleBasicChange("minGateQuotas", newMinQuotas);
                              }}
                              className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                              placeholder="Min count"
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {sharedArsenalLimitTargets.length > 0 && (
                  <div>
                    <label className="block text-[12px] font-semibold text-foreground mb-2">
                      3) Shared Arsenal Pieces (min/max)
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {sharedArsenalLimitTargets.map((target) => (
                        <div key={`${target.category}-${target.name}`} className="border p-2 rounded-lg bg-secondary/50">
                          <label className="text-[11px] font-semibold text-foreground">{target.name}</label>
                          {target.cost !== undefined && target.pins !== undefined && (
                            <div className="text-[10px] text-muted-foreground">
                              cost {target.cost} · pins {target.pins}
                            </div>
                          )}
                          <div className="text-[10px] text-muted-foreground mb-1">Category: {target.description}</div>
                          <div className="space-y-1">
                            <input
                              type="number"
                              min="1"
                              value={data.basic.gateQuotas[target.name] ?? ""}
                              onChange={(e) => {
                                const newQuotas = { ...data.basic.gateQuotas };
                                if (e.target.value) {
                                  newQuotas[target.name] = parseInt(e.target.value, 10);
                                } else {
                                  delete newQuotas[target.name];
                                }
                                handleBasicChange("gateQuotas", newQuotas);
                              }}
                              className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                              placeholder="Max count"
                            />
                            <input
                              type="number"
                              min="0"
                              value={data.basic.minGateQuotas[target.name] ?? ""}
                              onChange={(e) => {
                                const newMinQuotas = { ...data.basic.minGateQuotas };
                                if (e.target.value) {
                                  newMinQuotas[target.name] = parseInt(e.target.value, 10);
                                } else {
                                  delete newMinQuotas[target.name];
                                }
                                handleBasicChange("minGateQuotas", newMinQuotas);
                              }}
                              className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                              placeholder="Min count"
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {privateArsenalLimitTargets.length > 0 && (
                  <div>
                    <label className="block text-[12px] font-semibold text-foreground mb-2">
                      4) Non-Shared Arsenal (max only)
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      {privateArsenalLimitTargets.map((target) => (
                        <div key={`${target.category}-${target.name}`} className="border p-2 rounded-lg bg-secondary/50">
                          <label className="text-[11px] font-semibold text-foreground">{target.name}</label>
                          <div className="text-[10px] text-muted-foreground mb-1">Category: {target.description}</div>
                          <input
                            type="number"
                            min="1"
                            value={data.basic.gateQuotas[target.name] ?? ""}
                            onChange={(e) => {
                              const newQuotas = { ...data.basic.gateQuotas };
                              if (e.target.value) {
                                newQuotas[target.name] = parseInt(e.target.value, 10);
                              } else {
                                delete newQuotas[target.name];
                              }
                              handleBasicChange("gateQuotas", newQuotas);
                            }}
                            className="w-full rounded-lg border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                            placeholder="Max count"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[13px] font-medium text-foreground mb-2">Inputs *</label>
                <div className="space-y-2">
                  {data.basic.inputs.map((input, idx) => (
                    <div key={idx} className="flex gap-2">
                      <input
                        type="text"
                        value={input}
                        onChange={(e) => {
                          const newInputs = [...data.basic.inputs];
                          newInputs[idx] = e.target.value;
                          handleBasicChange("inputs", newInputs);
                        }}
                        className="flex-1 rounded-lg border border-border bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                        placeholder={`Input ${idx + 1}`}
                      />
                      <button
                        onClick={() => {
                          handleBasicChange(
                            "inputs",
                            data.basic.inputs.filter((_, i) => i !== idx)
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
                      handleBasicChange("inputs", [
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
                <label className="flex items-center gap-2 text-[13px] font-medium text-foreground mb-2">
                  Outputs *
                  <button
                    type="button"
                    onClick={() => setGuideModal('basic')}
                    className="p-0.5 text-foreground/40 hover:text-foreground/70 transition-opacity flex-shrink-0"
                    title="View puzzle structure guide"
                  >
                    <Info size={16} />
                  </button>
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
                          handleBasicChange("outputs", newOutputs);
                        }}
                        className="flex-1 rounded-lg border border-border bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                        placeholder={`Output ${idx + 1}`}
                      />
                      <button
                        onClick={() => {
                          handleBasicChange(
                            "outputs",
                            data.basic.outputs.filter((_, i) => i !== idx)
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
                      handleBasicChange("outputs", [
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

        {activeTab === "test-cases" && (
          <div className="space-y-6">
            <div className="rounded-xl border border-border bg-secondary/50 p-4">
              <h3 className="font-semibold mb-4">Add Test Case</h3>

              {(data.basic.inputs.length === 0 || data.basic.outputs.length === 0) && (
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
                      onClick={() => handleTabChange('basic')}
                      className="rounded-lg border border-border bg-card px-3 py-1.5 text-[12px] text-foreground hover:bg-secondary transition-colors"
                    >
                      Open Basic Info
                    </button>
                  </div>
                </div>
              )}

              <div className="mb-4">
                <label className="block text-[13px] font-medium text-foreground mb-2">Test Case Type</label>
                <select
                  value={testCaseForm.kind || 'blackbox'}
                  onChange={(e) =>
                    setTestCaseForm((prev) => ({
                      ...prev,
                      kind: e.target.value as 'blackbox' | 'stream',
                      inputs: {},
                      expectedOutputs: {},
                      inputStream: [],
                      expectedOutputStream: {},
                    }))
                  }
                  className="w-full rounded-lg border border-border bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                >
                  <option value="blackbox">Blackbox (Combinatorial)</option>
                  <option value="stream">Stream (Sequential)</option>
                </select>
                <p className="text-[11px] text-muted-foreground mt-1">
                  {testCaseForm.kind === 'stream'
                    ? 'Sequential test with input/output values at each time step'
                    : 'Single combinatorial test case with fixed inputs and outputs'}
                </p>
              </div>

              {(testCaseForm.kind === 'blackbox' || !testCaseForm.kind) && (
                <>
                  {data.basic.inputs.length > 0 && (
                    <div>
                      <label className="block text-[13px] font-medium text-foreground mb-2">Inputs</label>
                      <div className="space-y-2 mb-4">
                        {data.basic.inputs.map((inputName) => (
                          <div key={inputName} className="flex items-center gap-2">
                            <label className="w-32">{inputName}:</label>
                            <select
                              value={testCaseForm.inputs?.[inputName] ?? 0}
                              onChange={(e) =>
                                setTestCaseForm((prev) => ({
                                  ...prev,
                                  inputs: {
                                    ...prev.inputs,
                                    [inputName]: parseInt(e.target.value),
                                  },
                                }))
                              }
                              className="rounded-lg border border-border bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                            >
                              <option value={0}>0</option>
                              <option value={1}>1</option>
                            </select>
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
                          <div key={outputName} className="flex items-center gap-2">
                            <label className="w-32">{outputName}:</label>
                            <select
                              value={testCaseForm.expectedOutputs?.[outputName] ?? 0}
                              onChange={(e) =>
                                setTestCaseForm((prev) => ({
                                  ...prev,
                                  expectedOutputs: {
                                    ...prev.expectedOutputs,
                                    [outputName]: parseInt(e.target.value),
                                  },
                                }))
                              }
                              className="rounded-lg border border-border bg-transparent p-2 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                            >
                              <option value={0}>0</option>
                              <option value={1}>1</option>
                            </select>
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
                    <p className="font-semibold">Stream Test Case (Sequential)</p>
                    <p className="mt-1">Define input and output sequences for testing sequential circuits. Each step represents one clock cycle.</p>
                  </div>

                  <div className="mb-6">
                    <h4 className="font-semibold mb-3">Input Streams</h4>
                    <p className="text-[11px] text-muted-foreground mb-3">Enter binary sequences: "01010" or "0,1,0,1,0" format</p>
                    <div className="space-y-3">
                      {data.basic.inputs.map((inputName) => (
                        <div key={inputName}>
                          <label className="block text-[13px] font-medium text-foreground mb-1">{inputName}</label>
                          <input
                            type="text"
                            placeholder="e.g. 01010 or 0,1,0,1,0"
                            value={streamInputStrings[inputName] || ''}
                            onChange={(e) => {
                              const value = e.target.value;
                              // Only allow 0, 1, and commas
                              if (/^[01,]*$/.test(value)) {
                                setStreamInputStrings(prev => ({
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
                    <h4 className="font-semibold mb-3">Expected Output Streams</h4>
                    <p className="text-[11px] text-muted-foreground mb-3">Enter binary sequences: "01010" or "0,1,0,1,0" format</p>
                    <div className="space-y-3">
                      {data.basic.outputs.map((outputName) => (
                        <div key={outputName}>
                          <label className="block text-[13px] font-medium text-foreground mb-1">{outputName}</label>
                          <input
                            type="text"
                            placeholder="e.g. 01010 or 0,1,0,1,0"
                            value={streamOutputStrings[outputName] || ''}
                            onChange={(e) => {
                              const value = e.target.value;
                              // Only allow 0, 1, and commas
                              if (/^[01,]*$/.test(value)) {
                                setStreamOutputStrings(prev => ({
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
                              ? `${tc.inputStream?.length || 0} cycles`
                              : JSON.stringify(tc.inputs)
                            }
                          </td>
                          <td className="border p-2 font-mono text-[11px]">
                            {tc.kind === 'stream'
                              ? Object.entries(tc.expectedOutputStream || {}).map(([k, v]) => `${k}: [${(v as number[]).join(',')}]`).join('; ')
                              : JSON.stringify(tc.expectedOutputs)
                            }
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

        {activeTab === "instructions" && (
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
              <div className="text-[13px] text-muted-foreground">
                Use LaTeX syntax: {'\\section*'}, {'\\subsection*'}, {'\\textbf{}'}, {'\\textit{}'}, $...$ for math, {'\\begin{itemize}'} for lists, {'\\begin{tabular}'} for tables
              </div>
              <div className="text-right text-[11px] text-muted-foreground">
                {utf8ByteLength(data.instructions)}/{MAX_PUZZLE_INSTRUCTIONS_BYTES} bytes
              </div>
            </div>
            <div className="space-y-4">
              <label className="block font-semibold">Live Preview</label>
              <InstructionsPreview latex={data.instructions} />
            </div>
          </div>
        )}

        {activeTab === "initial-board" && (
          <div className="space-y-4">
            <div className="bg-secondary/50 border border-border p-4 rounded-lg">
              <h3 className="font-semibold text-foreground mb-2">📌 Design Your Initial Board (Pre-placed Locked Components)</h3>
              <div className="text-[13px] text-foreground mb-3 space-y-2">
                <p>
                  <strong>Instructions:</strong> Place the components that will be pre-placed for the solver. All components you place here are automatically locked and will:
                </p>
                <ul className="list-disc list-inside ml-2 space-y-1">
                  <li>Be immovable (cannot be dragged by solver)</li>
                  <li>Be undeletable (cannot be removed by solver)</li>
                  <li>Be mandatory (must be connected to validate the solution)</li>
                  <li>Be counted in the puzzle cost</li>
                </ul>
                <p className="text-blue-700 font-semibold mt-2">
                  💡 Just drag and place components. They automatically get a 🔒 icon and dashed wires when locked.
                </p>
              </div>
            </div>

            {/* Workstation Grid for Initial Board (similar to Solution) */}
            <div className="grid grid-cols-[240px_1fr] gap-4 rounded-xl border border-border bg-card shadow-card h-[700px]">
              {/* Gate Palette Sidebar */}
              <div className="border-r p-3 overflow-y-auto bg-secondary/50">
                <div className="text-[13px] font-semibold text-foreground mb-3">Available Components</div>
                {data.basic.gateSet.length === 0 && customPieces.length === 0 && selectedArsenalPieces.length === 0 ? (
                  <p className="text-[11px] text-muted-foreground">Select gates in "Basic Info" tab, create pieces in "Custom Pieces" tab, or select Arsenal pieces in "Basic Info" tab</p>
                ) : (
                  <div className="space-y-2">
                    {/* Basic Gates */}
                    {data.basic.gateSet.map((gateName) => (
                      <div
                        key={`initial-gate-${gateName}`}
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.effectAllowed = 'copy';
                          e.dataTransfer.setData('application/x-escapecircuit-component', gateName);
                          e.dataTransfer.setData('text/plain', gateName);
                          setInitialBoardDraggedPaletteComponentId(gateName);
                        }}
                        onDragEnd={() => setInitialBoardDraggedPaletteComponentId(null)}
                        className="flex items-center gap-2 p-2 border border-border bg-card rounded-lg cursor-move hover:bg-secondary/50 transition"
                      >
                        <span className="font-medium text-[13px] text-foreground">{gateName}</span>
                        <div className="flex-1" />
                        <div className="text-[10px] text-muted-foreground flex-shrink-0">
                          cost {GATE_PROPERTIES[gateName]?.cost ?? 1}
                        </div>
                      </div>
                    ))}
                    
                    {/* Custom Pieces */}
                    {customPieces.length > 0 && 
                      <div className="my-2 pt-2 border-t border-border/50">
                        <div className="text-[11px] font-semibold text-muted-foreground mb-2">Custom Pieces</div>
                        {customPieces.map((piece) => (
                          <div
                            key={`initial-custom-${piece.name}`}
                            draggable
                            onDragStart={(e) => {
                              e.dataTransfer.effectAllowed = 'copy';
                              e.dataTransfer.setData('application/x-escapecircuit-component', piece.name);
                              e.dataTransfer.setData('text/plain', piece.name);
                              setInitialBoardDraggedPaletteComponentId(piece.name);
                            }}
                            onDragEnd={() => setInitialBoardDraggedPaletteComponentId(null)}
                            className="flex items-center gap-2 p-2 border border-border/60 bg-amber-50/30 rounded-lg cursor-move hover:bg-amber-50/60 transition"
                          >
                            <span className="font-medium text-[13px] text-foreground">{piece.name}</span>
                            <div className="flex-1" />
                            <div className="text-[10px] text-muted-foreground flex-shrink-0">
                              cost {piece.cost} · pins {piece.num_inputs + piece.num_outputs}
                            </div>
                          </div>
                        ))}
                      </div>
                    }

                    {/* Arsenal Pieces */}
                    {selectedArsenalPieces.length > 0 && 
                      <div className="my-2 pt-2 border-t border-border/50">
                        <div className="text-[11px] font-semibold text-muted-foreground mb-2">Arsenal Pieces</div>
                        {selectedArsenalPieces.map((piece) => (
                          <div
                            key={`initial-arsenal-${piece.name}`}
                            draggable
                            onDragStart={(e) => {
                              e.dataTransfer.effectAllowed = 'copy';
                              e.dataTransfer.setData('application/x-escapecircuit-component', piece.name);
                              e.dataTransfer.setData('text/plain', piece.name);
                              setInitialBoardDraggedPaletteComponentId(piece.name);
                            }}
                            onDragEnd={() => setInitialBoardDraggedPaletteComponentId(null)}
                            className="flex items-center gap-2 p-2 border border-border/60 bg-blue-50/30 rounded-lg cursor-move hover:bg-blue-50/60 transition"
                          >
                            <span className="font-medium text-[13px] text-foreground">{piece.name}</span>
                            <div className="flex-1" />
                            <div className="text-[10px] text-muted-foreground flex-shrink-0">
                              cost {piece.cost} · pins {piece.num_inputs + piece.num_outputs}
                            </div>
                          </div>
                        ))}
                      </div>
                    }
                  </div>
                )}
              </div>

              {/* Workstation Grid */}
              <div className="overflow-hidden rounded-lg border border-border" data-initial-board="true">
                <style>{`
                  [data-initial-board="true"] .lock-indicator {
                    width: 16px !important;
                    height: 16px !important;
                    font-size: 8px !important;
                    border-width: 1px !important;
                  }
                `}</style>
                <WorkstationGrid
                  puzzleId="initial-board"
                  inputs={data.basic.inputs}
                  outputs={data.basic.outputs}
                  catalog={uiCatalog}
                  placed={initialBoardPlaced}
                  wires={initialBoardWires}
                  selectedComponent={initialBoardSelectedComponent}
                  onSelectedComponentChange={setInitialBoardSelectedComponent}
                  onPlacedChange={handleInitialBoardPlacedChange}
                  onWiresChange={handleInitialBoardWiresChange}
                  draggedPaletteComponentId={initialBoardDraggedPaletteComponentId}
                  boardRows={data.basic.boardRows}
                  boardCols={data.basic.boardCols}
                  isEditMode={true}
                />
              </div>
            </div>
          </div>
        )}

        {activeTab === "solution" && (
          <div className="space-y-6">
            <div className="bg-secondary/50 border border-border p-4 rounded-lg">
              <h3 className="font-semibold text-foreground mb-2">⚡ Design Your Solution Circuit</h3>
              <div className="text-[13px] text-foreground mb-3 space-y-2">
                <p>
                  <strong>IMPORTANT:</strong> Your circuit must correctly implement the logic for ALL test cases:
                </p>
                <ul className="list-disc list-inside ml-2">
                  {data.testCases.length > 0 ? (
                    data.testCases.map((tc, i) => {
                      if (tc.kind === 'blackbox') {
                        return (
                          <li key={i}>
                            Test {i}: Input {JSON.stringify(tc.inputs)} → Output {JSON.stringify(tc.expectedOutputs)}
                          </li>
                        );
                      }
                      return null;
                    })
                  ) : (
                    <li>No test cases defined yet</li>
                  )}
                </ul>
                <p className="text-orange-700 font-semibold mt-2">
                  ⚠️ Your circuit's actual output must match the expected outputs above. Test in the Debugger to verify!
                </p>
              </div>
              <button
                onClick={exportSolution}
                className="rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background hover:bg-foreground/90 transition-colors"
              >
                📥 Export Solution (generates eval_map from circuit)
              </button>
            </div>

            {/* Workstation Grid (with menu on left) */}
            <div className="grid grid-cols-[240px_1fr] gap-4 rounded-xl border border-border bg-card shadow-card h-[700px]">
              {/* Gate Palette Sidebar */}
              <div className="border-r p-3 overflow-y-auto bg-secondary/50">
                <div className="text-[13px] font-semibold text-foreground mb-3">Available Gates</div>
                {data.basic.gateSet.length === 0 && customPieces.length === 0 && selectedArsenalPieces.length === 0 ? (
                  <p className="text-[11px] text-muted-foreground">Select gates in "Basic Info" tab, create pieces in "Custom Pieces" tab, or select Arsenal pieces in "Basic Info" tab</p>
                ) : (
                  <div className="space-y-2">
                    {/* Basic Gates */}
                    {data.basic.gateSet.map((gateName) => (
                      <div
                        key={`gate-${gateName}`}
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.effectAllowed = 'copy';
                          e.dataTransfer.setData('application/x-escapecircuit-component', gateName);
                          e.dataTransfer.setData('text/plain', gateName);
                          setDraggedPaletteComponentId(gateName);
                        }}
                        onDragEnd={() => setDraggedPaletteComponentId(null)}
                        className="flex items-center gap-2 p-2 border border-border bg-card rounded-lg cursor-move hover:bg-secondary/50 transition"
                      >
                        <button
                          type="button"
                          onClick={() => setViewingTruthTableFor(gateName)}
                          className="p-0.5 text-foreground/40 hover:text-foreground/70 transition-opacity flex-shrink-0"
                          title="View Truth Table"
                        >
                          <Info size={14} />
                        </button>
                        <span className="font-medium text-[13px] text-foreground">{gateName}</span>
                        <div className="flex-1" />
                        <div className="text-[10px] text-muted-foreground flex-shrink-0">
                          cost {GATE_PROPERTIES[gateName]?.cost ?? 1} · pins {GATE_PROPERTIES[gateName]?.pins ?? 3}
                        </div>
                      </div>
                    ))}
                    
                    {/* Custom Pieces */}
                    {customPieces.length > 0 && 
                      <div className="my-2 pt-2 border-t border-border/50">
                        <div className="text-[11px] font-semibold text-muted-foreground mb-2">Custom Pieces</div>
                        {customPieces.map((piece) => (
                          <div
                            key={`custom-${piece.name}`}
                            draggable
                            onDragStart={(e) => {
                              e.dataTransfer.effectAllowed = 'copy';
                              e.dataTransfer.setData('application/x-escapecircuit-component', piece.name);
                              e.dataTransfer.setData('text/plain', piece.name);
                              setDraggedPaletteComponentId(piece.name);
                            }}
                            onDragEnd={() => setDraggedPaletteComponentId(null)}
                            className="flex items-center gap-2 p-2 border border-border/60 bg-amber-50/30 rounded-lg cursor-move hover:bg-amber-50/60 transition"
                          >
                            <span className="font-medium text-[13px] text-foreground">{piece.name}</span>
                            <div className="flex-1" />
                            <div className="text-[10px] text-muted-foreground flex-shrink-0">
                              cost {piece.cost} · pins {piece.num_inputs + piece.num_outputs}
                            </div>
                          </div>
                        ))}
                      </div>
                    }

                    {/* Arsenal Pieces */}
                    {selectedArsenalPieces.length > 0 && 
                      <div className="my-2 pt-2 border-t border-border/50">
                        <div className="text-[11px] font-semibold text-muted-foreground mb-2">Arsenal Pieces</div>
                        {selectedArsenalPieces.map((piece) => (
                          <div
                            key={`arsenal-${piece.name}`}
                            draggable
                            onDragStart={(e) => {
                              e.dataTransfer.effectAllowed = 'copy';
                              e.dataTransfer.setData('application/x-escapecircuit-component', piece.name);
                              e.dataTransfer.setData('text/plain', piece.name);
                              setDraggedPaletteComponentId(piece.name);
                            }}
                            onDragEnd={() => setDraggedPaletteComponentId(null)}
                            className="flex items-center gap-2 p-2 border border-border/60 bg-blue-50/30 rounded-lg cursor-move hover:bg-blue-50/60 transition"
                          >
                            <span className="font-medium text-[13px] text-foreground">{piece.name}</span>
                            <div className="flex-1" />
                            <div className="text-[10px] text-muted-foreground flex-shrink-0">
                              cost {piece.cost} · pins {piece.num_inputs + piece.num_outputs}
                            </div>
                          </div>
                        ))}
                      </div>
                    }
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
                boardRows={data.basic.boardRows}
                boardCols={data.basic.boardCols}
              />
            </div>

            {/* Export Status */}
            {data.solutionJSON.trim() && (
              <div className="p-3 bg-emerald-50/50 border border-border rounded-lg">
                <p className="text-[13px] text-emerald-700 font-semibold">✓ Solution exported and ready</p>
              </div>
            )}

            {/* Fallback: Manual JSON Input */}
            <details className="rounded-xl border border-border bg-secondary/50 p-4">
              <summary className="flex items-center gap-2 cursor-pointer font-semibold text-foreground">
                <span>OR: Paste Pre-Built Solution JSON</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setGuideModal('solution');
                  }}
                  className="p-0.5 text-foreground/40 hover:text-foreground/70 transition-opacity flex-shrink-0"
                  title="View solution structure guide"
                >
                  <Info size={16} />
                </button>
              </summary>
              <div className="mt-4 space-y-3">
                <p className="text-[13px] text-foreground">
                  If you have a solution from another source, paste its JSON here:
                </p>
                <textarea
                  value={data.solutionJSON}
                  onChange={(e) =>
                    setData((prev) => ({ ...prev, solutionJSON: e.target.value }))
                  }
                  className="w-full rounded-lg border border-border bg-transparent p-3 font-mono text-[11px] h-32 focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder={`{\n  "placed": [\n    {"id": "g1", "componentId": "XOR", "origin": {"row": 0, "col": 0}, "rotation": 0}\n  ],\n  "wires": [],\n  "inputs": ["A", "B"],\n  "outputs": ["S"],\n  "used_gates": ["XOR"]\n}`}
                />
              </div>
            </details>
          </div>
        )}

        {activeTab === "python-tests" && (
          <div className="space-y-6">
            <div className="rounded-xl border border-border bg-secondary/50 p-4">
              <h3 className="font-semibold mb-2">Python Tests (Optional)</h3>
              <p className="text-[13px] text-muted-foreground mb-4">
                Upload a Python file with custom test cases for puzzle validation. Tests will run when users submit solutions.
              </p>
              
              <div className="space-y-3 mb-4">
                <h4 className="text-[13px] font-semibold">How Tests Work:</h4>
                <ul className="text-[13px] text-muted-foreground space-y-2 list-disc list-inside">
                  <li><strong>REQUIRED:</strong> Define <code className="bg-black/20 px-1 rounded">def run_tests(solution):</code> function</li>
                  <li><strong>Purpose:</strong> Call your individual test functions from <code className="bg-black/20 px-1 rounded">run_tests()</code></li>
                  <li><strong>No return statements:</strong> Tests don't return values</li>
                  <li><strong>Raise on failure:</strong> Use <code className="bg-black/20 px-1 rounded">raise Exception("error message")</code> to fail</li>
                  <li><strong>Silent pass:</strong> If no error is raised, the test passes</li>
                  <li><strong>Available context:</strong> <code className="bg-black/20 px-1 rounded">solution</code> dict contains the circuit structure</li>
                </ul>
              </div>

              <div className="space-y-2">
                <label className="flex items-center gap-2 text-[13px] font-medium text-foreground">
                  <span>Python Tests File (optional)</span>
                  <button
                    type="button"
                    onClick={() => setGuideModal('python-tests')}
                    className="p-0.5 text-foreground/40 hover:text-foreground/70 transition-opacity flex-shrink-0"
                    title="View Python tests structure guide"
                  >
                    <Info size={16} />
                  </button>
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
                  <p className="text-[12px] text-green-600">✓ {data.pythonTests.name} selected</p>
                )}
              </div>

              <details className="mt-4 p-3 bg-black/20 rounded-lg">
                <summary className="cursor-pointer font-semibold text-[13px]">Example Test File</summary>
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

        {activeTab === "custom-pieces" && (
          <div className="space-y-6">
            <div className="rounded-xl border border-border bg-secondary/50 p-4">
              <h3 className="font-semibold mb-2">Create Custom Piece</h3>
              <p className="text-[13px] text-muted-foreground mb-4">
                Create special circuit pieces that solvers can use in this puzzle. Limited to 5 inputs and 3 outputs.
              </p>

              <div className="space-y-4">
                <div>
                  <label className="block text-[13px] font-medium text-foreground mb-2">Piece Name *</label>
                  <input
                    type="text"
                    placeholder="e.g., Majority Voter"
                    value={customPieceForm.name}
                    onChange={(e) => setCustomPieceForm({ ...customPieceForm, name: e.target.value })}
                    className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>

                <div>
                  <label className="block text-[13px] font-medium text-foreground mb-2">Description *</label>
                  <textarea
                    placeholder="Describe what this component does and how it works..."
                    value={customPieceForm.description}
                    onChange={(e) => setCustomPieceForm({ ...customPieceForm, description: e.target.value })}
                    className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring resize-none h-20"
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-[13px] font-medium text-foreground mb-2">Cost *</label>
                    <input
                      type="number"
                      min="0"
                      placeholder="0"
                      value={customPieceForm.cost}
                      onChange={(e) => setCustomPieceForm({ ...customPieceForm, cost: parseInt(e.target.value) || 0 })}
                      className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                  <div>
                    <label className="block text-[13px] font-medium text-foreground mb-2">Inputs (1-5) *</label>
                    <input
                      type="number"
                      min="1"
                      max="5"
                      placeholder="1"
                      value={customPieceForm.numInputs}
                      onChange={(e) => setCustomPieceForm({ ...customPieceForm, numInputs: parseInt(e.target.value) || 1 })}
                      className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                  <div>
                    <label className="block text-[13px] font-medium text-foreground mb-2">Outputs (1-3) *</label>
                    <input
                      type="number"
                      min="1"
                      max="3"
                      placeholder="1"
                      value={customPieceForm.numOutputs}
                      onChange={(e) => setCustomPieceForm({ ...customPieceForm, numOutputs: parseInt(e.target.value) || 1 })}
                      className="w-full rounded-lg border border-border bg-transparent p-3 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                    />
                  </div>
                </div>

                {customPieceForm.numInputs > 0 && customPieceForm.numOutputs > 0 && (
                  <div>
                    <label className="block text-[13px] font-medium text-foreground mb-3">Truth Table *</label>
                    <p className="text-[11px] text-muted-foreground mb-3">
                      Select the output value(s) for each input combination:
                    </p>
                    <div className="overflow-x-auto border border-border rounded-lg">
                      <table className="w-full text-[13px]">
                        <thead>
                          <tr className="bg-secondary">
                            {Array.from({ length: customPieceForm.numInputs }).map((_, i) => (
                              <th key={`in-${i}`} className="border p-2 text-left">IN{i}</th>
                            ))}
                            {Array.from({ length: customPieceForm.numOutputs }).map((_, i) => (
                              <th key={`out-${i}`} className="border p-2 text-left">OUT{i}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {Array.from({ length: Math.pow(2, customPieceForm.numInputs) }).map((_, rowIdx) => {
                            // Generate binary input combination
                            const inputs = rowIdx
                              .toString(2)
                              .padStart(customPieceForm.numInputs, '0')
                              .split('')
                              .map(Number);
                            const inputKey = inputs.join('');
                            const currentOutputs = customPieceForm.truthTable[inputKey];
                            
                            return (
                              <tr key={rowIdx} className="hover:bg-secondary/50">
                                {inputs.map((bit, bitIdx) => (
                                  <td key={`in-${rowIdx}-${bitIdx}`} className="border p-2 font-mono font-semibold">
                                    {bit}
                                  </td>
                                ))}
                                {Array.from({ length: customPieceForm.numOutputs }).map((_, outIdx) => {
                                  const outKey = `out${outIdx}`;
                                  let currentValue = 0;
                                  if (typeof currentOutputs === 'object' && currentOutputs !== null) {
                                    currentValue = (currentOutputs as Record<string, number>)[outKey] ?? 0;
                                  } else if (customPieceForm.numOutputs === 1 && outIdx === 0) {
                                    currentValue = (currentOutputs as number) ?? 0;
                                  }
                                  
                                  return (
                                    <td key={`out-${rowIdx}-${outIdx}`} className="border p-2">
                                      <select
                                        value={currentValue}
                                        onChange={(e) => {
                                          const newVal = parseInt(e.target.value);
                                          setCustomPieceForm((prev) => {
                                            const updated = { ...prev };
                                            if (customPieceForm.numOutputs === 1) {
                                              updated.truthTable = { ...prev.truthTable, [inputKey]: newVal };
                                            } else {
                                              const outputObj = (prev.truthTable[inputKey] as Record<string, number>) || {};
                                              updated.truthTable = {
                                                ...prev.truthTable,
                                                [inputKey]: { ...outputObj, [outKey]: newVal },
                                              };
                                            }
                                            return updated;
                                          });
                                        }}
                                        className="rounded border border-border bg-transparent p-1 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
                                      >
                                        <option value={0}>0</option>
                                        <option value={1}>1</option>
                                      </select>
                                    </td>
                                  );
                                })}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                <button
                  onClick={handleCreateCustomPiece}
                  disabled={!customPieceForm.name.trim() || !customPieceForm.description.trim()}
                  className="w-full rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background hover:bg-foreground/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  + Create Custom Piece
                </button>
              </div>
            </div>

            {customPieces.length > 0 && (
              <div>
                <h3 className="font-semibold mb-4">
                  Custom Pieces ({customPieces.length})
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-[13px]">
                    <thead>
                      <tr className="bg-secondary">
                        <th className="border p-2 text-left">Name</th>
                        <th className="border p-2 text-left">Cost</th>
                        <th className="border p-2 text-left">Inputs</th>
                        <th className="border p-2 text-left">Outputs</th>
                        <th className="border p-2 text-center">Truth Table</th>
                        <th className="border p-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {customPieces.map((piece, idx) => {
                        return (
                          <tr key={idx} className="hover:bg-secondary/50">
                            <td className="border p-2 font-medium text-[13px]">{piece.name}</td>
                            <td className="border p-2 font-mono text-[11px]">{piece.cost}</td>
                            <td className="border p-2 font-mono text-[11px]">{piece.num_inputs}</td>
                            <td className="border p-2 font-mono text-[11px]">{piece.num_outputs}</td>
                            <td className="border p-2 text-center">
                              <button
                                onClick={() => setViewingCustomPieceTruthTable(idx)}
                                className="px-3 py-1 rounded-lg bg-blue-50/50 text-blue-700 text-[13px] hover:bg-blue-100 transition-colors"
                              >
                                View
                              </button>
                            </td>
                            <td className="border p-2 text-center">
                              <button
                                onClick={() => setCustomPieces(customPieces.filter((_, i) => i !== idx))}
                                className="px-3 py-1 rounded-lg bg-red-50/50 text-red-700 text-[13px] hover:bg-red-100 transition-colors"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Submit/Cancel Buttons */}
      <div className="flex gap-4 justify-end border-t pt-6">
        <button
          onClick={() => setShowConfirm("cancel")}
          className="rounded-lg border border-border bg-card px-6 py-2 text-[13px] font-medium text-foreground hover:bg-secondary transition-colors"
          disabled={isSubmitting}
        >
          Cancel
        </button>
        <button
          onClick={() => setShowConfirm("submit")}
          className="rounded-lg bg-foreground px-6 py-2 text-[13px] font-medium text-background hover:bg-foreground/90 transition-colors disabled:opacity-50 create-puzzle-publish-button"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Creating..." : "Create Puzzle"}
        </button>
      </div>

      {/* Confirmation Dialogs */}
      {showConfirm === "submit" && (
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

      {showConfirm === "cancel" && (
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

      {/* Solution Structure Guide Modal */}
      <Dialog
        open={guideModal !== null}
        onOpenChange={(open) => !open && setGuideModal(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {guideModal === 'basic' && 'Puzzle Configuration Guide'}
              {guideModal === 'solution' && 'Solution Structure Guide'}
              {guideModal === 'python-tests' && 'Python Tests Format Guide'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 text-[13px] text-foreground">
            {guideModal === 'basic' && (
              <div className="space-y-3">
                <div>
                  <p className="font-semibold mb-2">Puzzle Configuration Format</p>
                  <ul className="list-disc list-inside space-y-1 text-[13px]">
                    <li>Define your puzzle's input and output signals</li>
                    <li>Inputs are the data sources (e.g., A, B, signal1)</li>
                    <li>Outputs are the result signals (e.g., sum, carry, result)</li>
                    <li>Both must contain at least one entry each</li>
                    <li>Names should be descriptive and unique</li>
                  </ul>
                </div>
                <div className="bg-secondary/50 p-3 rounded-lg">
                  <p className="font-semibold text-[12px] mb-1">Example:</p>
                  <p className="text-[11px] font-mono">Inputs: ["A", "B", "carry_in"]</p>
                  <p className="text-[11px] font-mono">Outputs: ["sum", "carry_out"]</p>
                </div>
              </div>
            )}
            {guideModal === 'solution' && (
              <div className="space-y-3">
                <div>
                  <p className="font-semibold mb-2">Solution JSON Structure</p>
                  <ul className="list-disc list-inside space-y-1 text-[13px]">
                    <li><strong>totalCost:</strong> Integer representing total gate cost</li>
                    <li><strong>eval_map:</strong> Maps input combinations to expected outputs</li>
                    <li><strong>circuit:</strong> Contains placed components and wires</li>
                    <li>Each input combination must map to correct outputs</li>
                    <li>Wires connect component outputs to component inputs</li>
                  </ul>
                </div>
                <div className="bg-secondary/50 p-3 rounded-lg">
                  <p className="font-semibold text-[12px] mb-1">Structure:</p>
                  <p className="text-[11px] font-mono leading-relaxed">{`{
  "totalCost": 5,
  "eval_map": {{"a":1,"b":1}: {"out":1}},
  "circuit": {"placed": [], "wires": []}
}`}</p>
                </div>
              </div>
            )}
            {guideModal === 'python-tests' && (
              <div className="space-y-3">
                <div>
                  <p className="font-semibold mb-2">Python Tests Format</p>
                  <ul className="list-disc list-inside space-y-1 text-[13px]">
                    <li><strong>REQUIRED:</strong> Define a <code className="bg-black/20 px-1 rounded text-[11px]">run_tests(solution)</code> function</li>
                    <li>Create individual test functions to validate the solution</li>
                    <li>Call all test functions from <code className="bg-black/20 px-1 rounded text-[11px]">run_tests()</code></li>
                    <li>Use <code className="bg-black/20 px-1 rounded text-[11px]">raise Exception()</code> to fail a test</li>
                    <li>Silent pass (no exception) means test passes</li>
                    <li>Solution dict contains: placedComponents, wires, totalCost, etc.</li>
                  </ul>
                </div>
                <div className="bg-secondary/50 p-3 rounded-lg">
                  <p className="font-semibold text-[12px] mb-1">Example:</p>
                  <p className="text-[11px] font-mono leading-relaxed">{`def run_tests(solution):
  components = solution.get('placedComponents')
  if len(components) < 2:
    raise Exception("Need 2+ gates")`}</p>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Truth Table Dialog */}
      <Dialog
        open={Boolean(viewingTruthTableFor)}
        onOpenChange={(open) => !open && setViewingTruthTableFor(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Truth Table: {viewingTruthTableFor}</DialogTitle>
          </DialogHeader>
          {viewingTruthTableFor && TRUTH_TABLES[viewingTruthTableFor] ? (
            <div className="overflow-hidden rounded-lg border border-border/60">
              <table className="w-full text-[13px] text-foreground">
                <thead className="bg-secondary/50 text-[11px] font-medium uppercase text-muted-foreground">
                  <tr>
                    {TRUTH_TABLES[viewingTruthTableFor].inputs.map((i: string) => (
                      <th key={i} className="px-3 py-2 text-center">
                        {i}
                      </th>
                    ))}
                    {TRUTH_TABLES[viewingTruthTableFor].outputs.map((o: string) => (
                      <th
                        key={o}
                        className="border-l border-border px-3 py-2 text-center"
                      >
                        {o}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {TRUTH_TABLES[viewingTruthTableFor].rows.map((row: string[], idx: number) => (
                    <tr key={idx} className="divide-x divide-border">
                      {row.map((cell: string, cIdx: number) => (
                        <td key={cIdx} className="px-3 py-2 text-center">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-[13px] text-muted-foreground">
              No truth table available for this component.
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Custom Piece Truth Table Dialog */}
      <Dialog
        open={viewingCustomPieceTruthTable !== null}
        onOpenChange={(open) => !open && setViewingCustomPieceTruthTable(null)}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Truth Table: {viewingCustomPieceTruthTable !== null ? customPieces[viewingCustomPieceTruthTable]?.name : ''}
            </DialogTitle>
          </DialogHeader>
          {viewingCustomPieceTruthTable !== null && customPieces[viewingCustomPieceTruthTable] ? (
            <div className="overflow-x-auto rounded-lg border border-border/60">
              <table className="w-full text-[13px] text-foreground">
                <thead className="bg-secondary/50 text-[11px] font-medium uppercase text-muted-foreground">
                  <tr>
                    {Array.from({ length: customPieces[viewingCustomPieceTruthTable].num_inputs }).map((_, i) => (
                      <th key={`in-${i}`} className="px-3 py-2 text-center border-r border-border">
                        IN{i}
                      </th>
                    ))}
                    {Array.from({ length: customPieces[viewingCustomPieceTruthTable].num_outputs }).map((_, i) => (
                      <th key={`out-${i}`} className="px-3 py-2 text-center">
                        OUT{i}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(() => {
                    const piece = customPieces[viewingCustomPieceTruthTable];
                    const truthTable = typeof piece.truth_table === 'string' 
                      ? JSON.parse(piece.truth_table)
                      : piece.truth_table;
                    const numRows = Math.pow(2, piece.num_inputs);
                    
                    return Array.from({ length: numRows }).map((_, rowIdx) => {
                      const inputs = rowIdx
                        .toString(2)
                        .padStart(piece.num_inputs, '0')
                        .split('')
                        .map(Number);
                      const inputKey = inputs.join('');
                      const outputs = truthTable[inputKey];
                      
                      return (
                        <tr key={rowIdx} className="divide-x divide-border">
                          {inputs.map((bit, bitIdx) => (
                            <td key={`in-${rowIdx}-${bitIdx}`} className="px-3 py-2 text-center">
                              {bit}
                            </td>
                          ))}
                          {Array.from({ length: piece.num_outputs }).map((_, outIdx) => {
                            let value = 0;
                            if (piece.num_outputs === 1) {
                              value = outputs ?? 0;
                            } else if (typeof outputs === 'object' && outputs !== null) {
                              value = outputs[`out${outIdx}`] ?? 0;
                            }
                            
                            return (
                              <td key={`out-${rowIdx}-${outIdx}`} className="px-3 py-2 text-center">
                                {value}
                              </td>
                            );
                          })}
                        </tr>
                      );
                    });
                  })()}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-[13px] text-muted-foreground">
              No custom piece selected or invalid truth table.
            </div>
          )}
        </DialogContent>
      </Dialog>
      </div>
    </>
  );
}
