import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
} from "framer-motion";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  Code2,
  GitBranch,
  Github,
  LockKeyhole,
  Menu,
  Shield,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { landingConfig } from "../config/landing";
import { GlassButton } from "../components/GlassButton";
import { GlassCard } from "../components/GlassCard";
import { Badge } from "../components/Badge";

const AgentScene = lazy(() => import("../components/AgentScene"));
const features = [
  {
    icon: Shield,
    title: "Specialized agents",
    body: "Bug, security, quality, and test coverage reviewers look at the change from focused perspectives.",
  },
  {
    icon: LockKeyhole,
    title: "Semgrep hybrid analysis",
    body: "Deterministic security rules add a static analysis pass beside agent review.",
  },
  {
    icon: Check,
    title: "Evidence-first verification",
    body: "A verifier checks the evidence and filters findings before the summary.",
  },
  {
    icon: Sparkles,
    title: "Local model option",
    body: "Connect an Ollama-backed setup when you want model inference on your own infrastructure.",
  },
  {
    icon: GitBranch,
    title: "CI-ready workflow",
    body: "Use the project’s GitHub Actions integration to run reviews as part of your workflow.",
  },
  {
    icon: Code2,
    title: "Structured findings",
    body: "Review severity, confidence, CWE tags, file locations, evidence, and suggested fixes together.",
  },
];
const tech = [
  "React",
  "TypeScript",
  "Vite",
  "Tailwind CSS",
  "TanStack Query",
  "Three.js",
  "Semgrep",
  "Ollama",
];
const flow = [
  {
    title: "Diff in",
    detail: "Start with a unified patch",
    color: "from-violet-300 to-violet-500",
  },
  {
    title: "Orchestrator",
    detail: "Route work to focused reviewers",
    color: "from-violet-300 to-indigo-400",
  },
  {
    title: "Specialists + Semgrep",
    detail: "Analyze in parallel",
    color: "from-indigo-300 to-cyan-300",
  },
  {
    title: "Verifier",
    detail: "Check evidence and confidence",
    color: "from-cyan-300 to-violet-300",
  },
  {
    title: "Summarizer",
    detail: "Build a concise review",
    color: "from-violet-300 to-fuchsia-300",
  },
  {
    title: "Verdict",
    detail: "See the review outcome",
    color: "from-fuchsia-300 to-violet-300",
  },
];

function ShieldFallback() {
  return (
    <div
      className="relative grid h-[330px] place-items-center overflow-hidden rounded-[32px] sm:h-[430px]"
      aria-label="Static SentinelCode shield illustration"
    >
      <div className="absolute inset-[12%] rounded-full bg-violet-500/20 blur-[70px]" />
      <div className="relative grid h-64 w-64 place-items-center rounded-full bg-[radial-gradient(circle,rgba(139,92,246,.35),rgba(79,70,229,.10)_48%,transparent_70%)]">
        <svg
          viewBox="0 0 180 200"
          className="h-44 w-44 drop-shadow-[0_0_28px_rgba(139,92,246,.55)]"
        >
          <defs>
            <linearGradient id="landing-shield" x1="0" x2="1" y1="0" y2="1">
              <stop stopColor="#c4b5fd" stopOpacity=".85" />
              <stop offset="1" stopColor="#6d28d9" stopOpacity=".35" />
            </linearGradient>
          </defs>
          <path
            d="M90 12 155 38v48c0 47-27 79-65 102C52 165 25 133 25 86V38z"
            fill="url(#landing-shield)"
            stroke="#ddd6fe"
            strokeOpacity=".65"
            strokeWidth="2"
          />
          <path
            d="m61 99 19 19 40-44"
            fill="none"
            stroke="#f5f3ff"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="8"
          />
        </svg>
        <span className="absolute inset-2 rounded-full border border-violet-200/20" />
        <span className="absolute inset-8 rounded-full border border-cyan-200/15" />
      </div>
    </div>
  );
}

function Pipeline() {
  const reducedMotion = useReducedMotion();
  return (
    <section id="how" className="landing-wrap scroll-mt-28 py-20 sm:py-28">
      <div className="mb-10 max-w-2xl">
        <p className="mb-3 text-xs font-bold uppercase tracking-[.22em] text-violet-200">
          How it works
        </p>
        <h2 className="display-heading text-3xl font-semibold sm:text-5xl">
          A careful review,
          <br />
          <span className="text-gradient">from diff to verdict.</span>
        </h2>
        <p className="mt-5 max-w-xl leading-relaxed text-secondary">
          Focused analysis runs in parallel, then findings pass through
          verification before a clear summary.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        {flow.map((step, index) => (
          <motion.div
            key={step.title}
            initial={reducedMotion ? false : { opacity: 0, y: 18 }}
            whileInView={reducedMotion ? undefined : { opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.45, delay: index * 0.07 }}
            className="relative"
          >
            <GlassCard className="relative h-full min-h-40 overflow-hidden p-5">
              <div
                className={`mb-7 h-1 w-14 rounded-full bg-gradient-to-r ${step.color}`}
              />
              <span
                aria-hidden="true"
                className="absolute right-4 top-5 h-1.5 w-1.5 rounded-full bg-violet-200/60"
              />
              <h3 className="text-sm font-semibold">{step.title}</h3>
              <p className="mt-2 text-xs leading-relaxed text-secondary">
                {step.detail}
              </p>
              {index < flow.length - 1 && (
                <span className="pipeline-track absolute -right-3 top-[30px] z-10 hidden h-px w-6 xl:block" />
              )}
            </GlassCard>
            {!reducedMotion && (
              <span
                aria-hidden="true"
                className="pointer-events-none absolute left-0 top-[30px] hidden h-1 w-1 animate-ping rounded-full bg-violet-200 xl:block"
                style={{ animationDelay: `${index * 0.35}s` }}
              />
            )}
          </motion.div>
        ))}
      </div>
      <div className="mt-6 flex items-center justify-center gap-2 text-xs text-secondary">
        <ArrowDown size={14} className="text-violet-200" /> Specialist agents
        and Semgrep run in parallel
      </div>
    </section>
  );
}

function FeatureTile({
  feature,
  index,
}: {
  feature: (typeof features)[number];
  index: number;
}) {
  const Icon = feature.icon;
  const reducedMotion = useReducedMotion();
  return (
    <motion.div
      initial={reducedMotion ? false : { opacity: 0, y: 16 }}
      whileInView={reducedMotion ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{
        duration: reducedMotion ? 0 : 0.45,
        delay: reducedMotion ? 0 : (index % 3) * 0.08,
      }}
      onMouseMove={(event) => {
        if (reducedMotion) return;
        const bounds = event.currentTarget.getBoundingClientRect();
        const x = (event.clientX - bounds.left) / bounds.width;
        const y = (event.clientY - bounds.top) / bounds.height;
        event.currentTarget.style.setProperty(
          "--tilt-x",
          `${(x - 0.5) * 5}deg`,
        );
        event.currentTarget.style.setProperty(
          "--tilt-y",
          `${(0.5 - y) * 5}deg`,
        );
        event.currentTarget.style.setProperty("--glare-x", `${x * 100}%`);
        event.currentTarget.style.setProperty("--glare-y", `${y * 100}%`);
      }}
      onMouseLeave={(event) => {
        if (reducedMotion) return;
        event.currentTarget.style.setProperty("--tilt-x", "0deg");
        event.currentTarget.style.setProperty("--tilt-y", "0deg");
      }}
      className="feature-tilt relative min-h-52 overflow-hidden rounded-[24px] border border-white/10 bg-white/[.045] p-6 shadow-[inset_0_1px_0_rgba(255,255,255,.12)] transition-transform duration-300 hover:border-violet-200/25 hover:shadow-[0_20px_55px_rgba(4,2,18,.4),0_0_28px_rgba(139,92,246,.10)]"
      style={{
        transform: reducedMotion
          ? "none"
          : "perspective(1200px) rotateX(var(--tilt-y,0deg)) rotateY(var(--tilt-x,0deg))",
      }}
    >
      <span className="feature-glare" />
      <span className="relative z-[1] mb-8 grid h-11 w-11 place-items-center rounded-2xl border border-violet-200/15 bg-gradient-to-br from-violet-300/15 to-indigo-400/5 text-violet-200">
        <Icon size={20} />
      </span>
      <h3 className="relative z-[1] text-base font-semibold">
        {feature.title}
      </h3>
      <p className="relative z-[1] mt-2 text-sm leading-relaxed text-secondary">
        {feature.body}
      </p>
    </motion.div>
  );
}

function ProductPreview() {
  const reducedMotion = useReducedMotion();
  const previewRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: previewRef,
    offset: ["start end", "end start"],
  });
  const parallaxY = useTransform(scrollYProgress, [0, 1], [12, -12]);
  return (
    <section
      className="landing-wrap py-20 sm:py-28"
      aria-labelledby="preview-title"
    >
      <div className="grid items-center gap-12 lg:grid-cols-[.8fr_1.2fr]">
        <div>
          <p className="mb-3 text-xs font-bold uppercase tracking-[.22em] text-violet-200">
            Inside the workspace
          </p>
          <h2
            id="preview-title"
            className="display-heading text-3xl font-semibold sm:text-5xl"
          >
            Clarity at every
            <br />
            <span className="text-gradient">stage of review.</span>
          </h2>
          <p className="mt-5 leading-relaxed text-secondary">
            Follow the live agent pipeline, inspect evidence, and compare the
            final findings with the original diff—all in one focused workspace.
          </p>
          <Link to="/app" className="mt-7 inline-flex">
            <GlassButton tone="neutral">
              Explore the dashboard <ArrowRight size={15} />
            </GlassButton>
          </Link>
        </div>
        <motion.div
          ref={previewRef}
          initial={reducedMotion ? false : { opacity: 0, y: 28, rotateX: 3 }}
          whileInView={
            reducedMotion ? undefined : { opacity: 1, y: 0, rotateX: 0 }
          }
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: reducedMotion ? 0 : 0.7 }}
          style={{ perspective: 1200, y: reducedMotion ? 0 : parallaxY }}
        >
          <div className="glass-panel overflow-hidden rounded-[26px] shadow-[0_40px_100px_rgba(0,0,0,.45),0_0_60px_rgba(139,92,246,.12)]">
            <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-white/30" />
              <span className="h-2.5 w-2.5 rounded-full bg-white/20" />
              <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
              <div className="ml-3 flex-1 rounded-lg border border-white/[.07] bg-black/20 px-3 py-1 text-[10px] text-secondary">
                sentinelcode / review
              </div>
              <Badge variant="brand">Demo data</Badge>
            </div>
            <div className="grid gap-4 p-4 sm:grid-cols-[.7fr_1.3fr] sm:p-6">
              <div className="space-y-3">
                <GlassCard className="p-4">
                  <div className="mb-4 flex items-center justify-between">
                    <span className="text-xs font-semibold">
                      Agent pipeline
                    </span>
                    <span className="flex items-center gap-1.5 text-[10px] text-safe">
                      <span className="h-1.5 w-1.5 rounded-full bg-safe" />
                      Complete
                    </span>
                  </div>
                  {[
                    "Orchestrator",
                    "Security",
                    "Semgrep",
                    "Verifier",
                    "Summarizer",
                  ].map((name, index) => (
                    <div
                      key={name}
                      className="flex items-center gap-2 border-t border-white/[.06] py-2 text-[10px] text-secondary"
                    >
                      <span className="grid h-4 w-4 place-items-center rounded-full bg-safe/10 text-safe">
                        <Check size={10} />
                      </span>
                      {name}
                      <span className="ml-auto text-safe">Done</span>
                      {index === 0 && null}
                    </div>
                  ))}
                </GlassCard>
              </div>
              <GlassCard className="code-glass p-4 sm:p-5">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-text">
                    Findings
                  </span>
                  <Badge variant="critical">Critical</Badge>
                </div>
                <article className="rounded-xl border border-white/[.07] bg-white/[.025] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="critical">CRITICAL</Badge>
                    <Badge variant="secondary" confidence="high">
                      HIGH confidence
                    </Badge>
                    <Badge variant="brand">CWE-89</Badge>
                  </div>
                  <h3 className="mt-3 text-sm font-semibold text-text">
                    SQL injection risk
                  </h3>
                  <p className="mt-1 font-mono text-[10px] text-secondary">
                    src/api.py:42
                  </p>
                  <pre className="mt-3 overflow-hidden rounded-lg border border-white/[.06] bg-[#0a0819]/85 p-3 text-[10px] leading-relaxed text-secondary">
                    query = "SELECT * FROM users WHERE id=" + user_id
                  </pre>
                  <p className="mt-3 text-[11px] leading-relaxed text-secondary">
                    Use a parameterized query so user input remains data.
                  </p>
                  <div className="mt-3 flex gap-2">
                    <Badge variant="secondary">Security</Badge>
                    <Badge variant="secondary">Semgrep</Badge>
                  </div>
                </article>
              </GlassCard>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

export default function Landing() {
  const reducedMotion = useReducedMotion();
  const [mobile, setMobile] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(max-width: 720px)").matches,
  );
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 16);
    const onResize = () =>
      setMobile(window.matchMedia("(max-width: 720px)").matches);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
    };
  }, []);
  const showStatic = reducedMotion || mobile;
  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="landing-page min-h-screen overflow-clip text-text">
      <header
        className={`landing-nav glass-panel ${scrolled ? "is-scrolled bg-[#110c27]/80 shadow-[0_16px_50px_rgba(0,0,0,.34)]" : "bg-white/[.045]"}`}
      >
        <nav
          aria-label="Main navigation"
          className="flex min-h-[68px] items-center justify-between gap-4 px-4 sm:px-6"
        >
          <Link
            to="/"
            className="flex shrink-0 items-center gap-2.5"
            onClick={closeMenu}
          >
            <span className="grid h-9 w-9 place-items-center rounded-xl border border-violet-200/20 bg-violet-400/10 text-violet-100">
              <ShieldCheck size={19} />
            </span>
            <span className="text-sm font-bold tracking-wide">
              Sentinel<span className="text-violet-300">Code</span>
            </span>
          </Link>
          <div
            className={`absolute left-0 right-0 top-[calc(100%+10px)] flex-col gap-1 rounded-2xl border border-white/10 bg-[#100b25]/95 p-3 shadow-xl backdrop-blur-2xl md:static md:flex md:flex-row md:items-center md:justify-center md:gap-1 md:border-0 md:bg-transparent md:p-0 md:shadow-none ${menuOpen ? "flex" : "hidden"}`}
          >
            {[
              ["Features", "#features"],
              ["How it works", "#how"],
              ["Tech", "#tech"],
              ...(landingConfig.team.length ? [["Team", "#team"]] : []),
            ].map(([label, href]) => (
              <a
                key={href}
                href={href}
                onClick={closeMenu}
                className="rounded-xl px-3 py-2 text-sm text-secondary transition hover:bg-white/5 hover:text-white"
              >
                {label}
              </a>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/app/new"
              onClick={closeMenu}
              className="hidden sm:inline-flex"
            >
              <GlassButton
                tone="primary"
                className="min-h-10 rounded-full px-4"
              >
                Try a review <ArrowUpRight size={14} />
              </GlassButton>
            </Link>
            <button
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              className="glass-control grid h-10 w-10 place-items-center rounded-xl md:hidden"
              onClick={() => setMenuOpen((value) => !value)}
            >
              {menuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </nav>
      </header>

      <main>
        <section className="landing-wrap grid min-h-[calc(100svh-92px)] items-center gap-8 py-16 lg:grid-cols-[1.02fr_.98fr] lg:py-12">
          <motion.div
            initial={reducedMotion ? false : { opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65 }}
            className="relative z-[1] py-6"
          >
            <Badge variant="brand" className="mb-6 px-3 py-1.5">
              Multi-agent code review
            </Badge>
            <h1 className="display-heading max-w-[800px] text-5xl font-semibold sm:text-6xl lg:text-[76px]">
              Code review,
              <br />
              <span className="text-gradient">with more depth.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-secondary sm:text-lg">
              Focused AI agents and static analysis work together to surface
              evidence-backed bugs, security issues, and quality risks in your
              changes.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/app/new">
                <GlassButton
                  tone="primary"
                  className="min-h-12 rounded-full px-6"
                >
                  Start a review <ArrowRight size={16} />
                </GlassButton>
              </Link>
              <a href="#how">
                <GlassButton
                  tone="neutral"
                  className="min-h-12 rounded-full px-6"
                >
                  See how it works
                </GlassButton>
              </a>
            </div>
            <p className="mt-5 flex items-center gap-2 text-xs text-secondary">
              <LockKeyhole size={14} className="text-safe" />
              Designed for a local-model workflow with Ollama.
            </p>
          </motion.div>
          <div className="relative min-h-[330px] sm:min-h-[430px]">
            <div className="absolute inset-[10%] rounded-full bg-violet-500/10 blur-[100px]" />
            {showStatic ? (
              <ShieldFallback />
            ) : (
              <Suspense fallback={<ShieldFallback />}>
                <AgentScene />
              </Suspense>
            )}
            <div className="absolute bottom-4 left-1/2 hidden -translate-x-1/2 items-center gap-2 rounded-full border border-white/10 bg-[#100b25]/70 px-4 py-2 text-[10px] text-secondary backdrop-blur-xl lg:flex">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-300" />
              Parallel analysis <span className="text-white/20">·</span>{" "}
              Evidence verification
            </div>
          </div>
        </section>

        <section className="landing-wrap pb-7">
          <div className="grid gap-4 rounded-[24px] border border-white/[.08] bg-white/[.025] p-5 text-sm leading-relaxed text-secondary md:grid-cols-[auto_1fr] md:items-center md:gap-5 md:p-6">
            <span className="grid h-11 w-11 place-items-center rounded-2xl border border-violet-200/15 bg-violet-400/10 text-violet-200">
              <Shield size={20} />
            </span>
            <p>
              <strong className="font-semibold text-text">
                Reviews need more than one perspective.
              </strong>{" "}
              SentinelCode coordinates focused analysis for bugs, security, code
              quality, and test coverage, then checks findings before building a
              report. It helps organize review work; engineers remain
              responsible for decisions.
            </p>
          </div>
        </section>

        <Pipeline />

        <section
          id="features"
          className="landing-wrap scroll-mt-28 py-16 sm:py-24"
        >
          <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="mb-3 text-xs font-bold uppercase tracking-[.22em] text-violet-200">
                Why SentinelCode
              </p>
              <h2 className="display-heading text-3xl font-semibold sm:text-5xl">
                Every signal,
                <br />
                <span className="text-gradient">in one review.</span>
              </h2>
            </div>
            <p className="max-w-md text-sm leading-relaxed text-secondary">
              A focused set of tools for understanding a change, tracing
              evidence, and deciding what needs attention.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {features.map((feature, index) => (
              <FeatureTile
                key={feature.title}
                feature={feature}
                index={index}
              />
            ))}
          </div>
        </section>

        <ProductPreview />

        <section
          id="tech"
          className="landing-wrap scroll-mt-28 overflow-hidden py-12"
        >
          <div className="mb-6 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[.22em] text-violet-200">
                Technology
              </p>
              <h2 className="mt-2 text-xl font-semibold">
                Built with a practical, extensible stack
              </h2>
            </div>
            <Code2 className="text-violet-200" size={20} />
          </div>
          <div className="marquee relative -mx-4 overflow-hidden py-3">
            <div className="marquee-track gap-3 px-3">
              {[...tech, ...tech].map((name, index) => (
                <span
                  key={`${name}-${index}`}
                  className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[.035] px-5 py-3 text-xs font-medium text-secondary"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-violet-300/80" />
                  {name}
                </span>
              ))}
            </div>
          </div>
        </section>

        {landingConfig.team.length > 0 && (
          <section id="team" className="landing-wrap scroll-mt-28 py-16">
            <p className="mb-3 text-xs font-bold uppercase tracking-[.22em] text-violet-200">
              Team
            </p>
            <h2 className="mb-8 text-3xl font-semibold">
              People behind the project
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {landingConfig.team.map((member) => (
                <GlassCard key={member.name} className="p-5">
                  <div className="mb-4 grid h-11 w-11 place-items-center rounded-2xl bg-violet-400/10 font-semibold text-violet-100">
                    {member.name.charAt(0)}
                  </div>
                  <h3 className="font-semibold">{member.name}</h3>
                  <p className="mt-1 text-sm text-secondary">{member.role}</p>
                </GlassCard>
              ))}
            </div>
          </section>
        )}

        <section className="landing-wrap py-16 sm:py-24">
          <div className="relative overflow-hidden rounded-[30px] border border-violet-200/15 bg-[linear-gradient(115deg,rgba(139,92,246,.20),rgba(79,70,229,.12)_48%,rgba(34,211,238,.06))] p-7 shadow-[0_30px_90px_rgba(4,2,18,.35),inset_0_1px_0_rgba(255,255,255,.14)] sm:p-12">
            <div className="pointer-events-none absolute -right-12 -top-24 h-64 w-64 rounded-full bg-violet-400/20 blur-[80px]" />
            <div className="relative flex flex-col items-start justify-between gap-7 md:flex-row md:items-center">
              <div>
                <p className="mb-3 text-xs font-bold uppercase tracking-[.22em] text-violet-100">
                  Start with a diff
                </p>
                <h2 className="max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
                  Make your next review easier to reason about.
                </h2>
                <p className="mt-3 max-w-xl text-sm leading-relaxed text-secondary">
                  Bring the change. Get a structured view of findings, evidence,
                  and suggested fixes.
                </p>
              </div>
              <Link to="/app/new" className="shrink-0">
                <GlassButton
                  tone="primary"
                  className="min-h-12 rounded-full px-6"
                >
                  Try a review <ArrowRight size={16} />
                </GlassButton>
              </Link>
            </div>
          </div>
        </section>
      </main>
      <footer className="landing-wrap flex flex-wrap items-center justify-between gap-4 border-t border-white/[.08] py-7 text-xs text-secondary">
        <Link to="/" className="font-semibold text-text">
          Sentinel<span className="text-violet-300">Code</span>
        </Link>
        <span>Multi-agent code review workspace</span>
        <a
          href="https://github.com/dhanalaxmi875/sentinel-multiagent-code-reviewer"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 transition hover:text-text"
        >
          <Github size={15} />
          View project
          <ArrowUpRight size={13} />
        </a>
      </footer>
    </div>
  );
}
