import { useEffect, useState } from "react";
import { animate, motion, useReducedMotion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowUpRight,
  CheckCircle,
  Clock3,
  Shield,
  Activity,
  AlertTriangle,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { NavBar } from "../components/NavBar";
import { Badge } from "../components/Badge";
import { Skeleton } from "../components/Skeleton";
import { GlassCard } from "../components/GlassCard";
import { GlassButton } from "../components/GlassButton";
import { PageTransition } from "../components/PageTransition";
import type { ReviewSummary } from "../api/types";

function CountUp({ value, suffix = "" }: { value: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const reducedMotion = useReducedMotion();
  useEffect(() => {
    if (reducedMotion) {
      setCount(value);
      return;
    }
    const controls = animate(0, value, {
      duration: 0.75,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (latest) => setCount(Math.round(latest)),
    });
    return () => controls.stop();
  }, [reducedMotion, value]);
  return (
    <motion.span>
      {count.toLocaleString()}
      {suffix}
    </motion.span>
  );
}

function Sparkline({
  reviews,
  metric,
}: {
  reviews: ReviewSummary[];
  metric: (review: ReviewSummary) => number;
}) {
  const values = [...reviews].reverse().map(metric);
  if (values.length < 2) return null;
  const max = Math.max(...values, 1);
  const points = values
    .map(
      (value, index) =>
        `${(index / (values.length - 1)) * 100},${34 - (value / max) * 30}`,
    )
    .join(" ");
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 100 36"
      className="h-9 w-24 overflow-visible"
    >
      <polyline
        points={points}
        fill="none"
        stroke="rgba(196,181,253,.9)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle
        cx="100"
        cy={34 - ((values[values.length - 1] ?? 0) / max) * 30}
        r="2.5"
        fill="#c4b5fd"
      />
    </svg>
  );
}

const severities = [
  { key: "critical", label: "Critical", color: "#F85149" },
  { key: "high", label: "High", color: "#FF8C42" },
  { key: "medium", label: "Medium", color: "#E3B341" },
  { key: "low", label: "Low", color: "#58A6FF" },
] as const;

export default function Dashboard() {
  const reducedMotion = useReducedMotion();
  const {
    data: stats,
    isLoading,
    isError,
  } = useQuery({ queryKey: ["stats"], queryFn: () => api.getStats() });
  const { data: reviews } = useQuery({
    queryKey: ["reviews"],
    queryFn: () => api.getReviews(),
  });
  const recent = reviews ?? [];

  if (isLoading)
    return (
      <div className="app-page">
        <NavBar />
        <main
          className="mx-auto max-w-[1500px] space-y-5"
          aria-label="Loading dashboard"
        >
          <Skeleton variant="title" />
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }, (_, index) => (
              <Skeleton key={index} variant="card" className="h-36" />
            ))}
          </div>
          <div className="grid gap-5 lg:grid-cols-3">
            <Skeleton variant="card" className="h-72 lg:col-span-2" />
            <Skeleton variant="card" className="h-72" />
          </div>
        </main>
      </div>
    );

  const counts = stats?.finding_counts;
  const totalFindings = counts
    ? counts.critical + counts.high + counts.medium + counts.low
    : 0;
  const donut = counts
    ? `conic-gradient(${severities
        .map((severity, index) => {
          const before = severities
            .slice(0, index)
            .reduce((sum, item) => sum + counts[item.key], 0);
          const start = totalFindings ? (before / totalFindings) * 100 : 0;
          const end = totalFindings
            ? ((before + counts[severity.key]) / totalFindings) * 100
            : 0;
          return `${severity.color} ${start}% ${end}%`;
        })
        .join(", ")})`
    : undefined;
  const runningCount = recent.filter(
    (review) => review.status === "queued" || review.status === "running",
  ).length;
  const kpis = [
    {
      label: "Reviews run",
      value: stats?.total_reviews,
      suffix: "",
      icon: Shield,
      color: "text-violet-200",
      metric: () => 1,
    },
    {
      label: "Critical findings",
      value: counts?.critical,
      suffix: "",
      icon: AlertTriangle,
      color: "text-critical",
      metric: (review) => review.finding_counts.critical,
    },
    {
      label: "High findings",
      value: counts?.high,
      suffix: "",
      icon: AlertTriangle,
      color: "text-high",
      metric: (review) => review.finding_counts.high,
    },
    {
      label: "Average review time",
      value: stats?.avg_review_time_s,
      suffix: stats ? "s" : "",
      icon: Clock3,
      color: "text-cyan-200",
      metric: (review) => review.duration_s ?? 0,
    },
  ];

  return (
    <div className="app-page">
      <NavBar />
      <main className="mx-auto max-w-[1500px]">
        <header className="mb-7 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[.22em] text-violet-200/80">
              Your workspace
            </p>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Dashboard
            </h1>
            <p className="mt-2 text-sm text-secondary">
              A clear view of your recent review activity.
            </p>
          </div>
          <div className="flex items-center gap-3">
            {import.meta.env.VITE_USE_MOCK === "true" && (
              <Badge variant="brand">Demo data</Badge>
            )}
            <Link to="/app/new">
              <GlassButton tone="primary">
                New review <ArrowUpRight size={16} />
              </GlassButton>
            </Link>
          </div>
        </header>
        {isError && (
          <p
            role="alert"
            className="mb-5 rounded-xl border border-critical/30 bg-critical/10 p-4 text-sm text-critical"
          >
            Could not load your workspace statistics.
          </p>
        )}

        <PageTransition>
          <section
            aria-label="Review KPIs"
            className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
          >
            {kpis.map(
              ({ label, value, suffix, icon: Icon, color, metric }, index) => (
                <motion.div
                  key={label}
                  initial={reducedMotion ? false : { opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: reducedMotion ? 0 : index * 0.06 }}
                >
                  <GlassCard hoverable className="h-full p-5 sm:p-6">
                    <div className="mb-5 flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-[.14em] text-secondary">
                        {label}
                      </span>
                      <span
                        className={`grid h-9 w-9 place-items-center rounded-xl border border-white/10 bg-white/5 ${color}`}
                      >
                        <Icon size={17} />
                      </span>
                    </div>
                    <div className="flex items-end justify-between gap-2">
                      <div
                        className={`text-3xl font-bold tracking-tight ${color}`}
                      >
                        {value === undefined ? (
                          "—"
                        ) : (
                          <>
                            <CountUp value={value} />
                            {suffix}
                          </>
                        )}
                      </div>
                      <Sparkline reviews={recent.slice(0, 7)} metric={metric} />
                    </div>
                  </GlassCard>
                </motion.div>
              ),
            )}
          </section>
        </PageTransition>

        <PageTransition>
          <section className="mt-5 grid gap-5 xl:grid-cols-12">
            <GlassCard className="p-5 sm:p-7 xl:col-span-4">
              <div className="mb-6 flex items-start justify-between">
                <div>
                  <h2 className="font-semibold">Findings by severity</h2>
                  <p className="mt-1 text-xs text-secondary">
                    Kept findings across your reviews
                  </p>
                </div>
                <Activity size={18} className="text-violet-200" />
              </div>
              {totalFindings > 0 && donut ? (
                <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-center">
                  <motion.div
                    initial={
                      reducedMotion ? false : { scale: 0.82, opacity: 0.4 }
                    }
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.7, ease: "easeOut" }}
                    className="relative grid h-40 w-40 shrink-0 place-items-center rounded-full"
                    style={{ background: donut }}
                  >
                    <div className="grid h-[116px] w-[116px] place-items-center rounded-full border border-white/10 bg-[#100b25] text-center shadow-inner">
                      <div>
                        <div className="text-3xl font-bold">
                          {totalFindings}
                        </div>
                        <div className="text-[10px] uppercase tracking-[.14em] text-secondary">
                          Findings
                        </div>
                      </div>
                    </div>
                  </motion.div>
                  <ul className="w-full max-w-48 space-y-3">
                    {severities.map((item) => (
                      <li
                        key={item.key}
                        className="flex items-center justify-between gap-5 text-sm"
                      >
                        <span className="flex items-center gap-2 text-secondary">
                          <span
                            className="h-2.5 w-2.5 rounded-full"
                            style={{ backgroundColor: item.color }}
                          />
                          {item.label}
                        </span>
                        <span className="font-semibold text-text">
                          {counts?.[item.key] ?? 0}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="flex min-h-48 flex-col items-center justify-center text-center">
                  <div className="mb-4 grid h-16 w-16 place-items-center rounded-2xl border border-violet-300/15 bg-violet-400/10">
                    <ShieldCheck className="text-violet-200" />
                  </div>
                  <p className="font-medium">No findings to chart yet</p>
                  <p className="mt-1 max-w-xs text-sm text-secondary">
                    Run a review to see severity distribution here.
                  </p>
                  <Link
                    className="mt-4 text-sm font-semibold text-violet-200 hover:text-white"
                    to="/app/new"
                  >
                    Start a review →
                  </Link>
                </div>
              )}
            </GlassCard>

            <GlassCard className="p-5 sm:p-7 xl:col-span-4">
              <div className="mb-6 flex items-start justify-between">
                <div>
                  <h2 className="font-semibold">Verdict split</h2>
                  <p className="mt-1 text-xs text-secondary">
                    Based on completed reviews
                  </p>
                </div>
                <CheckCircle size={18} className="text-safe" />
              </div>
              {stats ? (
                <>
                  <div className="mb-3 flex justify-between text-sm">
                    <span className="text-secondary">Approved</span>
                    <span className="font-semibold text-safe">
                      {stats.verdict_split.approve}
                    </span>
                  </div>
                  <div className="mb-6 flex h-2 overflow-hidden rounded-full bg-white/5">
                    <motion.div
                      initial={reducedMotion ? false : { scaleX: 0 }}
                      animate={{
                        scaleX:
                          stats.verdict_split.approve +
                          stats.verdict_split.request_changes
                            ? stats.verdict_split.approve /
                              (stats.verdict_split.approve +
                                stats.verdict_split.request_changes)
                            : 0,
                      }}
                      style={{ transformOrigin: "left" }}
                      transition={{ duration: reducedMotion ? 0 : 0.8 }}
                      className="rounded-full bg-safe"
                    />
                    <motion.div
                      initial={reducedMotion ? false : { scaleX: 0 }}
                      animate={{
                        scaleX:
                          stats.verdict_split.approve +
                          stats.verdict_split.request_changes
                            ? stats.verdict_split.request_changes /
                              (stats.verdict_split.approve +
                                stats.verdict_split.request_changes)
                            : 0,
                      }}
                      style={{ transformOrigin: "left" }}
                      transition={{ duration: reducedMotion ? 0 : 0.8 }}
                      className="rounded-full bg-critical"
                    />
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-secondary">Changes requested</span>
                    <span className="font-semibold text-critical">
                      {stats.verdict_split.request_changes}
                    </span>
                  </div>
                </>
              ) : (
                <p className="text-sm text-secondary">
                  Verdict data is unavailable.
                </p>
              )}
            </GlassCard>

            <GlassCard className="p-5 sm:p-7 xl:col-span-4">
              <div className="mb-5 flex items-start justify-between">
                <div>
                  <h2 className="font-semibold">Pipeline status</h2>
                  <p className="mt-1 text-xs text-secondary">
                    Your active reviews
                  </p>
                </div>
                <Activity size={18} className="text-cyan-200" />
              </div>
              <div className="flex items-center gap-4">
                <div
                  className={`grid h-14 w-14 place-items-center rounded-2xl border ${runningCount ? "border-violet-300/25 bg-violet-400/10 text-violet-200" : "border-white/10 bg-white/5 text-secondary"}`}
                >
                  <span
                    className={`h-3 w-3 rounded-full ${runningCount ? "animate-pulse bg-violet-300 shadow-[0_0_16px_#a78bfa]" : "bg-secondary/60"}`}
                  />
                </div>
                <div>
                  <p className="text-2xl font-bold">{runningCount}</p>
                  <p className="text-xs text-secondary">queued or running</p>
                </div>
              </div>
              <div className="mt-5 border-t border-white/10 pt-4 text-xs text-secondary">
                {recent.length} reviews in your history
              </div>
            </GlassCard>
          </section>
        </PageTransition>

        <PageTransition>
          <section className="mt-5 grid gap-5 xl:grid-cols-12">
            <GlassCard className="overflow-hidden xl:col-span-8">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-5 sm:px-7">
                <div>
                  <h2 className="font-semibold">Recent reviews</h2>
                  <p className="mt-1 text-xs text-secondary">
                    Your latest analysis runs
                  </p>
                </div>
                <Link
                  to="/app/history"
                  className="text-sm font-semibold text-violet-200 hover:text-white"
                >
                  View history{" "}
                  <ArrowUpRight className="ml-1 inline" size={14} />
                </Link>
              </div>
              {recent.length ? (
                <div className="divide-y divide-white/[.07]">
                  {recent.slice(0, 5).map((review) => (
                    <Link
                      key={review.id}
                      to={`/app/reviews/${review.id}`}
                      className="group flex flex-wrap items-center justify-between gap-3 px-5 py-4 transition-colors hover:bg-white/[.035] sm:px-7"
                    >
                      <div className="flex min-w-0 items-center gap-3">
                        <span
                          className={`h-2 w-2 shrink-0 rounded-full ${review.status === "done" ? "bg-safe" : review.status === "failed" ? "bg-critical" : "animate-pulse bg-violet-300"}`}
                        />
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-medium group-hover:text-violet-100">
                            Review{" "}
                            <span className="font-mono text-secondary">
                              {review.id.slice(0, 8)}
                            </span>
                          </span>
                          <span className="mt-1 block text-xs text-secondary">
                            {new Date(review.created_at).toLocaleString()}
                          </span>
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="hidden text-xs text-secondary sm:block">
                          C {review.finding_counts.critical} · H{" "}
                          {review.finding_counts.high} · M{" "}
                          {review.finding_counts.medium} · L{" "}
                          {review.finding_counts.low}
                        </span>
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
                        <ArrowUpRight
                          size={15}
                          className="text-secondary transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-violet-200"
                        />
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="p-7 text-center">
                  <p className="font-medium">Your review history starts here</p>
                  <p className="mt-1 text-sm text-secondary">
                    Submit a diff to see its progress and findings in this
                    workspace.
                  </p>
                  <Link to="/app/new" className="mt-4 inline-flex">
                    <GlassButton tone="primary">
                      Start your first review <ArrowUpRight size={15} />
                    </GlassButton>
                  </Link>
                </div>
              )}
            </GlassCard>
            <GlassCard className="p-5 sm:p-7 xl:col-span-4">
              <h2 className="font-semibold">Your activity</h2>
              <p className="mt-1 text-xs text-secondary">
                Latest workspace events
              </p>
              {recent.length ? (
                <ol className="mt-5 space-y-4">
                  {recent.slice(0, 4).map((review) => (
                    <li key={review.id} className="flex gap-3">
                      <span
                        className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${review.status === "failed" ? "bg-critical" : review.status === "done" ? "bg-safe" : "bg-violet-300"}`}
                      />
                      <div className="min-w-0">
                        <Link
                          to={`/app/reviews/${review.id}`}
                          className="text-sm font-medium hover:text-violet-200"
                        >
                          Review {review.id.slice(0, 8)}
                        </Link>
                        <p className="mt-1 text-xs text-secondary">
                          {review.status} ·{" "}
                          {new Date(review.created_at).toLocaleString()}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="mt-5 text-sm text-secondary">
                  New activity appears when you run a review.
                </p>
              )}
            </GlassCard>
          </section>
        </PageTransition>
      </main>
    </div>
  );
}
