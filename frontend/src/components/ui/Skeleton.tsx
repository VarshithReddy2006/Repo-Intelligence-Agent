import React from 'react';

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: string;
  rounded?: 'sm' | 'md' | 'lg' | 'full';
}

const radiusMap = {
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  full: 'rounded-full',
} as const;

/** Base shimmer block. */
export const Skeleton: React.FC<SkeletonProps> = ({
  size = 'h-4 w-full',
  rounded = 'md',
  className = '',
  ...rest
}) => (
  <div
    className={`skeleton ${size} ${radiusMap[rounded]} ${className}`}
    aria-hidden="true"
    {...rest}
  />
);

/** Presets for common container components */

export const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`card p-5 space-y-4 ${className}`} aria-hidden="true">
    <Skeleton size="h-3 w-20" rounded="sm" />
    <Skeleton size="h-6 w-1/3" />
    <div className="space-y-2">
      <Skeleton size="h-3 w-full" />
      <Skeleton size="h-3 w-5/6" />
    </div>
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
  <div className="card p-5 flex flex-col items-center gap-4" aria-hidden="true">
    <Skeleton size="h-3 w-24" />
    <Skeleton size="h-32 w-32" rounded="full" className="my-2" />
    <Skeleton size="h-3.5 w-16" />
  </div>
);

/** Placeholder for a graph canvas while React Flow loads */
export const SkeletonGraph: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div
    className={`card w-full h-[400px] flex items-center justify-center bg-surface-1/40 ${className}`}
    aria-hidden="true"
  >
    <div className="flex flex-col items-center gap-4 w-full max-w-sm px-6">
      <Skeleton size="h-3 w-32" />
      <div className="flex gap-4 my-2">
        <Skeleton size="h-10 w-10" rounded="full" />
        <Skeleton size="h-10 w-10" rounded="full" />
        <Skeleton size="h-10 w-10" rounded="full" />
      </div>
      <div className="space-y-2 w-full">
        <Skeleton size="h-1 w-full" />
        <Skeleton size="h-1 w-2/3" className="mx-auto" />
      </div>
    </div>
  </div>
);

/** Chat message placeholder */
export const SkeletonChat: React.FC = () => (
  <div className="space-y-4 w-full p-4" aria-hidden="true">
    <div className="flex gap-3 max-w-[80%]">
      <Skeleton size="h-8 w-8" rounded="full" className="shrink-0" />
      <div className="space-y-2 w-full">
        <Skeleton size="h-3 w-16" />
        <Skeleton size="h-16 w-full" />
      </div>
    </div>
    <div className="flex gap-3 ml-auto flex-row-reverse max-w-[80%]">
      <Skeleton size="h-8 w-8" rounded="full" className="shrink-0" />
      <div className="space-y-2 w-full">
        <Skeleton size="h-3 w-12" className="ml-auto" />
        <Skeleton size="h-12 w-full" />
      </div>
    </div>
  </div>
);

/** Code Block placeholder */
export const SkeletonCodeBlock: React.FC = () => (
  <div className="border border-border rounded-xl bg-surface-1 p-4 space-y-3 w-full" aria-hidden="true">
    <div className="flex items-center justify-between pb-2 border-b border-border/60">
      <Skeleton size="h-3.5 w-16" />
      <Skeleton size="h-3.5 w-12" />
    </div>
    <div className="space-y-2 font-mono">
      <Skeleton size="h-3 w-3/4" />
      <Skeleton size="h-3 w-full" />
      <Skeleton size="h-3 w-2/3" />
      <Skeleton size="h-3 w-4/5" />
    </div>
  </div>
);

/** Dashboard layout placeholder */
export const SkeletonDashboard: React.FC = () => (
  <div className="space-y-6 w-full py-4 fade-up" aria-hidden="true">
    <div className="space-y-3">
      <Skeleton size="h-8 w-1/3" />
      <Skeleton size="h-4.5 w-1/4" />
    </div>
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
      {Array.from({ length: 5 }, (_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-4 card p-5 space-y-4">
        <Skeleton size="h-4.5 w-24" />
        {Array.from({ length: 7 }, (_, i) => (
          <Skeleton key={i} size="h-3.5 w-full" />
        ))}
      </div>
      <div className="lg:col-span-8 space-y-4">
        <Skeleton size="h-10 w-full" />
        <div className="card p-5 space-y-4">
          <Skeleton size="h-4.5 w-32" />
          <Skeleton size="h-32 w-full" />
        </div>
      </div>
    </div>
  </div>
);

/** Status wrapper for SR accessibility */
export const SkeletonGroup: React.FC<React.PropsWithChildren<{ label?: string }>> = ({
  children,
  label = 'Loading content',
}) => (
  <div role="status" aria-live="polite" className="contents">
    <span className="sr-only">{label}</span>
    {children}
  </div>
);

export default Skeleton;
