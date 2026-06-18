import React from 'react';

const variantMap = {
  default: { bg: 'var(--color-surface-2)', color: 'var(--color-text-secondary)', border: 'var(--color-border)' },
  success: { bg: 'var(--color-success-bg)', color: 'var(--color-success-text)', border: 'var(--color-success)' },
  error:   { bg: 'var(--color-error-bg)',   color: 'var(--color-error-text)',   border: 'var(--color-error)'   },
  warning: { bg: 'var(--color-warning-bg)', color: 'var(--color-warning-text)', border: 'var(--color-warning)' },
};

export default function Badge({ children, variant = 'default', dot = false, style = {} }) {
  const v = variantMap[variant] || variantMap.default;
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      padding: '2px 8px',
      fontSize: 'var(--font-size-xs)',
      fontWeight: '500',
      fontFamily: 'var(--font-sans)',
      borderRadius: 'var(--radius-full)',
      border: `1px solid ${v.border}`,
      background: v.bg,
      color: v.color,
      whiteSpace: 'nowrap',
      ...style,
    }}>
      {dot && (
        <span style={{
          display: 'inline-block', width: '6px', height: '6px',
          borderRadius: '50%', background: v.color, flexShrink: 0,
        }} />
      )}
      {children}
    </span>
  );
}
