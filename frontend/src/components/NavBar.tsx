import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Clock,
  Command,
  FilePlus2,
  Menu,
  Search,
  Settings2,
  ShieldCheck,
  X,
} from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { api } from "../api/client";
import { Badge } from "./Badge";
import { GlassInput } from "./GlassInput";

const navigation = [
  { to: "/app", label: "Dashboard", icon: Activity },
  { to: "/app/new", label: "New review", icon: FilePlus2 },
  { to: "/app/history", label: "History", icon: Clock },
];

export function NavBar() {
  const reducedMotion = useReducedMotion();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const { data: reviews } = useQuery({
    queryKey: ["reviews"],
    queryFn: () => api.getReviews(),
  });
  const close = () => setOpen(false);

  return (
    <>
      <button
        aria-label="Close navigation"
        onClick={close}
        className={`app-overlay ${open ? "is-open" : ""}`}
      />
      <aside
        className={`app-sidebar glass-panel ${open ? "is-open" : ""}`}
        aria-label="Main navigation"
      >
        <Link
          to="/app"
          onClick={close}
          className="mb-9 flex items-center gap-3 px-2"
        >
          <span className="grid h-10 w-10 place-items-center rounded-2xl border border-violet-300/25 bg-gradient-to-br from-violet-400/30 to-indigo-500/10 text-violet-100 shadow-[0_8px_25px_rgba(139,92,246,.22)]">
            <ShieldCheck size={21} />
          </span>
          <span>
            <span className="block text-sm font-bold tracking-wide">
              Sentinel<span className="text-violet-300">Code</span>
            </span>
            <span className="mt-0.5 block text-[10px] uppercase tracking-[.2em] text-secondary">
              Review workspace
            </span>
          </span>
        </Link>
        <div className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[.18em] text-secondary/80">
          Workspace
        </div>
        <nav className="space-y-1" aria-label="Workspace">
          {navigation.map(({ to, label, icon: Icon }) => {
            const active =
              location.pathname === to ||
              (to === "/app" && location.pathname === "/app");
            return (
              <Link
                key={to}
                to={to}
                onClick={close}
                aria-current={active ? "page" : undefined}
                className={`relative flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors ${active ? "text-white" : "text-secondary hover:bg-white/5 hover:text-text"}`}
              >
                {active && (
                  <motion.span
                    layoutId="active-nav-pill"
                    className="absolute inset-0 rounded-xl border border-violet-300/15 bg-gradient-to-r from-violet-400/20 to-indigo-400/10 shadow-[0_0_25px_rgba(139,92,246,.16)]"
                    transition={
                      reducedMotion
                        ? { duration: 0 }
                        : { type: "spring", stiffness: 420, damping: 36 }
                    }
                  />
                )}
                <Icon size={17} className="relative z-[1]" />
                <span className="relative z-[1]">{label}</span>
              </Link>
            );
          })}
        </nav>
        <button
          disabled
          className="mt-1 flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm text-secondary/70"
          title="Settings are not available yet"
        >
          <Settings2 size={17} />
          Settings{" "}
          <span className="ml-auto text-[9px] uppercase tracking-widest">
            Soon
          </span>
        </button>
        <div className="mt-9 flex items-center justify-between px-3">
          <span className="text-[10px] font-bold uppercase tracking-[.18em] text-secondary/80">
            Recent reviews
          </span>
          <span className="grid h-5 min-w-5 place-items-center rounded-full bg-white/5 px-1 text-[10px] text-secondary">
            {reviews?.length ?? 0}
          </span>
        </div>
        <div className="recent-list mt-3 space-y-1">
          {reviews?.slice(0, 4).map((review) => (
            <Link
              key={review.id}
              to={`/app/reviews/${review.id}`}
              onClick={close}
              className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs text-secondary transition hover:bg-white/5 hover:text-text"
            >
              <span
                className={`h-1.5 w-1.5 shrink-0 rounded-full ${review.status === "done" ? "bg-safe" : review.status === "failed" ? "bg-critical" : "animate-pulse bg-violet-300"}`}
              />
              <span className="min-w-0 flex-1 truncate">
                Review {review.id.slice(0, 8)}
              </span>
            </Link>
          ))}
          {reviews?.length === 0 && (
            <p className="px-3 py-2 text-xs text-secondary">
              Reviews will appear here.
            </p>
          )}
        </div>
        <div className="mt-auto rounded-2xl border border-white/10 bg-white/[.035] p-3">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold">
            <Command size={14} className="text-violet-300" />
            Review console
          </div>
          <p className="text-[11px] leading-relaxed text-secondary">
            Focused agents, verified findings, and clear evidence.
          </p>
        </div>
      </aside>
      <header className="app-topbar glass-panel">
        <button
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          className="app-mobile-menu glass-control h-10 w-10 items-center justify-center rounded-xl"
        >
          {open ? <X size={18} /> : <Menu size={18} />}
        </button>
        <div className="app-search relative w-full max-w-md">
          <Search
            size={16}
            className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-secondary"
          />
          <GlassInput
            aria-label="Search reviews"
            placeholder="Search reviews…"
            className="pl-10"
          />
        </div>
        {import.meta.env.VITE_USE_MOCK === "true" && (
          <Badge variant="brand" className="hidden sm:inline-flex">
            Demo data
          </Badge>
        )}
        <button
          aria-label="User profile placeholder"
          className="flex shrink-0 items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1 pr-3 transition hover:border-violet-300/30"
        >
          <span className="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-violet-400/70 to-indigo-500/60 text-xs font-bold text-white">
            S
          </span>
          <span className="hidden text-xs font-medium sm:block">Workspace</span>
        </button>
      </header>
    </>
  );
}
