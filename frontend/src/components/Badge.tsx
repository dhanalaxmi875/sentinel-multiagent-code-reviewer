import { cva, type VariantProps } from "class-variance-authority";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[.12em] backdrop-blur-lg",
  {
    variants: {
      variant: {
        critical: "bg-critical/10 text-critical border-critical/50",
        high: "bg-high/10 text-high border-high/50",
        medium: "bg-medium/10 text-medium border-medium/50",
        low: "bg-low/10 text-low border-low/50",
        safe: "bg-safe/10 text-safe border-safe/50",
        brand: "bg-brand/15 text-violet-200 border-violet-300/30",
        secondary: "bg-white/5 text-secondary border-white/10",
        CRITICAL: "bg-critical/10 text-critical border-critical/50",
        HIGH: "bg-high/10 text-high border-high/50",
        MEDIUM: "bg-medium/10 text-medium border-medium/50",
        LOW: "bg-low/10 text-low border-low/50",
      },
      confidence: {
        high: "border-high bg-high/20 text-high",
        medium: "border-2 border-medium/70 bg-transparent text-medium",
        low: "border-dashed bg-transparent text-secondary",
        HIGH: "border-high bg-high/20 text-high",
        MEDIUM: "border-2 border-medium/70 bg-transparent text-medium",
        LOW: "border-dashed bg-transparent text-secondary",
      },
    },
    defaultVariants: {
      variant: "secondary",
    },
  },
);

interface BadgeProps extends VariantProps<typeof badgeVariants> {
  children: React.ReactNode;
  confidence?: "high" | "medium" | "low";
  className?: string;
}

export function Badge({
  children,
  variant,
  confidence,
  className,
}: BadgeProps) {
  return (
    <span className={badgeVariants({ variant, confidence, className })}>
      {children}
    </span>
  );
}
