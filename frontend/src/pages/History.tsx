import { useMemo, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import {
  Trash2,
  Clock,
  Search,
  ArrowDownWideNarrow,
  ShieldCheck,
} from "lucide-react";
import { NavBar } from "../components/NavBar";
import { Skeleton } from "../components/Skeleton";
import { PageTransition } from "../components/PageTransition";
import { GlassInput } from "../components/GlassInput";
import { Toast } from "../components/Toast";

export default function History() {
  const reducedMotion = useReducedMotion();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [sortOrder, setSortOrder] = useState<"newest" | "oldest">("newest");
  const [toast, setToast] = useState<string | null>(null);
  const { data: reviews, isLoading } = useQuery({
    queryKey: ["reviews"],
    queryFn: () => api.getReviews(),
  });

  const deleteReview = useMutation({
    mutationFn: (id: string) => api.deleteReview(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reviews"] }),
    onError: (deleteError) => setToast(deleteError.message),
  });
  const visibleReviews = useMemo(
    () =>
      [...(reviews ?? [])]
        .filter((review) =>
          `${review.id} ${review.status} ${review.verdict ?? ""}`
            .toLocaleLowerCase()
            .includes(search.trim().toLocaleLowerCase()),
        )
        .sort((a, b) =>
          sortOrder === "newest"
            ? b.created_at.localeCompare(a.created_at)
            : a.created_at.localeCompare(b.created_at),
        ),
    [reviews, search, sortOrder],
  );

  if (isLoading)
    return (
      <div className="app-page">
        <NavBar />
        <main className="space-y-4">
          <Skeleton variant="title" />
          <Skeleton variant="card" />
        </main>
      </div>
    );

  return (
    <div className="app-page">
      <NavBar />
      <PageTransition>
        <main className="mx-auto max-w-7xl">
          <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-[.22em] text-violet-200/80">
                Review archive
              </p>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                History
              </h1>
              <p className="mt-2 text-sm text-secondary">
                Find and revisit your previous analysis runs.
              </p>
            </div>
            {import.meta.env.VITE_USE_MOCK === "true" && (
              <Badge variant="brand">Demo data</Badge>
            )}
          </div>

          {reviews && reviews.length > 0 ? (
            <div className="glass-panel overflow-hidden rounded-[24px]">
              <div className="flex flex-col gap-3 border-b border-white/10 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
                <div className="relative w-full max-w-sm">
                  <Search
                    size={16}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-secondary"
                  />
                  <GlassInput
                    aria-label="Filter review history"
                    placeholder="Filter by review ID or status…"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    className="pl-10"
                  />
                </div>
                <label className="flex min-h-11 items-center gap-2 rounded-xl border border-white/10 bg-white/[.04] px-3 text-xs text-secondary">
                  <ArrowDownWideNarrow size={15} />
                  <span>Sort</span>
                  <select
                    aria-label="Sort history"
                    value={sortOrder}
                    onChange={(event) =>
                      setSortOrder(event.target.value as "newest" | "oldest")
                    }
                    className="bg-transparent font-medium text-text focus:outline-none"
                  >
                    <option value="newest">Newest first</option>
                    <option value="oldest">Oldest first</option>
                  </select>
                </label>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px]">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left p-4 text-secondary uppercase tracking-wider text-sm">
                        Status
                      </th>
                      <th className="text-left p-4 text-secondary uppercase tracking-wider text-sm">
                        Verdict
                      </th>
                      <th className="text-left p-4 text-secondary uppercase tracking-wider text-sm">
                        Findings
                      </th>
                      <th className="text-left p-4 text-secondary uppercase tracking-wider text-sm">
                        Time
                      </th>
                      <th className="text-left p-4 text-secondary uppercase tracking-wider text-sm">
                        Date
                      </th>
                      <th className="text-right p-4 text-secondary uppercase tracking-wider text-sm">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <AnimatePresence initial={false}>
                      {visibleReviews.map((review) => (
                        <motion.tr
                          layout={!reducedMotion}
                          initial={reducedMotion ? false : { opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={
                            reducedMotion
                              ? { opacity: 0 }
                              : { opacity: 0, y: -5 }
                          }
                          key={review.id}
                          className="border-b border-white/[.07] transition-colors hover:bg-white/[.035]"
                        >
                          <td className="p-4">
                            <Badge
                              variant={
                                review.status === "done"
                                  ? "safe"
                                  : review.status === "failed"
                                    ? "critical"
                                    : "brand"
                              }
                            >
                              {review.status}
                            </Badge>
                          </td>
                          <td className="p-4">
                            {review.verdict && (
                              <Badge
                                variant={
                                  review.verdict === "APPROVE"
                                    ? "safe"
                                    : "critical"
                                }
                              >
                                {review.verdict}
                              </Badge>
                            )}
                          </td>
                          <td className="p-4 text-sm">
                            C:{review.finding_counts.critical} H:
                            {review.finding_counts.high} M:
                            {review.finding_counts.medium} L:
                            {review.finding_counts.low}
                          </td>
                          <td className="p-4 text-sm text-secondary flex items-center gap-1">
                            <Clock size={14} />
                            {review.duration_s}s
                          </td>
                          <td className="p-4 text-sm text-secondary">
                            {new Date(review.created_at).toLocaleString()}
                          </td>
                          <td className="p-4 text-right">
                            <button
                              onClick={() =>
                                navigate(`/app/reviews/${review.id}`)
                              }
                              className="text-brand hover:underline mr-4"
                            >
                              View
                            </button>
                            <button
                              onClick={() => {
                                if (window.confirm("Delete this review?"))
                                  deleteReview.mutate(review.id);
                              }}
                              className="text-secondary hover:text-critical"
                            >
                              <Trash2 size={16} />
                            </button>
                          </td>
                        </motion.tr>
                      ))}
                    </AnimatePresence>
                  </tbody>
                </table>
                {visibleReviews.length === 0 && (
                  <div className="p-10 text-center text-sm text-secondary">
                    No reviews match this filter.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="glass-panel flex min-h-72 flex-col items-center justify-center rounded-[26px] p-8 text-center">
              <span className="mb-4 grid h-16 w-16 place-items-center rounded-2xl border border-violet-300/15 bg-violet-400/10 text-violet-200">
                <ShieldCheck size={26} />
              </span>
              <h2 className="text-lg font-semibold">Your archive is ready</h2>
              <p className="mt-2 max-w-sm text-sm leading-relaxed text-secondary">
                Reviews you run will show up here with their status, verdict,
                findings, and duration.
              </p>
              <button
                onClick={() => navigate("/app/new")}
                className="mt-5 rounded-xl bg-violet-500/90 px-4 py-2.5 text-sm font-semibold text-white shadow-[0_12px_35px_rgba(124,58,237,.25)] transition hover:bg-violet-400"
              >
                Start a review
              </button>
            </div>
          )}
        </main>
      </PageTransition>
      {toast && (
        <Toast message={toast} type="error" onClose={() => setToast(null)} />
      )}
    </div>
  );
}
