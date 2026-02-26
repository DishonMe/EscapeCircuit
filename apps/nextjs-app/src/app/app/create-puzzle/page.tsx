/**
 * Create Puzzle Form Component with Tabs
 * Supports creating puzzles with form input or file upload
 */
"use client";

import { useState, useMemo, useCallback } from "react";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { AUTH_TOKEN_COOKIE_NAME } from "@/utils/auth-constants";
import MarkdownIt from "markdown-it";
// @ts-ignore - markdown-it-katex doesn't have types
import markdownItKatex from "markdown-it-katex";
import DOMPurify from "isomorphic-dompurify";
import "katex/dist/katex.min.css";
import {
  WorkstationGrid,
  type ComponentDef,
  type PlacedGridComponent,
  type SelectedComponentState,
} from "@/app/app/puzzles/[id]/_components/workstation-grid";
import type { Wire } from "@/types/api";

type TabName = "basic" | "test-cases" | "instructions" | "solution";

interface BasicInfo {
  name: string;
  description: string;
  budget: number;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  timeLimit: number | null;
  minCycles: number | null;
  maxCycles: number | null;
  totalGateCount: number | null;
  gateQuotas: Record<string, number>;
  gateSet: string[];
  inputs: string[];
  outputs: string[];
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
    <div className="w-full border p-4 rounded bg-gray-50 min-h-96 overflow-y-auto text-sm">
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
          className="prose prose-sm max-w-none dark:prose-invert text-black [&_*]:text-black"
          dangerouslySetInnerHTML={{ __html: renderedHtml }}
        />
      ) : (
        <p className="text-gray-400">No instructions yet</p>
      )}
    </div>
  );
};

export default function CreatePuzzleForm() {
  const queryClient = useQueryClient();
  const router = useRouter();
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

  const [data, setData] = useState<CreatePuzzleData>({
    basic: {
      name: "",
      description: "",
      budget: 0,
      difficulty: "EASY",
      timeLimit: null,
      minCycles: null,
      maxCycles: null,
      totalGateCount: null,
      gateQuotas: {},
      gateSet: [],
      inputs: [],
      outputs: [],
    },
    testCases: [],
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

  const handleBasicChange = (
    field: keyof BasicInfo,
    value: any
  ) => {
    setData((prev) => ({
      ...prev,
      basic: { ...prev.basic, [field]: value },
    }));
  };

  const handleAddTestCase = () => {
    const initializedForm = { ...testCaseForm };
    
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
      
      // Log for debugging
      console.log('Stream test case created:', {
        numCycles,
        inputStream,
        expectedOutputStream: outputArrays,
      });
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
    let hasSimulationErrors = false;
    
    // Check if circuit exists
    if (placed.length === 0 && wires.length === 0) {
      alert('❌ No circuit designed! Please add gates and wires before exporting.');
      return;
    }
    
    // Simulate circuit for each test case
    for (const tc of data.testCases) {
      // Only process blackbox test cases for eval_map
      if (tc.kind === 'stream' || tc.inputs === undefined || tc.expectedOutputs === undefined) {
        continue;
      }
      
      const sortedInputKeys = Object.keys(tc.inputs).sort();
      const key = JSON.stringify(Object.fromEntries(sortedInputKeys.map(k => [k, tc.inputs![k]])), undefined, '');
      
      try {
        // Call backend API to actually simulate the circuit
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8081/api";
        const baseUrl = apiUrl.replace(/\/api\/?$/, "");
        
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
          throw new Error(err.detail || 'Simulation failed');
        }
        
        const result = await response.json();
        const simulatedOutputs = result.outputs || {};
        
        // Store the ACTUAL circuit output, not the expected output
        evalMap[key] = simulatedOutputs;
        
        // Check if it matches expected
        const matches = JSON.stringify(simulatedOutputs) === JSON.stringify(tc.expectedOutputs);
        if (!matches) {
          simulationErrors.push(
            `Test ${Object.keys(tc.inputs).map(k => `${k}=${tc.inputs![k]}`).join(',')}: ` +
            `Expected ${JSON.stringify(tc.expectedOutputs)} but got ${JSON.stringify(simulatedOutputs)}`
          );
          hasSimulationErrors = true;
        }
      } catch (e) {
        simulationErrors.push(`Simulation error: ${String(e)}`);
        hasSimulationErrors = true;
      }
    }
    
    if (hasSimulationErrors) {
      alert(
        '❌ Circuit output does NOT match test cases!\n\n' +
        simulationErrors.join('\n') +
        '\n\nPlease fix your circuit and try again.'
      );
      return;
    }
    
    // All tests passed - create solution
    const solution = {
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
    }));
    
    alert('✓ Circuit validated! All test cases passed. Solution exported.');
  }, [placed, wires, data.testCases]);

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

  const handleSubmit = async () => {
    if (!data.basic.name.trim()) {
      alert("Puzzle name is required");
      return;
    }
    if (data.basic.gateSet.length === 0) {
      alert("Select at least one gate type");
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
    if (!data.solutionJSON.trim()) {
      alert("Provide a sample solution");
      return;
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
      if (gateQuotasEntries.length > 0) {
        gateQuotasEntries.forEach(([gateName, gateLimit]) => {
          convertedTestCases.push({
            kind: 'gate_limit',
            gate_name: gateName,
            gate_limit: gateLimit,
          });
        });
      }
      
      // ADD: Add total gate count limit test case if specified
      if (data.basic.totalGateCount > 0) {
        convertedTestCases.push({
          kind: 'gate_count_limit',
          max_gate_count: data.basic.totalGateCount,
        });
      }
      
      const configData = {
        puzzle: {
          name: data.basic.name,
          description: data.basic.description,
          budget: data.basic.budget,
          time_limit_seconds: data.basic.timeLimit,
          difficulty: data.basic.difficulty,
          default_gate_set: data.basic.gateSet,
          inputs: data.basic.inputs,
          outputs: data.basic.outputs,
          min_cycles: data.basic.minCycles,
          max_cycles: data.basic.maxCycles,
          total_gate_count: data.basic.totalGateCount,
          gate_quotas: Object.keys(data.basic.gateQuotas).length > 0 ? data.basic.gateQuotas : undefined,
        },
        test_cases: convertedTestCases,
      };

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

      setShowConfirm(null);
      alert("Puzzle created successfully!");
      await queryClient.invalidateQueries({ queryKey: ["puzzles"] });
      router.push("/app/puzzles");
    } catch (err: any) {
      alert("Error: " + (err.message || "Failed to create puzzle"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setShowConfirm(null);
    router.push("/app/puzzles");
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Create New Puzzle</h1>

      {/* Tabs */}
      <div className="flex border-b mb-6">
        {(["basic", "test-cases", "instructions", "solution"] as TabName[]).map(
          (tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-2 font-semibold transition-colors ${
                activeTab === tab
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {tab === "basic"
                ? "Basic Info"
                : tab === "test-cases"
                  ? "Test Cases"
                  : tab === "instructions"
                    ? "Instructions"
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
              <label className="block font-semibold mb-2">Puzzle Name *</label>
              <input
                type="text"
                value={data.basic.name}
                onChange={(e) => handleBasicChange("name", e.target.value)}
                className="w-full border p-3 rounded"
                placeholder="e.g., Binary Adder"
              />
            </div>

            <div>
              <label className="block font-semibold mb-2">Description *</label>
              <textarea
                value={data.basic.description}
                onChange={(e) =>
                  handleBasicChange("description", e.target.value)
                }
                className="w-full border p-3 rounded"
                rows={3}
                placeholder="Brief description of the puzzle"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block font-semibold mb-2">Budget *</label>
                <input
                  type="number"
                  value={data.basic.budget}
                  onChange={(e) =>
                    handleBasicChange("budget", parseInt(e.target.value))
                  }
                  className="w-full border p-3 rounded"
                  placeholder="e.g., 20"
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Difficulty *</label>
                <select
                  value={data.basic.difficulty}
                  onChange={(e) =>
                    handleBasicChange(
                      "difficulty",
                      e.target.value as "EASY" | "MEDIUM" | "HARD"
                    )
                  }
                  className="w-full border p-3 rounded bg-white"
                >
                  <option value="EASY">Easy</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HARD">Hard</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block font-semibold mb-2">
                Time Limit (seconds, optional)
              </label>
              <input
                type="number"
                value={data.basic.timeLimit ?? ""}
                onChange={(e) =>
                  handleBasicChange("timeLimit", e.target.value ? parseInt(e.target.value) : null)
                }
                className="w-full border p-3 rounded"
                placeholder="Leave empty for no limit"
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block font-semibold mb-2">
                  Min Cycles (optional)
                </label>
                <input
                  type="number"
                  value={data.basic.minCycles ?? ""}
                  onChange={(e) =>
                    handleBasicChange("minCycles", e.target.value ? parseInt(e.target.value) : null)
                  }
                  className="w-full border p-3 rounded"
                  placeholder="For sequential circuits"
                />
              </div>
              <div>
                <label className="block font-semibold mb-2">
                  Max Cycles (optional)
                </label>
                <input
                  type="number"
                  value={data.basic.maxCycles ?? ""}
                  onChange={(e) =>
                    handleBasicChange("maxCycles", e.target.value ? parseInt(e.target.value) : null)
                  }
                  className="w-full border p-3 rounded"
                  placeholder="For sequential circuits"
                />
              </div>
              <div>
                <label className="block font-semibold mb-2">
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
                  className="w-full border p-3 rounded"
                  placeholder="Max gates allowed"
                />
              </div>
            </div>

            <div>
              <label className="block font-semibold mb-2">Gate Set *</label>
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
                    className={`px-4 py-2 rounded border transition-colors ${
                      data.basic.gateSet.includes(gate)
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white border-gray-300 hover:border-blue-600"
                    }`}
                  >
                    {gate}
                  </button>
                ))}
              </div>
            </div>

            {data.basic.gateSet.length > 0 && (
              <div>
                <label className="block font-semibold mb-2">
                  Per-Gate Limits (optional)
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {data.basic.gateSet.map((gate) => (
                    <div key={gate} className="border p-2 rounded bg-gray-50">
                      <label className="text-xs font-semibold text-gray-700">{gate}</label>
                      <input
                        type="number"
                        min="1"
                        value={data.basic.gateQuotas[gate] ?? ""}
                        onChange={(e) => {
                          const newQuotas = { ...data.basic.gateQuotas };
                          if (e.target.value) {
                            newQuotas[gate] = parseInt(e.target.value);
                          } else {
                            delete newQuotas[gate];
                          }
                          handleBasicChange("gateQuotas", newQuotas);
                        }}
                        className="w-full border p-1 rounded text-sm mt-1"
                        placeholder="Max count"
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block font-semibold mb-2">Inputs *</label>
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
                        className="flex-1 border p-2 rounded"
                        placeholder={`Input ${idx + 1}`}
                      />
                      <button
                        onClick={() => {
                          handleBasicChange(
                            "inputs",
                            data.basic.inputs.filter((_, i) => i !== idx)
                          );
                        }}
                        className="px-3 py-2 bg-red-100 text-red-600 rounded hover:bg-red-200"
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
                    className="w-full px-4 py-2 bg-green-100 text-green-600 rounded hover:bg-green-200"
                  >
                    + Add Input
                  </button>
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Outputs *</label>
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
                        className="flex-1 border p-2 rounded"
                        placeholder={`Output ${idx + 1}`}
                      />
                      <button
                        onClick={() => {
                          handleBasicChange(
                            "outputs",
                            data.basic.outputs.filter((_, i) => i !== idx)
                          );
                        }}
                        className="px-3 py-2 bg-red-100 text-red-600 rounded hover:bg-red-200"
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
                    className="w-full px-4 py-2 bg-green-100 text-green-600 rounded hover:bg-green-200"
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
            <div className="border p-4 rounded bg-gray-50">
              <h3 className="font-semibold mb-4">Add Test Case</h3>

              <div className="mb-4">
                <label className="block font-semibold mb-2">Test Case Type</label>
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
                  className="w-full border p-2 rounded bg-white"
                >
                  <option value="blackbox">Blackbox (Combinatorial)</option>
                  <option value="stream">Stream (Sequential)</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {testCaseForm.kind === 'stream'
                    ? 'Sequential test with input/output values at each time step'
                    : 'Single combinatorial test case with fixed inputs and outputs'}
                </p>
              </div>

              {(testCaseForm.kind === 'blackbox' || !testCaseForm.kind) && (
                <>
                  {data.basic.inputs.length > 0 && (
                    <div>
                      <label className="block font-semibold mb-2">Inputs</label>
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
                              className="border p-2 rounded bg-white"
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
                      <label className="block font-semibold mb-2">
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
                              className="border p-2 rounded bg-white"
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
                  <div className="p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800 mb-4">
                    <p className="font-semibold">Stream Test Case (Sequential)</p>
                    <p className="mt-1">Define input and output sequences for testing sequential circuits. Each step represents one clock cycle.</p>
                  </div>

                  <div className="mb-6">
                    <h4 className="font-semibold mb-3">Input Streams</h4>
                    <p className="text-xs text-gray-500 mb-3">Enter binary sequences: "01010" or "0,1,0,1,0" format</p>
                    <div className="space-y-3">
                      {data.basic.inputs.map((inputName) => (
                        <div key={inputName}>
                          <label className="block text-sm font-medium mb-1">{inputName}</label>
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
                            className="w-full border p-2 rounded font-mono text-sm"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mb-6">
                    <h4 className="font-semibold mb-3">Expected Output Streams</h4>
                    <p className="text-xs text-gray-500 mb-3">Enter binary sequences: "01010" or "0,1,0,1,0" format</p>
                    <div className="space-y-3">
                      {data.basic.outputs.map((outputName) => (
                        <div key={outputName}>
                          <label className="block text-sm font-medium mb-1">{outputName}</label>
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
                            className="w-full border p-2 rounded font-mono text-sm"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              <button
                onClick={handleAddTestCase}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
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
                  <table className="w-full border-collapse text-sm">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border p-2 text-left">Type</th>
                        <th className="border p-2 text-left">Inputs</th>
                        <th className="border p-2 text-left">Outputs</th>
                        <th className="border p-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.testCases.map((tc) => (
                        <tr key={tc.id} className="hover:bg-gray-50">
                          <td className="border p-2 font-mono text-xs">
                            {tc.kind === 'stream' ? 'Stream' : 'Blackbox'}
                          </td>
                          <td className="border p-2 font-mono text-xs">
                            {tc.kind === 'stream' 
                              ? `${tc.inputStream?.length || 0} cycles`
                              : JSON.stringify(tc.inputs)
                            }
                          </td>
                          <td className="border p-2 font-mono text-xs">
                            {tc.kind === 'stream'
                              ? Object.entries(tc.expectedOutputStream || {}).map(([k, v]) => `${k}: [${(v as number[]).join(',')}]`).join('; ')
                              : JSON.stringify(tc.expectedOutputs)
                            }
                          </td>
                          <td className="border p-2 text-center">
                            <button
                              onClick={() => handleRemoveTestCase(tc.id)}
                              className="px-3 py-1 bg-red-100 text-red-600 rounded text-sm hover:bg-red-200"
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
                className="w-full border p-4 rounded font-mono text-sm"
                rows={15}
                placeholder="\\section*{Puzzle Instructions}\n\nExplain the puzzle to users in LaTeX format with math expressions like $C_{out}$ for subscripts..."
              />
              <div className="text-sm text-gray-600">
                Use LaTeX syntax: {'\\section*'}, {'\\subsection*'}, {'\\textbf{}'}, {'\\textit{}'}, $...$ for math, {'\\begin{itemize}'} for lists, {'\\begin{tabular}'} for tables
              </div>
            </div>
            <div className="space-y-4">
              <label className="block font-semibold">Live Preview</label>
              <InstructionsPreview latex={data.instructions} />
            </div>
          </div>
        )}

        {activeTab === "solution" && (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 p-4 rounded">
              <h3 className="font-semibold text-blue-900 mb-2">⚡ Design Your Solution Circuit</h3>
              <div className="text-sm text-blue-900 mb-3 space-y-2">
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
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm font-semibold"
              >
                📥 Export Solution (generates eval_map from circuit)
              </button>
            </div>

            {/* Workstation Grid (with menu on left) */}
            <div className="grid grid-cols-[240px_1fr] gap-4 border rounded bg-white h-[700px]">
              {/* Gate Palette Sidebar */}
              <div className="border-r p-3 overflow-y-auto bg-gray-50">
                <div className="text-sm font-semibold text-gray-900 mb-3">Available Gates</div>
                {data.basic.gateSet.length === 0 ? (
                  <p className="text-xs text-gray-500">Select gates in "Basic Info" tab</p>
                ) : (
                  <div className="space-y-2">
                    {data.basic.gateSet.map((gateName) => (
                      <div
                        key={gateName}
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.effectAllowed = 'copy';
                          e.dataTransfer.setData('application/x-escapecircuit-component', gateName);
                          setDraggedPaletteComponentId(gateName);
                        }}
                        onDragEnd={() => setDraggedPaletteComponentId(null)}
                        className="p-2 border border-gray-300 bg-white rounded cursor-move hover:bg-blue-50 font-medium text-sm text-gray-900 transition"
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
              <div className="p-3 bg-green-50 border border-green-200 rounded">
                <p className="text-sm text-green-900 font-semibold">✓ Solution exported and ready</p>
              </div>
            )}

            {/* Fallback: Manual JSON Input */}
            <details className="border rounded p-4 bg-gray-50">
              <summary className="cursor-pointer font-semibold text-gray-900">OR: Paste Pre-Built Solution JSON</summary>
              <div className="mt-4 space-y-3">
                <p className="text-sm text-gray-700">
                  If you have a solution from another source, paste its JSON here:
                </p>
                <textarea
                  value={data.solutionJSON}
                  onChange={(e) =>
                    setData((prev) => ({ ...prev, solutionJSON: e.target.value }))
                  }
                  className="w-full border p-3 rounded font-mono text-xs h-32 bg-white"
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
          onClick={() => setShowConfirm("cancel")}
          className="px-6 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
          disabled={isSubmitting}
        >
          Cancel
        </button>
        <button
          onClick={() => setShowConfirm("submit")}
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          disabled={isSubmitting}
        >
          {isSubmitting ? "Creating..." : "Create Puzzle"}
        </button>
      </div>

      {/* Confirmation Dialogs */}
      {showConfirm === "submit" && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded max-w-sm">
            <h2 className="text-xl font-bold mb-4">Confirm Creation</h2>
            <p className="mb-6">
              Are you sure you want to create this puzzle? Make sure all
              information is correct.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setShowConfirm(null)}
                className="flex-1 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {showConfirm === "cancel" && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded max-w-sm">
            <h2 className="text-xl font-bold mb-4">Discard Changes?</h2>
            <p className="mb-6">
              You will lose all unsaved changes if you go back.
            </p>
            <div className="flex gap-4">
              <button
                onClick={() => setShowConfirm(null)}
                className="flex-1 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
              >
                Keep Editing
              </button>
              <button
                onClick={handleCancel}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
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
