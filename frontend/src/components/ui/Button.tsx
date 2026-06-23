import React from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  /** When true, the button stretches to fill its container */
  block?: boolean;
  /** When true, shows a spinner and disables the button */
  loading?: boolean;
  /** Left icon */
  leadingIcon?: React.ReactNode;
  /** Right icon */
  trailingIcon?: React.ReactNode;
}

const base =
  'inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-all ' +
  'focus-visible:outline-none focus-visible:shadow-ring disabled:cursor-not-allowed select-none';

const sizes: Record<Size, string> = {
  sm: 'text-xs px-3 py-1.5',
  md: 'text-sm px-4 py-2',
  lg: 'text-sm px-5 py-2.5',
};

const variants: Record<Variant, string> = {
  primary:   'bg-primary text-text hover:bg-primary-hover disabled:bg-primary/40 shadow-card',
  secondary: 'bg-surface-2 text-text border border-border hover:border-border-strong hover:bg-surface-3 disabled:opacity-50',
  ghost:     'bg-transparent text-text-muted border border-border hover:text-text hover:border-primary/40 disabled:opacity-50',
  danger:    'bg-danger/10 text-danger border border-danger/30 hover:bg-danger/20 disabled:opacity-50',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>((
  {
    variant = 'primary',
    size = 'md',
    block,
    loading,
    leadingIcon,
    trailingIcon,
    className = '',
    children,
    disabled,
    ...rest
  },
  ref,
) => (
  <button
    ref={ref}
    disabled={disabled || loading}
    aria-busy={loading || undefined}
    className={[
      base,
      sizes[size],
      variants[variant],
      block ? 'w-full' : '',
      className,
    ].filter(Boolean).join(' ')}
    {...rest}
  >
    {loading
      ? <svg className="h-3.5 w-3.5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>
      : leadingIcon && <span className="shrink-0" aria-hidden="true">{leadingIcon}</span>
    }
    {children}
    {!loading && trailingIcon && <span className="shrink-0" aria-hidden="true">{trailingIcon}</span>}
  </button>
));
Button.displayName = 'Button';

export default Button;
