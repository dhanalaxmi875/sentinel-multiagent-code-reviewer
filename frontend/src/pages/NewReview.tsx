import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  ArrowUpRight,
  FileCode2,
  FilePlus2,
  LockKeyhole,
  Sparkles,
  Upload,
} from "lucide-react";
import { api } from "../api/client";
import { FileText } from "lucide-react";
import { NavBar } from "../components/NavBar";
import { validateDiff, MAX_DIFF_CHARS } from "../utils/diffValidation";
import { Badge } from "../components/Badge";
import { Toast } from "../components/Toast";
import { GlassCard } from "../components/GlassCard";
import { GlassButton } from "../components/GlassButton";
import { GlassInput } from "../components/GlassInput";
import { PageTransition } from "../components/PageTransition";

export default function NewReview() {
  const navigate = useNavigate();
  const [diff, setDiff] = useState("");
  const [filePaths, setFilePaths] = useState("");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);
  const { data: samples } = useQuery({
    queryKey: ["samples"],
    queryFn: () => api.getSamples(),
  });

  const createReview = useMutation({
    mutationFn: (req: { diff_text: string; file_paths?: string[] }) =>
      api.createReview(req),
    onSuccess: (data) => navigate(`/app/reviews/${data.id}`),
    onError: (submissionError) =>
      setToast({ message: submissionError.message, type: "error" }),
  });

  const loadFile = async (file: File) => {
    setDiff(await file.text());
    setError("");
  };
  const handleSubmit = () => {
    setError("");
    const validationError = validateDiff(diff);
    if (validationError) {
      setError(validationError);
      return;
    }
    createReview.mutate({
      diff_text: diff,
      file_paths: filePaths
        ? filePaths
            .split(",")
            .map((path) => path.trim())
            .filter(Boolean)
        : undefined,
    });
  };
  const lineCount = diff ? diff.split(/\r\n|\r|\n/).length : 0;
  const charPercent = Math.min((diff.length / MAX_DIFF_CHARS) * 100, 100);

  return (
    <div className="app-page">
      <NavBar />
      <PageTransition>
        <main className="mx-auto max-w-5xl">
          <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[.22em] text-violet-200/80">
                Start an analysis
              </p>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                New review
              </h1>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-secondary">
                Share a unified diff and let the review pipeline look for bugs,
                security issues, quality concerns, and test gaps.
              </p>
            </div>
            {import.meta.env.VITE_USE_MOCK === "true" && (
              <Badge variant="brand">Demo data</Badge>
            )}
          </header>

          <GlassCard className="overflow-hidden p-0">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4 sm:px-7">
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-xl border border-violet-300/15 bg-violet-400/10 text-violet-200">
                  <FileCode2 size={19} />
                </span>
                <div>
                  <h2 className="font-semibold">Diff composer</h2>
                  <p className="text-xs text-secondary">
                    Paste a patch or drop a file below
                  </p>
                </div>
              </div>
              <span className="inline-flex items-center gap-1.5 text-xs text-secondary">
                <LockKeyhole size={14} className="text-safe" /> Sent to your
                configured review server
              </span>
            </div>
            <div className="p-4 sm:p-7">
              <div
                className={`relative rounded-2xl border transition-colors ${dragging ? "drop-highlight border-violet-300 bg-violet-400/10" : "border-white/10"}`}
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(event) => {
                  event.preventDefault();
                  setDragging(false);
                  const file = event.dataTransfer.files.item(0);
                  if (file) void loadFile(file);
                }}
              >
                <textarea
                  aria-label="Unified diff"
                  maxLength={MAX_DIFF_CHARS}
                  value={diff}
                  onChange={(event) => setDiff(event.target.value)}
                  placeholder={
                    "diff --git a/src/example.ts b/src/example.ts\n--- a/src/example.ts\n+++ b/src/example.ts\n@@ -1,1 +1,2 @@\n-old code\n+updated code"
                  }
                  className="code-glass min-h-[300px] w-full resize-y rounded-2xl p-5 pb-12 font-mono text-[13px] leading-6 text-text placeholder:text-secondary/60 focus:border-violet-300/50 focus:outline-none focus:ring-2 focus:ring-violet-400/20 sm:min-h-[390px]"
                />
                <div className="pointer-events-none absolute inset-x-4 bottom-3 flex items-center justify-between gap-2 text-[10px] text-secondary sm:text-[11px]">
                  <span>
                    {lineCount.toLocaleString()}{" "}
                    {lineCount === 1 ? "line" : "lines"}
                  </span>
                  <span className="flex items-center gap-2">
                    <span>{diff.length.toLocaleString()} / 40k chars</span>
                    <span className="h-1.5 w-10 overflow-hidden rounded-full bg-white/10 sm:w-20">
                      <span
                        className={`block h-full rounded-full ${diff.length > MAX_DIFF_CHARS * 0.9 ? "bg-medium" : "bg-violet-300"}`}
                        style={{ width: `${charPercent}%` }}
                      />
                    </span>
                  </span>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <label className="group flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border border-dashed border-white/15 px-4 text-sm font-medium text-secondary transition hover:border-violet-300/50 hover:bg-violet-400/[.06] hover:text-violet-100">
                  <Upload size={16} className="text-violet-200" />
                  <span>Choose .diff or .patch</span>
                  <input
                    type="file"
                    accept=".diff,.patch,.txt"
                    className="sr-only"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) void loadFile(file);
                    }}
                  />
                </label>
                <span className="text-xs text-secondary">
                  Drop a diff anywhere in the editor
                </span>
              </div>
              {error && (
                <p role="alert" className="mt-3 text-sm text-critical">
                  {error}
                </p>
              )}
              <div className="my-6 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
              <div className="mb-5">
                <label
                  htmlFor="file-paths"
                  className="mb-2 block text-sm font-medium"
                >
                  Files in this change{" "}
                  <span className="font-normal text-secondary">(optional)</span>
                </label>
                <GlassInput
                  id="file-paths"
                  type="text"
                  value={filePaths}
                  onChange={(event) => setFilePaths(event.target.value)}
                  placeholder="src/api.py, src/db.py"
                  className="font-mono"
                />
                <p className="mt-2 text-xs text-secondary">
                  Comma-separated file paths provide additional review context.
                </p>
              </div>
              <div className="mb-6 rounded-2xl border border-white/[.08] bg-white/[.025] p-4 sm:p-5">
                <div className="mb-3 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Sparkles size={16} className="text-violet-200" />
                    Try a sample diff
                  </div>
                  <span className="text-[10px] uppercase tracking-[.16em] text-secondary">
                    {samples?.length ?? 0} available
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {samples?.map((sample) => (
                    <button
                      key={sample.id}
                      type="button"
                      onClick={() => {
                        setDiff(sample.diff_text);
                        setError("");
                        setToast({
                          message: `${sample.name} loaded`,
                          type: "success",
                        });
                      }}
                      className="flex min-h-10 items-center gap-2 rounded-full border border-white/10 bg-white/[.04] px-4 text-left text-xs font-medium transition hover:border-violet-300/40 hover:bg-violet-400/10 hover:text-violet-100"
                    >
                      <FileText size={14} className="text-violet-200" />
                      {sample.name}
                    </button>
                  ))}
                  {samples?.length === 0 && (
                    <p className="text-sm text-secondary">
                      No sample diffs are available.
                    </p>
                  )}
                </div>
                {samples?.[0] && (
                  <p className="mt-3 text-xs leading-relaxed text-secondary">
                    {samples[0].description}
                  </p>
                )}
              </div>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <p className="max-w-md text-xs leading-relaxed text-secondary">
                  Your diff is sent to the configured review server and stored
                  with the review until you delete it from History.
                </p>
                <GlassButton
                  type="button"
                  tone="primary"
                  onClick={handleSubmit}
                  disabled={createReview.isPending}
                  className="min-h-12 px-6"
                >
                  {createReview.isPending ? (
                    "Creating review…"
                  ) : (
                    <>
                      <FilePlus2 size={16} />
                      Submit for review
                      <ArrowUpRight size={16} />
                    </>
                  )}
                </GlassButton>
              </div>
              {createReview.isError && (
                <p role="alert" className="mt-3 text-sm text-critical">
                  {createReview.error.message}
                </p>
              )}
            </div>
          </GlassCard>
          <div className="mt-5 flex items-start gap-3 rounded-2xl border border-white/[.07] bg-white/[.025] p-4 text-xs leading-relaxed text-secondary">
            <LockKeyhole size={15} className="mt-0.5 shrink-0 text-safe" />
            <p>
              Only submit code you are permitted to share with the configured
              review server. You can remove a review and its stored diff from
              the History page.
            </p>
          </div>
          {toast && (
            <Toast
              message={toast.message}
              type={toast.type}
              onClose={() => setToast(null)}
            />
          )}
        </main>
      </PageTransition>
    </div>
  );
}
