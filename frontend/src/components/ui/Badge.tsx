import React from 'react';

type Tone = 'success' | 'warn' | 'danger' | 'info' | 'neutral' | 'primary';

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
  icon?: React.ReactNode;
}

const toneMap: Record<Tone, string> = {
  success: 'badge-success',
  warn:    'badge-warn',
  danger:  'badge-danger',
  info:    'badge-info',
  neutral: 'badge-neutral',
  primary: 'badge bg-primary/10 text-primary border-primary/30',
};

export const Badge: React.FC<BadgeProps> = ({
  tone = 'neutral', icon, className = '', children, ...rest
}) => (
  <span className={`${toneMap[tone]} ${className}`} {...rest}>
    {icon && <span aria-hidden="true">{icon}</span>}
    {children}
  </span>
);

export default Badge;
