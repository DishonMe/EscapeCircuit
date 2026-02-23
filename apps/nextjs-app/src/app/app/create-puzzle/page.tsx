/**
 * Create Puzzle Form Component with Tabs
 * Supports creating puzzles with form input or file upload
 */
"use client";

import { useState, useMemo } from "react";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { AUTH_TOKEN_COOKIE_NAME } from "@/utils/auth-constants";
import MarkdownIt from "markdown-it";
// @ts-ignore - markdown-it-katex doesn't have types
import markdownItKatex from "markdown-it-katex";
import DOMPurify from "isomorphic-dompurify";
import "katex/dist/katex.min.css";

type TabName = "basic" | "test-cases" | "instructions" | "solution";

interface BasicInfo {
  name: string;
  description: string;
  budget: number;
  difficulty: "EASY" | "MEDIUM" | "HARD";
  timeLimit: number | null;
  gateSet: string[];
  inputs: string[];
  outputs: string[];
}

interface TestCase {
  id?: string;
  inputs: Record<string, number>;
  expectedOutputs: Record<string, number>;
}

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

  const [data, setData] = useState<CreatePuzzleData>({
    basic: {
      name: "",
      description: "",
      budget: 0,
      difficulty: "EASY",
      timeLimit: null,
      gateSet: [],
      inputs: [],
      outputs: [],
    },
    testCases: [],
    instructions: "",
    solutionJSON: "",
  });

  const [testCaseForm, setTestCaseForm] = useState<TestCase>({
    inputs: {},
    expectedOutputs: {},
  });

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
    // Auto-initialize any missing inputs/outputs (shouldn't be needed, but safety check)
    const initializedForm = { ...testCaseForm };
    
    // Ensure all required inputs are in the form
    data.basic.inputs.forEach((inputName) => {
      if (!(inputName in initializedForm.inputs)) {
        initializedForm.inputs[inputName] = 0;
      }
    });
    
    // Ensure all required outputs are in the form
    data.basic.outputs.forEach((outputName) => {
      if (!(outputName in initializedForm.expectedOutputs)) {
        initializedForm.expectedOutputs[outputName] = 0;
      }
    });

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
    setTestCaseForm({ inputs: {}, expectedOutputs: {} });
  };

  const handleRemoveTestCase = (id: string | undefined) => {
    if (!id) return;
    setData((prev) => ({
      ...prev,
      testCases: prev.testCases.filter((tc) => tc.id !== id),
    }));
  };

  const handleAddInputField = () => {
    // Find the first input that hasn't been added to the form yet
    const missingInput = data.basic.inputs.find(
      (inputName) => !(inputName in testCaseForm.inputs)
    );
    const inputName = missingInput || `input_${Object.keys(testCaseForm.inputs).length}`;
    setTestCaseForm((prev) => ({
      ...prev,
      inputs: { ...prev.inputs, [inputName]: 0 },
    }));
  };

  const handleAddOutputField = () => {
    // Find the first output that hasn't been added to the form yet
    const missingOutput = data.basic.outputs.find(
      (outputName) => !(outputName in testCaseForm.expectedOutputs)
    );
    const outputName = missingOutput || `output_${Object.keys(testCaseForm.expectedOutputs).length}`;
    setTestCaseForm((prev) => ({
      ...prev,
      expectedOutputs: { ...prev.expectedOutputs, [outputName]: 0 },
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
        },
        test_cases: data.testCases.map(({ id, ...tc }) => tc),
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

      const res = await fetch(`${baseUrl}/create-puzzle-form`, {
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

              {data.basic.inputs.length > 0 &&  (
                <div>
                  <label className="block font-semibold mb-2">Inputs</label>
                  <div className="space-y-2 mb-4">
                    {data.basic.inputs.map((inputName) => (
                      <div key={inputName} className="flex items-center gap-2">
                        <label className="w-32">{inputName}:</label>
                        <select
                          value={testCaseForm.inputs[inputName] ?? 0}
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
                          value={testCaseForm.expectedOutputs[outputName] ?? 0}
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
                        <th className="border p-2 text-left">
                          {data.basic.inputs.join(", ")}
                        </th>
                        <th className="border p-2 text-left">
                          {data.basic.outputs.join(", ")}
                        </th>
                        <th className="border p-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.testCases.map((tc) => (
                        <tr key={tc.id} className="hover:bg-gray-50">
                          <td className="border p-2">
                            {JSON.stringify(tc.inputs)}
                          </td>
                          <td className="border p-2">
                            {JSON.stringify(tc.expectedOutputs)}
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
          <div className="space-y-6">
            <div className="bg-blue-50 border border-blue-200 p-6 rounded">
              <h3 className="font-semibold text-blue-900 mb-4">Create Solution</h3>
              <ol className="list-decimal list-inside space-y-3 text-blue-900 mb-6">
                <li className="ml-2">Navigate to <span className="font-semibold">Puzzles</span> page</li>
                <li className="ml-2">Find the puzzle you just created and click <span className="font-semibold">Solve</span></li>
                <li className="ml-2">Design a circuit that passes all test cases using the circuit builder</li>
                <li className="ml-2">When all tests pass, click <span className="font-semibold">Export Solution</span></li>
                <li className="ml-2">Copy the exported JSON and paste it below</li>
              </ol>
            </div>

            <div className="space-y-4">
              <label className="block font-semibold text-gray-900">Sample Solution (JSON) *</label>
              <textarea
                value={data.solutionJSON}
                onChange={(e) =>
                  setData((prev) => ({ ...prev, solutionJSON: e.target.value }))
                }
                className="w-full border p-4 rounded font-mono text-sm h-48"
                placeholder={`{\n  "eval_map": {\n    "{\\"A\\": 0, \\"B\\": 0}": {"S": 0},\n    "{\\"A\\": 0, \\"B\\": 1}": {"S": 1},\n    "{\\"A\\": 1, \\"B\\": 0}": {"S": 1},\n    "{\\"A\\": 1, \\"B\\": 1}": {"S": 0}\n  },\n  "used_gates": ["XOR"],\n  "inputs": ["A", "B"],\n  "outputs": ["S"]\n}`}
              />
              {data.solutionJSON.trim() && (
                <div className="p-3 bg-green-50 border border-green-200 rounded">
                  <p className="text-sm text-green-900 font-semibold">✓ Solution JSON loaded</p>
                </div>
              )}
            </div>

            <details className="border rounded p-4 bg-gray-50">
              <summary className="cursor-pointer font-semibold text-gray-900">Solution Format Reference</summary>
              <div className="mt-4 space-y-4 text-sm text-gray-700">
                <div>
                  <p className="font-semibold text-gray-900 mb-2">eval_map (required):</p>
                  <p>Maps input combinations to their output values. Key is a JSON string of inputs, value is an object of outputs.</p>
                  <pre className="mt-2 p-2 bg-white border rounded text-xs overflow-x-auto">
{`"eval_map": {
  "{\\"A\\": 0, \\"B\\": 0}": {"S": 0},
  "{\\"A\\": 0, \\"B\\": 1}": {"S": 1},
  "{\\"A\\": 1, \\"B\\": 0}": {"S": 1},
  "{\\"A\\": 1, \\"B\\": 1}": {"S": 0}
}`}
                  </pre>
                </div>

                <div>
                  <p className="font-semibold text-gray-900 mb-2">used_gates (recommended):</p>
                  <p>List of gate types used in your solution.</p>
                  <pre className="mt-2 p-2 bg-white border rounded text-xs overflow-x-auto">
{`"used_gates": ["AND", "OR", "NOT", "XOR"]`}
                  </pre>
                </div>

                <div>
                  <p className="font-semibold text-gray-900 mb-2">inputs & outputs:</p>
                  <p>Arrays of input and output signal names (must match puzzle definition).</p>
                  <pre className="mt-2 p-2 bg-white border rounded text-xs overflow-x-auto">
{`"inputs": ["A", "B", "C_in"],
"outputs": ["S", "C_out"]`}
                  </pre>
                </div>
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
