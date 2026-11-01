import type { ButtonHTMLAttributes, ReactNode } from "react";

interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  tone?: "primary" | "neutral" | "quiet";
}

export function GlassButton({
  children,
  tone = "neutral",
  className = "",
  ...props
}: GlassButtonProps) {
  const toneClass =
    tone === "primary"
      ? "border-violet-300/30 bg-violet-500/90 text-white shadow-[0_12px_35px_rgba(124,58,237,.28)] hover:bg-violet-400"
      : tone === "quiet"
        ? "border-transparent bg-transparent text-secondary hover:bg-white/5 hover:text-text"
        : "glass-control text-text";
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold transition-transform duration-300 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-300/80 ${toneClass} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
