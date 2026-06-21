import React from 'react';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Tailwind sizing className(s) — e.g. "h-4 w-32" */
  size?: string;
  rounded?: 'sm' | 'md' | 'lg' | 'full';
}

const radiusMap = {
  sm: 'rounded-sm', md: 'rounded-md', lg: 'rounded-lg', full: 'rounded-full',
} as const;

/** Base shimmer block. */
export const Skeleton: React.FC<SkeletonProps> = ({
  size = 'h-4 w-full', rounded = 'md', className = '', ...rest
}) => (
  <div
    className={`skeleton ${size} ${radiusMap[rounded]} ${className}`}
    aria-hidden="true"
    {...rest}
  />
);

/** Quick presets — compose with the base for common shapes. */

export const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`card p-5 space-y-3 ${className}`} aria-hidden="true">
    <Skeleton size="h-3 w-24" />
    <Skeleton size="h-8 w-1/2" />
    <Skeleton size="h-3 w-3/4" />
  </div>
);

export const SkeletonRow: React.FC<{ cols?: number }> = ({ cols = 4 }) => (
  <div className="flex items-center gap-3 py-3 border-b border-border/40" aria-hidden="true">
    {Array.from({ length: cols }, (_, i) => (
      <Skeleton key={i} size={i === 0 ? 'h-3 flex-grow' : 'h-3 w-20'} />
    ))}
  </div>
);

export const SkeletonGauge: React.FC = () => (
  <div className="card p-5 flex flex-col items-center gap-3" aria-hidden="true">
    <Skeleton size="h-3 w-32" />
    <Skeleton size="h-36 w-36" rounded="full" />
    <Skeleton size="h-3 w-24" />
  </div>
);

/** Status wrapper — provides an SR-only "Loading…" message. */
export const SkeletonGroup: React.FC<React.PropsWithChildren<{ label?: string }>> = ({
  children, label = 'Loading content',
}) => (
  <div role="status" aria-live="polite" className="contents">
    <span className="sr-only">{label}</span>
    {children}
  </div>
);

export default Skeleton;
