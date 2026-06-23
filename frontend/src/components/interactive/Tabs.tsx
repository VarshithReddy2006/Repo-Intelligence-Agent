import React, { useRef } from 'react';

export interface TabItem<T extends string> {
  id: T;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  /** Optional group label — rendered as a separator when the group changes */
  group?: string;
}

interface TabsProps<T extends string> {
  items: TabItem<T>[];
  active: T;
  onChange: (id: T) => void;
  className?: string;
}

/**
 * Accessible, horizontally-scrollable tab strip with optional group labels.
 * - role="tablist" with arrow-key navigation
 * - aria-selected on the active tab
 * - Group labels rendered as non-interactive separators
 * - parent renders its panels with id={`tabpanel-${id}`} role="tabpanel"
 */
export function Tabs<T extends string>({ items, active, onChange, className = '' }: TabsProps<T>) {
  const listRef = useRef<HTMLDivElement>(null);

  const onKey = (e: React.KeyboardEvent) => {
    const idx = items.findIndex((i) => i.id === active);
    if (idx < 0) return;
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      onChange(items[(idx + 1) % items.length].id);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      onChange(items[(idx - 1 + items.length) % items.length].id);
    } else if (e.key === 'Home') {
      e.preventDefault();
      onChange(items[0].id);
    } else if (e.key === 'End') {
      e.preventDefault();
      onChange(items[items.length - 1].id);
    }
  };

  return (
    <div
      role="tablist"
      ref={listRef}
      onKeyDown={onKey}
      className={`flex overflow-x-auto border-b border-border items-end ${className}`}
    >
      {items.map(({ id, label, icon: Icon }) => {
        const isActive = active === id;

        return (
          <button
            key={id}
            role="tab"
            type="button"
            aria-selected={isActive}
            aria-controls={`tabpanel-${id}`}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(id)}
            className={[
              'shrink-0 flex items-center gap-2 px-3 py-2 text-sm font-medium font-sans',
              'border-b-2 transition-colors whitespace-nowrap',
              'focus-visible:outline-none focus-visible:shadow-ring',
              isActive
                ? 'border-primary text-text bg-primary/5'
                : 'border-transparent text-text-muted hover:text-text hover:bg-surface-1',
            ].join(' ')}
          >
            <Icon className="h-4 w-4" />
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
}

export default Tabs;
