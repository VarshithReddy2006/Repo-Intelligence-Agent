import React from 'react';

interface PageHeaderProps {
  icon?: React.ReactNode;
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

/**
 * Standardised page-level header — eyebrow + title + description + actions.
 * Use for every top-of-page heading instead of inline mark-up.
 */
export const PageHeader: React.FC<PageHeaderProps> = ({
  icon, eyebrow, title, description, actions, className = '',
}) => (
  <div className={`flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 border-b border-border pb-5 ${className}`}>
    <div className="min-w-0">
      {eyebrow && (
        <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-primary mb-1">
          {eyebrow}
        </div>
      )}
      <h1 className="text-2xl font-semibold text-text tracking-tight flex items-center gap-2.5">
        {icon && <span className="text-primary" aria-hidden="true">{icon}</span>}
        <span>{title}</span>
      </h1>
      {description && (
        <p className="text-sm text-text-muted mt-2 max-w-2xl leading-relaxed font-sans">
          {description}
        </p>
      )}
    </div>
    {actions && <div className="shrink-0 flex flex-wrap items-center gap-2">{actions}</div>}
  </div>
);

interface SectionHeaderProps {
  icon?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

/** In-card / in-section sub-header. */
export const SectionHeader: React.FC<SectionHeaderProps> = ({
  icon, title, description, actions, className = '',
}) => (
  <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${className}`}>
    <div className="min-w-0">
      <h2 className="text-sm font-semibold text-text flex items-center gap-2">
        {icon && <span className="text-primary" aria-hidden="true">{icon}</span>}
        <span>{title}</span>
      </h2>
      {description && (
        <p className="text-xs text-text-muted mt-1 font-sans leading-relaxed">{description}</p>
      )}
    </div>
    {actions && <div className="shrink-0 flex flex-wrap items-center gap-2">{actions}</div>}
  </div>
);

export default PageHeader;
