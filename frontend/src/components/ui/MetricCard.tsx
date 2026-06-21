import React from 'react';

type Tone = 'primary' | 'success' | 'warn' | 'danger' | 'info' | 'neutral';

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  /** Small contextual suffix below the value (e.g. "+12 this PR", "2 cycles") */
  hint?: React.ReactNode;
  /** Optional Badge node — usually for trend or status */
  trailing?: React.ReactNode;
  tone?: Tone;
  /** When provided, makes the card a focusable button */
  onClick?: () => void;
  className?: string;
}

const toneIconClass: Record<Tone, string> = {
  primary: 'bg-primary/10 text-primary border-primary/30',
  success: 'bg-success/10 text-success border-success/30',
  warn:    'bg-warn/10 text-warn border-warn/30',
  danger:  'bg-danger/10 text-danger border-danger/30',
  info:    'bg-info/10 text-info border-info/30',
  neutral: 'bg-surface-2 text-text-muted border-border',
};

export const MetricCard: React.FC<MetricCardProps> = ({
  icon, label, value, hint, trailing, tone = 'primary', onClick, className = '',
}) => {
  const inner = (
    <>
      <div className={`p-2.5 border rounded-lg shrink-0 ${toneIconClass[tone]}`} aria-hidden="true">
        {icon}
      </div>
      <div className="min-w-0 flex-grow">
        <div className="text-[10px] uppercase tracking-wider font-mono font-semibold text-text-subtle">
          {label}
        </div>
        <div className="flex items-baseline gap-2 mt-1">
          <div className="text-2xl font-extrabold text-text tracking-tight font-mono leading-none">
            {value}
          </div>
          {trailing}
        </div>
        {hint && (
          <div className="text-[11px] text-text-muted mt-1 font-sans">{hint}</div>
        )}
      </div>
    </>
  );

  const baseCls = 'card p-4 flex items-center gap-3.5 transition-all';

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={`${baseCls} text-left w-full hover:border-primary/40 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:shadow-ring ${className}`}
      >
        {inner}
      </button>
    );
  }

  return <div className={`${baseCls} ${className}`}>{inner}</div>;
};

export default MetricCard;
