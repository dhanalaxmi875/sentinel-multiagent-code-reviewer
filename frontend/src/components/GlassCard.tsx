import type { HTMLAttributes, ReactNode } from "react";

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  hoverable?: boolean;
}

export function GlassCard({
  children,
  hoverable = false,
  className = "",
  ...props
}: GlassCardProps) {
  return (
    <div
      className={`glass-panel rounded-2xl ${hoverable ? "glass-card" : ""} ${className}`}
      data-cursor-glow={className.includes("code-glass") ? undefined : ""}
      {...props}
    >
      {children}
    </div>
  );
}
