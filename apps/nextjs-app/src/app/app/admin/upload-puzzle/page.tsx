'use client';

import { useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState, ChangeEvent, FormEvent, useEffect } from 'react';
import { CircleCheck, Upload, BookOpen } from 'lucide-react';
import Cookies from 'js-cookie';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';
import { PageHero } from '@/components/ui/page-hero/page-hero';
import { StyledSelect } from '@/components/ui/styled-select/styled-select';
import { useUser } from '@/lib/auth';

const DIFFICULTY_OPTIONS = [
  { value: 'EASY' as const, label: 'Easy' },
  { value: 'MEDIUM' as const, label: 'Medium' },
  { value: 'HARD' as const, label: 'Hard' },
];

export default function UploadPuzzlePage() {
  const MAX_PUZZLE_NAME_LENGTH = 100;
  const MAX_PUZZLE_DESCRIPTION_LENGTH = 2000;
  const MAX_PUZZLE_INSTRUCTIONS_BYTES = 5 * 1024;
  const queryClient = useQueryClient();
  const router = useRouter();
  const user = useUser();

  // Redirect non-admins away from upload page
  useEffect(() => {
    if (user.data && user.data.role !== 'admin') {
      router.push('/app/puzzles');
    }
  }, [user.data, router]);
  const [showInfo, setShowInfo] = useState(false);
  const [expandedFormat, setExpandedFormat] = useState<string | null>(null);
  const [files, setFiles] = useState<{
    config: File | null;
    solution: File | null;
    instructions: File | null;
    pythonTests: File | null;
  }>({
    config: null,
    solution: null,
    instructions: null,
    pythonTests: null,
  });

  const [status, setStatus] = useState<
    'idle' | 'uploading' | 'success' | 'error'
  >('idle');
  const [message, setMessage] = useState('');
  const [difficulty, setDifficulty] = useState<'EASY' | 'MEDIUM' | 'HARD'>(
    'EASY',
  );

  const requiredFiles = [
    { key: 'config', label: 'Configuration JSON', ext: '.json' },
    { key: 'solution', label: 'Sample Solution JSON', ext: '.json' },
    { key: 'instructions', label: 'Instructions LaTeX', ext: '.tex' },
  ] as const;

  const optionalFiles = [
    { key: 'pythonTests', label: 'Python Tests (optional)', ext: '.py' },
  ] as const;

  const handleFileChange = (
    key: keyof typeof files,
    e: ChangeEvent<HTMLInputElement>,
  ) => {
    if (e.target.files && e.target.files[0]) {
      setFiles((prev) => ({ ...prev, [key]: e.target.files![0] }));
    }
  };

  const isFormValid = requiredFiles.every((f) => {
    const file = files[f.key];
    return file && file.name.endsWith(f.ext);
  });

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;

    setStatus('uploading');
    setMessage('');

    try {
      const configText = await files.config!.text();
      const configJson = JSON.parse(configText);
      const puzzle = configJson?.puzzle ?? {};
      const puzzleName =
        typeof puzzle.name === 'string' ? puzzle.name.trim() : '';
      const description =
        typeof puzzle.description === 'string' ? puzzle.description : '';
      const instructionsText = await files.instructions!.text();

      if (!puzzleName) {
        throw new Error('Puzzle name is required');
      }
      if (puzzleName.length > MAX_PUZZLE_NAME_LENGTH) {
        throw new Error(
          `Puzzle name must be at most ${MAX_PUZZLE_NAME_LENGTH} characters`,
        );
      }
      if (description.length > MAX_PUZZLE_DESCRIPTION_LENGTH) {
        throw new Error(
          `Puzzle description must be at most ${MAX_PUZZLE_DESCRIPTION_LENGTH} characters`,
        );
      }
      if (
        new TextEncoder().encode(instructionsText).length >
        MAX_PUZZLE_INSTRUCTIONS_BYTES
      ) {
        throw new Error(
          `Puzzle instructions must be at most ${MAX_PUZZLE_INSTRUCTIONS_BYTES} bytes`,
        );
      }

      const formData = new FormData();
      formData.append('config_file', files.config!);
      formData.append('sample_solution_file', files.solution!);
      formData.append('instructions_file', files.instructions!);
      if (files.pythonTests) {
        formData.append('python_tests_file', files.pythonTests);
      }
      formData.append('difficulty', difficulty);

      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8081/api';
      const baseUrl = apiUrl.replace(/\/api\/?$/, '');
      const authToken = Cookies.get(AUTH_TOKEN_COOKIE_NAME);
      const res = await fetch(`${baseUrl}/admin/upload-puzzle`, {
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
            : JSON.stringify(detail) ||
              'Upload failed with status ' + res.status;
        throw new Error(errorMessage);
      }

      await res.json(); // Consume body just in case

      setStatus('success');
      setMessage('Puzzle uploaded successfully! Redirecting...');

      try {
        await queryClient.invalidateQueries({ queryKey: ['puzzles'] });
        await queryClient.invalidateQueries({ queryKey: ['admin-puzzles'] });
      } catch (e) {
        console.error('Failed to invalidate queries', e);
      }

      setTimeout(() => {
        router.push('/app/puzzles');
      }, 1500);
    } catch (err: any) {
      console.error(err);
      setStatus('error');
      setMessage(err.message || 'An unexpected error occurred');
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto text-foreground">
      <PageHero
        badge="Admin tools"
        icon={Upload}
        title="Upload New Puzzle"
        description="Drop in puzzle configs, solutions, instructions, and tests to publish a full puzzle bundle in one go."
        rightSlot={
          <button
            onClick={() => setShowInfo(!showInfo)}
            className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/70 px-4 py-2 text-sm font-semibold text-foreground shadow-sm backdrop-blur-sm transition-all hover:border-primary/50 hover:bg-primary/10"
          >
            <BookOpen className="size-4" />
            File Format Guide
          </button>
        }
      />

      {showInfo && (
        <div className="mb-8 p-6 bg-secondary/50 border border-border rounded-xl space-y-6">
          <h2 className="text-lg font-semibold text-foreground">
            File Format Guide
          </h2>

          <details className="border border-border p-4 rounded-lg bg-card">
            <summary className="font-medium cursor-pointer text-foreground text-[13px]">
              Configuration JSON (puzzle_config.json)
            </summary>
            <pre className="mt-3 p-3 bg-secondary/50 rounded-lg text-[11px] text-foreground overflow-x-auto font-mono">
              {`{
  "puzzle": {
    "name": "Binary Adder Quiz",
    "description": "Design a full adder circuit",
    "budget": 200,
    "time_limit_seconds": 30,
    "default_gate_set": ["XOR", "AND", "OR"],
    "inputs": ["A", "B", "C_in"],
    "outputs": ["S", "C_out"]
  },
  "shared_arsenal_pieces": [
    {
      "name": "wonce",
      "description": "Write once bit",
      "cost": 2,
      "num_inputs": 1,
      "num_outputs": 1,
      "structure": {
        "numInputs": 1,
        "numOutputs": 1,
        "placed": [],
        "wires": []
      },
      "basic_gates": ["OR", "DFF"],
      "truth_table": {}
    }
  ],
  "test_cases": [
    {
      "inputs": {"A": 0, "B": 0, "C_in": 0},
      "expected_outputs": {"S": 0, "C_out": 0}
    },
    {
      "kind": "gate_count_limit",
      "max_gate_count": 10,
      "min_gate_count": 3
    },
    {
      "kind": "gate_limit",
      "gate_name": "AND",
      "min_gate_limit": 1,
      "gate_limit": 5
    }
  ]
}`}
            </pre>
            <div className="mt-3 text-[12px] text-foreground/80 space-y-2">
              <p>
                <strong>Constraint Examples in test_cases:</strong>
              </p>
              <ul className="list-disc list-inside space-y-1">
                <li>
                  <code className="bg-black/20 px-1 rounded">
                    "gate_count_limit"
                  </code>{' '}
                  - Total gate constraint: max_gate_count (limit),
                  min_gate_count (minimum required)
                </li>
                <li>
                  <code className="bg-black/20 px-1 rounded">"gate_limit"</code>{' '}
                  - Per-gate type constraint: gate_name, gate_limit (max),
                  min_gate_limit (min, optional)
                </li>
              </ul>
              <p>
                Shared arsenal pieces can be bundled in
                <code className="bg-black/20 px-1 rounded ml-1">
                  shared_arsenal_pieces
                </code>{' '}
                and referenced by name in
                <code className="bg-black/20 px-1 rounded ml-1">
                  allowed_arsenal_component_ids
                </code>
                .
              </p>
            </div>
          </details>

          <details className="border border-border p-4 rounded-lg bg-card">
            <summary className="font-medium cursor-pointer text-foreground text-[13px]">
              Instructions LaTeX (puzzle_instructions.tex)
            </summary>
            <pre className="mt-3 p-3 bg-secondary/50 rounded-lg text-[11px] text-foreground overflow-x-auto font-mono">
              {`\section*{Binary Adder Quiz Instructions}

\\subsection*{Objective}
Design a digital circuit that implements a \\textbf{full adder} using:
\\begin{itemize}
  \\item AND gate
  \\item NAND gate
  \\item DFF gate
\\end{itemize}

\\subsection*{What is a Full Adder?}
A full adder is a digital circuit that adds three binary digits. It produces two outputs:
\\begin{itemize}
  \\item Sum (\$S\$): The least significant bit
  \\item Carry-out (\$C_{\\text{out}}\$): The carry bit
\\end{itemize}

\\subsection*{Truth Table}
\\begin{center}
\\begin{tabular}{|c|c|c|c|c|}
\\hline
\$A\$ & \$B\$ & \$C_{\\text{in}}\$ & \$S\$ & \$C_{\\text{out}}\$ \\\\
\\hline
0 & 0 & 0 & 0 & 0 \\\\
... \\\\
\\hline
\\end{tabular}
\\end{center}

Note: Use LaTeX syntax for all formatting. Math expressions use single \$ for inline or \\\\[\\ ... \\\\] for display math.`}
            </pre>
          </details>

          <details className="border border-border p-4 rounded-lg bg-card">
            <summary className="font-medium cursor-pointer text-foreground text-[13px]">
              Sample Solution JSON (puzzle_solution.json)
            </summary>
            <pre className="mt-3 p-3 bg-secondary/50 rounded-lg text-[11px] text-foreground overflow-x-auto font-mono">
              {`{
  "eval_map": {
    "{\\"A\\": 0, \\"B\\": 0, \\"C_in\\": 0}": {"S": 0, "C_out": 0},
    "{\\"A\\": 0, \\"B\\": 0, \\"C_in\\": 1}": {"S": 1, "C_out": 0},
    "{\\"A\\": 0, \\"B\\": 1, \\"C_in\\": 0}": {"S": 1, "C_out": 0},
    "{\\"A\\": 0, \\"B\\": 1, \\"C_in\\": 1}": {"S": 0, "C_out": 1},
    "{\\"A\\": 1, \\"B\\": 0, \\"C_in\\": 0}": {"S": 1, "C_out": 0},
    "{\\"A\\": 1, \\"B\\": 0, \\"C_in\\": 1}": {"S": 0, "C_out": 1},
    "{\\"A\\": 1, \\"B\\": 1, \\"C_in\\": 0}": {"S": 0, "C_out": 1},
    "{\\"A\\": 1, \\"B\\": 1, \\"C_in\\": 1}": {"S": 1, "C_out": 1}
  },
  "placedComponents": [{"componentId": "AND", "x": 0, "y": 0}, ...],
  "wires": [{"from": {...}, "to": {...}}, ...],
  "inputs": ["A", "B", "C_in"],
  "outputs": ["S", "C_out"],
  "totalCost": 25
}`}
            </pre>
            <p className="mt-3 text-[13px] text-foreground/80">
              The eval_map must contain entries for all possible input
              combinations. The solution must pass all test cases.
            </p>
          </details>

          <div className="bg-amber-50/50 border border-amber-200/60 p-4 rounded-lg">
            <p className="text-[13px] font-semibold text-amber-900">
              Important:
            </p>
            <ul className="list-disc list-inside text-[13px] text-amber-800 mt-2">
              <li>Config and Solution files must be valid JSON</li>
              <li>Instructions file must be LaTeX format</li>
              <li>Sample solution must pass all test cases</li>
              <li>
                All inputs/outputs in test cases must match config specification
              </li>
              <li>
                Python tests file naming: riddle_XX_[name]_tests.py (optional)
              </li>
            </ul>
          </div>

          <details className="border border-border p-4 rounded-lg bg-card">
            <summary className="font-medium cursor-pointer text-foreground text-[13px]">
              Python Tests File (optional)
            </summary>
            <div className="mt-3 text-[12px] text-foreground/80 mb-3 space-y-2 bg-black/10 p-3 rounded-lg">
              <p className="font-semibold">Available in test code:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>
                  <code className="bg-black/20 px-1 rounded">solution</code> -
                  Full circuit dict: placedComponents, wires, inputs, outputs,
                  totalCost
                </li>
                <li>
                  <code className="bg-black/20 px-1 rounded">circuit</code> -
                  Same as solution
                </li>
                <li>
                  <code className="bg-black/20 px-1 rounded">
                    placed_components
                  </code>{' '}
                  - Component list
                </li>
                <li>
                  <code className="bg-black/20 px-1 rounded">wires</code> - Wire
                  connections
                </li>
              </ul>
              <p className="font-semibold mt-2">Test Rules:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>
                  <strong>REQUIRED:</strong> Define{' '}
                  <code className="bg-black/20 px-1 rounded">
                    def run_tests(solution):
                  </code>{' '}
                  function
                </li>
                <li>
                  Call your individual test functions from{' '}
                  <code className="bg-black/20 px-1 rounded">run_tests()</code>
                </li>
                <li>No return statements needed</li>
                <li>
                  Use{' '}
                  <code className="bg-black/20 px-1 rounded">
                    raise Exception("message")
                  </code>{' '}
                  to fail
                </li>
                <li>Silent pass on success (no error raised)</li>
              </ul>
            </div>
            <pre className="p-3 bg-black/20 rounded-lg text-[11px] text-foreground overflow-x-auto font-mono">
              {`# Define individual test functions
def test_uses_xor():
    """Check solution uses at least one XOR gate"""
    components = solution.get('placedComponents', [])
    has_xor = any(c.get('componentId') == 'XOR' for c in components)
    if not has_xor:
        raise Exception("Solution must use at least one XOR gate")

def test_min_components():
    """Check solution has minimum components"""
    components = solution.get('placedComponents', [])
    if len(components) < 2:
        raise Exception("Solution must have at least 2 components")

def test_connections():
    """Check circuit is properly wired"""
    wires = solution.get('wires', [])
    if len(wires) < 1:
        raise Exception("Solution must have at least one wire connection")

# REQUIRED: Main test runner function
def run_tests(solution):
    """Called automatically to run all tests"""
    test_uses_xor()
    test_min_components()
    test_connections()`}
            </pre>
          </details>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="space-y-6 bg-card p-6 rounded-xl border border-border"
      >
        {/* Difficulty selector */}
        <div className="flex flex-col">
          <label className="text-[13px] font-medium text-foreground mb-2">
            Difficulty
          </label>
          <StyledSelect
            aria-label="Difficulty"
            className="w-48"
            value={difficulty}
            onValueChange={(v) => setDifficulty(v)}
            options={DIFFICULTY_OPTIONS}
          />
        </div>

        {requiredFiles.map((req) => (
          <div key={req.key} className="flex flex-col">
            <div className="flex justify-between items-center mb-2">
              <label className="text-[13px] font-medium text-foreground">
                {req.label}
              </label>
              <button
                type="button"
                onClick={() =>
                  setExpandedFormat(expandedFormat === req.key ? null : req.key)
                }
                className="text-[11px] px-3 py-1 bg-secondary hover:bg-secondary/80 rounded-md transition-colors text-foreground"
              >
                {expandedFormat === req.key ? 'Hide Format' : 'Show Format'}
              </button>
            </div>

            {expandedFormat === req.key && (
              <div className="mb-3 p-3 bg-secondary/50 rounded-lg border border-border text-[13px]">
                {req.key === 'config' && (
                  <div>
                    <p className="font-medium text-[13px] text-foreground mb-2">
                      Configuration JSON Format:
                    </p>
                    <pre className="bg-secondary/50 p-2 rounded-lg text-[11px] text-foreground overflow-x-auto font-mono">
                      {`{
  "puzzle": {
    "name": "...",
    "description": "...",
    "budget": 200,
    "time_limit_seconds": 30,
    "default_gate_set": ["XOR", "AND"],
    "inputs": ["A", "B"],
    "outputs": ["S"]
  },
  "test_cases": [
    {
      "inputs": {"A": 0, "B": 0},
      "expected_outputs": {"S": 0}
    },
    {
      "kind": "gate_count_limit",
      "max_gate_count": 10,
      "min_gate_count": 3
    }
  ]
}`}
                    </pre>
                  </div>
                )}
                {req.key === 'solution' && (
                  <div>
                    <p className="font-medium text-[13px] text-foreground mb-2">
                      Solution JSON Format:
                    </p>
                    <pre className="bg-secondary/50 p-2 rounded-lg text-[11px] text-foreground overflow-x-auto font-mono">
                      {`{
  "eval_map": {
    "{\\"A\\": 0, \\"B\\": 0}": {"S": 0},
    "{\\"A\\": 0, \\"B\\": 1}": {"S": 1}
  },
  "placedComponents": [...],
  "wires": [...],
  "inputs": ["A", "B"],
  "outputs": ["S"]
}`}
                    </pre>
                  </div>
                )}
                {req.key === 'instructions' && (
                  <div>
                    <p className="font-medium text-[13px] text-foreground mb-2">
                      Instructions LaTeX Format:
                    </p>
                    <pre className="bg-secondary/50 p-2 rounded-lg text-[11px] text-foreground overflow-x-auto font-mono">
                      {`\\section*{Puzzle Name}
\\subsection*{Objective}
Design a circuit that...

\\subsection*{Requirements}
\\begin{itemize}
\\item Input A: Binary
\\item Output S: Sum
\\end{itemize}

\\subsection*{Truth Table}
\\begin{tabular}{|c|c|c|}
\\hline
A & B & S \\\\
\\hline
0 & 0 & 0 \\\\
\\hline
\\end{tabular}

Use $...$ for math: $C_{out}$`}
                    </pre>
                  </div>
                )}
              </div>
            )}

            <input
              type="file"
              accept={req.ext}
              onChange={(e) => handleFileChange(req.key, e)}
              className="border border-border p-2 rounded-lg text-[13px] text-foreground"
            />
            {files[req.key] && !files[req.key]!.name.endsWith(req.ext) && (
              <span className="text-destructive text-[13px]">
                Invalid extension. Must be {req.ext}
              </span>
            )}
          </div>
        ))}

        {optionalFiles.map((opt) => (
          <div key={opt.key} className="flex flex-col">
            <label className="text-[13px] font-medium text-foreground mb-2">
              {opt.label}
            </label>
            <input
              type="file"
              accept={opt.ext}
              onChange={(e) => handleFileChange(opt.key, e)}
              className="border border-border p-2 rounded-lg text-[13px] text-foreground"
            />
            {files[opt.key] && (
              <p className="mt-1 inline-flex items-center gap-1.5 text-[12px] text-green-600">
                <CircleCheck className="size-3.5" aria-hidden />
                {files[opt.key]!.name} selected
              </p>
            )}
            {files[opt.key] && !files[opt.key]!.name.endsWith(opt.ext) && (
              <span className="text-destructive text-[13px]">
                Invalid extension. Must be {opt.ext}
              </span>
            )}
          </div>
        ))}

        <div className="pt-4">
          <button
            type="submit"
            disabled={!isFormValid || status === 'uploading'}
            className={`w-full p-3 font-medium text-[13px] rounded-lg transition-colors ${
              isFormValid
                ? 'bg-foreground text-background hover:bg-foreground/90'
                : 'bg-secondary text-muted-foreground cursor-not-allowed'
            }`}
          >
            {status === 'uploading' ? 'Uploading...' : 'Upload to Database'}
          </button>
        </div>

        {message && (
          <div
            className={`p-4 rounded-lg text-[13px] ${status === 'success' ? 'bg-emerald-50/50 border border-emerald-200/60 text-emerald-700' : 'bg-red-50/50 border border-red-200/60 text-red-700'}`}
          >
            {message}
          </div>
        )}
      </form>
    </div>
  );
}
