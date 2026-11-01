import { cva } from "class-variance-authority";

const skeletonVariants = cva(
  "skeleton-glass rounded-2xl border border-white/[.08]",
  {
    variants: {
      variant: {
        default: "h-4 w-full",
        text: "h-4 w-3/4",
        title: "h-6 w-1/2",
        card: "h-24 w-full",
        circle: "h-12 w-12 rounded-full",
        button: "h-10 w-24",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

interface SkeletonProps {
  className?: string;
  variant?: "default" | "text" | "title" | "card" | "circle" | "button";
}

export function Skeleton({ className, variant = "default" }: SkeletonProps) {
  return <div className={skeletonVariants({ variant, className })} />;
}
