"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, ChangeEvent, FormEvent } from "react";
import Cookies from "js-cookie";
import { AUTH_TOKEN_COOKIE_NAME } from "@/utils/auth-constants";

export default function UploadPuzzlePage() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [files, setFiles] = useState<{
    config: File | null;
    solution: File | null;
    test: File | null;
    setup: File | null;
    instructions: File | null;
    readme: File | null;
  }>({
    config: null,
    solution: null,
    test: null,
    setup: null,
    instructions: null,
    readme: null,
  });

  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [difficulty, setDifficulty] = useState<"EASY" | "MEDIUM" | "HARD">("EASY");

  const requiredFiles = [
    { key: "config", label: "Configuration JSON", ext: ".json" },
    { key: "solution", label: "Sample Solution JSON", ext: ".json" },
    { key: "test", label: "Test Script (.py)", ext: ".py" },
    { key: "setup", label: "Setup Script (.py)", ext: ".py" },
    { key: "instructions", label: "Instructions MD", ext: ".md" },
    { key: "readme", label: "Readme MD", ext: ".md" },
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

    const formData = new FormData();
    formData.append("config_file", files.config!);
    formData.append("sample_solution_file", files.solution!);
    formData.append("test_file", files.test!);
    formData.append("setup_file", files.setup!);
    formData.append("instructions_file", files.instructions!);
    formData.append("readme_file", files.readme!);
    formData.append("difficulty", difficulty);

    try {
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
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Upload New Puzzle</h1>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Difficulty selector */}
        <div className="flex flex-col">
          <label className="font-semibold mb-2">Difficulty</label>
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as "EASY" | "MEDIUM" | "HARD")}
            className="border p-2 rounded bg-white"
          >
            <option value="EASY">Easy</option>
            <option value="MEDIUM">Medium</option>
            <option value="HARD">Hard</option>
          </select>
        </div>

        {requiredFiles.map((req) => (
          <div key={req.key} className="flex flex-col">
            <label className="font-semibold mb-2">{req.label}</label>
            <input
              type="file"
              accept={req.ext}
              onChange={(e) => handleFileChange(req.key, e)}
              className="border p-2 rounded"
            />
            {files[req.key] && !files[req.key]!.name.endsWith(req.ext) && (
              <span className="text-red-500 text-sm">Invalid extension. Must be {req.ext}</span>
            )}
          </div>
        ))}

        <div className="pt-4">
          <button
            type="submit"
            disabled={!isFormValid || status === "uploading"}
            className={`w-full p-3 text-white font-bold rounded transition-colors ${
              isFormValid 
                ? "bg-blue-600 hover:bg-blue-700" 
                : "bg-gray-400 cursor-not-allowed"
            }`}
          >
            {status === "uploading" ? "Uploading..." : "Upload to Database"}
          </button>
        </div>

        {message && (
          <div className={`p-4 rounded ${status === "success" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
            {message}
          </div>
        )}
      </form>
    </div>
  );
}
