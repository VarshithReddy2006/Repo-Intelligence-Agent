import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Visual elevation variant */
  variant?: 'default' | 'flat' | 'subtle';
  /** Internal padding preset; falls back to none when `false` */
  padding?: 'sm' | 'md' | 'lg' | false;
  /** Adds a subtle hover lift */
  interactive?: boolean;
}

const paddingMap = { sm: 'p-3', md: 'p-5', lg: 'p-6' } as const;

const variantMap = {
  default: 'card',
  flat:    'card-flat',
  subtle:  'border border-border bg-canvas/40 rounded-lg',
};

export const Card: React.FC<CardProps> = ({
  variant = 'default',
  padding = 'md',
  interactive,
  className = '',
  children,
  ...rest
}) => (
  <div
    className={[
      variantMap[variant],
      padding ? paddingMap[padding] : '',
      interactive ? 'transition-all hover:border-primary/40 hover:-translate-y-0.5' : '',
      className,
    ].filter(Boolean).join(' ')}
    {...rest}
  >
    {children}
  </div>
);

interface CardHeaderProps {
  icon?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  icon, title, description, actions, className = '',
}) => (
  <div className={`flex items-start justify-between gap-4 ${className}`}>
    <div className="min-w-0">
      <h3 className="text-base font-semibold text-text flex items-center gap-2">
        {icon && <span className="text-primary" aria-hidden="true">{icon}</span>}
        <span>{title}</span>
      </h3>
      {description && (
        <p className="text-xs text-text-muted mt-1 font-sans leading-relaxed">{description}</p>
      )}
    </div>
    {actions && <div className="shrink-0">{actions}</div>}
  </div>
);

export default Card;
