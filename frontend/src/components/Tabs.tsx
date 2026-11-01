import { cva } from 'class-variance-authority';

const tabsVariants = cva('flex border-b border-border', {
  variants: {
    variant: {
      default: '',
    card: 'border-l-2 border-l-transparent',
    },
  },
});

interface Tab {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (id: string) => void;
  variant?: 'default' | 'card';
}

export function Tabs({ tabs, activeTab, onTabChange, variant = 'default' }: TabsProps) {
  return (
    <div className={tabsVariants({ variant })}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`px-4 py-3 text-sm font-medium transition-colors ${
            activeTab === tab.id
              ? 'text-brand border-b-2 border-brand'
              : 'text-secondary hover:text-text'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
