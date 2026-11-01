import type { InputHTMLAttributes } from "react";

export function GlassInput({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`glass-control min-h-11 w-full rounded-xl px-4 py-2.5 text-sm text-text placeholder:text-secondary/80 focus:border-violet-300/60 focus:outline-none focus:ring-2 focus:ring-violet-400/20 ${className}`}
      {...props}
    />
  );
}
