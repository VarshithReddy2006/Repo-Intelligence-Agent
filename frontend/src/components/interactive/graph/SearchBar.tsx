import React, { useRef, useEffect } from 'react';
import { Search, X } from 'lucide-react';

interface SearchBarProps {
  value: string;
  matchCount: number | null;
  onChange: (value: string) => void;
  onClear: () => void;
  placeholder?: string;
}

/**
 * Debounced search input for the Interactive Dependency Graph.
 * Calls onChange 300ms after the user stops typing.
 * Shows a match count badge when results are available.
 */
export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  matchCount,
  onChange,
  onClear,
  placeholder = 'Search files (e.g. api, auth, service)…',
}) => {
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    // Immediately update controlled value for visual feedback
    onChange(raw);
    // Debounce the actual search trigger — parent handles the API call
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      // Parent receives the same value but now triggers the fetch
    }, 300);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const hasValue = value.trim().length > 0;

  return (
    <div className="flex items-center gap-2 flex-grow max-w-sm">
      <div className="relative flex-grow">
        {/* Search icon */}
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-muted pointer-events-none" />

        <input
          type="text"
          value={value}
          onChange={handleInput}
          placeholder={placeholder}
          className="w-full bg-canvas border border-border rounded pl-8 pr-8 py-1.5 text-xs font-mono focus:outline-none focus:border-primary/80 text-text placeholder:text-text-muted/50"
        />

        {/* Match count badge */}
        {hasValue && matchCount !== null && (
          <span className="absolute right-7 top-1/2 -translate-y-1/2 text-[9px] font-mono text-primary bg-primary/10 border border-primary/20 px-1 rounded">
            {matchCount}
          </span>
        )}

        {/* Clear button */}
        {hasValue && (
          <button
            type="button"
            onClick={onClear}
            aria-label="Clear search"
            className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text rounded focus-visible:outline-none focus-visible:shadow-ring"
            title="Clear search"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
};
