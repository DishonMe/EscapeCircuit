"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, ChangeEvent, FormEvent, useEffect } from "react";
import Cookies from "js-cookie";
import { AUTH_TOKEN_COOKIE_NAME } from "@/utils/auth-constants";
import { useUser } from "@/lib/auth";

export default function UploadPuzzlePage() {
  const MAX_PUZZLE_NAME_LENGTH = 100;
  const MAX_PUZZLE_DESCRIPTION_LENGTH = 2000;
  const MAX_PUZZLE_INSTRUCTIONS_BYTES = 5 * 1024;
  const queryClient = useQueryClient();
  const router = useRouter();
  const user = useUser();
  
  // Redirect non-admins away from upload page
  useEffect(() => {
    if (user.data && user.data.role !== "admin") {
      router.push("/app/puzzles");
    }
  }, [user.data, router]);
  const [showInfo, setShowInfo] = useState(false);
  const [expandedFormat, setExpandedFormat] = useState<string | null>(null);
  const [files, setFiles] = useState<{
    config: File | null;
    solution: File | null;
    instructions: File | null;
  }>({
    config: null,
    solution: null,
    instructions: null,
  });

  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [difficulty, setDifficulty] = useState<"EASY" | "MEDIUM" | "HARD">("EASY");

  const requiredFiles = [
    { key: "config", label: "Configuration JSON", ext: ".json" },
    { key: "solution", label: "Sample Solution JSON", ext: ".json" },
    { key: "instructions", label: "Instructions LaTeX", ext: ".tex" },
  ] as const;

  const handleFileChange = (key: keyof typeof files, e: ChangeEvent<HTMLInputElement>) => {
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

    setStatus("uploading");
    setMessage("");

    try {
      const configText = await files.config!.text();
      const configJson = JSON.parse(configText);
      const puzzle = configJson?.puzzle ?? {};
      const puzzleName = typeof puzzle.name === "string" ? puzzle.name.trim() : "";
      const description = typeof puzzle.description === "string" ? puzzle.description : "";
      const instructionsText = await files.instructions!.text();

      if (!puzzleName) {
        throw new Error("Puzzle name is required");
      }
      if (puzzleName.length > MAX_PUZZLE_NAME_LENGTH) {
        throw new Error(`Puzzle name must be at most ${MAX_PUZZLE_NAME_LENGTH} characters`);
      }
      if (description.length > MAX_PUZZLE_DESCRIPTION_LENGTH) {
        throw new Error(`Puzzle description must be at most ${MAX_PUZZLE_DESCRIPTION_LENGTH} characters`);
      }
      if (new TextEncoder().encode(instructionsText).length > MAX_PUZZLE_INSTRUCTIONS_BYTES) {
        throw new Error(`Puzzle instructions must be at most ${MAX_PUZZLE_INSTRUCTIONS_BYTES} bytes`);
      }

      const formData = new FormData();
      formData.append("config_file", files.config!);
      formData.append("sample_solution_file", files.solution!);
      formData.append("instructions_file", files.instructions!);
      formData.append("difficulty", difficulty);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8081/api";
      const baseUrl = apiUrl.replace(/\/api\/?$/, "");
      const authToken = Cookies.get(AUTH_TOKEN_COOKIE_NAME);
      const res = await fetch(`${baseUrl}/admin/upload-puzzle`, {
        method: "POST",
        headers: {
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        const detail = err.detail;
        const errorMessage = typeof detail === 'string' 
          ? detail 
          : JSON.stringify(detail) || "Upload failed with status " + res.status;
        throw new Error(errorMessage);
      }

      await res.json(); // Consume body just in case

      setStatus("success");
      setMessage("Puzzle uploaded successfully! Redirecting...");
      
      try {
        await queryClient.invalidateQueries({ queryKey: ['puzzles'] });
        await queryClient.invalidateQueries({ queryKey: ['admin-puzzles'] });
      } catch (e) {
        console.error("Failed to invalidate queries", e);
      }
      
      setTimeout(() => {
        router.push("/app/puzzles");
      }, 1500);
    } catch (err: any) {
      console.error(err);
      setStatus("error");
      setMessage(err.message || "An unexpected error occurred");
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-6 flex justify-between items-center">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Upload New Puzzle</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowInfo(!showInfo)}
            className="px-4 py-2 bg-secondary text-foreground rounded-lg hover:bg-secondary/80 font-medium text-[13px] transition-colors"
          >
            ℹ️ File Format Guide
          </button>
        </div>
      </div>

      {showInfo && (
        <div className="mb-8 p-6 bg-secondary/50 border border-border rounded-xl space-y-6">
          <h2 className="text-lg font-semibold text-foreground">File Format Guide</h2>

          <details className="border border-border p-4 rounded-lg bg-card">
            <summary className="font-medium cursor-pointer text-foreground text-[13px]">
              📋 Configuration JSON (puzzle_config.json)
            </summary>
            <pre className="mt-3 p-3 bg-secondary/50 rounded-lg text-[11px] overflow-x-auto font-mono">
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
  "test_cases": [
    {
      "inputs": {"A": 0, "B": 0, "C_in": 0},
      "expected_outputs": {"S": 0, "C_out": 0}
    },
    ...more test cases...
  ]
}`}
            </pre>
          </details>

          <details className="border border-border p-4 rounded-lg bg-card">
            <summary className="font-medium cursor-pointer text-foreground text-[13px]">
              💡 Instructions LaTeX (puzzle_instructions.tex)
            </summary>
            <pre className="mt-3 p-3 bg-secondary/50 rounded-lg text-[11px] overflow-x-auto font-mono">
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
              ✓ Sample Solution JSON (puzzle_solution.json)
            </summary>
            <pre className="mt-3 p-3 bg-secondary/50 rounded-lg text-[11px] overflow-x-auto font-mono">
{`{
  "eval_map": {
    "{\\"A\\": 0, \\"B\\": 0, \\"C_in\\": 0}": {"S": 0, "C_out": 0},
    "{\\"A\\": 0, \\"B\\": 0, \\"C_in\\": 1}": {"S": 1, "C_out": 0},
    "{\\"A\\": 0, \\"B\\": 1, \\"C_in\\": 0}": {"S": 1, "C_out": 0},
    ...all 8 combinations...
  },
  "used_gates": ["AND", "NAND", "DFF"],
  "inputs": ["A", "B", "C_in"],
  "outputs": ["S", "C_out"]
}`}
            </pre>
            <p className="mt-3 text-[13px] text-muted-foreground">
              The eval_map must contain entries for all possible input combinations.
              Keys are JSON strings of the input dict, values are the expected outputs.
            </p>
          </details>

          <div className="bg-amber-50/50 border border-amber-200/60 p-4 rounded-lg">
            <p className="text-[13px] font-semibold text-amber-900">Important:</p>
            <ul className="list-disc list-inside text-[13px] text-amber-800 mt-2">
              <li>Config and Solution files must be valid JSON</li>
              <li>Instructions file must be LaTeX format</li>
              <li>Sample solution must pass all test cases</li>
              <li>All inputs/outputs in test cases must match config specification</li>
            </ul>
          </div>
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="space-y-6 bg-card p-6 rounded-xl border border-border">
        {/* Difficulty selector */}
        <div className="flex flex-col">
          <label className="text-[13px] font-medium text-foreground mb-2">Difficulty</label>
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as "EASY" | "MEDIUM" | "HARD")}
            className="border border-border p-2 rounded-lg bg-transparent w-48 text-[13px] focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="EASY">Easy</option>
            <option value="MEDIUM">Medium</option>
            <option value="HARD">Hard</option>
          </select>
        </div>

        {requiredFiles.map((req) => (
          <div key={req.key} className="flex flex-col">
            <div className="flex justify-between items-center mb-2">
              <label className="text-[13px] font-medium text-foreground">{req.label}</label>
              <button
                type="button"
                onClick={() => setExpandedFormat(expandedFormat === req.key ? null : req.key)}
                className="text-[11px] px-3 py-1 bg-secondary hover:bg-secondary/80 rounded-md transition-colors text-foreground"
              >
                {expandedFormat === req.key ? "Hide Format" : "Show Format"}
              </button>
            </div>
            
            {expandedFormat === req.key && (
              <div className="mb-3 p-3 bg-secondary/50 rounded-lg border border-border text-[13px]">
                {req.key === "config" && (
                  <div>
                    <p className="font-medium text-[13px] text-foreground mb-2">Configuration JSON Format:</p>
                    <pre className="bg-secondary/50 p-2 rounded-lg text-[11px] overflow-x-auto font-mono">
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
    }
  ]
}`}
                    </pre>
                  </div>
                )}
                {req.key === "solution" && (
                  <div>
                    <p className="font-medium text-[13px] text-foreground mb-2">Solution JSON Format:</p>
                    <pre className="bg-secondary/50 p-2 rounded-lg text-[11px] overflow-x-auto font-mono">
{`{
  "eval_map": {
    "{\\"A\\": 0, \\"B\\": 0}": {"S": 0},
    "{\\"A\\": 0, \\"B\\": 1}": {"S": 1}
  },
  "used_gates": ["XOR"],
  "inputs": ["A", "B"],
  "outputs": ["S"]
}`}
                    </pre>
                  </div>
                )}
                {req.key === "instructions" && (
                  <div>
                    <p className="font-medium text-[13px] text-foreground mb-2">Instructions LaTeX Format:</p>
                    <pre className="bg-secondary/50 p-2 rounded-lg text-[11px] overflow-x-auto font-mono">
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
              className="border border-border p-2 rounded-lg text-[13px]"
            />
            {files[req.key] && !files[req.key]!.name.endsWith(req.ext) && (
              <span className="text-destructive text-[13px]">Invalid extension. Must be {req.ext}</span>
            )}
          </div>
        ))}

        <div className="pt-4">
          <button
            type="submit"
            disabled={!isFormValid || status === "uploading"}
            className={`w-full p-3 font-medium text-[13px] rounded-lg transition-colors ${
              isFormValid
                ? "bg-foreground text-background hover:bg-foreground/90"
                : "bg-secondary text-muted-foreground cursor-not-allowed"
            }`}
          >
            {status === "uploading" ? "Uploading..." : "Upload to Database"}
          </button>
        </div>

        {message && (
          <div className={`p-4 rounded-lg text-[13px] ${status === "success" ? "bg-emerald-50/50 border border-emerald-200/60 text-emerald-700" : "bg-red-50/50 border border-red-200/60 text-red-700"}`}>
            {message}
          </div>
        )}
      </form>
    </div>
  );
}
