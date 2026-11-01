import { cva } from 'class-variance-authority';

const cardVariants = cva('rounded-lg border border-border bg-panel p-4', {
  variants: {
    hover: {
      true: 'hover:border-brand transition-colors',
      false: '',
    },
  },
});

interface CardProps {
  children: React.ReactNode;
  hover?: boolean;
  className?: string;
}

export function Card({ children, hover = false, className }: CardProps) {
  return <div className={cardVariants({ hover, className })}>{children}</div>;
}
