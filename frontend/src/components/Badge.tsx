import { cva, type VariantProps } from 'class-variance-authority';

const badgeVariants = cva(
  'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wide',
  {
    variants: {
      variant: {
        critical: 'bg-critical/10 text-critical border border-critical/30',
        high: 'bg-high/10 text-high border border-high/30',
        medium: 'bg-medium/10 text-medium border border-medium/30',
        low: 'bg-low/10 text-low border border-low/30',
        safe: 'bg-safe/10 text-safe border border-safe/30',
        brand: 'bg-brand/10 text-brand border border-brand/30',
        secondary: 'bg-secondary/10 text-secondary border border-secondary/30',
        CRITICAL: 'bg-critical/10 text-critical border border-critical/30',
        HIGH: 'bg-high/10 text-high border border-high/30',
        MEDIUM: 'bg-medium/10 text-medium border border-medium/30',
        LOW: 'bg-low/10 text-low border border-low/30',
      },
      confidence: {
        high: 'font-bold',
        medium: 'border-2',
        low: 'border-dashed',
        HIGH: 'font-bold',
        MEDIUM: 'border-2',
        LOW: 'border-dashed',
      },
    },
    defaultVariants: {
      variant: 'secondary',
    },
  }
);

interface BadgeProps extends VariantProps<typeof badgeVariants> {
  children: React.ReactNode;
  confidence?: 'high' | 'medium' | 'low';
  className?: string;
}

export function Badge({ children, variant, confidence, className }: BadgeProps) {
  return (
    <span className={badgeVariants({ variant, confidence, className })}>
      {children}
    </span>
  );
}
