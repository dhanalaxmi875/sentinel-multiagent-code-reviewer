import { cva } from "class-variance-authority";
import { motion, useReducedMotion } from "framer-motion";

const tabsVariants = cva(
  "relative flex gap-1 overflow-x-auto border-b border-white/10",
  {
    variants: {
      variant: {
        default: "",
        card: "border-l-2 border-l-transparent",
      },
    },
  },
);

interface Tab {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (id: string) => void;
  variant?: "default" | "card";
}

export function Tabs({
  tabs,
  activeTab,
  onTabChange,
  variant = "default",
}: TabsProps) {
  const reducedMotion = useReducedMotion();
  return (
    <div
      className={tabsVariants({ variant })}
      role="tablist"
      aria-label="Review sections"
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={activeTab === tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`animated-tab relative whitespace-nowrap rounded-t-xl px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === tab.id
              ? "text-brand border-b-2 border-brand"
              : "text-secondary hover:text-text"
          }`}
        >
          {tab.label}
          {activeTab === tab.id && (
            <motion.span
              layoutId="review-tab-indicator"
              className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-violet-300 shadow-[0_0_12px_rgba(167,139,250,.8)]"
              transition={
                reducedMotion
                  ? { duration: 0 }
                  : { type: "spring", stiffness: 450, damping: 35 }
              }
            />
          )}
        </button>
      ))}
    </div>
  );
}
