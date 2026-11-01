import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { NavBar } from "../components/NavBar";
import { Tabs } from "../components/Tabs";
import {
  Clock,
  Trash2,
  AlertCircle,
  RefreshCw,
  Download,
  Copy,
  Search,
  ChevronDown,
  CheckCircle2,
} from "lucide-react";
import type { Finding, Review, Severity } from "../api/types";
import { usePollingQuery } from "../hooks/usePolling";
import { filterFindings } from "../utils/filterLogic";
import { PageTransition } from "../components/PageTransition";
import { GlassInput } from "../components/GlassInput";
import { Toast } from "../components/Toast";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

export default function ReviewResult() {
  const reducedMotion = useReducedMotion();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("findings");
  const [searchTerm, setSearchTerm] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);

  const {
    data: review,
    isLoading,
    error,
  } = usePollingQuery(
    ["review", id],
    () => api.getReview(id!),
    (result) => result.status,
  );
  const retryReview = useMutation({
    mutationFn: () => api.createReview({ diff_text: review?.diff_text ?? "" }),
    onSuccess: (result) => navigate(`/app/reviews/${result.id}`),
  });
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);

  const deleteReview = async () => {
    if (confirm("Delete this review?")) {
      try {
        await api.deleteReview(id!);
        await queryClient.invalidateQueries({ queryKey: ["reviews"] });
        navigate("/app/history");
      } catch (deleteError) {
        setToast({
          message:
            deleteError instanceof Error
              ? deleteError.message
              : "Unable to delete review",
          type: "error",
        });
      }
    }
  };

  const copyToClipboard = (text: string) => {
    void navigator.clipboard
      .writeText(text)
      .then(() =>
        setToast({ message: "Fix copied to clipboard", type: "success" }),
      )
      .catch(() =>
        setToast({ message: "Could not copy to clipboard", type: "error" }),
      );
  };

  const exportMarkdown = () => {
    if (!review) return;
    const reviewData = review as Review;
    const md =
      reviewData.report_md || "# Review Report\n\nNo report available.";
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `review-${id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading)
    return (
      <div className="app-page">
        <NavBar />
        <div className="space-y-4">
          <div className="skeleton-glass h-8 w-64 rounded-xl" />
          <div className="skeleton-glass h-40 rounded-2xl" />
        </div>
      </div>
    );
  if (error)
    return (
      <div className="app-page">
        <NavBar />
        <div role="alert" className="text-critical">
          Error loading review: {error.message}
        </div>
      </div>
    );
  if (!review)
    return (
      <div className="app-page">
        <NavBar />
        <div className="text-secondary">Review not found</div>
      </div>
    );

  const reviewData = review as Review;
  const isRunning =
    reviewData.status === "queued" || reviewData.status === "running";

  const filteredFindings = filterFindings(
    reviewData.findings,
    searchTerm,
    severityFilter as Severity | "",
  );

  return (
    <div className="app-page">
      <NavBar />
      <PageTransition>
        <main className="mx-auto max-w-[1500px]">
          <div className="flex justify-between items-start mb-8">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl font-bold uppercase tracking-wider text-secondary">
                  Review {id!.slice(0, 8)}
                </h1>
                {USE_MOCK && <Badge variant="brand">Demo data</Badge>}
              </div>
              <div className="flex items-center gap-4">
                <Badge
                  variant={
                    reviewData.verdict === "APPROVE" ? "safe" : "critical"
                  }
                >
                  {reviewData.verdict || "Pending"}
                </Badge>
                {reviewData.agents.length > 0 && (
                  <span className="flex items-center gap-2 text-brand">
                    <span className="w-2 h-2 bg-brand rounded-full animate-pulse" />
                    Running
                  </span>
                )}
                {reviewData.duration_s && (
                  <span className="text-secondary flex items-center gap-1">
                    <Clock size={16} />
                    {reviewData.duration_s}s
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {reviewData.status === "failed" && (
                <button
                  onClick={() => retryReview.mutate()}
                  disabled={retryReview.isPending}
                  className="flex items-center gap-2 text-brand hover:text-brand/80 transition-colors"
                >
                  <RefreshCw size={20} />
                  {retryReview.isPending ? "Retrying…" : "Retry review"}
                </button>
              )}
              {reviewData.status === "done" && (
                <button
                  onClick={exportMarkdown}
                  className="flex items-center gap-2 text-brand hover:text-brand/80 transition-colors"
                >
                  <Download size={20} />
                  Export
                </button>
              )}
              <button
                onClick={deleteReview}
                className="text-secondary hover:text-critical transition-colors"
              >
                <Trash2 size={20} />
              </button>
            </div>
          </div>

          {retryReview.isError && (
            <p role="alert" className="mb-4 text-critical">
              {retryReview.error.message}
            </p>
          )}
          {reviewData.status === "failed" && (
            <div className="glass-panel mb-6 rounded-2xl border-critical/30 bg-critical/5 p-4 text-critical">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle size={20} />
                <span className="font-semibold">Review Failed</span>
              </div>
              <p>{reviewData.error}</p>
            </div>
          )}

          {isRunning && (
            <div className="glass-panel mb-6 rounded-[26px] p-5 sm:p-7">
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">Agent pipeline</h2>
                  <p className="mt-1 text-xs text-secondary">
                    Live progress for this review
                  </p>
                </div>
                <Badge variant="brand">{reviewData.status}</Badge>
              </div>
              <div
                className="flex gap-3 overflow-x-auto pb-3"
                aria-live="polite"
              >
                {reviewData.agents.map((agent, index) => (
                  <div
                    key={agent.agent}
                    className="flex shrink-0 items-center gap-3"
                  >
                    <div
                      className={`agent-node ${agent.status === "running" ? "is-running" : ""} min-w-32 rounded-2xl p-3 ${agent.status === "skipped" || agent.status === "idle" ? "opacity-45" : ""}`}
                    >
                      <div className="flex items-center gap-2">
                        {agent.status === "done" ? (
                          <CheckCircle2 size={15} className="text-safe" />
                        ) : (
                          <span
                            className={`h-2 w-2 rounded-full ${agent.status === "running" ? "animate-pulse bg-violet-200" : "bg-secondary/60"}`}
                          />
                        )}
                        <span className="text-xs font-semibold">
                          {agent.agent}
                        </span>
                      </div>
                      <div className="mt-2 text-[10px] text-secondary">
                        {agent.status} · {agent.finding_count} findings
                      </div>
                    </div>
                    {index < reviewData.agents.length - 1 && (
                      <span
                        className={`pipeline-track h-px w-8 shrink-0 ${agent.status === "running" ? "opacity-100" : "opacity-45"}`}
                      />
                    )}
                  </div>
                ))}
              </div>
              <div
                className="code-glass mt-4 overflow-hidden rounded-2xl border border-white/[.08] p-4"
                aria-live="polite"
              >
                <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold text-secondary">
                  <span className="h-2 w-2 rounded-full bg-safe" />
                  Activity log
                </h3>
                <ul className="space-y-2 font-mono text-[11px] leading-relaxed text-secondary">
                  <li>
                    <span className="mr-2 text-violet-200">›</span>
                    {new Date(reviewData.created_at).toLocaleTimeString()}{" "}
                    review {reviewData.status}
                  </li>
                  {reviewData.agents
                    .filter((agent) => agent.status !== "idle")
                    .map((agent) => (
                      <li key={`log-${agent.agent}`}>
                        <span className="mr-2 text-violet-200">›</span>
                        {agent.agent}: {agent.status}
                        {agent.finding_count
                          ? ` · ${agent.finding_count} findings`
                          : ""}
                      </li>
                    ))}
                </ul>
              </div>
            </div>
          )}

          {reviewData.status === "done" && (
            <>
              <Tabs
                tabs={[
                  {
                    id: "findings",
                    label: `Findings (${filteredFindings.length})`,
                  },
                  {
                    id: "rejected",
                    label: `Rejected (${reviewData.findings.filter((f: Finding) => f.status === "rejected").length})`,
                  },
                  { id: "diff", label: "Diff" },
                  { id: "report", label: "Report" },
                ]}
                activeTab={activeTab}
                onTabChange={setActiveTab}
              />

              {activeTab === "findings" && (
                <div className="mt-6">
                  <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
                    <div className="flex-1 relative">
                      <Search
                        size={16}
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary"
                      />
                      <GlassInput
                        type="text"
                        placeholder="Search findings..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-10 pr-4"
                      />
                    </div>
                    <select
                      value={severityFilter}
                      onChange={(e) => setSeverityFilter(e.target.value)}
                      className="glass-control min-h-11 rounded-xl px-4 text-sm text-text focus:border-violet-300/60 focus:outline-none focus:ring-2 focus:ring-violet-400/20"
                    >
                      <option value="">All Severities</option>
                      <option value="CRITICAL">Critical</option>
                      <option value="HIGH">High</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="LOW">Low</option>
                    </select>
                  </div>

                  {filteredFindings.length === 0 ? (
                    <div className="glass-panel rounded-2xl p-8 text-center text-secondary">
                      No findings match your filters.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {filteredFindings.map((finding: Finding) => {
                        const expanded = expandedFinding === finding.id;
                        return (
                          <motion.article
                            layout={!reducedMotion}
                            key={finding.id}
                            className="glass-panel overflow-hidden rounded-[24px]"
                          >
                            <button
                              type="button"
                              aria-expanded={expanded}
                              onClick={() =>
                                setExpandedFinding(expanded ? null : finding.id)
                              }
                              className="flex w-full items-start justify-between gap-4 p-4 text-left transition hover:bg-white/[.025] sm:p-5"
                            >
                              <div className="min-w-0">
                                <div className="mb-3 flex flex-wrap items-center gap-2">
                                  <Badge
                                    variant={
                                      finding.severity.toLowerCase() as
                                        "critical" | "high" | "medium" | "low"
                                    }
                                  >
                                    {finding.severity}
                                  </Badge>
                                  <Badge
                                    variant="secondary"
                                    confidence={
                                      finding.confidence.toLowerCase() as
                                        "high" | "medium" | "low"
                                    }
                                  >
                                    {finding.confidence} confidence
                                  </Badge>
                                  <Badge variant="brand">{finding.cwe}</Badge>
                                </div>
                                <h3 className="font-semibold">
                                  {finding.title}
                                </h3>
                                <p className="mt-1 truncate font-mono text-xs text-secondary">
                                  {finding.file}:{finding.line}
                                </p>
                                <div className="mt-3 flex flex-wrap gap-1.5">
                                  {finding.sources.map((source) => (
                                    <Badge key={source} variant="secondary">
                                      {source}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                              <ChevronDown
                                size={18}
                                className={`mt-1 shrink-0 text-secondary transition-transform duration-300 ${expanded ? "rotate-180" : ""}`}
                              />
                            </button>
                            <AnimatePresence initial={false}>
                              {expanded && (
                                <motion.div
                                  key="finding-details"
                                  initial={
                                    reducedMotion ? false : { opacity: 0, y: 6 }
                                  }
                                  animate={{ opacity: 1, y: 0 }}
                                  exit={
                                    reducedMotion
                                      ? { opacity: 0 }
                                      : { opacity: 0, y: 4 }
                                  }
                                  transition={{ duration: 0.24 }}
                                  className="overflow-hidden"
                                >
                                  <div className="space-y-3 border-t border-white/[.08] p-4 sm:p-5">
                                    <div className="code-glass rounded-2xl border p-4">
                                      <p className="mb-2 text-[10px] font-semibold uppercase tracking-[.16em] text-secondary">
                                        Evidence
                                      </p>
                                      <pre className="overflow-x-auto whitespace-pre-wrap text-xs leading-relaxed">
                                        {finding.evidence}
                                      </pre>
                                    </div>
                                    <div className="code-glass rounded-2xl border p-4">
                                      <div className="mb-2 flex items-center justify-between gap-3">
                                        <p className="text-[10px] font-semibold uppercase tracking-[.16em] text-secondary">
                                          Suggested fix
                                        </p>
                                        <button
                                          type="button"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            copyToClipboard(finding.fix);
                                          }}
                                          className="inline-flex min-h-9 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 text-xs font-medium text-secondary transition hover:text-violet-100"
                                        >
                                          <Copy size={13} />
                                          Copy fix
                                        </button>
                                      </div>
                                      <pre className="overflow-x-auto whitespace-pre-wrap text-xs leading-relaxed">
                                        {finding.fix}
                                      </pre>
                                    </div>
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </motion.article>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {activeTab === "rejected" && (
                <div className="mt-6">
                  <div className="space-y-4">
                    {reviewData.findings
                      .filter((f: Finding) => f.status === "rejected")
                      .map((finding: Finding) => (
                        <div
                          key={finding.id}
                          className="glass-panel rounded-2xl border-dashed p-5"
                        >
                          <div className="mb-3 flex flex-wrap items-center gap-2">
                            <Badge variant="secondary">Rejected</Badge>
                            <Badge
                              variant={
                                finding.severity.toLowerCase() as
                                  "critical" | "high" | "medium" | "low"
                              }
                            >
                              {finding.severity}
                            </Badge>
                            <Badge variant="brand">{finding.cwe}</Badge>
                          </div>
                          <p className="font-semibold">{finding.title}</p>
                          <p className="mt-2 text-sm leading-relaxed text-secondary">
                            {finding.rejection_reason ||
                              "The verifier did not retain this finding."}
                          </p>
                        </div>
                      ))}
                    {reviewData.findings.filter(
                      (f: Finding) => f.status === "rejected",
                    ).length === 0 && (
                      <div className="glass-panel rounded-2xl p-8 text-center text-secondary">
                        No rejected findings.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {activeTab === "diff" && (
                <div className="mt-6">
                  <div className="code-glass rounded-2xl border p-4 sm:p-6">
                    <pre className="text-sm overflow-x-auto whitespace-pre-wrap">
                      {reviewData.diff_text}
                    </pre>
                  </div>
                </div>
              )}

              {activeTab === "report" && (
                <div className="mt-6">
                  <div className="code-glass rounded-2xl border p-4 sm:p-6">
                    <pre className="text-sm overflow-x-auto whitespace-pre-wrap">
                      {reviewData.report_md || "No report available."}
                    </pre>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </PageTransition>
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
