import React from 'react';

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  tone?: 'neutral' | 'success' | 'warn' | 'danger';
  className?: string;
  /** When true, renders without the outer card so it can sit inside another card */
  compact?: boolean;
}

const toneRing: Record<NonNullable<EmptyStateProps['tone']>, string> = {
  neutral: 'text-text-muted',
  success: 'text-success',
  warn:    'text-warn',
  danger:  'text-danger',
};

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon, title, description, action, tone = 'neutral', className = '', compact,
}) => {
  const body = (
    <>
      <div
        className={`h-12 w-12 rounded-full bg-surface-2 border border-border flex items-center justify-center ${toneRing[tone]}`}
        aria-hidden="true"
      >
        {icon}
      </div>
      <div className="space-y-1 max-w-md">
        <p className="text-sm font-semibold text-text">{title}</p>
        {description && (
          <p className="text-xs text-text-muted leading-relaxed font-sans">{description}</p>
        )}
      </div>
      {action && <div className="pt-1">{action}</div>}
    </>
  );

  if (compact) {
    return (
      <div className={`flex flex-col items-center justify-center gap-3 text-center py-8 ${className}`}>
        {body}
      </div>
    );
  }

  return (
    <div className={`card flex flex-col items-center justify-center gap-3 text-center py-12 px-6 ${className}`}>
      {body}
    </div>
  );
};

export default EmptyState;
